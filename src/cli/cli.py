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
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@system.command()
def start() -> None:
    """Start the task scheduler"""
    try:
        scheduler = TaskScheduler()
        scheduler.start()
        click.echo("Scheduler started")
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@system.command()
def stop() -> None:
    """Stop the task scheduler"""
    try:
        scheduler = TaskScheduler()
        scheduler.stop()
        click.echo("Scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
