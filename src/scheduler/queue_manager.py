import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import heapq

logger = logging.getLogger(__name__)

class TaskPriority(Enum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3

@dataclass
class Task:
    id: str
    priority: TaskPriority
    created_at: datetime
    coroutine: Callable
    args: tuple = ()
    kwargs: dict = None
    max_retries: int = 3
    retry_count: int = 0
    
    def __lt__(self, other):
        # For priority queue comparison
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at

class RateLimitError(Exception):
    """Raised when a rate limit is hit"""
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds")

class QueueManager:
    def __init__(self, max_concurrent_tasks: int = 5):
        """Initialize the queue manager
        
        Args:
            max_concurrent_tasks: Maximum number of tasks that can run concurrently
        """
        self.max_concurrent_tasks = max_concurrent_tasks
        self.task_queue = []  # Priority queue
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self.task_results: Dict[str, Any] = {}
        self.cancelled_tasks = set()  # Track cancelled tasks
        self.queue_lock = asyncio.Lock()  # Lock for queue operations
        self.rate_limit_delays: Dict[str, datetime] = {}  # Track rate limit delays by platform
        
    async def add_task(self, task: Task) -> str:
        """Add a task to the queue
        
        Args:
            task: Task to add
            
        Returns:
            str: ID of added task
        """
        logger.info(f"Adding task {task.id} with priority {task.priority}")
        
        async with self.queue_lock:
            # Add task to queue
            heapq.heappush(self.task_queue, task)
            
            # Schedule queue processing
            asyncio.create_task(self._process_queue())
            
        return task.id
        
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task
        
        Args:
            task_id: ID of task to cancel
            
        Returns:
            bool: True if task was cancelled, False if not found
        """
        # Mark as cancelled first
        self.cancelled_tasks.add(task_id)
        self.task_results[task_id] = {
            'status': 'cancelled',
            'error': 'Task cancelled',
            'completed_at': datetime.now()
        }
        
        # Check if task is running
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
            return True
            
        # Check if task is queued
        for task in list(self.task_queue):  # Create a copy to avoid modification during iteration
            if task.id == task_id:
                # Remove from queue
                self.task_queue.remove(task)
                heapq.heapify(self.task_queue)  # Maintain heap property
                return True
                
        return False
        
    async def _execute_task(self, task: Task):
        """Execute a task with retry logic and error handling"""
        while task.retry_count <= task.max_retries:
            try:
                # Check if we need to wait for rate limit
                platform = task.kwargs.get('platform', 'default') if task.kwargs else 'default'
                if platform in self.rate_limit_delays:
                    wait_until = self.rate_limit_delays[platform]
                    if wait_until > datetime.now():
                        wait_seconds = (wait_until - datetime.now()).total_seconds()
                        logger.info(f"Waiting {wait_seconds} seconds for rate limit on {platform}")
                        await asyncio.sleep(wait_seconds)
                    del self.rate_limit_delays[platform]

                # Execute the task
                result = await task.coroutine(*task.args, **(task.kwargs or {}))
                
                # Store successful result
                self.task_results[task.id] = {
                    'status': 'completed',
                    'result': result,
                    'completed_at': datetime.now(),
                    'retries': task.retry_count
                }
                return result
                
            except RateLimitError as e:
                logger.warning(f"Rate limit hit for task {task.id}, platform {platform}")
                self.rate_limit_delays[platform] = datetime.now() + timedelta(seconds=e.retry_after)
                # Requeue the task
                task.retry_count += 1
                if task.retry_count <= task.max_retries:
                    await self.add_task(task)
                    return None
                    
            except Exception as e:
                logger.error(f"Error executing task {task.id}: {str(e)}", exc_info=True)
                task.retry_count += 1
                
                if task.retry_count <= task.max_retries:
                    # Exponential backoff for retries
                    delay = 2 ** task.retry_count
                    logger.info(f"Retrying task {task.id} in {delay} seconds (attempt {task.retry_count})")
                    await asyncio.sleep(delay)
                else:
                    # Store failed result
                    self.task_results[task.id] = {
                        'status': 'failed',
                        'error': str(e),
                        'completed_at': datetime.now(),
                        'retries': task.retry_count
                    }
                    return None
                    
        return None

    async def _process_queue(self):
        """Process tasks in the queue"""
        async with self.queue_lock:
            while self.task_queue:
                # Check if we're at max concurrent tasks
                if len(self.running_tasks) >= self.max_concurrent_tasks:
                    break
                    
                task = heapq.heappop(self.task_queue)
                
                # Skip if task was cancelled
                if task.id in self.cancelled_tasks:
                    continue
                    
                # Create and store the running task
                running_task = asyncio.create_task(self._execute_task(task))
                self.running_tasks[task.id] = running_task
                
                # Clean up task when done
                running_task.add_done_callback(
                    lambda t, task_id=task.id: self.running_tasks.pop(task_id, None)
                )

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a task
        
        Args:
            task_id: ID of the task to check
            
        Returns:
            Optional[Dict[str, Any]]: Task status and result if available
        """
        return self.task_results.get(task_id)
        
    def get_queue_status(self) -> Dict[str, Any]:
        """Get the current status of the queue
        
        Returns:
            Dict[str, Any]: Queue statistics
        """
        return {
            'queued_tasks': len(self.task_queue),
            'running_tasks': len(self.running_tasks),
            'completed_tasks': len(self.task_results),
            'tasks_by_priority': {
                priority.name: len([t for t in self.task_queue if t.priority == priority])
                for priority in TaskPriority
            }
        }
