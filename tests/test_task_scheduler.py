import unittest
from unittest.mock import patch, MagicMock, AsyncMock, call
import asyncio
import pytest
from src.scheduler.task_scheduler import TaskScheduler, SchedulerConfig, PlatformConfig
from src.scheduler.exceptions import RateLimitError
from src.scheduler.queue_manager import QueueManager, Task, TaskPriority
from src.database.models import Platform
from datetime import datetime

@pytest.mark.asyncio
class TestTaskScheduler(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        """Set up test fixtures before each test method."""
        self.mock_db = AsyncMock()
        self.mock_db.get_unreplied_comments = AsyncMock(return_value=[])
        self.mock_db.get_recent_posts = AsyncMock(return_value=[])
        self.mock_db.update_metrics = AsyncMock()
        
        self.config = SchedulerConfig(
            content_generation_interval=30,
            reply_check_interval=2,
            metrics_update_interval=5,
            max_concurrent_tasks=3
        )
        # Ensure Twitter is explicitly enabled for tests
        self.config.twitter.enabled = True
        self.config.bluesky.enabled = True
        
        self.task_scheduler = TaskScheduler(self.mock_db, config=self.config)
        self.task_scheduler.db_ops = self.mock_db
        self.task_scheduler.content_generator.generate_post = AsyncMock(return_value="Generated post")

    async def asyncTearDown(self):
        """Clean up after each test"""
        if hasattr(self, 'task_scheduler'):
            await self.task_scheduler.stop()
            self.task_scheduler.tasks.clear()
            self.task_scheduler.queue_manager.task_queue.clear()
            self.task_scheduler.queue_manager.running_tasks.clear()
            self.task_scheduler.queue_manager.task_results.clear()

    async def test_init_with_custom_config(self):
        """Test initialization with custom configuration"""
        # Arrange & Act
        custom_config = SchedulerConfig(
            content_generation_interval=45,
            reply_check_interval=3,
            metrics_update_interval=7,
            max_concurrent_tasks=4
        )
        scheduler = TaskScheduler(self.mock_db, config=custom_config)

        # Assert
        self.assertEqual(scheduler.config.content_generation_interval, 45)
        self.assertEqual(scheduler.config.reply_check_interval, 3)
        self.assertEqual(scheduler.config.metrics_update_interval, 7)
        self.assertEqual(scheduler.config.max_concurrent_tasks, 4)
        self.assertEqual(scheduler.queue_manager.max_concurrent_tasks, 4)

    async def test_init_with_default_config(self):
        """Test initialization with default configuration"""
        # Arrange & Act
        scheduler = TaskScheduler(self.mock_db)

        # Assert
        self.assertEqual(scheduler.config.content_generation_interval, 60)
        self.assertEqual(scheduler.config.reply_check_interval, 5)
        self.assertEqual(scheduler.config.metrics_update_interval, 10)
        self.assertEqual(scheduler.config.max_concurrent_tasks, 5)

    async def test_update_config(self):
        """Test updating configuration at runtime"""
        # Arrange
        new_config = SchedulerConfig(
            content_generation_interval=15,
            reply_check_interval=1,
            metrics_update_interval=3,
            max_concurrent_tasks=2
        )

        # Act
        self.task_scheduler.update_config(new_config)

        # Assert
        self.assertEqual(self.task_scheduler.config.content_generation_interval, 15)
        self.assertEqual(self.task_scheduler.config.reply_check_interval, 1)
        self.assertEqual(self.task_scheduler.config.metrics_update_interval, 3)
        self.assertEqual(self.task_scheduler.queue_manager.max_concurrent_tasks, 2)

    async def test_update_interval(self):
        """Test updating task intervals at runtime"""
        # Arrange
        original_interval = self.task_scheduler.intervals['content_generation']
        
        # Act
        self.task_scheduler.update_interval('content_generation', 45)
        
        # Assert
        self.assertEqual(self.task_scheduler.intervals['content_generation'], 45)
        self.assertNotEqual(self.task_scheduler.intervals['content_generation'], original_interval)

    async def test_invalid_interval_update(self):
        """Test updating invalid task interval"""
        # Act & Assert
        with self.assertRaises(ValueError):
            self.task_scheduler.update_interval('nonexistent_task', 30)

    async def test_platform_config(self):
        """Test platform-specific configuration"""
        # Arrange
        config = SchedulerConfig(
            twitter=PlatformConfig(
                enabled=True,
                retry_limit=5,
                rate_limit_window=900,
                max_requests_per_window=50
            ),
            bluesky=PlatformConfig(
                enabled=True,
                retry_limit=3,
                rate_limit_window=600,
                max_requests_per_window=30
            )
        )
        
        # Act
        scheduler = TaskScheduler(self.mock_db, config=config)
        
        # Assert
        self.assertEqual(scheduler.config.twitter.retry_limit, 5)
        self.assertEqual(scheduler.config.twitter.rate_limit_window, 900)
        self.assertEqual(scheduler.config.bluesky.max_requests_per_window, 30)

    async def test_handle_platform_error_rate_limit(self):
        """Test handling of platform rate limit errors"""
        # Arrange
        error = RateLimitError(retry_after=60)
        
        # Act
        handled = await self.task_scheduler._handle_platform_error('twitter', error)
        
        # Assert
        self.assertTrue(handled)
        self.assertTrue(self.task_scheduler.config.twitter.enabled)

    async def test_handle_platform_error_unauthorized(self):
        """Test handling of platform authentication errors"""
        # Arrange
        error = Exception("Unauthorized: Invalid credentials")
        
        # Act
        handled = await self.task_scheduler._handle_platform_error('twitter', error)
        
        # Assert
        self.assertTrue(handled)
        self.assertFalse(self.task_scheduler.config.twitter.enabled)

    async def test_handle_platform_error_not_found(self):
        """Test handling of platform not found errors"""
        # Arrange
        error = Exception("Not Found: Resource does not exist")
        
        # Act
        handled = await self.task_scheduler._handle_platform_error('twitter', error)
        
        # Assert
        self.assertTrue(handled)
        self.assertTrue(self.task_scheduler.config.twitter.enabled)

    async def test_handle_platform_error_unknown(self):
        """Test handling of unknown platform errors"""
        # Arrange
        error = Exception("Unknown error")
        
        # Act
        handled = await self.task_scheduler._handle_platform_error('twitter', error)
        
        # Assert
        self.assertFalse(handled)
        # Unknown errors should not disable the platform
        self.assertTrue(self.task_scheduler.config.twitter.enabled)

    @patch('src.scheduler.task_scheduler.TaskScheduler._schedule_content_generation')
    @patch('src.scheduler.task_scheduler.TaskScheduler._schedule_metrics_collection')
    @patch('src.scheduler.task_scheduler.TaskScheduler._schedule_reply_checking')
    async def test_start_scheduled_tasks(self, mock_reply, mock_metrics, mock_content):
        """Test starting scheduled tasks"""
        # Arrange
        mock_reply.return_value = AsyncMock()()
        mock_metrics.return_value = AsyncMock()()
        mock_content.return_value = AsyncMock()()

        # Act
        await self.task_scheduler.start()

        # Assert
        self.assertEqual(len(self.task_scheduler.tasks), 3)  # content_generation, reply_checking, metrics_collection
        mock_content.assert_called_once()
        mock_metrics.assert_called_once()
        mock_reply.assert_called_once()

    async def test_schedule_content_generation(self):
        """Test content generation scheduling"""
        # Arrange
        self.task_scheduler.content_generator.generate_post = AsyncMock(return_value="Test post")
        self.task_scheduler.twitter_client.post_content = AsyncMock()
        self.task_scheduler.bluesky_client.post_content = AsyncMock()

        # Act
        task = asyncio.create_task(self.task_scheduler._schedule_content_generation())
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=0.1)  # Let the first iteration run
        except asyncio.TimeoutError:
            pass  # Expected timeout
        finally:
            task.cancel()  # Stop the infinite loop
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Assert
        self.task_scheduler.content_generator.generate_post.assert_called_once()
        self.task_scheduler.twitter_client.post_content.assert_called_once_with("Test post")
        self.task_scheduler.bluesky_client.post_content.assert_called_once_with("Test post")

    async def test_schedule_reply_checking(self):
        """Test reply checking scheduling"""
        # Arrange
        mock_comments = [{'id': '1'}, {'id': '2'}]
        self.task_scheduler.db_ops.get_unreplied_comments = AsyncMock(return_value=mock_comments)
        self.task_scheduler.content_generator.generate_reply = AsyncMock(return_value="Test reply")
        self.task_scheduler._check_and_handle_replies = AsyncMock()

        # Act
        task = asyncio.create_task(self.task_scheduler._schedule_reply_checking())
        try:
            # Wait longer to ensure the task executes
            await asyncio.sleep(1)

            # Wait for all running tasks to complete
            while self.task_scheduler.queue_manager.running_tasks:
                await asyncio.sleep(0.1)

            # Assert
            self.task_scheduler._check_and_handle_replies.assert_called_once()
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def test_schedule_metrics_collection(self):
        """Test metrics collection scheduling"""
        # Arrange
        mock_posts = [{'id': '1'}, {'id': '2'}]
        self.task_scheduler.db_ops.get_recent_posts = AsyncMock(return_value=mock_posts)
        self.task_scheduler.db_ops.update_metrics = AsyncMock()

        # Act
        task = asyncio.create_task(self.task_scheduler._schedule_metrics_collection())
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=0.1)
        except asyncio.TimeoutError:
            pass
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Assert
        self.task_scheduler.db_ops.get_recent_posts.assert_called_once_with(hours=24)

    async def test_stop_cancels_all_tasks(self):
        """Test stopping all tasks"""
        # Arrange
        async def mock_coro():
            try:
                # Make sure task runs long enough to test cancellation
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                # Properly handle cancellation
                raise

        mock_task1 = asyncio.create_task(mock_coro())
        mock_task2 = asyncio.create_task(mock_coro())
        mock_task3 = asyncio.create_task(mock_coro())

        self.task_scheduler.tasks = {
            'content_generation': mock_task1,
            'reply_checking': mock_task2,
            'metrics_collection': mock_task3
        }

        # Act
        await self.task_scheduler.stop()

        # Assert
        self.assertTrue(mock_task1.cancelled())
        self.assertTrue(mock_task2.cancelled())
        self.assertTrue(mock_task3.cancelled())

    async def test_adaptive_scheduling_write_rate_limit(self):
        """Test adaptive scheduling when write operations are rate limited"""
        # Arrange
        error = RateLimitError("Rate limited", operation_type="write", backoff=60)
        original_interval = self.task_scheduler.intervals['content_generation']
        
        # Act
        handled = await self.task_scheduler._handle_platform_error('twitter', error)
        
        # Assert
        self.assertTrue(handled)
        self.assertEqual(self.task_scheduler.intervals['content_generation'], 
                        min(original_interval * 2, 120))  # Doubled but capped at 2 hours

    async def test_adaptive_scheduling_read_rate_limit(self):
        """Test adaptive scheduling when read operations are rate limited"""
        # Arrange
        error = RateLimitError("Rate limited", operation_type="read", backoff=60)
        original_reply_interval = self.task_scheduler.intervals['reply_check']
        original_metrics_interval = self.task_scheduler.intervals['metrics_update']
        
        # Act
        handled = await self.task_scheduler._handle_platform_error('twitter', error)
        
        # Assert
        self.assertTrue(handled)
        self.assertEqual(self.task_scheduler.intervals['reply_check'], 
                        min(original_reply_interval * 2, 30))  # Doubled but capped at 30 minutes
        self.assertEqual(self.task_scheduler.intervals['metrics_update'], 
                        min(original_metrics_interval * 2, 60))  # Doubled but capped at 1 hour

    async def test_interval_reduction_after_success(self):
        """Test gradual interval reduction after successful operations"""
        # Arrange
        self.task_scheduler.intervals['content_generation'] = 120  # Start at max
        self.task_scheduler.content_generator.generate_post = AsyncMock(return_value="Test post")
        self.task_scheduler.twitter_client.post_content = AsyncMock()
        self.task_scheduler.bluesky_client.post_content = AsyncMock()
        
        # Act
        task = asyncio.create_task(self._schedule_content_generation())
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=0.1)
        except asyncio.TimeoutError:
            pass
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Assert
        self.assertEqual(self.task_scheduler.intervals['content_generation'], 60)  # Reduced by half

    async def test_skip_rate_limited_operations(self):
        """Test skipping operations when rate limited"""
        # Arrange
        self.task_scheduler.queue_manager.is_rate_limited = MagicMock(return_value=True)
        self.task_scheduler.queue_manager.get_rate_limit_delay = MagicMock(return_value=60)
        self.task_scheduler._generate_and_post_content = AsyncMock()
        
        # Act
        task = asyncio.create_task(self.task_scheduler._schedule_content_generation())
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=0.1)
        except asyncio.TimeoutError:
            pass
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Assert
        self.task_scheduler._generate_and_post_content.assert_not_called()

    async def test_rate_limit_error_propagation(self):
        """Test rate limit error propagation through task scheduler"""
        # Arrange
        self.task_scheduler.twitter_client.post_content = AsyncMock(
            side_effect=RateLimitError("Rate limited", "write", 60)
        )
        self.task_scheduler.content_generator.generate_post = AsyncMock(return_value="Test post")
        
        # Act
        post_ids = await self.task_scheduler._generate_and_post_content()
        
        # Assert
        self.assertIsNone(post_ids.get(Platform.TWITTER))
        self.assertTrue(self.task_scheduler.queue_manager.is_rate_limited("write"))

    async def test_platform_specific_rate_limits(self):
        """Test handling platform-specific rate limits"""
        # Arrange
        self.task_scheduler.twitter_client.post_content = AsyncMock(
            side_effect=RateLimitError("Twitter rate limit", "write", 60)
        )
        self.task_scheduler.bluesky_client.post_content = AsyncMock(
            side_effect=RateLimitError("Bluesky rate limit", "write", 30)
        )
        self.task_scheduler.content_generator.generate_post = AsyncMock(return_value="Test post")
        
        # Act
        post_ids = await self.task_scheduler._generate_and_post_content()
        
        # Assert
        self.assertIsNone(post_ids.get(Platform.TWITTER))
        self.assertIsNone(post_ids.get(Platform.BLUESKY))
        self.assertTrue(self.task_scheduler.queue_manager.is_rate_limited("write"))
        self.assertGreater(self.task_scheduler.intervals['content_generation'], 
                          self.config.content_generation_interval)

if __name__ == '__main__':
    pytest.main([__file__])
