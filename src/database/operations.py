from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging

from . import models
from .models import Platform

logger = logging.getLogger("botitibot.database")

class DatabaseOperations:
    def __init__(self, db: Session):
        logger.info("Initializing database operations", extra={
            'context': {
                'component': 'database'
            }
        })
        self.db = db

    # Credentials operations
    def create_credentials(self, platform: Platform, username: str, auth_data: Dict[str, Any]) -> models.Credentials:
        """Create new credentials for a platform."""
        logger.debug("Creating new credentials", extra={
            'context': {
                'platform': platform.value,
                'username': username,
                'component': 'database.credentials'
            }
        })
        db_credentials = models.Credentials(
            platform=platform,
            username=username,
            auth_data=auth_data
        )
        self.db.add(db_credentials)
        self.db.commit()
        self.db.refresh(db_credentials)
        logger.info("Successfully created credentials", extra={
            'context': {
                'platform': platform.value,
                'username': username,
                'credentials_id': db_credentials.id,
                'component': 'database.credentials'
            }
        })
        return db_credentials

    def get_credentials(self, platform: Platform, username: str) -> Optional[models.Credentials]:
        """Get credentials for a platform and username."""
        logger.debug("Fetching credentials", extra={
            'context': {
                'platform': platform.value,
                'username': username,
                'component': 'database.credentials'
            }
        })
        credentials = self.db.query(models.Credentials).filter(
            models.Credentials.platform == platform,
            models.Credentials.username == username
        ).first()
        
        if credentials:
            logger.info("Found credentials", extra={
                'context': {
                    'platform': platform.value,
                    'username': username,
                    'credentials_id': credentials.id,
                    'component': 'database.credentials'
                }
            })
        else:
            logger.info("No credentials found", extra={
                'context': {
                    'platform': platform.value,
                    'username': username,
                    'component': 'database.credentials'
                }
            })
        return credentials

    def update_credentials(self, credentials_id: int, auth_data: Dict[str, Any]) -> Optional[models.Credentials]:
        """Update credentials auth data."""
        logger.debug("Updating credentials", extra={
            'context': {
                'credentials_id': credentials_id,
                'component': 'database.credentials'
            }
        })
        db_credentials = self.db.query(models.Credentials).filter(
            models.Credentials.id == credentials_id
        ).first()
        if db_credentials:
            db_credentials.auth_data = auth_data
            db_credentials.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(db_credentials)
            logger.info("Successfully updated credentials", extra={
                'context': {
                    'credentials_id': credentials_id,
                    'platform': db_credentials.platform.value,
                    'username': db_credentials.username,
                    'component': 'database.credentials'
                }
            })
        else:
            logger.warning("Credentials not found for update", extra={
                'context': {
                    'credentials_id': credentials_id,
                    'component': 'database.credentials'
                }
            })
        return db_credentials

    # Post operations
    def create_post(self, credentials_id: int, platform_post_id: str, content: str) -> models.Post:
        """Create a new post record."""
        logger.debug("Creating new post record", extra={
            'context': {
                'credentials_id': credentials_id,
                'platform_post_id': platform_post_id,
                'component': 'database.posts'
            }
        })
        db_post = models.Post(
            credentials_id=credentials_id,
            platform_post_id=platform_post_id,
            content=content
        )
        self.db.add(db_post)
        self.db.commit()
        self.db.refresh(db_post)
        logger.info("Successfully created post record", extra={
            'context': {
                'post_id': db_post.id,
                'platform_post_id': platform_post_id,
                'component': 'database.posts'
            }
        })
        return db_post

    def get_post(self, platform_post_id: str) -> Optional[models.Post]:
        """Get post by platform post ID."""
        logger.debug("Fetching post", extra={
            'context': {
                'platform_post_id': platform_post_id,
                'component': 'database.posts'
            }
        })
        post = self.db.query(models.Post).filter(
            models.Post.platform_post_id == platform_post_id
        ).first()
        
        if post:
            logger.info("Found post", extra={
                'context': {
                    'post_id': post.id,
                    'platform_post_id': platform_post_id,
                    'component': 'database.posts'
                }
            })
        else:
            logger.info("No post found", extra={
                'context': {
                    'platform_post_id': platform_post_id,
                    'component': 'database.posts'
                }
            })
        return post

    def get_recent_posts(self, hours: int = 24) -> List[models.Post]:
        """Get posts from the last N hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        logger.debug("Fetching recent posts", extra={
            'context': {
                'hours': hours,
                'cutoff': cutoff.isoformat(),
                'component': 'database.posts'
            }
        })
        posts = self.db.query(models.Post).filter(
            models.Post.created_at >= cutoff
        ).all()
        logger.info(f"Found {len(posts)} recent posts", extra={
            'context': {
                'post_count': len(posts),
                'hours': hours,
                'component': 'database.posts'
            }
        })
        return posts

    # Engagement metrics operations
    def update_post_metrics(self, post_id: int, metrics: Dict[str, int]) -> Optional[models.EngagementMetrics]:
        """Update or create engagement metrics for a post."""
        logger.debug("Updating post metrics", extra={
            'context': {
                'post_id': post_id,
                'metrics': metrics,
                'component': 'database.metrics'
            }
        })
        db_metrics = self.db.query(models.EngagementMetrics).filter(
            models.EngagementMetrics.post_id == post_id
        ).first()
        
        if db_metrics:
            # Update existing metrics
            for key, value in metrics.items():
                setattr(db_metrics, key, value)
            db_metrics.updated_at = datetime.utcnow()
            logger.info("Updated existing metrics", extra={
                'context': {
                    'post_id': post_id,
                    'metrics_id': db_metrics.id,
                    'component': 'database.metrics'
                }
            })
        else:
            # Create new metrics
            db_metrics = models.EngagementMetrics(post_id=post_id, **metrics)
            self.db.add(db_metrics)
            logger.info("Created new metrics", extra={
                'context': {
                    'post_id': post_id,
                    'metrics': metrics,
                    'component': 'database.metrics'
                }
            })
            
        self.db.commit()
        self.db.refresh(db_metrics)
        return db_metrics

    def get_post_metrics(self, post_id: int) -> Optional[models.EngagementMetrics]:
        """Get engagement metrics for a post."""
        logger.debug("Fetching post metrics", extra={
            'context': {
                'post_id': post_id,
                'component': 'database.metrics'
            }
        })
        metrics = self.db.query(models.EngagementMetrics).filter(
            models.EngagementMetrics.post_id == post_id
        ).first()
        
        if metrics:
            logger.info("Found metrics", extra={
                'context': {
                    'post_id': post_id,
                    'metrics_id': metrics.id,
                    'component': 'database.metrics'
                }
            })
        else:
            logger.info("No metrics found", extra={
                'context': {
                    'post_id': post_id,
                    'component': 'database.metrics'
                }
            })
        return metrics

    # Comment operations
    def create_comment(
        self,
        post_id: int,
        platform_comment_id: str,
        author_username: str,
        content: str
    ) -> models.Comment:
        """Create a new comment record."""
        logger.debug("Creating new comment record", extra={
            'context': {
                'post_id': post_id,
                'platform_comment_id': platform_comment_id,
                'author_username': author_username,
                'component': 'database.comments'
            }
        })
        db_comment = models.Comment(
            post_id=post_id,
            platform_comment_id=platform_comment_id,
            author_username=author_username,
            content=content
        )
        self.db.add(db_comment)
        self.db.commit()
        self.db.refresh(db_comment)
        logger.info("Successfully created comment record", extra={
            'context': {
                'comment_id': db_comment.id,
                'post_id': post_id,
                'platform_comment_id': platform_comment_id,
                'component': 'database.comments'
            }
        })
        return db_comment

    def get_unreplied_comments(self) -> List[models.Comment]:
        """Get all comments that haven't been replied to."""
        logger.debug("Fetching unreplied comments", extra={
            'context': {
                'component': 'database.comments'
            }
        })
        comments = self.db.query(models.Comment).filter(
            models.Comment.is_replied_to == False
        ).all()
        logger.info(f"Found {len(comments)} unreplied comments", extra={
            'context': {
                'comment_count': len(comments),
                'component': 'database.comments'
            }
        })
        return comments

    def mark_comment_replied(
        self,
        comment_id: int,
        reply_id: str,
        reply_content: str
    ) -> Optional[models.Comment]:
        """Mark a comment as replied to."""
        logger.debug("Marking comment as replied to", extra={
            'context': {
                'comment_id': comment_id,
                'reply_id': reply_id,
                'component': 'database.comments'
            }
        })
        db_comment = self.db.query(models.Comment).filter(
            models.Comment.id == comment_id
        ).first()
        if db_comment:
            db_comment.is_replied_to = True
            db_comment.our_reply_id = reply_id
            db_comment.our_reply_content = reply_content
            db_comment.replied_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(db_comment)
            logger.info("Successfully marked comment as replied to", extra={
                'context': {
                    'comment_id': comment_id,
                    'reply_id': reply_id,
                    'component': 'database.comments'
                }
            })
        else:
            logger.warning("Comment not found for reply", extra={
                'context': {
                    'comment_id': comment_id,
                    'component': 'database.comments'
                }
            })
        return db_comment