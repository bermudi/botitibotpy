import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from dataclasses import dataclass
from .queue_manager import QueueManager, Task, TaskPriority
from .exceptions import RateLimitError
from ..database.operations import DatabaseOperations
from ..content.generator import ContentGenerator
from ..social.twitter import TwitterClient
from ..social.bluesky import BlueskyClient
from ..database.models import Platform, Post

logger = logging.getLogger(__name__)

@dataclass
class PlatformConfig:
    enabled: bool = True
    retry_limit: int = 3
    rate_limit_window: int = 15 * 60  # 15 minutes in seconds
    max_requests_per_window: int = 100

@dataclass
class SchedulerConfig:
    content_generation_interval: int = 60  # minutes
    reply_check_interval: int = 5  # minutes
    metrics_update_interval: int = 10  # minutes
    max_concurrent_tasks: int = 5
    twitter: PlatformConfig = PlatformConfig()
    bluesky: PlatformConfig = PlatformConfig()

class TaskScheduler:
    def __init__(self, db: Session, config: Optional[SchedulerConfig] = None, log_level: int = logging.INFO):
        """Initialize the task scheduler
        
        Args:
            db: SQLAlchemy database session
            config: Scheduler configuration
            log_level: Logging level to use
        """
        # Configure logging
        logger.setLevel(log_level)
        logger.info("Initializing TaskScheduler", extra={
            'context': {
                'component': 'task_scheduler'
            }
        })
        
        # Initialize components
        self.db_ops = DatabaseOperations(db)
        self.content_generator = ContentGenerator(log_level=log_level)
        self.twitter_client = TwitterClient(log_level=log_level)
        self.bluesky_client = BlueskyClient()
        
        # Initialize configuration
        self.config = config or SchedulerConfig()
        
        # Initialize queue manager
        self.queue_manager = QueueManager(max_concurrent_tasks=self.config.max_concurrent_tasks, log_level=log_level)
        
        # Track running tasks and intervals
        self.tasks: Dict[str, asyncio.Task] = {}
        self.intervals: Dict[str, int] = {
            'content_generation': self.config.content_generation_interval,
            'reply_check': self.config.reply_check_interval,
            'metrics_update': self.config.metrics_update_interval
        }
        
        logger.debug("TaskScheduler initialized with intervals", extra={
            'context': {
                'intervals': self.intervals,
                'component': 'task_scheduler'
            }
        })

    def update_config(self, new_config: SchedulerConfig):
        """Update scheduler configuration"""
        logger.info("Updating scheduler configuration", extra={
            'context': {
                'old_intervals': self.intervals,
                'new_content_interval': new_config.content_generation_interval,
                'new_reply_interval': new_config.reply_check_interval,
                'new_metrics_interval': new_config.metrics_update_interval,
                'component': 'task_scheduler.update_config'
            }
        })
        self.config = new_config
        self.intervals.update({
            'content_generation': new_config.content_generation_interval,
            'reply_check': new_config.reply_check_interval,
            'metrics_update': new_config.metrics_update_interval
        })
        # Update queue manager's max concurrent tasks
        self.queue_manager.max_concurrent_tasks = new_config.max_concurrent_tasks

    def update_interval(self, task_type: str, minutes: int):
        """Update the interval for a specific task type"""
        if task_type not in self.intervals:
            logger.error("Invalid task type for interval update", extra={
                'context': {
                    'task_type': task_type,
                    'valid_types': list(self.intervals.keys()),
                    'component': 'task_scheduler.update_interval'
                }
            })
            raise ValueError(f"Invalid task type: {task_type}")
            
        logger.info("Updating task interval", extra={
            'context': {
                'task_type': task_type,
                'old_interval': self.intervals[task_type],
                'new_interval': minutes,
                'component': 'task_scheduler.update_interval'
            }
        })
        self.intervals[task_type] = minutes

    async def start(self):
        """Start all scheduled tasks"""
        logger.info("Starting scheduled tasks", extra={
            'context': {
                'task_types': list(self.intervals.keys()),
                'component': 'task_scheduler.start'
            }
        })
        
        # Create tasks for each scheduled job
        self.tasks = {
            'content_generation': asyncio.create_task(self._schedule_content_generation()),
            'metrics_collection': asyncio.create_task(self._schedule_metrics_collection()),
            'reply_checking': asyncio.create_task(self._schedule_reply_checking())
        }
        
        # Wait for all tasks to complete
        try:
            await asyncio.gather(*self.tasks.values())
        except Exception as e:
            logger.error("Error in scheduled tasks", exc_info=True, extra={
                'context': {
                    'error': str(e),
                    'component': 'task_scheduler.start'
                }
            })
            raise

    async def stop(self):
        """Stop all running tasks"""
        logger.info("Stopping all scheduled tasks", extra={
            'context': {
                'running_tasks': list(self.tasks.keys()),
                'component': 'task_scheduler.stop'
            }
        })
        
        # Make a copy first, so we don't mutate the dict while iterating
        tasks_to_cancel = list(self.tasks.values())
        
        # Cancel all tasks first
        for task in tasks_to_cancel:
            task.cancel()

        # Now await them to ensure they're properly cancelled
        for task in tasks_to_cancel:
            try:
                await task
            except asyncio.CancelledError:
                pass
                
        # Clear the dictionary only after all tasks are cancelled
        self.tasks.clear()

    async def _handle_platform_error(self, platform: str, error: Exception) -> bool:
        """Handle platform-specific errors
        
        Args:
            platform: Platform name (twitter or bluesky)
            error: Exception that occurred
            
        Returns:
            bool: True if error was handled, False otherwise
        """
        error_str = str(error).lower()
        logger.error(f"Platform error occurred", exc_info=True, extra={
            'context': {
                'platform': platform,
                'error_type': type(error).__name__,
                'error': error_str,
                'component': 'task_scheduler.handle_platform_error'
            }
        })
        
        # Handle rate limit errors
        if isinstance(error, RateLimitError):
            logger.warning("Rate limit hit", extra={
                'context': {
                    'platform': platform,
                    'operation_type': error.operation_type,
                    'backoff': error.backoff,
                    'component': 'task_scheduler.handle_platform_error'
                }
            })
            
            # Adjust intervals based on rate limit type
            if error.operation_type == "write":
                # Double the content generation interval temporarily
                self.intervals['content_generation'] = min(
                    self.intervals['content_generation'] * 2,
                    120  # Cap at 2 hours
                )
            elif error.operation_type == "read":
                # Double the check intervals temporarily
                self.intervals['reply_check'] = min(
                    self.intervals['reply_check'] * 2,
                    30  # Cap at 30 minutes
                )
                self.intervals['metrics_update'] = min(
                    self.intervals['metrics_update'] * 2,
                    60  # Cap at 1 hour
                )
                
            logger.info("Adjusted task intervals due to rate limit", extra={
                'context': {
                    'new_intervals': self.intervals,
                    'component': 'task_scheduler.handle_platform_error'
                }
            })
            return True
            
        # Handle unauthorized errors
        if "unauthorized" in error_str:
            logger.error("Unauthorized access", extra={
                'context': {
                    'platform': platform,
                    'component': 'task_scheduler.handle_platform_error'
                }
            })
            # Disable the platform only for unauthorized errors
            if platform == 'twitter':
                self.config.twitter.enabled = False
            elif platform == 'bluesky':
                self.config.bluesky.enabled = False
            return True
            
        # Handle not found errors
        if "not found" in error_str:
            logger.warning("Resource not found", extra={
                'context': {
                    'platform': platform,
                    'component': 'task_scheduler.handle_platform_error'
                }
            })
            return True
            
        # Unknown errors should not disable the platform
        return False

    async def _schedule_content_generation(self):
        """Schedule periodic content generation and posting"""
        logger.info("Starting content generation scheduler", extra={
            'context': {
                'interval_minutes': self.intervals['content_generation'],
                'component': 'task_scheduler.schedule_content_generation'
            }
        })
        
        while True:
            try:
                # Check if we're rate limited for write operations
                if self.queue_manager.is_rate_limited("write"):
                    delay = self.queue_manager.get_rate_limit_delay("write")
                    logger.warning("Write operations rate limited, skipping content generation", extra={
                        'context': {
                            'delay': delay,
                            'component': 'task_scheduler.schedule_content_generation'
                        }
                    })
                    await asyncio.sleep(min(delay, self.intervals['content_generation'] * 60))
                    continue
                
                await self._generate_and_post_content()
                
                # If successful, gradually reduce the interval back to normal
                if self.intervals['content_generation'] > self.config.content_generation_interval:
                    self.intervals['content_generation'] = max(
                        self.config.content_generation_interval,
                        self.intervals['content_generation'] // 2
                    )
                    
            except Exception as e:
                logger.error("Error in content generation cycle", exc_info=True, extra={
                    'context': {
                        'error': str(e),
                        'component': 'task_scheduler.schedule_content_generation'
                    }
                })
            
            await asyncio.sleep(self.intervals['content_generation'] * 60)

    async def _schedule_reply_checking(self):
        """Schedule periodic checking and handling of replies"""
        logger.info("Starting reply checking scheduler", extra={
            'context': {
                'interval_minutes': self.intervals['reply_check'],
                'component': 'task_scheduler.schedule_reply_checking'
            }
        })
        
        while True:
            try:
                # Check if we're rate limited for read operations
                if self.queue_manager.is_rate_limited("read"):
                    delay = self.queue_manager.get_rate_limit_delay("read")
                    logger.warning("Read operations rate limited, skipping reply check", extra={
                        'context': {
                            'delay': delay,
                            'component': 'task_scheduler.schedule_reply_checking'
                        }
                    })
                    await asyncio.sleep(min(delay, self.intervals['reply_check'] * 60))
                    continue
                
                await self._check_and_handle_replies()
                
                # If successful, gradually reduce the interval back to normal
                if self.intervals['reply_check'] > self.config.reply_check_interval:
                    self.intervals['reply_check'] = max(
                        self.config.reply_check_interval,
                        self.intervals['reply_check'] // 2
                    )
                    
            except Exception as e:
                logger.error("Error in reply checking cycle", exc_info=True, extra={
                    'context': {
                        'error': str(e),
                        'component': 'task_scheduler.schedule_reply_checking'
                    }
                })
            
            await asyncio.sleep(self.intervals['reply_check'] * 60)

    async def _schedule_metrics_collection(self):
        """Schedule periodic collection of engagement metrics"""
        logger.info("Starting metrics collection scheduler", extra={
            'context': {
                'interval_minutes': self.intervals['metrics_update'],
                'component': 'task_scheduler.schedule_metrics_collection'
            }
        })
        
        while True:
            try:
                # Check if we're rate limited for read operations
                if self.queue_manager.is_rate_limited("read"):
                    delay = self.queue_manager.get_rate_limit_delay("read")
                    logger.warning("Read operations rate limited, skipping metrics collection", extra={
                        'context': {
                            'delay': delay,
                            'component': 'task_scheduler.schedule_metrics_collection'
                        }
                    })
                    await asyncio.sleep(min(delay, self.intervals['metrics_update'] * 60))
                    continue
                
                # Get recent posts from the last 24 hours
                posts = await self.db_ops.get_recent_posts(hours=24)
                logger.info("Retrieved recent posts", extra={
                    'context': {
                        'post_count': len(posts),
                        'component': 'task_scheduler.schedule_metrics_collection'
                    }
                })
                
                # Collect metrics for each post
                for post in posts:
                    await self._collect_post_metrics(post)
                    
                # If successful, gradually reduce the interval back to normal
                if self.intervals['metrics_update'] > self.config.metrics_update_interval:
                    self.intervals['metrics_update'] = max(
                        self.config.metrics_update_interval,
                        self.intervals['metrics_update'] // 2
                    )
                    
            except Exception as e:
                logger.error("Error in metrics collection cycle", exc_info=True, extra={
                    'context': {
                        'error': str(e),
                        'component': 'task_scheduler.schedule_metrics_collection'
                    }
                })
            
            await asyncio.sleep(self.intervals['metrics_update'] * 60)

    async def _generate_and_post_content(self):
        """Generate and post content to all platforms"""
        logger.debug("Starting content generation cycle", extra={
            'context': {
                'component': 'task_scheduler.generate_and_post_content'
            }
        })
        
        content = await self.content_generator.generate_post()
        if not content:
            logger.warning("No content generated", extra={
                'context': {
                    'component': 'task_scheduler.generate_and_post_content'
                }
            })
            return
            
        logger.info("Content generated successfully", extra={
            'context': {
                'content_length': len(content),
                'component': 'task_scheduler.generate_and_post_content'
            }
        })
        
        # Post to each platform
        post_ids = {}
        for platform in [Platform.TWITTER, Platform.BLUESKY]:
            try:
                post_id = await self._post_to_platform(platform, content)
                if post_id:
                    post_ids[platform] = post_id
            except Exception as e:
                if not await self._handle_platform_error(platform.name.lower(), e):
                    raise
                    
        return post_ids

    async def _check_and_handle_replies(self):
        """Check for new replies and generate responses"""
        logger.debug("Starting reply check cycle", extra={
            'context': {
                'component': 'task_scheduler.check_and_handle_replies'
            }
        })
        
        # Get recent posts
        recent_posts = await self._get_recent_posts()
        logger.info("Retrieved recent posts", extra={
            'context': {
                'post_count': len(recent_posts),
                'component': 'task_scheduler.check_and_handle_replies'
            }
        })
        
        for post in recent_posts:
            try:
                # Get replies for each platform
                if post.platform == Platform.TWITTER:
                    replies = await self.twitter_client.get_tweet_thread(post.platform_id)
                else:
                    replies = await self.bluesky_client.get_post_thread(post.platform_id)
                    
                logger.debug("Retrieved replies for post", extra={
                    'context': {
                        'post_id': post.id,
                        'platform': post.platform.name,
                        'reply_count': len(replies),
                        'component': 'task_scheduler.check_and_handle_replies'
                    }
                })
                
                # Handle each reply
                for reply in replies:
                    # Generate response
                    response = await self.content_generator.generate_reply(reply.text)
                    if not response:
                        continue
                        
                    # Post response
                    if post.platform == Platform.TWITTER:
                        await self._reply_on_twitter(reply.id, response)
                    else:
                        await self._reply_on_bluesky(reply.id, response)
                        
            except Exception as e:
                logger.error("Error handling replies for post", exc_info=True, extra={
                    'context': {
                        'post_id': post.id,
                        'platform': post.platform.name,
                        'error': str(e),
                        'component': 'task_scheduler.check_and_handle_replies'
                    }
                })

    async def _collect_all_metrics(self):
        """Collect metrics for all recent posts"""
        logger.debug("Starting metrics collection cycle", extra={
            'context': {
                'component': 'task_scheduler.collect_all_metrics'
            }
        })
        
        recent_posts = await self._get_recent_posts()
        logger.info("Retrieved posts for metrics collection", extra={
            'context': {
                'post_count': len(recent_posts),
                'component': 'task_scheduler.collect_all_metrics'
            }
        })
        
        for post in recent_posts:
            try:
                await self._collect_post_metrics(post)
            except Exception as e:
                logger.error("Error collecting metrics for post", exc_info=True, extra={
                    'context': {
                        'post_id': post.id,
                        'platform': post.platform.name,
                        'error': str(e),
                        'component': 'task_scheduler.collect_all_metrics'
                    }
                })

    async def _collect_post_metrics(self, post):
        """Collect metrics for a single post"""
        logger.debug("Collecting metrics for post", extra={
            'context': {
                'post_id': post.id,
                'platform': post.platform.name,
                'component': 'task_scheduler.collect_post_metrics'
            }
        })
        
        try:
            if post.platform == Platform.TWITTER:
                metrics = await self.twitter_client.get_tweet_metrics(post.platform_id)
            else:
                metrics = await self.bluesky_client.get_post_metrics(post.platform_id)
                
            # Update database
            await self.db_ops.update_post_metrics(post.id, metrics)
            
            logger.info("Successfully updated post metrics", extra={
                'context': {
                    'post_id': post.id,
                    'platform': post.platform.name,
                    'metrics': metrics,
                    'component': 'task_scheduler.collect_post_metrics'
                }
            })
            
        except Exception as e:
            logger.error("Failed to collect metrics for post", exc_info=True, extra={
                'context': {
                    'post_id': post.id,
                    'platform': post.platform.name,
                    'error': str(e),
                    'component': 'task_scheduler.collect_post_metrics'
                }
            })
            raise

    async def _post_to_platform(self, platform: Platform, content: str) -> Optional[str]:
        """Post content to a specific platform"""
        logger.debug("Posting content to platform", extra={
            'context': {
                'platform': platform.name,
                'content_length': len(content),
                'component': 'task_scheduler.post_to_platform'
            }
        })
        
        try:
            if platform == Platform.TWITTER:
                post_id = await self.twitter_client.post_content(content)
            else:
                post_id = await self.bluesky_client.post_content(content)
                
            if post_id:
                # Save to database
                await self.db_ops.create_post(platform, post_id, content)
                
                logger.info("Successfully posted content", extra={
                    'context': {
                        'platform': platform.name,
                        'post_id': post_id,
                        'component': 'task_scheduler.post_to_platform'
                    }
                })
                
            return post_id
            
        except Exception as e:
            logger.error("Failed to post content", exc_info=True, extra={
                'context': {
                    'platform': platform.name,
                    'error': str(e),
                    'component': 'task_scheduler.post_to_platform'
                }
            })
            raise

    async def _get_recent_posts(self):
        """Get posts from the last 24 hours"""
        logger.debug("Retrieving recent posts", extra={
            'context': {
                'time_window': '24h',
                'component': 'task_scheduler.get_recent_posts'
            }
        })
        
        try:
            posts = await self.db_ops.get_posts_since(
                datetime.now() - timedelta(hours=24)
            )
            
            logger.info("Retrieved recent posts", extra={
                'context': {
                    'post_count': len(posts),
                    'component': 'task_scheduler.get_recent_posts'
                }
            })
            
            return posts
            
        except Exception as e:
            logger.error("Failed to retrieve recent posts", exc_info=True, extra={
                'context': {
                    'error': str(e),
                    'component': 'task_scheduler.get_recent_posts'
                }
            })
            raise