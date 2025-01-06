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
        await self._process_queue()
        return task.id
        
    async def _process_queue(self):
        """Process tasks in the queue based on priority"""
        while self.task_queue and len(self.running_tasks) < self.max_concurrent_tasks:
            task = heapq.heappop(self.task_queue)
            asyncio.create_task(self._run_task(task))
            
    async def _run_task(self, task: Task):
        """Run a task with the semaphore and handle retries"""
        async with self.semaphore:
            try:
                logger.info(f"Starting task {task.id}")
                self.running_tasks[task.id] = asyncio.current_task()
                
                kwargs = task.kwargs or {}
                result = await task.coroutine(*task.args, **kwargs)
                
                self.task_results[task.id] = {
                    'status': 'completed',
                    'result': result,
                    'completed_at': datetime.now()
                }
                logger.info(f"Task {task.id} completed successfully")
                
            except Exception as e:
                logger.error(f"Task {task.id} failed: {str(e)}", exc_info=True)
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    logger.info(f"Retrying task {task.id} (attempt {task.retry_count}/{task.max_retries})")
                    heapq.heappush(self.task_queue, task)
                else:
                    self.task_results[task.id] = {
                        'status': 'failed',
                        'error': str(e),
                        'completed_at': datetime.now()
                    }
            finally:
                if task.id in self.running_tasks:
                    del self.running_tasks[task.id]
                await self._process_queue()
                
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a task
        
        Args:
            task_id: ID of the task to check
            
        Returns:
            Optional[Dict[str, Any]]: Task status and result if available
        """
        if task_id in self.running_tasks:
            return {'status': 'running', 'started_at': datetime.now()}
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
        
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running or queued task
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            bool: True if task was cancelled, False if not found
        """
        # Check running tasks
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            del self.running_tasks[task_id]
            self.task_results[task_id] = {
                'status': 'cancelled',
                'completed_at': datetime.now()
            }
            return True
            
        # Check queued tasks
        for i, task in enumerate(self.task_queue):
            if task.id == task_id:
                self.task_queue.pop(i)
                heapq.heapify(self.task_queue)
                self.task_results[task_id] = {
                    'status': 'cancelled',
                    'completed_at': datetime.now()
                }
                return True
                
        return False
