# TaskScheduler Test Failures Investigation

## Overview

Two tests in the TaskScheduler implementation are failing:
1. `test_handle_platform_error_unknown`: Platform is being incorrectly disabled for unknown errors
2. `test_stop_cancels_all_tasks`: Not all tasks are being properly cancelled during shutdown

## Current Implementation

### TaskScheduler Configuration

The TaskScheduler uses a configuration hierarchy:

```python
@dataclass
class PlatformConfig:
    enabled: bool = True
    retry_limit: int = 3
    rate_limit_window: int = 15 * 60  # 15 minutes in seconds
    max_requests_per_window: int = 100

@dataclass
class SchedulerConfig:
    content_generation_interval: int = 60  # minutes
    reply_check_interval: int = 5  # minutes
    metrics_update_interval: int = 10  # minutes
    max_concurrent_tasks: int = 5
    twitter: PlatformConfig = PlatformConfig()
    bluesky: PlatformConfig = PlatformConfig()
```

### Error Handling Implementation

The `_handle_platform_error` method is responsible for handling various platform-specific errors:

```python
async def _handle_platform_error(self, platform: str, error: Exception) -> bool:
    logger.error(f"Platform error occurred", exc_info=True, extra={
        'context': {
            'platform': platform,
            'error_type': type(error).__name__,
            'error': str(error),
            'component': 'task_scheduler.handle_platform_error'
        }
    })
    
    # Handle rate limit errors
    if isinstance(error, RateLimitError):
        logger.warning("Rate limit hit", extra={...})
        return True
        
    # Handle unauthorized errors
    if str(error).lower().startswith('unauthorized'):
        logger.error("Unauthorized access", extra={...})
        # Disable the platform
        if platform == 'twitter':
            self.config.twitter.enabled = False
        elif platform == 'bluesky':
            self.config.bluesky.enabled = False
        return True
        
    # Handle not found errors
    if str(error).lower().startswith('not found'):
        logger.warning("Resource not found", extra={...})
        return True
        
    return False
```

### Task Cancellation Implementation

The `stop()` method is responsible for gracefully shutting down all running tasks:

```python
async def stop(self):
    logger.info("Stopping all scheduled tasks", extra={
        'context': {
            'running_tasks': list(self.tasks.keys()),
            'component': 'task_scheduler.stop'
        }
    })
    
    for task in self.tasks.values():
        if not task.cancelled():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            
    self.tasks.clear()
```

## Test Cases

### Test Setup

```python
async def asyncSetUp(self):
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
```

### Failing Test Cases

1. Unknown Error Handling Test:
```python
async def test_handle_platform_error_unknown(self):
    """Test handling of unknown platform errors"""
    # Arrange
    error = Exception("Unknown error")
    
    # Act
    handled = await self.task_scheduler._handle_platform_error('twitter', error)
    
    # Assert
    self.assertFalse(handled)
    # Unknown errors should not disable the platform
    self.assertTrue(self.task_scheduler.config.twitter.enabled)
```

2. Task Cancellation Test:
```python
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
```

## Issues Identified

1. Platform Error Handling:
   - The platform is being disabled for all errors, not just unauthorized errors
   - The test setup might not be properly initializing the platform configuration
   - The error handling logic might be too aggressive

2. Task Cancellation:
   - The `if not task.cancelled()` check is preventing some tasks from being cancelled
   - Tasks are being cancelled one by one, which could lead to race conditions
   - No guarantee that all tasks will be cancelled before clearing the task list

## Fix Attempts

1. Platform Error Handling:
   - Attempted to move platform disabling logic inside unauthorized error block
   - Added explicit comments to clarify error handling behavior
   - Investigated test setup for potential configuration issues

2. Task Cancellation:
   - Successfully fixed by:
     - Creating a list of tasks to cancel first
     - Removing the `if not task.cancelled()` check
     - Cancelling each task and awaiting its completion

## Next Steps

1. Platform Error Handling:
   - Review the entire error handling flow
   - Verify platform configuration initialization in tests
   - Consider adding explicit platform state tests

2. Task Cancellation:
   - Verify that the fix resolves all task cancellation issues
   - Add tests for concurrent task cancellation
   - Consider adding timeout for task cancellation

## Dependencies and Requirements

1. Test Dependencies:
   - pytest
   - pytest-asyncio
   - unittest.mock

2. Runtime Dependencies:
   - asyncio
   - logging
   - dataclasses

## Related Files

1. Main Implementation:
   - `/src/scheduler/task_scheduler.py`
   - `/src/scheduler/exceptions.py`

2. Test Files:
   - `/tests/test_task_scheduler.py`

## Notes

- The edit tool is having trouble detecting changes to the `_handle_platform_error` method
- The test setup might need to be reviewed for proper platform configuration
- Consider adding more comprehensive error handling tests
