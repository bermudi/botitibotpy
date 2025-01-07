"""
Content management commands for Botitibot CLI.
"""

import click
import logging
from typing import Optional, List
from pathlib import Path

from ...content.generator import ContentGenerator
from ...database.operations import DatabaseOperations

logger = logging.getLogger(__name__)

@click.group()
def content():
    """Content management commands"""
    pass

@content.command()
@click.argument('source', type=click.Path(exists=True))
def add_source(source: str) -> None:
    """Add a content source (file or directory) to the system"""
    try:
        generator = ContentGenerator()
        generator.add_source(Path(source))
        click.echo(f"Successfully added content source: {source}")
    except Exception as e:
        logger.error(f"Error adding content source: {e}")
        click.echo(f"Error: {str(e)}", err=True)

@content.command()
def list_sources():
    """List all registered content sources"""
    try:
        generator = ContentGenerator()
        sources = generator.list_sources()
        if not sources:
            click.echo("No content sources registered")
            return
        
        click.echo("\nRegistered content sources:")
        for source in sources:
            click.echo(f"- {source}")
    except Exception as e:
        logger.error(f"Error listing content sources: {e}")
        click.echo(f"Error: {str(e)}", err=True)

@content.command()
@click.argument('source', type=click.Path(exists=True))
def remove_source(source: str) -> None:
    """Remove a content source from the system"""
    try:
        generator = ContentGenerator()
        generator.remove_source(Path(source))
        click.echo(f"Successfully removed content source: {source}")
    except Exception as e:
        logger.error(f"Error removing content source: {e}")
        click.echo(f"Error: {str(e)}", err=True)

@content.command()
@click.option('--dry-run/--no-dry-run', default=False, help='Perform a dry run without saving')
def update_index(dry_run: bool):
    """Update the content index with latest changes"""
    try:
        generator = ContentGenerator()
        changes = generator.update_index(dry_run=dry_run)
        if not changes:
            click.echo("No changes detected in content sources")
            return
        
        click.echo("\nContent index changes:")
        for change in changes:
            click.echo(f"- {change}")
    except Exception as e:
        logger.error(f"Error updating content index: {e}")
        click.echo(f"Error: {str(e)}", err=True)
