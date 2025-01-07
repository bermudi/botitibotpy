import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import heapq
from .exceptions import RateLimitError
from collections import defaultdict
from sqlalchemy.orm import Session
from ..database.models import ScheduledTask, Platform

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
    def __init__(self, db: Optional[Session] = None, max_concurrent_tasks: int = 5, log_level: int = logging.INFO):
        """Initialize the queue manager
        
        Args:
            db: Database session for persistence
            max_concurrent_tasks: Maximum number of tasks that can run concurrently
            log_level: Logging level to use
        """
        logger.setLevel(log_level)
        logger.info("Initializing QueueManager")
        
        self.db = db
        self.max_concurrent_tasks = max_concurrent_tasks
        self.task_queue = []
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
        """Start the queue processor and load persisted tasks"""
        if self._queue_processor is None:
            self._shutdown = False
            self._queue_processor = asyncio.create_task(self._process_queue())
            
        if self.db:
            # Load persisted tasks
            persisted_tasks = self.db.query(ScheduledTask).filter(
                ScheduledTask.status == "pending"
            ).all()
            
            for task in persisted_tasks:
                if task.platform == Platform.TWITTER:
                    from ..social.twitter import TwitterClient
                    client = TwitterClient()
                    coroutine = client.post_content
                else:
                    from ..social.bluesky import BlueskyClient
                    client = BlueskyClient()
                    coroutine = client.post_content
                
                task_obj = Task(
                    id=task.task_id,
                    priority=TaskPriority[task.priority],
                    created_at=task.created_at,
                    coroutine=coroutine,
                    args=(task.content,)
                )
                heapq.heappush(self.task_queue, task_obj)
            
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
        
    async def add_task(self, task: Task, scheduled_time: Optional[datetime] = None) -> str:
        """Add a task to the queue"""
        logger.debug(f"Adding task {task.id} to queue")
        
        async with self.queue_lock:
            heapq.heappush(self.task_queue, task)
            
            if self.db and scheduled_time:
                # Persist the task
                platform = Platform.TWITTER if "twitter" in str(task.coroutine).lower() else Platform.BLUESKY
                db_task = ScheduledTask(
                    task_id=task.id,
                    platform=platform,
                    content=task.args[0] if task.args else "",
                    scheduled_time=scheduled_time,
                    priority=task.priority.name,
                    status="pending"
                )
                self.db.add(db_task)
                self.db.commit()
            
        logger.info(f"Successfully added task {task.id} to queue")
        return task.id
        
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task by ID"""
        logger.info(f"Attempting to cancel task {task_id}")

        if task_id in self.running_tasks:
            logger.info(f"Cancelling running task {task_id}")
            self.cancelled_tasks.add(task_id)
            self.running_tasks[task_id].cancel()
            self._task_results[task_id] = {
                'status': 'cancelled',
                'result': None,
                'retries': 0
            }
            
            if self.db:
                db_task = self.db.query(ScheduledTask).filter(
                    ScheduledTask.task_id == task_id
                ).first()
                if db_task:
                    db_task.status = "cancelled"
                    self.db.commit()
                    
            return True

        # Then check if task is in queue
        async with self.queue_lock:
            for task in self.task_queue:
                if task.id == task_id:
                    logger.info(f"Cancelling queued task {task_id}")
                    self.cancelled_tasks.add(task_id)
                    self._task_results[task_id] = {
                        'status': 'cancelled',
                        'result': None,
                        'retries': task.retries
                    }
                    
                    if self.db:
                        db_task = self.db.query(ScheduledTask).filter(
                            ScheduledTask.task_id == task_id
                        ).first()
                        if db_task:
                            db_task.status = "cancelled"
                            self.db.commit()
                            
                    return True

        logger.info(f"Task {task_id} not found")
        return False

    async def get_queue_status(self) -> Dict[str, int]:
        """Get current queue status
        
        Returns:
            Dict with queue statistics including:
            - queued_tasks: Number of tasks in queue
            - running_tasks: Number of currently running tasks
            - completed_tasks: Number of completed tasks
        """
        async with self.queue_lock:
            return {
                'queued_tasks': len(self.task_queue),
                'running_tasks': len(self.running_tasks),
                'completed_tasks': len([r for r in self._task_results.values() if r.get('status') == 'completed'])
            }

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
                    continue

                task = heapq.heappop(self.task_queue)
                if task.id in self.cancelled_tasks:
                    continue

                # Create task
                async def execute_task():
                    try:
                        if task.kwargs:
                            result = await task.coroutine(*task.args, **task.kwargs)
                        else:
                            result = await task.coroutine(*task.args)
                            
                        self._task_results[task.id] = {
                            'status': 'completed',
                            'result': result,
                            'retries': task.retries
                        }
                        
                        if self.db:
                            db_task = self.db.query(ScheduledTask).filter(
                                ScheduledTask.task_id == task.id
                            ).first()
                            if db_task:
                                db_task.status = "completed"
                                self.db.commit()
                                
                    except Exception as e:
                        logger.error(f"Task {task.id} failed: {str(e)}")
                        if task.retries < task.max_retries:
                            task.retries += 1
                            heapq.heappush(self.task_queue, task)
                        else:
                            self._task_results[task.id] = {
                                'status': 'failed',
                                'error': str(e),
                                'retries': task.retries
                            }
                            
                            if self.db:
                                db_task = self.db.query(ScheduledTask).filter(
                                    ScheduledTask.task_id == task.id
                                ).first()
                                if db_task:
                                    db_task.status = "failed"
                                    self.db.commit()
                    finally:
                        if task.id in self.running_tasks:
                            del self.running_tasks[task.id]

                self.running_tasks[task.id] = asyncio.create_task(execute_task())

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
        
    def is_rate_limited(self, operation_type: str) -> bool:
        """Check if an operation type is currently rate limited"""
        return datetime.now() < self.rate_limit_delays[operation_type]

    def get_rate_limit_delay(self, operation_type: str) -> int:
        """Get remaining delay in seconds for a rate limited operation"""
        delay = (self.rate_limit_delays[operation_type] - datetime.now()).total_seconds()
        return max(0, int(delay))
