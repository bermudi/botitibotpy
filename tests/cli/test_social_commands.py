"""
Tests for social media CLI commands.
"""

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from .test_base import BaseCliTest
from src.database.models import Platform, Post
from src.cli.cli import social

class TestSocialCommands(BaseCliTest):
    """Test cases for social media commands."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.mock_db = patch('src.cli.cli.DatabaseOperations').start()
        self.db_instance = self.mock_db.return_value
        self.mock_twitter = patch('src.cli.cli.TwitterClient').start()
        self.twitter_instance = self.mock_twitter.return_value
        self.mock_bluesky = patch('src.cli.cli.BlueskyClient').start()
        self.bluesky_instance = self.mock_bluesky.return_value
        
    def test_auth_twitter(self):
        """Test Twitter authentication."""
        result = self.invoke_cli(['social', 'auth', 'twitter'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Successfully authenticated with twitter", result.output)
        self.mock_twitter.assert_called_once()
        
    def test_auth_bluesky(self):
        """Test Bluesky authentication."""
        result = self.invoke_cli(['social', 'auth', 'bluesky'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Successfully authenticated with bluesky", result.output)
        self.mock_bluesky.assert_called_once()
        
    def test_post_immediate_twitter(self):
        """Test immediate posting to Twitter."""
        self.twitter_instance.post.return_value = "tweet_123"
        
        result = self.invoke_cli(['social', 'post', 'twitter', 'Test tweet'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Post created successfully on twitter", result.output)
        self.twitter_instance.post.assert_called_once_with("Test tweet")
        self.db_instance.add_post.assert_called_once()
        
    def test_post_scheduled(self):
        """Test scheduling a post."""
        schedule_time = "2025-01-07 10:00:00"
        
        result = self.invoke_cli([
            'social', 'post', 'twitter', 'Test tweet',
            '--schedule', schedule_time
        ])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn(f"Post scheduled for {schedule_time}", result.output)
        self.db_instance.add_post.assert_called_once()
        
    def test_list_scheduled_posts(self):
        """Test listing scheduled posts."""
        mock_posts = [
            MagicMock(
                platform=Platform.TWITTER,
                scheduled_time=datetime(2025, 1, 7, 10, 0),
                content="Test tweet 1"
            ),
            MagicMock(
                platform=Platform.BLUESKY,
                scheduled_time=datetime(2025, 1, 7, 11, 0),
                content="Test post 2"
            )
        ]
        self.db_instance.get_scheduled_posts.return_value = mock_posts
        
        result = self.invoke_cli(['social', 'list-scheduled'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Test tweet 1", result.output)
        self.assertIn("Test post 2", result.output)
        self.assertIn("TWITTER", result.output)
        self.assertIn("BLUESKY", result.output)
        
    def test_list_scheduled_posts_empty(self):
        """Test listing scheduled posts when none exist."""
        self.db_instance.get_scheduled_posts.return_value = []
        
        result = self.invoke_cli(['social', 'list-scheduled'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No scheduled posts found", result.output)
        
    def test_cancel_scheduled_post(self):
        """Test canceling a scheduled post."""
        post_id = 123
        self.db_instance.get_post.return_value = MagicMock(
            id=post_id,
            platform=Platform.TWITTER,
            scheduled_time=datetime(2025, 1, 7, 10, 0),
            content="Test tweet"
        )
        
        result = self.invoke_cli(['social', 'cancel', str(post_id)])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn(f"Post {post_id} canceled successfully", result.output)
        self.db_instance.delete_post.assert_called_once_with(post_id)
        
    def test_cancel_nonexistent_post(self):
        """Test canceling a nonexistent post."""
        post_id = 999
        self.db_instance.get_post.return_value = None
        
        result = self.invoke_cli(['social', 'cancel', str(post_id)])
        
        self.assertEqual(result.exit_code, 1)
        self.assertIn(f"Post {post_id} not found", result.output)
        self.db_instance.delete_post.assert_not_called()
