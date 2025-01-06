# QueueManager Implementation Report
*Date: 2025-01-06*

## Overview
This report details the current issues and attempted solutions in the QueueManager implementation, specifically focusing on task cancellation, retry mechanisms, and priority ordering.

## Current Issues

### 1. Task Cancellation
#### Problem
The task cancellation mechanism is not working as expected. In `test_cancel_queued_task`, cancelled tasks are still appearing in the results with a 'completed' status.

```python
# From test_queue_manager.py
async def test_cancel_queued_task(self):
    # ...
    await self.queue_manager.cancel_task("queued")
    self.assertNotIn("queued", self.queue_manager.task_results)  # This fails
```

#### Root Cause
The issue stems from a race condition in the task execution flow:

1. When a task is cancelled via `cancel_task()`, we attempt to remove it from the queue:
```python
# In queue_manager.py
async def cancel_task(self, task_id: str) -> bool:
    # ...
    for task in list(self.task_queue):
        if task.id == task_id:
            self.task_queue.remove(task)
            self.task_results[task_id] = {
                'status': 'cancelled',
                'error': 'Task cancelled before execution',
                'completed_at': datetime.now()
            }
            return True
```

2. However, due to the async nature of the code, the task might already be picked up by `_process_queue()` before the cancellation is processed:
```python
async def _process_queue(self):
    # ...
    task = heapq.heappop(self.task_queue)
    running_task = asyncio.create_task(self._run_task(task))
```

#### Attempted Solutions
1. Added status checks before task execution:
```python
if task.id in self.task_results and self.task_results[task.id]['status'] == 'cancelled':
    return
```

2. Tried to implement a pre-execution hook to check cancellation status:
```python
async def _pre_execute_check(self, task_id):
    return task_id not in self.task_results or self.task_results[task_id]['status'] != 'cancelled'
```

### 2. Task Retry Mechanism
#### Problem
The retry mechanism is not functioning correctly. In `test_task_retry`, tasks are not being retried the expected number of times.

#### Root Cause
The retry loop in `_run_task()` is not properly handling the retry state:
```python
while retry_count <= task.max_retries:
    try:
        # ...
    except Exception as e:
        retry_count += 1
        if retry_count <= task.max_retries:
            logger.warning(f"Task {task.id} failed, attempt {retry_count}/{task.max_retries + 1}: {str(e)}")
            continue
```

The issue is that we're not properly waiting between retries and the retry count is not being properly tracked.

### 3. Priority Ordering
#### Problem
Tasks are not being executed in the correct priority order. High priority tasks are sometimes executed after lower priority tasks.

#### Root Cause
The issue lies in the async task scheduling:
```python
async def add_task(self, task: Task) -> str:
    heapq.heappush(self.task_queue, task)
    asyncio.create_task(self._process_queue())
    return task.id
```

We're not properly waiting for the task to be queued before processing the next task.

## Proposed Solutions

### 1. Task Cancellation
Implement a two-phase cancellation:
1. Mark task as cancelled in a separate cancelled_tasks set
2. Check this set before task execution
3. Use atomic operations for status updates

### 2. Task Retry
1. Implement a proper retry delay mechanism
2. Use a separate retry counter per task
3. Ensure proper state tracking between retries

### 3. Priority Queue
1. Implement a priority lock mechanism
2. Wait for task queuing to complete before processing
3. Use a proper async priority queue implementation

## Next Steps
1. Implement the two-phase cancellation mechanism
2. Add proper retry delay and state tracking
3. Refactor the priority queue handling to ensure proper ordering
4. Add more comprehensive logging for debugging
5. Add unit tests for edge cases in task cancellation and retry scenarios

## References
- [asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
- [heapq Documentation](https://docs.python.org/3/library/heapq.html)
- Current Implementation: `/home/daniel/build/botitibot-py/src/scheduler/queue_manager.py`
- Test Suite: `/home/daniel/build/botitibot-py/tests/test_queue_manager.py`
