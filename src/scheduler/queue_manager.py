import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import heapq
from .exceptions import RateLimitError
from collections import defaultdict

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
        
        # Track rate limits by operation type
        self.rate_limit_delays: Dict[str, datetime] = defaultdict(lambda: datetime.min)
        
        self._shutdown = False
        self._queue_processor = None
        
        # Start queue processor
        self._queue_processor = asyncio.create_task(self._process_queue())
            
    async def start(self):
        """Start the queue processor"""
        if self._queue_processor is None:
            self._shutdown = False
            self._queue_processor = asyncio.create_task(self._process_queue())
            
    async def shutdown(self):
        """Shutdown the queue processor and cleanup resources"""
        self._shutdown = True
        if self._queue_processor:
            self._queue_processor.cancel()
            try:
                await self._queue_processor
            except asyncio.CancelledError:
                pass
            self._queue_processor = None
            
        # Cancel all running tasks
        tasks = list(self.running_tasks.values())
        for task in tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
                
        # Clear collections
        self.task_queue.clear()
        self.running_tasks.clear()
        self._task_results.clear()
        self.cancelled_tasks.clear()
        
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
        """Cancel a task by ID

        Args:
            task_id: ID of task to cancel

        Returns:
            bool: True if task was cancelled, False otherwise
        """
        logger.info("Attempting to cancel task", extra={
            'context': {
                'task_id': task_id,
                'component': 'queue_manager.cancel_task'
            }
        })

        # First check if task is running
        if task_id in self.running_tasks:
            logger.info("Cancelling running task", extra={
                'context': {
                    'task_id': task_id,
                    'component': 'queue_manager.cancel_task'
                }
            })
            self.cancelled_tasks.add(task_id)
            self.running_tasks[task_id].cancel()
            self._task_results[task_id] = {
                'status': 'cancelled',
                'result': None,
                'retries': 0
            }
            return True

        # Then check if task is in queue
        async with self.queue_lock:
            for task in self.task_queue:
                if task.id == task_id:
                    logger.info("Cancelling queued task", extra={
                        'context': {
                            'task_id': task_id,
                            'component': 'queue_manager.cancel_task'
                        }
                    })
                    self.cancelled_tasks.add(task_id)
                    self._task_results[task_id] = {
                        'status': 'cancelled',
                        'result': None,
                        'retries': task.retries
                    }
                    return True

        logger.warning("Task not found for cancellation", extra={
            'context': {
                'task_id': task_id,
                'component': 'queue_manager.cancel_task'
            }
        })
        return False

    async def _process_queue(self):
        """Process tasks in the queue"""
        while not self._shutdown:
            if not self.task_queue:
                await asyncio.sleep(0.1)  # Reduced sleep time for faster processing
                continue

            async with self.queue_lock:
                if not self.task_queue:
                    continue

                # Skip if we've reached max concurrent tasks
                if len(self.running_tasks) >= self.max_concurrent_tasks:
                    await asyncio.sleep(0.1)
                    continue

                task = heapq.heappop(self.task_queue)

                # Skip cancelled tasks
                if task.id in self.cancelled_tasks:
                    logger.info("Skipping cancelled task", extra={
                        'context': {
                            'task_id': task.id,
                            'component': 'queue_manager.process_queue'
                        }
                    })
                    continue

                logger.debug("Processing task from queue", extra={
                    'context': {
                        'task_id': task.id,
                        'queue_size': len(self.task_queue),
                        'component': 'queue_manager.process_queue'
                    }
                })

                # Create and store task
                task_future = asyncio.create_task(self._execute_task(task))
                self.running_tasks[task.id] = task_future

            # Wait a short time to allow other tasks to be queued
            await asyncio.sleep(0.01)

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

            # Check if task was cancelled before execution
            if task.id in self.cancelled_tasks:
                self._task_results[task.id] = {
                    'status': 'cancelled',
                    'result': None,
                    'retries': task.retries
                }
                return

            async with self.semaphore:
                if task.kwargs is None:
                    task.kwargs = {}

                # Check again for cancellation
                if task.id in self.cancelled_tasks:
                    self._task_results[task.id] = {
                        'status': 'cancelled',
                        'result': None,
                        'retries': task.retries
                    }
                    return

                result = await task.coroutine(*task.args, **task.kwargs)

                # Final cancellation check
                if task.id in self.cancelled_tasks:
                    self._task_results[task.id] = {
                        'status': 'cancelled',
                        'result': None,
                        'retries': task.retries
                    }
                else:
                    self._task_results[task.id] = {
                        'status': 'completed',
                        'result': result,
                        'retries': task.retries
                    }

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
                    'operation_type': e.operation_type,
                    'backoff': e.backoff,
                    'component': 'queue_manager.execute_task'
                }
            })
            
            # Update rate limit delay for this operation type
            self.rate_limit_delays[e.operation_type] = datetime.now() + timedelta(seconds=e.backoff)
            
            self._task_results[task.id] = {
                'status': 'rate_limited',
                'result': None,
                'retries': task.retries,
                'error': str(e),
                'operation_type': e.operation_type,
                'backoff': e.backoff
            }
            
            # Schedule retry after backoff
            await self._schedule_retry(task, e.backoff)

        except Exception as e:
            logger.error("Task execution failed", exc_info=True, extra={
                'context': {
                    'task_id': task.id,
                    'error': str(e),
                    'component': 'queue_manager.execute_task'
                }
            })

            if task.retries < task.max_retries:
                self._task_results[task.id] = {
                    'status': 'retrying',
                    'result': None,
                    'error': str(e),
                    'retries': task.retries
                }
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
                self._task_results[task.id] = {
                    'status': 'failed',
                    'result': None,
                    'error': str(e),
                    'retries': task.retries + 1  # Include the last attempt
                }
        finally:
            if task.id in self.running_tasks:
                del self.running_tasks[task.id]
                
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
        if task.id not in self.cancelled_tasks:
            async with self.queue_lock:
                heapq.heappush(self.task_queue, task)
                
    @property
    def task_results(self) -> Dict[str, Any]:
        """Get task results dictionary"""
        return self._task_results
        
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a specific task

        Args:
            task_id: ID of task to get status for

        Returns:
            Dict containing task status information or None if task not found
        """
        if task_id in self._task_results:
            return self._task_results[task_id]
        elif task_id in self.running_tasks:
            return {
                'status': 'running',
                'result': None,
                'retries': 0
            }
        elif any(task.id == task_id for task in self.task_queue):
            return {
                'status': 'queued',
                'result': None,
                'retries': 0
            }
        return None
        
    def get_queue_status(self) -> Dict[str, Any]:
        """Get the current status of the queue

        Returns:
            Dict containing queue statistics
        """
        completed = 0
        running = len(self.running_tasks)
        queued = len(self.task_queue)
        tasks_by_priority = defaultdict(int)

        for task in self.task_queue:
            tasks_by_priority[task.priority.name] += 1

        # Count completed tasks
        for result in self._task_results.values():
            if result.get('status') == 'completed':
                completed += 1

        return {
            'queued_tasks': queued,
            'running_tasks': running,
            'completed_tasks': completed,
            'tasks_by_priority': dict(tasks_by_priority)
        }

    def is_rate_limited(self, operation_type: str) -> bool:
        """Check if an operation type is currently rate limited"""
        return datetime.now() < self.rate_limit_delays[operation_type]

    def get_rate_limit_delay(self, operation_type: str) -> int:
        """Get remaining delay in seconds for a rate limited operation"""
        delay = (self.rate_limit_delays[operation_type] - datetime.now()).total_seconds()
        return max(0, int(delay))
