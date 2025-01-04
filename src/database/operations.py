from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from . import models
from .models import Platform

class DatabaseOperations:
    def __init__(self, db: Session):
        self.db = db

    # Credentials operations
    def create_credentials(self, platform: Platform, username: str, auth_data: Dict[str, Any]) -> models.Credentials:
        """Create new credentials for a platform."""
        db_credentials = models.Credentials(
            platform=platform,
            username=username,
            auth_data=auth_data
        )
        self.db.add(db_credentials)
        self.db.commit()
        self.db.refresh(db_credentials)
        return db_credentials

    def get_credentials(self, platform: Platform, username: str) -> Optional[models.Credentials]:
        """Get credentials for a platform and username."""
        return self.db.query(models.Credentials).filter(
            models.Credentials.platform == platform,
            models.Credentials.username == username
        ).first()

    def update_credentials(self, credentials_id: int, auth_data: Dict[str, Any]) -> Optional[models.Credentials]:
        """Update credentials auth data."""
        db_credentials = self.db.query(models.Credentials).filter(
            models.Credentials.id == credentials_id
        ).first()
        if db_credentials:
            db_credentials.auth_data = auth_data
            db_credentials.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(db_credentials)
        return db_credentials

    # Post operations
    def create_post(self, credentials_id: int, platform_post_id: str, content: str) -> models.Post:
        """Create a new post record."""
        db_post = models.Post(
            credentials_id=credentials_id,
            platform_post_id=platform_post_id,
            content=content
        )
        self.db.add(db_post)
        self.db.commit()
        self.db.refresh(db_post)
        return db_post

    def get_post(self, platform_post_id: str) -> Optional[models.Post]:
        """Get post by platform post ID."""
        return self.db.query(models.Post).filter(
            models.Post.platform_post_id == platform_post_id
        ).first()

    # Engagement metrics operations
    def update_engagement_metrics(
        self, 
        post_id: int, 
        likes: int, 
        replies: int, 
        reposts: int,
        views: int
    ) -> models.EngagementMetrics:
        """Update engagement metrics for a post."""
        db_metrics = self.db.query(models.EngagementMetrics).filter(
            models.EngagementMetrics.post_id == post_id
        ).first()

        if not db_metrics:
            db_metrics = models.EngagementMetrics(post_id=post_id)
            self.db.add(db_metrics)

        total_engagement = likes + replies + reposts
        total_reach = views if views > 0 else 1
        engagement_rate = (total_engagement / total_reach) * 100

        db_metrics.likes = likes
        db_metrics.replies = replies
        db_metrics.reposts = reposts
        db_metrics.views = views
        db_metrics.engagement_rate = engagement_rate
        db_metrics.last_updated = datetime.utcnow()

        self.db.commit()
        self.db.refresh(db_metrics)
        return db_metrics

    # Comment operations
    def create_comment(
        self,
        post_id: int,
        platform_comment_id: str,
        author_username: str,
        content: str
    ) -> models.Comment:
        """Create a new comment record."""
        db_comment = models.Comment(
            post_id=post_id,
            platform_comment_id=platform_comment_id,
            author_username=author_username,
            content=content
        )
        self.db.add(db_comment)
        self.db.commit()
        self.db.refresh(db_comment)
        return db_comment

    def get_unreplied_comments(self) -> List[models.Comment]:
        """Get all comments that haven't been replied to."""
        return self.db.query(models.Comment).filter(
            models.Comment.is_replied_to == False
        ).all()

    def mark_comment_replied(
        self,
        comment_id: int,
        reply_id: str,
        reply_content: str
    ) -> Optional[models.Comment]:
        """Mark a comment as replied to."""
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
        return db_comment 