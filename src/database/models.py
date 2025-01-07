from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
import enum

from . import Base

class Platform(enum.Enum):
    TWITTER = "twitter"
    BLUESKY = "bluesky"

class Credentials(Base):
    """Store social media platform credentials"""
    __tablename__ = "credentials"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(Enum(Platform), nullable=False)
    username = Column(String, nullable=False)
    # Store auth tokens, cookies, or other credentials as JSON
    auth_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to posts
    posts = relationship("Post", back_populates="credentials")

class Post(Base):
    """Store posts made by the bot"""
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    platform_post_id = Column(String, nullable=False)  # ID from the platform (tweet ID, post ID)
    credentials_id = Column(Integer, ForeignKey("credentials.id"), nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    credentials = relationship("Credentials", back_populates="posts")
    engagement_metrics = relationship("EngagementMetrics", back_populates="post", uselist=False)
    comments = relationship("Comment", back_populates="post")

class EngagementMetrics(Base):
    """Store engagement metrics for posts"""
    __tablename__ = "engagement_metrics"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), unique=True, nullable=False)
    likes = Column(Integer, default=0)
    replies = Column(Integer, default=0)
    reposts = Column(Integer, default=0)  # retweets/reposts
    views = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to post
    post = relationship("Post", back_populates="engagement_metrics")

class Comment(Base):
    """Store comments/replies on posts"""
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    platform_comment_id = Column(String, nullable=False)  # ID from the platform
    author_username = Column(String, nullable=False)
    content = Column(String, nullable=False)
    is_replied_to = Column(Integer, default=False)  # Track if we've responded
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # If this is a reply from our bot
    our_reply_id = Column(String, nullable=True)
    our_reply_content = Column(String, nullable=True)
    replied_at = Column(DateTime, nullable=True)

    # Relationship to post
    post = relationship("Post", back_populates="comments")

class ScheduledTask(Base):
    """Store scheduled tasks"""
    __tablename__ = "scheduled_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, nullable=False, unique=True)
    platform = Column(Enum(Platform), nullable=False)
    content = Column(String, nullable=False)
    scheduled_time = Column(DateTime, nullable=False)
    priority = Column(String, nullable=False)  # HIGH, MEDIUM, LOW
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending")  # pending, completed, cancelled, failed 