import unittest
from unittest.mock import patch, MagicMock, AsyncMock, call
import asyncio
import pytest
from src.scheduler.task_scheduler import TaskScheduler, SchedulerConfig
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
            pass
        
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

if __name__ == '__main__':
    pytest.main([__file__])
