"""
Main CLI implementation for Botitibot.
"""

import sys
import click
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional
from functools import update_wrapper
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..config import Config
from ..database import Base
from ..content.generator import ContentGenerator
from ..database.operations import DatabaseOperations
from ..scheduler.task_scheduler import TaskScheduler
from ..scheduler.queue_manager import QueueManager, Task, TaskPriority
from ..monitoring.system import SystemMonitoring
from ..social.twitter import TwitterClient
from ..social.bluesky import BlueskyClient

logger = logging.getLogger(__name__)

# Create database engine and session
engine = create_engine("sqlite:///data/social_bot.db")
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

def async_command(f):
    """Decorator to run async commands"""
    @click.pass_context
    def wrapper(ctx, *args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return update_wrapper(wrapper, f)

def get_client(platform: str):
    """Get the appropriate client for the specified platform."""
    try:
        if platform == 'twitter':
            from ..social.twitter import TwitterClient
            return TwitterClient()
        elif platform == 'bluesky':
            from ..social.bluesky import BlueskyClient
            return BlueskyClient()
        else:
            logger.error(f"Unsupported platform: {platform}")
            return None
    except Exception as e:
        logger.error(f"Error initializing {platform} client: {e}", exc_info=True)
        return None

@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging')
def main(debug):
    """Botitibot CLI"""
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

@main.group()
def content():
    """Content generation and management commands"""
    pass

@content.command()
@click.argument('prompt')
@click.option('--length', type=int, default=280, help='Maximum content length')
@click.option('--tone', type=click.Choice(['casual', 'professional', 'humorous']), default='casual', help='Content tone')
@click.option('--style', type=click.Choice(['tweet', 'thread', 'article']), default='tweet', help='Content style')
@click.option('--use-rag', is_flag=True, default=False, help='Use RAG for content generation')
def generate(prompt: str, length: int, tone: str, style: str, use_rag: bool):
    """Generate content using the specified parameters"""
    try:
        generator = ContentGenerator()
        
        if use_rag:
            # Load content sources and index for RAG
            if not generator.load_content_source("content_sources"):
                logger.error("Failed to load content sources")
                click.echo("Error: Failed to load content sources", err=True)
                sys.exit(1)
                
            # Load the index
            if not generator.load_index():
                logger.error("Failed to load index")
                click.echo("Error: Failed to load index", err=True)
                sys.exit(1)
            
            # Generate content with RAG
            content = generator.generate_post_withRAG(prompt, max_length=length, tone=tone, style=style)
        else:
            # Generate content without RAG
            content = generator.generate_post(prompt, max_length=length, tone=tone, style=style)
            
        if content:
            click.echo("\nGenerated Content:")
            click.echo(content)
        else:
            click.echo("Error: Failed to generate content", err=True)
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error generating content: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@content.command()
@click.argument('url')
def add_webpage(url: str):
    """Add a webpage as a content source"""
    try:
        generator = ContentGenerator()
        generator.load_webpage(url)
        click.echo(f"Successfully added webpage: {url}")
    except Exception as e:
        logger.error(f"Error adding webpage: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@content.command()
@click.argument('url')
def add_rss(url: str):
    """Add an RSS feed as a content source"""
    try:
        generator = ContentGenerator()
        generator.parse_rss_feed(url)
        click.echo(f"Successfully added RSS feed: {url}")
    except Exception as e:
        logger.error(f"Error adding RSS feed: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@content.command()
@click.argument('directory')
def add_directory(directory: str):
    """Add a directory of files as a content source"""
    try:
        generator = ContentGenerator()
        generator.load_content_source(directory)
        click.echo(f"Successfully added directory: {directory}")
    except Exception as e:
        logger.error(f"Error adding directory: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@content.command()
def list_sources():
    """List all content sources"""
    try:
        generator = ContentGenerator()
        sources = generator.list_sources()
        
        if not sources:
            click.echo("No content sources found")
            return
            
        click.echo("\nContent Sources:")
        for source in sources:
            click.echo(f"Type: {source['type']}")
            click.echo(f"Location: {source['location']}")
            click.echo(f"Last Updated: {source['last_updated']}")
            click.echo(f"Document Count: {source['document_count']}")
            click.echo("")
    except Exception as e:
        logger.error(f"Error listing content sources: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@content.command()
@click.argument('source_id')
def remove_source(source_id: str):
    """Remove a content source"""
    try:
        generator = ContentGenerator()
        if generator.remove_source(source_id):
            click.echo(f"Successfully removed source {source_id}")
        else:
            click.echo(f"Source {source_id} not found", err=True)
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error removing content source: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@content.command()
def update_index():
    """Update the content index"""
    try:
        generator = ContentGenerator()
        generator.update_index()
        click.echo("Content index updated successfully")
    except Exception as e:
        logger.error(f"Error updating content index: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@main.group()
def social():
    """Social media management commands"""
    pass

@social.command()
@click.argument('platform', type=click.Choice(['twitter', 'bluesky']))
@async_command
async def auth(platform):
    """Authenticate with a social media platform"""
    try:
        if platform == 'bluesky':
            with BlueskyClient() as client:
                if client.setup_auth():
                    click.echo("Successfully authenticated with bluesky")
                else:
                    click.echo("Failed to authenticate with bluesky", err=True)
                    sys.exit(1)
        elif platform == 'twitter':
            client = TwitterClient()
            if await client.setup_auth():
                click.echo("Successfully authenticated with Twitter")
                click.echo("\nCurrent status:")
                click.echo("  - Cookie file: ✓")
                click.echo("  - Authentication: ✓")
                try:
                    # Try to verify credentials by fetching the timeline
                    timeline = await client.get_timeline(limit=1)
                    if timeline:
                        click.echo("  - API access: ✓")
                    else:
                        click.echo("  - API access: ✗")
                        click.echo("\nWarning: Timeline fetch returned no data")
                except Exception as e:
                    click.echo("  - API access: ✗")
                    click.echo(f"\nWarning: Authenticated but API access failed: {str(e)}")
            else:
                click.echo("Failed to authenticate with Twitter", err=True)
                if not Config.TWITTER_USERNAME or not Config.TWITTER_PASSWORD:
                    click.echo("\nError: Twitter credentials not found in config")
                    click.echo("Please ensure TWITTER_USERNAME and TWITTER_PASSWORD are set in your .env file")
                sys.exit(1)
    except Exception as e:
        click.echo(f"Error authenticating with {platform}: {str(e)}", err=True)
        sys.exit(1)

@social.command(name='post')
@click.argument('platform', type=click.Choice(['twitter', 'bluesky']))
@click.argument('content')
@click.option('--schedule', type=str, help='Schedule the post for a specific time (format: YYYY-MM-DD HH:MM:SS)')
@click.option('--use-rag', is_flag=True, help='Use RAG for content generation')
@click.option('--tone', type=str, help='Tone for content generation')
@click.option('--style', type=str, help='Style for content generation')
@click.option('--length', type=str, help='Length for content generation')
@click.option('--keywords', type=str, help='Keywords for content generation')
@click.option('--hashtags', type=str, help='Hashtags for content generation')
@click.option('--emojis', type=str, help='Emojis for content generation')
@async_command
async def post(platform: str, content: str, schedule: Optional[str] = None, use_rag: bool = False, **kwargs):
    """Post content to a social media platform."""
    try:
        # Get the client for the specified platform
        client = get_client(platform)
        if not client:
            click.echo(f"Failed to initialize {platform} client")
            return

        # Ensure client is authenticated
        if platform == 'twitter':
            if not await client.setup_auth():
                click.echo("Failed to authenticate with Twitter")
                return

        # Extract generation kwargs
        generation_kwargs = {k: v for k, v in kwargs.items() if v is not None}

        # If schedule is provided, use the queue manager
        if schedule:
            try:
                scheduled_time = datetime.strptime(schedule, '%Y-%m-%d %H:%M:%S')
                queue_manager = QueueManager()
                queue_manager.add_task(
                    platform=platform,
                    task_type='post',
                    content=content,
                    scheduled_time=scheduled_time,
                    use_rag=use_rag,
                    generation_kwargs=generation_kwargs
                )
                click.echo(f"Post scheduled for {schedule}")
                return
            except ValueError:
                click.echo("Invalid schedule format. Use YYYY-MM-DD HH:MM:SS")
                return

        # Post directly if no schedule is provided
        if platform == 'bluesky':
            with client as bluesky_client:
                if bluesky_client.post_content(content, use_rag=use_rag, **generation_kwargs):
                    click.echo(f"Posted to {platform} successfully")
                else:
                    click.echo(f"Failed to post to {platform}")
        else:
            if await client.post_content(content, use_rag=use_rag, **generation_kwargs):
                click.echo(f"Posted to {platform} successfully")
            else:
                click.echo(f"Failed to post to {platform}")
    except Exception as e:
        logger.error(f"Error posting content: {e}", exc_info=True)
        click.echo(f"Error: {str(e)}")
        sys.exit(1)

@social.command(name='list-scheduled')
@async_command
async def list_scheduled_posts() -> None:
    """List all scheduled posts"""
    try:
        db = get_db()
        queue = QueueManager(db=db)
        await queue.start()
        try:
            status = await queue.get_queue_status()
            if status['queued_tasks'] > 0:
                click.echo("\nScheduled Posts:")
                for task in queue.task_queue:
                    click.echo(f"ID: {task.id}")
                    click.echo(f"Priority: {task.priority.name}")
                    click.echo(f"Created: {task.created_at}")
                    click.echo("")
            else:
                click.echo("No scheduled posts")
        finally:
            await queue.shutdown()
            db.close()
    except Exception as e:
        logger.error(f"Error listing scheduled posts: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@social.command()
@click.argument('post_id', type=str)
@async_command
async def cancel(post_id: str) -> None:
    """Cancel a scheduled post"""
    try:
        db = get_db()
        queue = QueueManager(db=db)
        await queue.start()
        try:
            if await queue.cancel_task(post_id):
                click.echo(f"Cancelled post {post_id}")
            else:
                click.echo(f"Post {post_id} not found", err=True)
                sys.exit(1)
        finally:
            await queue.shutdown()
            db.close()
    except Exception as e:
        logger.error(f"Error cancelling post: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@social.command()
@click.argument('platform', type=click.Choice(['twitter', 'bluesky']))
@click.argument('username')
@async_command
async def author_feed(platform: str, username: str) -> None:
    """Fetch posts from a specific author"""
    try:
        if platform == 'twitter':
            client = TwitterClient()
            posts = await client.get_author_feed(username)
        else:
            with BlueskyClient() as client:
                posts = client.get_author_feed(username)
        
        if not posts:
            click.echo("No posts found")
            return
            
        click.echo(f"\nPosts from {username}:")
        for post in posts.feed:
            click.echo(f"Content: {post.post.record.text}")
            click.echo(f"Posted at: {post.post.record.created_at}")
            click.echo(f"URI: {post.post.uri}")
            click.echo("")
    except Exception as e:
        logger.error(f"Error fetching author feed: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@social.command()
@click.argument('platform', type=click.Choice(['twitter', 'bluesky']))
@click.argument('post_id')
@click.argument('comment_text')
@async_command
async def comment(platform: str, post_id: str, comment_text: str) -> None:
    """Add a comment to a post"""
    try:
        if platform == 'twitter':
            client = TwitterClient()
            result = await client.reply_to_tweet(post_id, comment_text)
        else:
            with BlueskyClient() as client:
                result = client.reply_to_post(post_id, comment_text)
        
        if result:
            click.echo("Comment posted successfully")
        else:
            click.echo("Failed to post comment", err=True)
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error posting comment: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@social.command()
@click.argument('platform', type=click.Choice(['twitter', 'bluesky']))
@click.argument('post_id')
@async_command
async def view_comments(platform: str, post_id: str) -> None:
    """View comments on a post"""
    try:
        if platform == 'twitter':
            client = TwitterClient()
            comments = await client.get_tweet_thread(post_id)
        else:
            with BlueskyClient() as client:
                thread = client.get_post_thread(post_id)
                if not thread:
                    click.echo("Failed to fetch thread")
                    return
                
                # Display the original post
                click.echo("\nOriginal Post:")
                click.echo(f"Author: {thread.thread.post.author.display_name} (@{thread.thread.post.author.handle})")
                click.echo(f"Content: {thread.thread.post.record.text}")
                click.echo(f"Posted at: {thread.thread.post.record.created_at}")
                click.echo("")
                
                # Display replies
                if hasattr(thread.thread, 'replies') and thread.thread.replies:
                    click.echo("Replies:")
                    for reply in thread.thread.replies:
                        click.echo(f"Author: {reply.post.author.display_name} (@{reply.post.author.handle})")
                        click.echo(f"Content: {reply.post.record.text}")
                        click.echo(f"Posted at: {reply.post.record.created_at}")
                        click.echo("")
                else:
                    click.echo("No replies yet")
    except Exception as e:
        logger.error(f"Error fetching comments: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@social.command()
@click.argument('platform', type=click.Choice(['twitter', 'bluesky']))
@click.argument('post_id')
@async_command
async def like(platform: str, post_id: str) -> None:
    """Like a post"""
    try:
        if platform == 'twitter':
            client = TwitterClient()
            result = await client.like_tweet(post_id)
        else:
            with BlueskyClient() as client:
                result = await client.like_post(post_id)
        
        if result:
            click.echo("Post liked successfully")
        else:
            click.echo("Failed to like post", err=True)
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error liking post: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@social.command()
@click.argument('platform', type=click.Choice(['twitter', 'bluesky']))
@click.argument('post_id')
@async_command
async def engagement(platform: str, post_id: str) -> None:
    """View engagement metrics for a post"""
    try:
        db = get_db()
        db_ops = DatabaseOperations(db)
        metrics = await db_ops.get_post_metrics(post_id)
        
        if metrics:
            click.echo("\nEngagement Metrics:")
            click.echo(f"Likes: {metrics.likes}")
            click.echo(f"Replies: {metrics.replies}")
            click.echo(f"Reposts: {metrics.reposts}")
            click.echo(f"Views: {metrics.views}")
            click.echo(f"Engagement Rate: {metrics.engagement_rate}%")
            click.echo(f"Last Updated: {metrics.last_updated}")
        else:
            click.echo("No metrics found for this post")
    except Exception as e:
        logger.error(f"Error fetching engagement metrics: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@main.group()
def system():
    """System management commands"""
    pass

@system.command()
def status() -> None:
    """View system status and active tasks"""
    try:
        monitoring = SystemMonitoring()
        status = monitoring.get_current_status()
        click.echo("\nSystem Status:")
        click.echo(f"Scheduler: {'Running' if status['scheduler_running'] else 'Stopped'}")
        click.echo(f"Tasks queued: {status['tasks_queued']}")
        click.echo(f"CPU Usage: {status['cpu_percent']}%")
        click.echo(f"Memory Usage: {status['memory_percent']}%")
        click.echo(f"Disk Usage: {status['disk_usage_percent']}%")
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@system.command()
@async_command
async def start() -> None:
    """Start the task scheduler"""
    try:
        db = get_db()
        scheduler = TaskScheduler(db=db)
        await scheduler.start()
        click.echo("Scheduler started")
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@system.command()
@async_command
async def stop() -> None:
    """Stop the task scheduler"""
    try:
        db = get_db()
        scheduler = TaskScheduler(db=db)
        await scheduler.stop()
        click.echo("Scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@system.command()
def metrics() -> None:
    """View system metrics and performance data"""
    try:
        monitoring = SystemMonitoring()
        metrics = monitoring.get_metrics_summary()
        click.echo("\nSystem Metrics:")
        click.echo(f"Task Success Rate: {metrics['success_rate']}%")
        click.echo(f"Average Task Duration: {metrics['avg_task_duration']}s")
        click.echo(f"Error Rate: {metrics['error_rate']}%")
        click.echo("\nActive Alerts:")
        for alert in metrics['active_alerts']:
            click.echo(f"- {alert['message']} ({alert['severity']})")
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@system.command()
@click.argument('interval', type=int)
def set_check_interval(interval: int):
    """Set the interval (in minutes) for checking comments"""
    try:
        db = get_db()
        scheduler = TaskScheduler(db=db)
        scheduler.update_interval('reply_check', interval)
        click.echo(f"Comment check interval set to {interval} minutes")
    except Exception as e:
        logger.error(f"Error setting check interval: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@system.command()
@click.argument('platform', type=click.Choice(['twitter', 'bluesky']))
def platform_status(platform: str):
    """View status and rate limits for a platform"""
    try:
        if platform == 'twitter':
            client = TwitterClient()
            status = client.get_rate_limit_status()
        else:
            with BlueskyClient() as client:
                status = client.get_rate_limit_status()
        
        click.echo(f"\n{platform.title()} Status:")
        click.echo(f"Write Operations Remaining: {status['write_remaining']}")
        click.echo(f"Read Operations Remaining: {status['read_remaining']}")
        click.echo(f"Rate Limit Reset: {status['reset_time']}")
        if 'rate_limited_operations' in status:
            click.echo("\nRate Limited Operations:")
            for op in status['rate_limited_operations']:
                click.echo(f"- {op['operation']}: Reset in {op['reset_in']} seconds")
    except Exception as e:
        logger.error(f"Error getting platform status: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
