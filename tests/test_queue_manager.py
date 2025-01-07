import unittest
import asyncio
import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch
from src.scheduler.queue_manager import QueueManager, Task, TaskPriority
from src.scheduler.exceptions import RateLimitError

@pytest.mark.asyncio
class TestQueueManager(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        """Set up test fixtures before each test method."""
        self.queue_manager = QueueManager(max_concurrent_tasks=3)
        await self.queue_manager.start()
        
    async def asyncTearDown(self):
        """Clean up after each test"""
        if hasattr(self, 'queue_manager'):
            await self.queue_manager.shutdown()

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
        await asyncio.sleep(0.2)  # Increased sleep time to let task complete

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
        await asyncio.sleep(3.0)  # Allow time for retries
        
        # Assert
        self.assertEqual(attempts, 2)  # Called twice (original + retry)
        result = self.queue_manager.get_task_status("retry_task")
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['result'], 'success')

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
        await asyncio.sleep(4.0)  # Allow time for all retries to complete
    
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
        await asyncio.sleep(0.05)  # Wait for first task to start processing
        await self.queue_manager.add_task(queued_task)

        # Wait for first task to start
        try:
            await asyncio.wait_for(start_event.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            self.fail("Task did not start in time")

        # Cancel the queued task immediately
        cancelled = await self.queue_manager.cancel_task("queued")
        self.assertTrue(cancelled)

        # Allow the running task to complete
        task_event.set()
        await asyncio.sleep(0.1)  # Give time for cleanup

        # Assert
        self.assertEqual(self.queue_manager.task_results["queued"]["status"], "cancelled")

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

    async def test_retry_mechanism(self):
        """Test task retry mechanism with exponential backoff"""
        # Arrange
        attempt_count = 0
        
        async def failing_coroutine():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:  # Fail first two attempts
                raise ValueError("Simulated failure")
            return "success"
            
        task = Task(
            id="retry_test",
            priority=TaskPriority.HIGH,
            created_at=datetime.now(),
            coroutine=failing_coroutine,
            max_retries=3
        )
        
        # Act
        await self.queue_manager.add_task(task)
        await asyncio.sleep(4.0)  # Let retries happen
        
        # Assert
        result = self.queue_manager.get_task_status("retry_test")
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['result'], 'success')
        self.assertEqual(result['retries'], 2)

    async def test_rate_limit_handling(self):
        """Test handling of rate limit errors"""
        # Arrange
        rate_limited = False
        
        async def rate_limited_coroutine(*args, **kwargs):
            nonlocal rate_limited
            if not rate_limited:
                rate_limited = True
                raise RateLimitError(retry_after=1)
            return "success after rate limit"
            
        task = Task(
            id="rate_limit_test",
            priority=TaskPriority.HIGH,
            created_at=datetime.now(),
            coroutine=rate_limited_coroutine,
            kwargs={'platform': 'twitter'},
            max_retries=2
        )
        
        # Act
        await self.queue_manager.add_task(task)
        await asyncio.sleep(2.0)  # Wait for rate limit and retry
        
        # Assert
        result = self.queue_manager.get_task_status("rate_limit_test")
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['result'], 'success after rate limit')

    async def test_max_retries_exceeded(self):
        """Test behavior when max retries is exceeded"""
        # Arrange
        async def always_failing_coroutine():
            raise ValueError("Always fails")
            
        task = Task(
            id="max_retries_test",
            priority=TaskPriority.HIGH,
            created_at=datetime.now(),
            coroutine=always_failing_coroutine,
            max_retries=2
        )
        
        # Act
        await self.queue_manager.add_task(task)
        await asyncio.sleep(4.0)  # Let all retries happen
        
        # Assert
        result = self.queue_manager.get_task_status("max_retries_test")
        self.assertEqual(result['status'], 'failed')
        self.assertIn('Always fails', result['error'])
        self.assertEqual(result['retries'], 3)  # Initial try + 2 retries

    async def test_rate_limit_tracking(self):
        """Test operation-specific rate limit tracking"""
        # Arrange
        task_id = "rate_limited_task"
        operation_type = "write"
        backoff = 60
        
        async def failing_coroutine():
            raise RateLimitError("Rate limited", operation_type=operation_type, backoff=backoff)
            
        task = Task(
            id=task_id,
            priority=TaskPriority.HIGH,
            created_at=datetime.now(),
            coroutine=failing_coroutine,
            max_retries=1
        )
        
        # Act
        await self.queue_manager.add_task(task)
        await asyncio.sleep(0.1)  # Let task execute
        
        # Assert
        self.assertTrue(self.queue_manager.is_rate_limited(operation_type))
        self.assertGreater(self.queue_manager.get_rate_limit_delay(operation_type), 0)
        self.assertLessEqual(self.queue_manager.get_rate_limit_delay(operation_type), backoff)

    async def test_multiple_operation_types(self):
        """Test handling multiple operation types independently"""
        # Arrange
        write_task = Task(
            id="write_task",
            priority=TaskPriority.HIGH,
            created_at=datetime.now(),
            coroutine=lambda: RateLimitError("Write limited", "write", 60),
            max_retries=1
        )
        
        read_task = Task(
            id="read_task",
            priority=TaskPriority.HIGH,
            created_at=datetime.now(),
            coroutine=lambda: RateLimitError("Read limited", "read", 30),
            max_retries=1
        )
        
        # Act
        await self.queue_manager.add_task(write_task)
        await self.queue_manager.add_task(read_task)
        await asyncio.sleep(0.1)  # Let tasks execute
        
        # Assert
        self.assertTrue(self.queue_manager.is_rate_limited("write"))
        self.assertTrue(self.queue_manager.is_rate_limited("read"))
        self.assertGreater(self.queue_manager.get_rate_limit_delay("write"), 
                          self.queue_manager.get_rate_limit_delay("read"))

    async def test_rate_limit_expiry(self):
        """Test rate limit expiry"""
        # Arrange
        operation_type = "write"
        backoff = 1  # 1 second backoff for testing
        
        async def failing_coroutine():
            raise RateLimitError("Rate limited", operation_type=operation_type, backoff=backoff)
            
        task = Task(
            id="expiring_task",
            priority=TaskPriority.HIGH,
            created_at=datetime.now(),
            coroutine=failing_coroutine,
            max_retries=1
        )
        
        # Act
        await self.queue_manager.add_task(task)
        await asyncio.sleep(0.1)  # Let task execute
        
        # Assert initial state
        self.assertTrue(self.queue_manager.is_rate_limited(operation_type))
        
        # Wait for expiry
        await asyncio.sleep(backoff + 0.1)
        
        # Assert expired state
        self.assertFalse(self.queue_manager.is_rate_limited(operation_type))
        self.assertEqual(self.queue_manager.get_rate_limit_delay(operation_type), 0)

    async def test_rate_limit_task_rescheduling(self):
        """Test task rescheduling after rate limit"""
        # Arrange
        attempts = 0
        operation_type = "write"
        backoff = 1  # 1 second backoff
        
        async def rate_limited_coroutine():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise RateLimitError("Rate limited", operation_type=operation_type, backoff=backoff)
            return "success"
            
        task = Task(
            id="reschedule_task",
            priority=TaskPriority.HIGH,
            created_at=datetime.now(),
            coroutine=rate_limited_coroutine,
            max_retries=2
        )
        
        # Act
        await self.queue_manager.add_task(task)
        
        # Wait for initial execution and rate limit
        await asyncio.sleep(0.1)
        
        # Assert rate limited state
        self.assertTrue(self.queue_manager.is_rate_limited(operation_type))
        task_status = self.queue_manager.get_task_status("reschedule_task")
        self.assertEqual(task_status['status'], 'rate_limited')
        
        # Wait for backoff and retry
        await asyncio.sleep(backoff + 0.2)
        
        # Assert completion
        task_status = self.queue_manager.get_task_status("reschedule_task")
        self.assertEqual(task_status['status'], 'completed')
        self.assertEqual(task_status['result'], 'success')
        self.assertEqual(attempts, 2)

if __name__ == '__main__':
    pytest.main([__file__])
