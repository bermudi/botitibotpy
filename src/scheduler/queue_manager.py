import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from datetime import datetime
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
        
    async def add_task(self, task: Task) -> str:
        """Add a task to the queue
        
        Args:
            task: Task object containing the coroutine and metadata
            
        Returns:
            str: Task ID
        """
        logger.info(f"Adding task {task.id} with priority {task.priority}")
        heapq.heappush(self.task_queue, task)
        # Create a new task to process the queue
        asyncio.create_task(self._process_queue())
        return task.id
        
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task
        
        Args:
            task_id: ID of task to cancel
            
        Returns:
            bool: True if task was cancelled, False if not found
        """
        # Check if task is running
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            self.task_results[task_id] = {
                'status': 'cancelled',
                'error': 'Task cancelled during execution',
                'completed_at': datetime.now()
            }
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
            return True
            
        # Check if task is queued
        for task in list(self.task_queue):  # Create a copy to avoid modification during iteration
            if task.id == task_id:
                # Remove from queue
                self.task_queue.remove(task)
                heapq.heapify(self.task_queue)
                # Store result
                self.task_results[task_id] = {
                    'status': 'cancelled',
                    'error': 'Task cancelled before execution',
                    'completed_at': datetime.now()
                }
                return True
                
        return False
        
    async def _process_queue(self):
        """Process tasks in the queue based on priority"""
        if not self.task_queue:
            return

        # Only process if we're under the concurrent task limit
        if len(self.running_tasks) >= self.max_concurrent_tasks:
            return

        # Get next task
        task = heapq.heappop(self.task_queue)
        
        # Check if task was cancelled before processing
        if task.id in self.task_results and self.task_results[task.id]['status'] == 'cancelled':
            return
            
        # Create and store the task
        running_task = asyncio.create_task(self._run_task(task))
        self.running_tasks[task.id] = running_task
        # Set initial status
        self.task_results[task.id] = {
            'status': 'running',
            'started_at': datetime.now()
        }
        
        # Schedule next task processing
        asyncio.create_task(self._process_queue())
                
    async def _run_task(self, task: Task):
        """Run a task with the semaphore and handle retries
        
        Args:
            task: Task to run
        """
        logger.info(f"Starting task {task.id}")
        
        try:
            async with self.semaphore:  # Use context manager for proper semaphore handling
                retry_count = 0
                while retry_count <= task.max_retries:
                    try:
                        # Check if task was cancelled
                        if task.id in self.task_results and self.task_results[task.id]['status'] == 'cancelled':
                            return
                            
                        # Run the task
                        result = await task.coroutine(*task.args, **(task.kwargs or {}))
                        
                        # Store result if task wasn't cancelled
                        if task.id in self.task_results and self.task_results[task.id]['status'] != 'cancelled':
                            self.task_results[task.id] = {
                                'status': 'completed',
                                'result': result,
                                'completed_at': datetime.now()
                            }
                            logger.info(f"Task {task.id} completed successfully")
                        return
                        
                    except Exception as e:
                        # Check if task was cancelled
                        if task.id in self.task_results and self.task_results[task.id]['status'] == 'cancelled':
                            return
                            
                        retry_count += 1
                        if retry_count <= task.max_retries:
                            logger.warning(f"Task {task.id} failed, attempt {retry_count}/{task.max_retries + 1}: {str(e)}")
                            await asyncio.sleep(0.1)  # Small delay before retry
                            continue
                            
                        # Store error after max retries
                        logger.error(f"Task {task.id} failed: {str(e)}")
                        if task.id in self.task_results and self.task_results[task.id]['status'] != 'cancelled':
                            self.task_results[task.id] = {
                                'status': 'failed',
                                'error': str(e),
                                'completed_at': datetime.now()
                            }
                        raise
                    
        except asyncio.CancelledError:
            # Handle task cancellation
            self.task_results[task.id] = {
                'status': 'cancelled',
                'error': 'Task cancelled during execution',
                'completed_at': datetime.now()
            }
            raise
        finally:
            # Clean up
            if task.id in self.running_tasks:
                del self.running_tasks[task.id]

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
