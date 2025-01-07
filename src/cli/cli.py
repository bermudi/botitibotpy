"""
Main CLI implementation for Botitibot.
"""

import click
import logging
from pathlib import Path
from typing import Optional

from ..config import Config
from ..content.generator import ContentGenerator
from ..database.operations import DatabaseOperations
from ..scheduler.task_scheduler import TaskScheduler
from ..scheduler.queue_manager import QueueManager
from ..monitoring import MonitoringSystem

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
        content = generator.generate(prompt, length=length, tone=tone)
        click.echo(f"Generated content:\n{content}")
    except Exception as e:
        logger.error(f"Error generating content: {e}")
        click.echo(f"Error: {str(e)}", err=True)

@main.group()
def system():
    """System management commands"""
    pass

@system.command()
def status():
    """View system status and active tasks"""
    try:
        monitoring = MonitoringSystem()
        status = monitoring.get_current_status()
        click.echo("\nSystem Status:")
        click.echo(f"CPU Usage: {status['cpu_usage']}%")
        click.echo(f"Memory Usage: {status['memory_usage']}%")
        click.echo(f"Disk Usage: {status['disk_usage']}%")
        click.echo(f"\nActive Tasks: {status['active_tasks']}")
        click.echo(f"Task Queue Size: {status['queue_size']}")
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        click.echo(f"Error: {str(e)}", err=True)

@system.command()
def start():
    """Start the task scheduler"""
    try:
        scheduler = TaskScheduler()
        scheduler.start()
        click.echo("Task scheduler started successfully")
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        click.echo(f"Error: {str(e)}", err=True)

@system.command()
def stop():
    """Stop the task scheduler"""
    try:
        scheduler = TaskScheduler()
        scheduler.stop()
        click.echo("Task scheduler stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
        click.echo(f"Error: {str(e)}", err=True)

if __name__ == '__main__':
    main()
