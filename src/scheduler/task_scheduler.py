import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from dataclasses import dataclass
from .queue_manager import QueueManager, Task, TaskPriority
from ..database.operations import DatabaseOperations
from ..content.generator import ContentGenerator
from ..social.twitter import TwitterClient
from ..social.bluesky import BlueskyClient
from ..database.models import Platform, Post

logger = logging.getLogger(__name__)

@dataclass
class SchedulerConfig:
    content_generation_interval: int = 60  # minutes
    reply_check_interval: int = 5  # minutes
    metrics_update_interval: int = 10  # minutes
    max_concurrent_tasks: int = 5

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
        
        # Initialize components
        self.db_ops = DatabaseOperations(db)
        self.content_generator = ContentGenerator(log_level=log_level)
        self.twitter_client = TwitterClient(log_level=log_level)
        self.bluesky_client = BlueskyClient()
        
        # Initialize configuration
        self.config = config or SchedulerConfig()
        
        # Initialize queue manager
        self.queue_manager = QueueManager(max_concurrent_tasks=self.config.max_concurrent_tasks)
        
        # Track running tasks
        self.tasks: Dict[str, asyncio.Task] = {}
        
    async def start(self):
        """Start all scheduled tasks"""
        logger.info("Starting scheduled tasks")
        
        # Create tasks for each scheduled job
        self.tasks = {
            'content_generation': asyncio.create_task(self._schedule_content_generation()),
            'metrics_collection': asyncio.create_task(self._schedule_metrics_collection()),
            'reply_checking': asyncio.create_task(self._schedule_reply_checking())
        }
        
        # Wait for all tasks to complete
        await asyncio.gather(*self.tasks.values())
        
    async def stop(self):
        """Stop all running tasks"""
        logger.info("Stopping scheduled tasks")
        for task in self.tasks.values():
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        self.tasks.clear()
        
    def update_config(self, new_config: SchedulerConfig):
        """Update scheduler configuration
        
        Args:
            new_config: New configuration to apply
        """
        logger.info("Updating scheduler configuration")
        self.config = new_config
        self.queue_manager.max_concurrent_tasks = new_config.max_concurrent_tasks
        
    async def _schedule_content_generation(self):
        """Schedule periodic content generation and posting"""
        while True:
            try:
                logger.info("Starting content generation cycle")
                
                # Create content generation task
                task = Task(
                    id=f"content_gen_{datetime.now().timestamp()}",
                    priority=TaskPriority.HIGH,
                    created_at=datetime.now(),
                    coroutine=self._generate_and_post_content
                )
                
                await self.queue_manager.add_task(task)
                
            except Exception as e:
                logger.error(f"Error in content generation cycle: {str(e)}", exc_info=True)
                
            # Wait for next cycle
            await asyncio.sleep(self.config.content_generation_interval * 60)
            
    async def _schedule_reply_checking(self):
        """Schedule periodic checking and handling of replies"""
        while True:
            try:
                logger.info("Starting reply check cycle")
                
                # Create reply checking task
                task = Task(
                    id=f"reply_check_{datetime.now().timestamp()}",
                    priority=TaskPriority.MEDIUM,
                    created_at=datetime.now(),
                    coroutine=self._check_and_handle_replies
                )
                
                await self.queue_manager.add_task(task)
                
            except Exception as e:
                logger.error(f"Error in reply check cycle: {str(e)}", exc_info=True)
                
            # Wait for next cycle
            await asyncio.sleep(self.config.reply_check_interval * 60)
            
    async def _schedule_metrics_collection(self):
        """Schedule periodic collection of engagement metrics"""
        while True:
            try:
                logger.info("Starting metrics collection cycle")
                
                # Create metrics collection task
                task = Task(
                    id=f"metrics_{datetime.now().timestamp()}",
                    priority=TaskPriority.LOW,
                    created_at=datetime.now(),
                    coroutine=self._collect_all_metrics
                )
                
                await self.queue_manager.add_task(task)
                
            except Exception as e:
                logger.error(f"Error in metrics collection cycle: {str(e)}", exc_info=True)
                
            # Wait for next cycle
            await asyncio.sleep(self.config.metrics_update_interval * 60)
            
    async def _generate_and_post_content(self):
        """Generate and post content to all platforms"""
        # Generate content
        content = self.content_generator.generate_post(
            "Create an engaging social media post about technology trends",
            tone="professional",
            style="informative"
        )
        
        if content:
            # Post to Twitter
            twitter_post_id = await self._post_to_platform(
                Platform.TWITTER,
                content
            )
            
            # Post to Bluesky
            bluesky_post_id = await self._post_to_platform(
                Platform.BLUESKY,
                content
            )
            
            logger.info("Content generation and posting cycle completed")
            return {'twitter_id': twitter_post_id, 'bluesky_id': bluesky_post_id}
        else:
            logger.error("Failed to generate content")
            raise Exception("Content generation failed")
            
    async def _check_and_handle_replies(self):
        """Check for new replies and generate responses"""
        try:
            # Get recent posts
            posts = await self._get_recent_posts()
            
            for post in posts:
                # Convert dict to object if needed
                post_id = post.get('id') if isinstance(post, dict) else post.id
                platform = post.get('platform') if isinstance(post, dict) else post.platform
                
                # Get new comments
                if platform == Platform.TWITTER:
                    comments = await self.twitter_client.get_new_comments(post_id)
                elif platform == Platform.BLUESKY:
                    comments = await self.bluesky_client.get_new_comments(post_id)
                else:
                    continue

                # Process each comment
                for comment in comments:
                    try:
                        # Convert dict to object if needed
                        comment_content = comment.get('content') if isinstance(comment, dict) else comment.content
                        comment_id = comment.get('id') if isinstance(comment, dict) else comment.id
                        
                        # Generate and post reply
                        prompt = f"Generate a friendly and engaging reply to this comment: {comment_content}"
                        reply = await self.content_generator.generate_reply(prompt)
                        
                        if platform == Platform.TWITTER:
                            await self.twitter_client.post_reply(comment_id, reply)
                        elif platform == Platform.BLUESKY:
                            await self.bluesky_client.post_reply(comment_id, reply)
                            
                    except Exception as e:
                        logger.error(f"Error handling reply for comment {comment_id}: {str(e)}", exc_info=True)

        except Exception as e:
            logger.error(f"Error checking replies: {str(e)}", exc_info=True)
            
    async def _collect_all_metrics(self):
        """Collect metrics for all recent posts"""
        try:
            recent_posts = await self.db_ops.get_recent_posts(hours=24)
            for post in recent_posts:
                metrics = await self._collect_post_metrics(post)
                if metrics:
                    await self.db_ops.update_engagement_metrics(
                        post.id,
                        likes=metrics['likes'],
                        replies=metrics['replies'],
                        reposts=metrics['reposts'],
                        views=metrics.get('views', 0)
                    )
        except Exception as e:
            logger.error(f"Error collecting metrics: {str(e)}", exc_info=True)
            
    async def _post_to_platform(self, platform: Platform, content: str) -> Optional[str]:
        """Post content to a specific platform
        
        Returns:
            Optional[str]: The platform-specific post ID if successful
        """
        try:
            if platform == Platform.TWITTER:
                self.twitter_client.post_content(content)
            else:  # Bluesky
                self.bluesky_client.post_content(content)
                
            return "post_id"  # Replace with actual post ID from response
            
        except Exception as e:
            logger.error(f"Error posting to {platform.value}: {str(e)}")
            return None
            
    async def _reply_on_twitter(self, comment_id: str, content: str) -> Optional[str]:
        """Post a reply on Twitter"""
        try:
            self.twitter_client.reply_to_tweet(comment_id, content)
            return "reply_id"  # Replace with actual reply ID
        except Exception as e:
            logger.error(f"Error replying on Twitter: {str(e)}")
            return None
            
    async def _reply_on_bluesky(self, comment_id: str, content: str) -> Optional[str]:
        """Post a reply on Bluesky"""
        try:
            self.bluesky_client.reply_to_post(comment_id, content)
            return "reply_id"  # Replace with actual reply ID
        except Exception as e:
            logger.error(f"Error replying on Bluesky: {str(e)}")
            return None
            
    def _get_recent_posts(self) -> List[Post]:
        """Get posts from the last 24 hours"""
        return self.db_ops.get_recent_posts(hours=24)
        
    async def _collect_post_metrics(self, post):
        """Collect metrics for a single post"""
        try:
            # Convert dict to object if needed
            if isinstance(post, dict):
                post_id = post.get('id')
                platform = post.get('platform')
            else:
                post_id = post.id
                platform = post.platform

            if platform == Platform.TWITTER:
                metrics = await self.twitter_client.get_post_metrics(post_id)
            elif platform == Platform.BLUESKY:
                metrics = await self.bluesky_client.get_post_metrics(post_id)
            else:
                logger.warning(f"Unknown platform for post {post_id}")
                return None

            return metrics
        except Exception as e:
            logger.error(f"Error collecting metrics for post {post_id}: {str(e)}")
            return None