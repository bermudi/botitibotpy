import unittest
import asyncio
import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch
from src.scheduler.queue_manager import QueueManager, Task, TaskPriority

@pytest.mark.asyncio
class TestQueueManager(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        """Set up test fixtures before each test method."""
        self.queue_manager = QueueManager(max_concurrent_tasks=3)
        
    async def asyncTearDown(self):
        """Clean up after each test"""
        if hasattr(self, 'queue_manager'):
            # Make a copy of the tasks before iterating
            tasks = list(self.queue_manager.running_tasks.values())
            # Cancel all running tasks
            for task in tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            # Clear all collections
            self.queue_manager.task_queue.clear()
            self.queue_manager.running_tasks.clear()
            self.queue_manager.task_results.clear()
            # Reset semaphore
            self.queue_manager.semaphore = asyncio.Semaphore(self.queue_manager.max_concurrent_tasks)

    async def test_add_task(self):
        """Test adding a task to the queue"""
        # Arrange
        async def mock_coroutine():
            await asyncio.sleep(0.01)  # Small delay to simulate work
            return "done"
            
        task = Task(
            id="test_task",
            priority=TaskPriority.MEDIUM,
            created_at=datetime.now(),
            coroutine=mock_coroutine
        )

        # Act
        task_id = await self.queue_manager.add_task(task)
        await asyncio.sleep(0.05)  # Let task process

        # Assert
        self.assertEqual(task_id, "test_task")
        queue_status = self.queue_manager.get_queue_status()
        self.assertEqual(queue_status['completed_tasks'], 1)

    async def test_task_priority_order(self):
        """Test tasks are executed in priority order"""
        # Arrange
        completed_tasks = []
        completion_event = asyncio.Event()
        task_count = 0
        
        async def mock_coroutine(task_id):
            nonlocal task_count
            task_count += 1
            completed_tasks.append(task_id)
            if task_count == 3:  # All tasks have started
                completion_event.set()
            return f"{task_id}_done"
            
        tasks = [
            Task(id="low", priority=TaskPriority.LOW, created_at=datetime.now(), 
                 coroutine=mock_coroutine, args=("low",)),
            Task(id="high", priority=TaskPriority.HIGH, created_at=datetime.now(),
                 coroutine=mock_coroutine, args=("high",)),
            Task(id="medium", priority=TaskPriority.MEDIUM, created_at=datetime.now(),
                 coroutine=mock_coroutine, args=("medium",))
        ]

        # Act
        for task in tasks:
            await self.queue_manager.add_task(task)

        # Wait for all tasks to complete
        try:
            await asyncio.wait_for(completion_event.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            self.fail("Tasks did not complete in time")

        # Assert
        self.assertEqual(completed_tasks[0], "high")  # High priority should be first

    async def test_max_concurrent_tasks(self):
        """Test concurrent task limit is respected"""
        # Arrange
        self.queue_manager.max_concurrent_tasks = 2
        running_tasks = []
        completed_tasks = []
        task_event = asyncio.Event()
        start_event = asyncio.Event()
        tasks_started = 0
        
        async def mock_coroutine(task_id):
            nonlocal tasks_started
            tasks_started += 1
            running_tasks.append(task_id)
            if tasks_started == 1:  # Only set event for first task
                start_event.set()
            await asyncio.wait_for(task_event.wait(), timeout=1.0)  # Add timeout
            running_tasks.remove(task_id)
            completed_tasks.append(task_id)
            return f"{task_id}_done"
            
        tasks = [
            Task(id=f"task_{i}", priority=TaskPriority.MEDIUM, created_at=datetime.now(),
                 coroutine=mock_coroutine, args=(f"task_{i}",))
            for i in range(4)
        ]

        try:
            # Act
            # Add all tasks
            for task in tasks:
                await self.queue_manager.add_task(task)

            # Wait for first task to start
            try:
                await asyncio.wait_for(start_event.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                self.fail("No tasks started in time")
            
            # Give a short time for any additional tasks to potentially start
            await asyncio.sleep(0.1)
            
            # Assert initial state
            self.assertLessEqual(len(running_tasks), 2)  # No more than 2 tasks running at once
            queue_status = self.queue_manager.get_queue_status()
            self.assertEqual(queue_status['running_tasks'], len(running_tasks))
            self.assertEqual(queue_status['queued_tasks'], 4 - len(running_tasks))
            
            # Allow tasks to complete
            task_event.set()
            await asyncio.sleep(0.1)  # Let remaining tasks complete
            
        finally:
            # Ensure events are set to prevent hanging
            start_event.set()
            task_event.set()
            # Cancel any remaining tasks
            for task_id in list(self.queue_manager.running_tasks.keys()):
                await self.queue_manager.cancel_task(task_id)

    async def test_task_retry(self):
        """Test task retry mechanism"""
        # Arrange
        attempts = 0
        
        async def failing_coroutine():
            nonlocal attempts
            attempts += 1
            await asyncio.sleep(0.01)  # Small delay to simulate work
            if attempts == 1:
                raise Exception("Test error")
            return "success"
            
        task = Task(
            id="retry_task",
            priority=TaskPriority.HIGH,
            created_at=datetime.now(),
            coroutine=failing_coroutine,
            max_retries=1
        )

        # Act
        await self.queue_manager.add_task(task)
        await asyncio.sleep(0.1)  # Allow time for retry

        # Assert
        self.assertEqual(attempts, 2)  # Called twice (original + retry)
        task_status = self.queue_manager.get_task_status("retry_task")
        self.assertEqual(task_status['status'], 'completed')

    async def test_task_failure_max_retries(self):
        """Test task fails after max retries"""
        # Arrange
        async def failing_coroutine():
            await asyncio.sleep(0.01)  # Small delay to simulate work
            raise Exception("Test error")
            
        task = Task(
            id="fail_task",
            priority=TaskPriority.HIGH,
            created_at=datetime.now(),
            coroutine=failing_coroutine,
            max_retries=2
        )

        # Act
        await self.queue_manager.add_task(task)
        await asyncio.sleep(0.2)  # Allow time for retries

        # Assert
        task_status = self.queue_manager.get_task_status("fail_task")
        self.assertEqual(task_status['status'], 'failed')
        self.assertIn('Test error', task_status['error'])

    async def test_cancel_running_task(self):
        """Test cancelling a running task"""
        # Arrange
        task_started = asyncio.Event()
        
        async def long_running_task():
            task_started.set()
            await asyncio.sleep(1)
            return "done"

        task = Task(
            id="cancel_task",
            priority=TaskPriority.HIGH,
            created_at=datetime.now(),
            coroutine=long_running_task
        )

        # Act
        await self.queue_manager.add_task(task)
        await task_started.wait()  # Wait for task to start
        cancelled = await self.queue_manager.cancel_task("cancel_task")

        # Assert
        self.assertTrue(cancelled)
        task_status = self.queue_manager.get_task_status("cancel_task")
        self.assertEqual(task_status['status'], 'cancelled')

    async def test_cancel_queued_task(self):
        """Test cancelling a queued task"""
        # Arrange
        task_event = asyncio.Event()
        start_event = asyncio.Event()

        async def running_coroutine():
            start_event.set()
            await task_event.wait()  # Wait until explicitly allowed to complete
            return "done"

        async def queued_coroutine():
            return "queued"

        running_task = Task(id="running", priority=TaskPriority.HIGH, created_at=datetime.now(),
                          coroutine=running_coroutine)
        queued_task = Task(id="queued", priority=TaskPriority.LOW, created_at=datetime.now(),
                          coroutine=queued_coroutine)

        # Act
        await self.queue_manager.add_task(running_task)
        await self.queue_manager.add_task(queued_task)

        # Wait for first task to start
        try:
            await asyncio.wait_for(start_event.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            self.fail("Task did not start in time")

        # Allow some time for the second task to be queued
        await asyncio.sleep(0.1)

        # Cancel the queued task
        await self.queue_manager.cancel_task("queued")

        # Allow the running task to complete
        task_event.set()
        await asyncio.sleep(0.1)  # Give time for cleanup

        # Assert
        self.assertNotIn("queued", self.queue_manager.task_results)
        self.assertEqual(len(self.queue_manager.task_queue), 0)

    async def test_queue_status(self):
        """Test queue status reporting"""
        # Arrange
        task_event = asyncio.Event()
        
        async def mock_coroutine():
            await task_event.wait()  # Keep task running until explicitly completed
            return "done"
            
        tasks = [
            Task(id=f"task_{p.name}", priority=p, created_at=datetime.now(),
                 coroutine=mock_coroutine)
            for p in TaskPriority
        ]

        # Act
        for task in tasks:
            await self.queue_manager.add_task(task)
            
        await asyncio.sleep(0.05)  # Let tasks start

        # Assert
        status = self.queue_manager.get_queue_status()
        self.assertIn('queued_tasks', status)
        self.assertIn('running_tasks', status)
        self.assertIn('completed_tasks', status)
        self.assertIn('tasks_by_priority', status)
        total_tasks = status['queued_tasks'] + status['running_tasks']
        self.assertEqual(total_tasks, len(TaskPriority))
        
        # Cleanup
        task_event.set()  # Allow tasks to complete
        await asyncio.sleep(0.05)

if __name__ == '__main__':
    pytest.main([__file__])
