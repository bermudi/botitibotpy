"""
Main CLI implementation for Botitibot.
"""

import sys
import click
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from ..config import Config
from ..content.generator import ContentGenerator
from ..database.operations import DatabaseOperations
from ..scheduler.task_scheduler import TaskScheduler
from ..scheduler.queue_manager import QueueManager
from ..monitoring.system import SystemMonitoring
from ..social.twitter import TwitterClient
from ..social.bluesky import BlueskyClient

logger = logging.getLogger(__name__)

@click.group()
@click.option('--debug/--no-debug', default=False, help='Enable debug logging')
def main(debug: bool) -> None:
    """Botitibot CLI - Social Media Content Management and Automation"""
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=log_level)

@main.group()
def content():
    """Content management commands"""
    pass

@content.command()
@click.option('--prompt', '-p', required=True, help='Content generation prompt')
@click.option('--length', '-l', default='medium', type=click.Choice(['short', 'medium', 'long']))
@click.option('--tone', '-t', default='neutral', type=click.Choice(['casual', 'neutral', 'formal']))
def generate(prompt: str, length: str, tone: str) -> None:
    """Generate content manually using specified parameters"""
    try:
        generator = ContentGenerator()
        content = generator.generate_post(prompt, max_length=None, tone=tone)
        if content:
            click.echo(f"Generated content:\n{content}")
        else:
            click.echo("Failed to generate content", err=True)
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error generating content: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@content.command(name='list-sources')
def list_sources() -> None:
    """List available content sources"""
    try:
        generator = ContentGenerator()
        sources = generator.list_sources()
        if sources:
            click.echo("\nContent Sources:")
            for source in sources:
                click.echo(f"- {source}")
        else:
            click.echo("No content sources registered")
    except Exception as e:
        logger.error(f"Error listing sources: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@content.command(name='update-index')
@click.option('--dry-run', is_flag=True, help='Show what would be updated without making changes')
def update_index(dry_run: bool) -> None:
    """Update content source index"""
    try:
        generator = ContentGenerator()
        changes = generator.update_index(dry_run=dry_run)
        if changes:
            click.echo("\nIndex Changes:")
            for change in changes:
                click.echo(f"- {change}")
        else:
            click.echo("No changes to index")
    except Exception as e:
        logger.error(f"Error updating index: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@main.group()
def social():
    """Social media management commands"""
    pass

@social.command()
@click.argument('platform', type=click.Choice(['twitter', 'bluesky']))
def auth(platform: str) -> None:
    """Authenticate with a social media platform"""
    try:
        if platform == 'twitter':
            client = TwitterClient()
            click.echo("Successfully authenticated with twitter")
        elif platform == 'bluesky':
            client = BlueskyClient()
            click.echo("Successfully authenticated with bluesky")
    except Exception as e:
        logger.error(f"Error authenticating with {platform}: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@social.command()
@click.argument('platform', type=click.Choice(['twitter', 'bluesky']))
@click.argument('content')
@click.option('--schedule', '-s', help='Schedule post for future (format: YYYY-MM-DD HH:MM)')
def post(platform: str, content: str, schedule: Optional[str] = None) -> None:
    """Post content to a social media platform"""
    try:
        if schedule:
            try:
                schedule_time = datetime.strptime(schedule, "%Y-%m-%d %H:%M")
            except ValueError:
                click.echo("Invalid schedule format. Use YYYY-MM-DD HH:MM", err=True)
                sys.exit(1)
                
            queue = QueueManager()
            post_id = queue.schedule_post(platform, content, schedule_time)
            click.echo(f"Post scheduled with ID: {post_id}")
        else:
            if platform == 'twitter':
                client = TwitterClient()
                client.post(content)
                click.echo("Posted to Twitter successfully")
            elif platform == 'bluesky':
                client = BlueskyClient()
                client.post(content)
                click.echo("Posted to Bluesky successfully")
    except Exception as e:
        logger.error(f"Error posting to {platform}: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@social.command(name='list-scheduled')
def list_scheduled_posts() -> None:
    """List all scheduled posts"""
    try:
        queue = QueueManager()
        posts = queue.list_scheduled_posts()
        if posts:
            click.echo("\nScheduled Posts:")
            for post in posts:
                click.echo(f"ID: {post['id']}")
                click.echo(f"Platform: {post['platform']}")
                click.echo(f"Content: {post['content']}")
                click.echo(f"Schedule: {post['schedule']}\n")
        else:
            click.echo("No scheduled posts")
    except Exception as e:
        logger.error(f"Error listing scheduled posts: {e}")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@social.command()
@click.argument('post_id', type=int)
def cancel(post_id: int) -> None:
    """Cancel a scheduled post"""
    try:
        queue = QueueManager()
        if queue.cancel_post(post_id):
            click.echo(f"Cancelled post {post_id}")
        else:
            click.echo(f"Post {post_id} not found", err=True)
            sys.exit(1)
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
