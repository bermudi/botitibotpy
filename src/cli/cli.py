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
def generate(prompt: str, length: int, tone: str, style: str):
    """Generate content using the specified parameters"""
    try:
        generator = ContentGenerator()
        content = generator.generate_post(prompt, max_length=length, tone=tone, style=style)
        click.echo("\nGenerated Content:")
        click.echo(content)
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

@main.group()
def social():
    """Social media management commands"""
    pass

@social.command()
@click.argument('platform', type=click.Choice(['twitter', 'bluesky']))
def auth(platform):
    """Authenticate with a social media platform"""
    try:
        if platform == 'bluesky':
            with BlueskyClient() as client:
                if client.setup_auth():
                    click.echo("Successfully authenticated with bluesky")
                else:
                    click.echo("Failed to authenticate with bluesky")
        elif platform == 'twitter':
            with TwitterClient() as client:
                if client.setup_auth():
                    click.echo("Successfully authenticated with twitter")
                else:
                    click.echo("Failed to authenticate with twitter")
    except Exception as e:
        click.echo(f"Error authenticating with {platform}: {str(e)}")
        sys.exit(1)

@social.command(name='post')
@click.argument('platform', type=click.Choice(['twitter', 'bluesky']))
@click.argument('content')
@click.option('--schedule', '-s', help='Schedule post for future (format: YYYY-MM-DD HH:MM)')
@async_command
async def post(platform: str, content: str, schedule: Optional[str] = None) -> None:
    """Post content to a social media platform"""
    try:
        if schedule:
            try:
                schedule_time = datetime.strptime(schedule, "%Y-%m-%d %H:%M")
            except ValueError:
                click.echo("Invalid schedule format. Use YYYY-MM-DD HH:MM", err=True)
                sys.exit(1)
                
            db = get_db()
            queue = QueueManager(db=db)
            await queue.start()
            try:
                if platform == 'twitter':
                    client = TwitterClient()
                    task = Task(
                        id=f"post_{datetime.now().timestamp()}",
                        priority=TaskPriority.MEDIUM,
                        created_at=datetime.now(),
                        coroutine=client.post_content,
                        args=(content,)
                    )
                else:
                    client = BlueskyClient()
                    task = Task(
                        id=f"post_{datetime.now().timestamp()}",
                        priority=TaskPriority.MEDIUM,
                        created_at=datetime.now(),
                        coroutine=client.post_content,
                        args=(content,)
                    )
                post_id = await queue.add_task(task, scheduled_time=schedule_time)
                click.echo(f"Post scheduled with ID: {post_id}")
            finally:
                await queue.shutdown()
                db.close()
        else:
            if platform == 'twitter':
                client = TwitterClient()
                client.post_content(content)
                click.echo("Posted to Twitter successfully")
            elif platform == 'bluesky':
                with BlueskyClient() as client:
                    result = client.post_content(content)
                    if result:
                        click.echo("Posted to Bluesky successfully")
                    else:
                        click.echo("Failed to post to Bluesky", err=True)
                        sys.exit(1)
    except Exception as e:
        logger.error(f"Error posting to {platform}: {e}")
        click.echo(f"Error: {str(e)}", err=True)
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
@async_command
async def timeline(platform: str) -> None:
    """View recent posts from your timeline"""
    try:
        if platform == 'twitter':
            client = TwitterClient()
            posts = await client.get_timeline()
        else:
            with BlueskyClient() as client:
                posts = await client.get_timeline()
        
        click.echo("\nRecent Posts:")
        for post in posts:
            click.echo(f"Author: {post.author}")
            click.echo(f"Content: {post.content}")
            click.echo(f"Engagement: {post.engagement_metrics}")
            click.echo("")
    except Exception as e:
        logger.error(f"Error fetching timeline: {e}")
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


@main.group()
def content_management():
    """Content management commands"""
    pass

@content_management.command()
def list_content_sources():
    """List all content sources"""
    # TODO: Implement list content sources
    pass

@content_management.command()
def remove_content_source():
    """Remove a content source"""
    # TODO: Implement remove content source
    pass

if __name__ == '__main__':
    main()
