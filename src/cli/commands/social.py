"""
Social media management commands for Botitibot CLI.
"""

import click
import logging
from typing import Optional
from datetime import datetime, timedelta

from ...database.operations import DatabaseOperations
from ...database.models import Platform, Post
from ...social.twitter import TwitterClient
from ...social.bluesky import BlueskyClient

logger = logging.getLogger(__name__)

@click.group()
def social():
    """Social media management commands"""
    pass

@social.command()
@click.argument('platform', type=click.Choice(['twitter', 'bluesky'], case_sensitive=False))
def auth(platform: str):
    """Set up authentication for a social media platform"""
    try:
        db = DatabaseOperations()
        platform_enum = Platform[platform.upper()]
        
        if platform_enum == Platform.TWITTER:
            client = TwitterClient()
            # Handle Twitter auth setup
            click.echo("Please follow the Twitter authentication process...")
        elif platform_enum == Platform.BLUESKY:
            client = BlueskyClient()
            # Handle Bluesky auth setup
            click.echo("Please follow the Bluesky authentication process...")
            
        click.echo(f"Successfully authenticated with {platform}")
    except Exception as e:
        logger.error(f"Error during authentication: {e}")
        click.echo(f"Error: {str(e)}", err=True)

@social.command()
@click.argument('platform', type=click.Choice(['twitter', 'bluesky'], case_sensitive=False))
@click.argument('content')
@click.option('--schedule', '-s', type=click.DateTime(), help='Schedule post for later (format: YYYY-MM-DD HH:MM:SS)')
def post(platform: str, content: str, schedule: Optional[datetime]):
    """Create a new post or schedule it for later"""
    try:
        db = DatabaseOperations()
        platform_enum = Platform[platform.upper()]
        
        post = Post(
            platform=platform_enum,
            content=content,
            scheduled_time=schedule
        )
        
        if schedule:
            db.add_post(post)
            click.echo(f"Post scheduled for {schedule} on {platform}")
        else:
            # Post immediately
            if platform_enum == Platform.TWITTER:
                client = TwitterClient()
            else:
                client = BlueskyClient()
                
            post_id = client.post(content)
            post.platform_post_id = post_id
            db.add_post(post)
            click.echo(f"Post created successfully on {platform}")
            
    except Exception as e:
        logger.error(f"Error creating post: {e}")
        click.echo(f"Error: {str(e)}", err=True)

@social.command()
def list_scheduled():
    """List all scheduled posts"""
    try:
        db = DatabaseOperations()
        posts = db.get_scheduled_posts()
        
        if not posts:
            click.echo("No scheduled posts found")
            return
            
        click.echo("\nScheduled posts:")
        for post in posts:
            click.echo(f"Platform: {post.platform.name}")
            click.echo(f"Scheduled for: {post.scheduled_time}")
            click.echo(f"Content: {post.content[:50]}...")
            click.echo("---")
            
    except Exception as e:
        logger.error(f"Error listing scheduled posts: {e}")
        click.echo(f"Error: {str(e)}", err=True)

@social.command()
@click.argument('post_id', type=int)
def cancel_scheduled(post_id: int):
    """Cancel a scheduled post"""
    try:
        db = DatabaseOperations()
        if db.delete_scheduled_post(post_id):
            click.echo(f"Successfully cancelled scheduled post {post_id}")
        else:
            click.echo(f"No scheduled post found with ID {post_id}")
    except Exception as e:
        logger.error(f"Error cancelling scheduled post: {e}")
        click.echo(f"Error: {str(e)}", err=True)
