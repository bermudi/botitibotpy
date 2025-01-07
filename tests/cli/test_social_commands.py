"""
Tests for social media CLI commands.
"""

import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

from .test_base import BaseCliTest

class TestSocialCommands(BaseCliTest):
    """Test cases for social media commands."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.mock_twitter = patch('src.cli.cli.TwitterClient').start()
        self.twitter_instance = self.mock_twitter.return_value
        self.mock_bluesky = patch('src.cli.cli.BlueskyClient').start()
        self.bluesky_instance = self.mock_bluesky.return_value
        self.mock_queue = patch('src.cli.cli.QueueManager').start()
        self.queue_instance = self.mock_queue.return_value
        
    def test_auth_twitter(self):
        """Test Twitter authentication."""
        result = self.invoke_cli(['social', 'auth', 'twitter'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Successfully authenticated with twitter", result.output)
        
    def test_auth_bluesky(self):
        """Test Bluesky authentication."""
        result = self.invoke_cli(['social', 'auth', 'bluesky'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Successfully authenticated with bluesky", result.output)
        
    def test_post_immediate_twitter(self):
        """Test immediate posting to Twitter."""
        content = "Test tweet"
        
        result = self.invoke_cli(['social', 'post', 'twitter', content])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Posted to Twitter successfully", result.output)
        self.twitter_instance.post.assert_called_once_with(content)
        
    def test_post_scheduled(self):
        """Test scheduling a post."""
        content = "Test tweet"
        schedule = "2025-01-07 10:00"
        self.queue_instance.schedule_post.return_value = 123
        
        result = self.invoke_cli(['social', 'post', 'twitter', content,
                                '--schedule', schedule])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Post scheduled with ID: 123", result.output)
        self.queue_instance.schedule_post.assert_called_once()
        
    def test_list_scheduled_posts(self):
        """Test listing scheduled posts."""
        self.queue_instance.list_scheduled_posts.return_value = [
            {
                'id': 1,
                'platform': 'twitter',
                'content': 'Test tweet',
                'schedule': '2025-01-07 10:00'
            }
        ]
        
        result = self.invoke_cli(['social', 'list-scheduled'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Scheduled Posts:", result.output)
        self.assertIn("ID: 1", result.output)
        self.assertIn("Platform: twitter", result.output)
        self.assertIn("Content: Test tweet", result.output)
        
    def test_list_scheduled_posts_empty(self):
        """Test listing scheduled posts when none exist."""
        self.queue_instance.list_scheduled_posts.return_value = []
        
        result = self.invoke_cli(['social', 'list-scheduled'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No scheduled posts", result.output)
        
    def test_cancel_scheduled_post(self):
        """Test canceling a scheduled post."""
        post_id = 123
        self.queue_instance.cancel_post.return_value = True
        
        result = self.invoke_cli(['social', 'cancel', str(post_id)])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn(f"Cancelled post {post_id}", result.output)
        self.queue_instance.cancel_post.assert_called_once_with(post_id)
        
    def test_cancel_nonexistent_post(self):
        """Test canceling a nonexistent post."""
        post_id = 999
        self.queue_instance.cancel_post.return_value = False
        
        result = self.invoke_cli(['social', 'cancel', str(post_id)])
        
        self.assertEqual(result.exit_code, 1)
        self.assertIn(f"Post {post_id} not found", result.stderr)
