import unittest
from unittest.mock import patch, MagicMock, call
import asyncio
import pytest
from src.scheduler.task_scheduler import TaskScheduler
from src.database.models import Platform

@pytest.mark.asyncio
class TestTaskScheduler(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_db = MagicMock()
        self.task_scheduler = TaskScheduler(self.mock_db)

    @patch('asyncio.create_task')
    async def test_start_scheduled_tasks(self, mock_create_task):
        # Arrange
        mock_content_generation = MagicMock()
        mock_reply_checking = MagicMock()
        mock_metrics_collection = MagicMock()
        mock_create_task.side_effect = [mock_content_generation, mock_reply_checking, mock_metrics_collection]

        # Act
        await self.task_scheduler.start()

        # Assert
        self.assertEqual(mock_create_task.call_count, 3)
        mock_create_task.assert_has_calls([
            call(self.task_scheduler._schedule_content_generation()),
            call(self.task_scheduler._schedule_reply_checking()),
            call(self.task_scheduler._schedule_metrics_collection())
        ])
        self.assertEqual(len(self.task_scheduler.tasks), 3)
        self.assertIn('content_generation', self.task_scheduler.tasks)
        self.assertIn('reply_checking', self.task_scheduler.tasks)
        self.assertIn('metrics_collection', self.task_scheduler.tasks)
        self.assertEqual(self.task_scheduler.tasks['content_generation'], mock_content_generation)
        self.assertEqual(self.task_scheduler.tasks['reply_checking'], mock_reply_checking)
        self.assertEqual(self.task_scheduler.tasks['metrics_collection'], mock_metrics_collection)

    @patch('src.scheduler.task_scheduler.ContentGenerator')
    @patch('src.scheduler.task_scheduler.TwitterClient')
    @patch('src.scheduler.task_scheduler.BlueskyClient')
    @patch('src.scheduler.task_scheduler.DatabaseOperations')
    async def test_schedule_content_generation(self, mock_db_ops, mock_bluesky, mock_twitter, mock_content_gen):
        # Arrange
        mock_content = "Test content"
        mock_content_gen.return_value.generate_post.return_value = mock_content
        mock_twitter.return_value.post_content.return_value = True
        mock_bluesky.return_value.post_content.return_value = {'uri': 'bluesky_post_id'}

        # Act
        with patch('asyncio.sleep', return_value=None):
            task = asyncio.create_task(self.task_scheduler._schedule_content_generation())
            await asyncio.sleep(0.1)  # Allow the task to run once
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Assert
        mock_content_gen.return_value.generate_post.assert_called_once_with(
            "Create an engaging social media post about technology trends",
            tone="professional",
            style="informative"
        )
        mock_twitter.return_value.post_content.assert_called_once_with(mock_content)
        mock_bluesky.return_value.post_content.assert_called_once_with(mock_content)

    @patch('src.scheduler.task_scheduler.DatabaseOperations')
    @patch('src.scheduler.task_scheduler.ContentGenerator')
    @patch('src.scheduler.task_scheduler.TwitterClient')
    @patch('src.scheduler.task_scheduler.BlueskyClient')
    async def test_schedule_reply_checking(self, mock_bluesky, mock_twitter, mock_content_gen, mock_db_ops):
        # Arrange
        mock_twitter_comment = MagicMock(id=1, platform_comment_id='twitter_comment_id', post_id=1, content="Twitter comment")
        mock_bluesky_comment = MagicMock(id=2, platform_comment_id='bluesky_comment_id', post_id=2, content="Bluesky comment")
        mock_db_ops.return_value.get_unreplied_comments.return_value = [mock_twitter_comment, mock_bluesky_comment]

        # Mock associated posts
        mock_db_ops.return_value.get_post.side_effect = [
            MagicMock(platform=Platform.TWITTER),
            MagicMock(platform=Platform.BLUESKY)
        ]

        # Mock content generation
        mock_content_gen.return_value.direct_prompt.return_value = "Generated reply"

        # Mock reply posting
        mock_twitter.return_value.reply_to_tweet.return_value = True
        mock_bluesky.return_value.reply_to_post.return_value = {'uri': 'bluesky_reply_id'}

        # Act
        with patch('asyncio.sleep', return_value=None):
            task = asyncio.create_task(self.task_scheduler._schedule_reply_checking())
            await asyncio.sleep(0.1)  # Allow the task to run once
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Assert
        mock_db_ops.return_value.get_unreplied_comments.assert_called_once()
        mock_content_gen.return_value.direct_prompt.assert_has_calls([
            call("Generate a friendly and engaging reply to this comment: Twitter comment"),
            call("Generate a friendly and engaging reply to this comment: Bluesky comment")
        ])
        mock_twitter.return_value.reply_to_tweet.assert_called_once_with('twitter_comment_id', "Generated reply")
        mock_bluesky.return_value.reply_to_post.assert_called_once_with('bluesky_comment_id', "Generated reply")

    @patch('src.scheduler.task_scheduler.DatabaseOperations')
    @patch('src.scheduler.task_scheduler.TwitterClient')
    @patch('src.scheduler.task_scheduler.BlueskyClient')
    async def test_schedule_metrics_collection(self, mock_bluesky, mock_twitter, mock_db_ops):
        # Arrange
        # Mock recent posts
        mock_twitter_post = MagicMock(id=1, platform=Platform.TWITTER, platform_post_id='twitter_post_id')
        mock_bluesky_post = MagicMock(id=2, platform=Platform.BLUESKY, platform_post_id='bluesky_post_id')
        mock_db_ops.return_value.get_recent_posts.return_value = [mock_twitter_post, mock_bluesky_post]
        
        # Mock Twitter metrics
        mock_twitter_thread = MagicMock()
        mock_twitter_thread.data.tweet.public_metrics = MagicMock(
            like_count=10,
            reply_count=5,
            retweet_count=3,
            view_count=100
        )
        mock_twitter.return_value.get_tweet_thread.return_value = mock_twitter_thread
        
        # Mock Bluesky metrics
        mock_bluesky_thread = MagicMock()
        mock_bluesky_thread.thread.post.likeCount = 7
        mock_bluesky_thread.thread.post.replyCount = 2
        mock_bluesky_thread.thread.post.repostCount = 1
        mock_bluesky.return_value.get_post_thread.return_value = mock_bluesky_thread
        
        # Act
        with patch('asyncio.sleep', return_value=None):
            task = asyncio.create_task(self.task_scheduler._schedule_metrics_collection())
            await asyncio.sleep(0.1)  # Allow the task to run once
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Assert
        mock_db_ops.return_value.get_recent_posts.assert_called_once_with(hours=24)
        mock_twitter.return_value.get_tweet_thread.assert_called_once_with('twitter_post_id')
        mock_bluesky.return_value.get_post_thread.assert_called_once_with('bluesky_post_id')
        mock_db_ops.return_value.update_engagement_metrics.assert_has_calls([
            call(1, likes=10, replies=5, reposts=3, views=100),
            call(2, likes=7, replies=2, reposts=1, views=0)
        ])

    @patch('asyncio.gather')
    async def test_stop_cancels_all_tasks(self, mock_gather):
        # Arrange
        mock_task1 = MagicMock()
        mock_task2 = MagicMock()
        mock_task3 = MagicMock()
        self.task_scheduler.tasks = {
            'content_generation': mock_task1,
            'reply_checking': mock_task2,
            'metrics_collection': mock_task3
        }

        # Act
        await self.task_scheduler.stop()

        # Assert
        mock_task1.cancel.assert_called_once()
        mock_task2.cancel.assert_called_once()
        mock_task3.cancel.assert_called_once()
        mock_gather.assert_called_once_with(mock_task1, mock_task2, mock_task3, return_exceptions=True)
        self.assertEqual(len(self.task_scheduler.tasks), 0)

if __name__ == '__main__':
    pytest.main([__file__])
