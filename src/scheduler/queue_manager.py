import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import heapq
from .exceptions import RateLimitError

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
    retries: int = 0
    
    def __lt__(self, other):
        # For priority queue comparison
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at

class QueueManager:
    def __init__(self, max_concurrent_tasks: int = 5, log_level: int = logging.INFO):
        """Initialize the queue manager
        
        Args:
            max_concurrent_tasks: Maximum number of tasks that can run concurrently
            log_level: Logging level to use
        """
        logger.setLevel(log_level)
        logger.info("Initializing QueueManager", extra={
            'context': {
                'max_concurrent_tasks': max_concurrent_tasks,
                'component': 'queue_manager'
            }
        })
        
        self.max_concurrent_tasks = max_concurrent_tasks
        self.task_queue = []  # Priority queue
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self._task_results: Dict[str, Any] = {}
        self.cancelled_tasks = set()  # Track cancelled tasks
        self.queue_lock = asyncio.Lock()  # Lock for queue operations
        self.rate_limit_delays: Dict[str, datetime] = {}  # Track rate limit delays by platform
        
    async def add_task(self, task: Task) -> str:
        """Add a task to the queue"""
        logger.debug("Adding task to queue", extra={
            'context': {
                'task_id': task.id,
                'priority': task.priority.name,
                'retries': task.retries,
                'component': 'queue_manager.add_task'
            }
        })
        
        async with self.queue_lock:
            heapq.heappush(self.task_queue, task)
            
        logger.info("Successfully added task to queue", extra={
            'context': {
                'task_id': task.id,
                'queue_size': len(self.task_queue),
                'component': 'queue_manager.add_task'
            }
        })
        return task.id
        
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        logger.info("Attempting to cancel task", extra={
            'context': {
                'task_id': task_id,
                'component': 'queue_manager.cancel_task'
            }
        })
        
        # Check if task is running
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            self.cancelled_tasks.add(task_id)
            logger.info("Cancelled running task", extra={
                'context': {
                    'task_id': task_id,
                    'component': 'queue_manager.cancel_task'
                }
            })
            return True
            
        # Check if task is in queue
        async with self.queue_lock:
            for i, task in enumerate(self.task_queue):
                if task.id == task_id:
                    self.task_queue.pop(i)
                    heapq.heapify(self.task_queue)
                    self.cancelled_tasks.add(task_id)
                    logger.info("Cancelled queued task", extra={
                        'context': {
                            'task_id': task_id,
                            'component': 'queue_manager.cancel_task'
                        }
                    })
                    return True
                    
        logger.warning("Task not found for cancellation", extra={
            'context': {
                'task_id': task_id,
                'component': 'queue_manager.cancel_task'
            }
        })
        return False
        
    async def _execute_task(self, task: Task):
        """Execute a task and handle any errors"""
        try:
            logger.debug("Executing task", extra={
                'context': {
                    'task_id': task.id,
                    'retries': task.retries,
                    'component': 'queue_manager.execute_task'
                }
            })
            
            async with self.semaphore:
                if task.kwargs is None:
                    task.kwargs = {}
                result = await task.coroutine(*task.args, **task.kwargs)
                self._task_results[task.id] = result
                
                logger.info("Task completed successfully", extra={
                    'context': {
                        'task_id': task.id,
                        'component': 'queue_manager.execute_task'
                    }
                })
                
        except RateLimitError as e:
            logger.warning("Rate limit hit, scheduling retry", extra={
                'context': {
                    'task_id': task.id,
                    'retry_after': e.retry_after,
                    'component': 'queue_manager.execute_task'
                }
            })
            await self._schedule_retry(task, e.retry_after)
            
        except Exception as e:
            logger.error("Task execution failed", exc_info=True, extra={
                'context': {
                    'task_id': task.id,
                    'error': str(e),
                    'component': 'queue_manager.execute_task'
                }
            })
            
            if task.retries < task.max_retries:
                delay = 2 ** task.retries  # Exponential backoff
                await self._schedule_retry(task, delay)
            else:
                logger.error("Task failed permanently after max retries", extra={
                    'context': {
                        'task_id': task.id,
                        'max_retries': task.max_retries,
                        'component': 'queue_manager.execute_task'
                    }
                })
                self._task_results[task.id] = None
                
    async def _schedule_retry(self, task: Task, delay: int):
        """Schedule a task for retry after delay seconds"""
        task.retries += 1
        logger.info("Scheduling task retry", extra={
            'context': {
                'task_id': task.id,
                'retry_number': task.retries,
                'delay': delay,
                'component': 'queue_manager.schedule_retry'
            }
        })
        
        await asyncio.sleep(delay)
        async with self.queue_lock:
            heapq.heappush(self.task_queue, task)
            
    async def _process_queue(self):
        """Process tasks in the queue"""
        while True:
            if not self.task_queue:
                await asyncio.sleep(1)
                continue
                
            async with self.queue_lock:
                if not self.task_queue:
                    continue
                task = heapq.heappop(self.task_queue)
                
            logger.debug("Processing task from queue", extra={
                'context': {
                    'task_id': task.id,
                    'queue_size': len(self.task_queue),
                    'component': 'queue_manager.process_queue'
                }
            })
            
            # Skip cancelled tasks
            if task.id in self.cancelled_tasks:
                logger.info("Skipping cancelled task", extra={
                    'context': {
                        'task_id': task.id,
                        'component': 'queue_manager.process_queue'
                    }
                })
                continue
                
            # Create task
            self.running_tasks[task.id] = asyncio.create_task(self._execute_task(task))
            
    @property
    def task_results(self) -> Dict[str, Any]:
        """Get task results dictionary"""
        return self._task_results
        
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a task"""
        status = {
            'id': task_id,
            'status': 'unknown',
            'result': None
        }
        
        # Check if task is running
        if task_id in self.running_tasks:
            status['status'] = 'running'
            
        # Check if task is completed
        elif task_id in self._task_results:
            status['status'] = 'completed'
            status['result'] = self._task_results[task_id]
            
        # Check if task is cancelled
        elif task_id in self.cancelled_tasks:
            status['status'] = 'cancelled'
            
        # Check if task is queued
        else:
            for task in self.task_queue:
                if task.id == task_id:
                    status['status'] = 'queued'
                    status['retries'] = task.retries
                    break
                    
        logger.debug("Retrieved task status", extra={
            'context': {
                'task_id': task_id,
                'status': status['status'],
                'component': 'queue_manager.get_task_status'
            }
        })
        return status
        
    def get_queue_status(self) -> Dict[str, Any]:
        """Get the current status of the queue"""
        status = {
            'queue_size': len(self.task_queue),
            'running_tasks': len(self.running_tasks),
            'completed_tasks': len(self._task_results),
            'cancelled_tasks': len(self.cancelled_tasks)
        }
        
        logger.debug("Retrieved queue status", extra={
            'context': {
                'status': status,
                'component': 'queue_manager.get_queue_status'
            }
        })
        return status
