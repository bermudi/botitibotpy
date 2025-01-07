# Architecture Overview

This document provides an overview of the project's architecture, based on the contents of the `src/` directory.

## Core Components

The project is structured into the following main components:

### `src/config.py`

This file defines the project's configuration, loading environment variables from a `.env` file using the `dotenv` library. It includes settings for:

-   **Core Settings**:
    -   Application name (`APP_NAME`) and logging configuration (`LOG_LEVEL`, `LOG_DIR`)
    -   Component-specific log levels (`CONTENT_LOG_LEVEL`, `SOCIAL_LOG_LEVEL`, `SCHEDULER_LOG_LEVEL`, `DATABASE_LOG_LEVEL`)
    -   Environment variable validation
-   **API Configuration**:
    -   OpenAI API settings (`OPENAI_API_KEY`, `OPENAI_API_BASE`, `OPENAI_API_MODEL`)
    -   Google API configuration for Gemini (`GOOGLE_API_KEY`)
-   **Platform Credentials**:
    -   Twitter authentication settings (`TWITTER_USERNAME`, `TWITTER_PASSWORD`)
    -   Bluesky authentication settings (`BLUESKY_IDENTIFIER`, `BLUESKY_PASSWORD`)
-   **Validation**:
    -   Environment variable validation
    -   Required variable checking (`OPENAI_API_KEY` is required)

### `src/content/`

This directory contains the `generator.py` file, which implements content generation and management:

-   **Content Generation**:
    -   Uses LlamaIndex with OpenAI for content generation using `VectorStoreIndex` and `OpenAI`
    -   Integrates Gemini embeddings for vector search using `GeminiEmbedding`
    -   Supports direct prompts using `direct_prompt` and RAG-based generation using `generate_post`
    -   Configurable content parameters (length, tone, style) using `_build_generation_prompt`
-   **Content Management** (Needs Implementation):
    -   Persistent vector storage using ChromaDB with `chromadb.PersistentClient`
    -   Document change tracking with content hashing using `_calculate_document_hash`
    -   Support for multiple content sources:
        -   Directory-based content loading using `SimpleDirectoryReader` and `load_content_source`
        -   Web page content parsing using `load_webpage` and `load_webpage_batch`
        -   RSS feed monitoring using `parse_rss_feed` and `monitor_rss_feed`
    -   Missing functionality:
        -   Content source listing (`list_sources` method)
        -   Index updating (`update_index` method)
        -   Proper content source loading mechanism

### `src/database/`

This directory contains files for database interaction:

-   `models.py`: SQLAlchemy models including:
    -   `Platform`: Enum for supported platforms (`TWITTER`, `BLUESKY`)
    -   `Credentials`: Secure storage for platform authentication, including `id`, `platform`, `username`, `auth_data`, `created_at`, `updated_at`
    -   `Post`: Tracks posts with platform IDs and content, including `id`, `platform_post_id`, `credentials_id`, `content`, `created_at`, `updated_at`
    -   `EngagementMetrics`: Comprehensive engagement tracking, including `id`, `post_id`, `likes`, `replies`, `reposts`, `views`, `engagement_rate`, `last_updated`
    -   `Comment`: Manages post interactions and responses, including `id`, `post_id`, `platform_comment_id`, `author_username`, `content`, `is_replied_to`, `created_at`, `our_reply_id`, `our_reply_content`, `replied_at`
-   `operations.py`: Database operations including:
    -   Credential management (create, retrieve, update) using `create_credentials`, `get_credentials`, `update_credentials`
    -   Post tracking and metrics collection using `create_post`, `get_post`, `get_recent_posts`, `update_post_metrics`, `get_post_metrics`
    -   Comment management with reply tracking using `create_comment`, `get_unreplied_comments`, `mark_comment_replied`
    -   Structured logging for all operations

### `src/logging/`

This directory contains the application's comprehensive logging system:

-   **Structured Logging**:
    -   JSON-formatted log output using `JSONFormatter`
    -   Consistent context tracking using `StructuredLogger`
    -   Component-specific logging
-   **Log Management**:
    -   Rotated file logging (10MB files, 5 backups) using `RotatingFileHandler`
    -   Separate error logging to `error.log`
    -   Console output for development using `StreamHandler`
    -   Log archival and cleanup using `archive_logs` and `cleanup_archives`
-   **Configuration**:
    -   Component-specific log levels configurable via `component_levels`
    -   Configurable rotation settings (`max_size`, `backup_count`)
    -   Archive management (30-day retention) using `archive_logs`

### `src/monitoring.py`

This file implements a comprehensive monitoring system for tracking system resources and application performance:

-   **Resource Monitoring**:
    -   Tracks CPU usage, memory usage, and disk usage using `psutil`
    -   Collects metrics at regular intervals
    -   Maintains 24-hour history of resource metrics
    -   Configurable alert thresholds for resource usage (e.g., `cpu_percent`, `memory_percent`, `disk_usage_percent`)
-   **Performance Monitoring**:
    -   Tracks task counts, error counts, and success rates
    -   Measures average task duration
    -   Maintains performance metrics history
    -   Configurable alert thresholds for performance (e.g., `error_rate`, `task_duration`)
-   **Alert System**:
    -   Generates alerts for threshold violations using `_generate_alert`
    -   Implements alert cooldown to prevent alert spam using `active_alerts` and `alert_cooldown`
    -   Logs alerts with detailed context
-   **Metrics Collection**:
    -   Provides methods to record task completion metrics using `record_task_completion`
    -   Maintains task duration history per task type
    -   Offers summary views of current metrics using `get_metrics_summary`
-   `system.py`: Implements system monitoring using `SystemMonitoring` class
    -   Provides a method `get_current_status` to view system status and active tasks

### `src/scheduler/`

This directory contains files for scheduling and managing tasks:

-   `exceptions.py`: Defines custom exceptions, such as `RateLimitError`, which includes:
    -   Operation type ("auth", "write", "read")
    -   Backoff time in seconds
    -   Error message
-   `queue_manager.py`: Manages a priority queue of tasks using `heapq`, including:
    -   Task prioritization with `HIGH`, `MEDIUM`, and `LOW` priorities using `TaskPriority` enum
    -   Concurrent task execution with configurable limits using `asyncio.Semaphore`
    -   Operation-specific rate limit tracking
    -   Rate limit status checking and delay calculation
    -   Task cancellation and cleanup using `cancel_task`
    -   Queue status monitoring using `get_queue_status`
    -   Resource management with semaphores
    -   Graceful shutdown capabilities using `shutdown`
-   `task_scheduler.py`: Schedules and executes tasks using `asyncio`, including:
    -   Platform-specific configurations (`PlatformConfig`) for rate limits and retries
    -   Configurable intervals for content generation, reply checking, and metrics collection
    -   Integration with database operations, content generation, and social media clients
    -   Dynamic configuration updates using `update_config`
    -   Task type-specific interval management using `update_interval`
    -   Comprehensive logging with context
    -   Schedules content generation using `_schedule_content_generation`
    -   Schedules reply checking using `_schedule_reply_checking`
    -   Schedules metrics collection using `_schedule_metrics_collection`
    -   Adaptive task scheduling based on rate limits:
        -   Interval adjustment for rate-limited operations
        -   Gradual interval reduction on success
        -   Operation-specific backoff handling

### `src/cli/`

This directory contains the command-line interface for the application:

-   `cli.py`: Implements the CLI using `click` (Needs Updates):
    -   Provides commands for content generation, social media management, and system control
    -   Includes options for debugging and specifying parameters
    -   Uses `ContentGenerator`, `QueueManager`, `TaskScheduler`, `SystemMonitoring`, `TwitterClient`, and `BlueskyClient`
    -   Known Issues:
        -   Async operations not properly handled
        -   Runtime warnings about module loading
        -   Missing proper error handling for async commands
    -   **Content Commands** (Needs Fixes):
        -   `generate`: Generates content based on a prompt, length, and tone
        -   `list-sources`: Lists available content sources (not implemented)
        -   `update-index`: Updates the content source index (not implemented)
    -   **Social Commands** (Needs Fixes):
        -   `auth`: Authenticates with a social media platform
        -   `post`: Posts content to a social media platform, with optional scheduling (async issues)
        -   `list-scheduled`: Lists all scheduled posts (async issues)
        -   `cancel`: Cancels a scheduled post
    -   **System Commands**:
        -   `status`: View system status and active tasks
        -   `start`: Starts the task scheduler
        -   `stop`: Stops the task scheduler

### `src/social/`

This directory contains platform-specific clients:

-   `twitter.py`: Twitter client using `twitter_openapi_python`:
    -   Cookie-based authentication with persistence using `CookieSessionUserHandler`
    -   Automatic retry mechanism with exponential backoff using `retry_on_failure` decorator
    -   Comprehensive error handling and logging
    -   Platform-specific API adaptations
    -   Provides methods for posting content (`post_content`), fetching timeline (`get_timeline`), fetching tweet threads (`get_tweet_thread`), liking tweets (`like_tweet`), replying to tweets (`reply_to_tweet`), and fetching author feed (`get_author_feed`)
-   `bluesky.py`: Bluesky client using `atproto`:
    -   Context manager-based resource management using context manager
    -   Structured logging for operations
    -   Support for posts with links
    -   Timeline and thread retrieval
    -   Simplified rate limiting with operation-specific buckets:
        -   Separate buckets for "auth", "write", and "read" operations
        -   Local rate limit tracking with reserved capacity
        -   Graceful degradation with shorter backoff times
        -   Rate limit error propagation with operation type and backoff info
    -   Provides methods for fetching timeline (`get_timeline`), fetching post threads (`get_post_thread`), liking posts (`like_post`), and replying to posts (`reply_to_post`)

## Overall Architecture

The project uses a modular design, separating concerns into distinct components. The `content` module handles content loading and generation, the `database` module manages data persistence, the `scheduler` module handles task scheduling and execution, the `social` module interacts with social media platforms, the `logging` module provides a comprehensive logging system, and the `monitoring` module tracks system resources and application performance. The `config` module provides configuration settings for the entire project.
