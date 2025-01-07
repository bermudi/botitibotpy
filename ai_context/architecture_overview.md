# Architecture Overview

This document provides an overview of the project's architecture, based on the contents of the `src/` directory.

## Core Components

The project is structured into the following main components:

### `src/config.py`

This file defines the project's configuration, loading environment variables from a `.env` file using the `dotenv` library. It includes settings for:

-   **Core Settings**:
    -   Application name and logging configuration
    -   Component-specific log levels
    -   Environment variable validation
-   **API Configuration**:
    -   OpenAI API settings (key, base URL, model)
    -   Google API configuration for Gemini
-   **Platform Credentials**:
    -   Twitter authentication settings
    -   Bluesky authentication settings
-   **Validation**:
    -   Environment variable validation
    -   Required variable checking

### `src/content/`

This directory contains the `generator.py` file, which implements content generation and management:

-   **Content Generation**:
    -   Uses LlamaIndex with OpenAI for content generation
    -   Integrates Gemini embeddings for vector search
    -   Supports direct prompts and RAG-based generation
    -   Configurable content parameters (length, tone, style)
-   **Content Management**:
    -   Persistent vector storage using ChromaDB
    -   Document change tracking with content hashing
    -   Support for multiple content sources:
        -   Directory-based content loading
        -   Web page content parsing
        -   RSS feed monitoring
    -   Automatic content updates and indexing

### `src/database/`

This directory contains files for database interaction:

-   `models.py`: SQLAlchemy models including:
    -   `Platform`: Enum for supported platforms (`TWITTER`, `BLUESKY`)
    -   `Credentials`: Secure storage for platform authentication
    -   `Post`: Tracks posts with platform IDs and content
    -   `EngagementMetrics`: Comprehensive engagement tracking
    -   `Comment`: Manages post interactions and responses
-   `operations.py`: Database operations including:
    -   Credential management (create, retrieve, update)
    -   Post tracking and metrics collection
    -   Comment management with reply tracking
    -   Structured logging for all operations

### `src/logging/`

This directory contains the application's comprehensive logging system:

-   **Structured Logging**:
    -   JSON-formatted log output
    -   Consistent context tracking
    -   Component-specific logging
-   **Log Management**:
    -   Rotated file logging (10MB files, 5 backups)
    -   Separate error logging
    -   Console output for development
    -   Log archival and cleanup
-   **Configuration**:
    -   Component-specific log levels
    -   Configurable rotation settings
    -   Archive management (30-day retention)

### `src/monitoring.py`

This file implements a comprehensive monitoring system for tracking system resources and application performance:

-   **Resource Monitoring**:
    -   Tracks CPU usage, memory usage, and disk usage
    -   Collects metrics at regular intervals
    -   Maintains 24-hour history of resource metrics
    -   Configurable alert thresholds for resource usage
-   **Performance Monitoring**:
    -   Tracks task counts, error counts, and success rates
    -   Measures average task duration
    -   Maintains performance metrics history
    -   Configurable alert thresholds for performance
-   **Alert System**:
    -   Generates alerts for threshold violations
    -   Implements alert cooldown to prevent alert spam
    -   Logs alerts with detailed context
-   **Metrics Collection**:
    -   Provides methods to record task completion metrics
    -   Maintains task duration history per task type
    -   Offers summary views of current metrics

### `src/scheduler/`

This directory contains files for scheduling and managing tasks:

-   `exceptions.py`: Defines custom exceptions, such as `RateLimitError`, which includes a `retry_after` attribute.
-   `queue_manager.py`: Manages a priority queue of tasks, including:
    -   Task prioritization with `HIGH`, `MEDIUM`, and `LOW` priorities
    -   Concurrent task execution with configurable limits
    -   Rate limit handling with exponential backoff
    -   Task cancellation and cleanup
    -   Queue status monitoring
    -   Resource management with semaphores
    -   Graceful shutdown capabilities
-   `task_scheduler.py`: Schedules and executes tasks, including:
    -   Platform-specific configurations (`PlatformConfig`) for rate limits and retries
    -   Configurable intervals for content generation, reply checking, and metrics collection
    -   Integration with database operations, content generation, and social media clients
    -   Dynamic configuration updates
    -   Task type-specific interval management
    -   Comprehensive logging with context

### `src/social/`

This directory contains platform-specific clients:

-   `twitter.py`: Twitter client using `twitter_openapi_python`:
    -   Cookie-based authentication with persistence
    -   Automatic retry mechanism with exponential backoff
    -   Comprehensive error handling and logging
    -   Platform-specific API adaptations
-   `bluesky.py`: Bluesky client using `atproto`:
    -   Context manager-based resource management
    -   Structured logging for operations
    -   Support for posts with links
    -   Timeline and thread retrieval

## Overall Architecture

The project uses a modular design, separating concerns into distinct components. The `content` module handles content loading and generation, the `database` module manages data persistence, the `scheduler` module handles task scheduling and execution, the `social` module interacts with social media platforms, the `logging` module provides a comprehensive logging system, and the `monitoring` module tracks system resources and application performance. The `config` module provides configuration settings for the entire project.
