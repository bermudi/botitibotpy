# Architecture Overview

This document provides an overview of the project's architecture, based on the contents of the `src/` directory.

## Core Components

The project is structured into the following main components:

### `src/config.py`

This file defines the project's configuration, loading environment variables from a `.env` file using the `dotenv` library. It includes settings for:

-   **OpenAI Configuration**:
    -   `OPENAI_API_KEY`: API key for accessing OpenAI services.
    -   `OPENAI_API_BASE`: Base URL for the OpenAI API.
    -   `OPENAI_API_MODEL`: The specific OpenAI model to use.
-   **Google API Configuration**:
    -   `GOOGLE_API_KEY`: API key for accessing Google services (used for Gemini embeddings).
-   **Twitter Credentials**:
    -   `TWITTER_USERNAME`: Username for Twitter authentication.
    -   `TWITTER_PASSWORD`: Password for Twitter authentication.
-   **Bluesky Credentials**:
    -   `BLUESKY_IDENTIFIER`: Identifier for Bluesky authentication.
    -   `BLUESKY_PASSWORD`: Password for Bluesky authentication.

    The `validate` method checks if the required environment variables are set, raising a `ValueError` if any are missing.

### `src/content/`

This directory contains the `generator.py` file, which is responsible for:

-   **Content Loading and Indexing**:
    -   Loads content from directories using `SimpleDirectoryReader`.
    -   Loads and parses content from web pages using `requests` and `BeautifulSoup`.
    -   Parses RSS feeds using `feedparser`.
    -   Uses `llama_index` to create a vector store index for loaded content.
    -   Uses `chromadb` for persistent storage of the vector index.
    -   Calculates document hashes to track changes and avoid re-indexing.
-   **Content Generation**:
    -   Generates content using prompts and the OpenAI API via `llama_index`.
    -   Supports direct prompts to the LLM without using RAG.
    -   Builds prompts with optional parameters for max length, tone, and style.
-   **Document Management**:
    -   Generates unique document IDs combining file paths and content hashes.
    -   Tracks document hashes to detect changes.
-   **RSS Feed Monitoring**:
    -   Monitors RSS feeds for new entries and adds them to the index.
    -   Handles malformed RSS feeds and extracts content from various fields.

### `src/database/`

This directory contains files for database interaction:

-   `models.py`: Defines the database models using SQLAlchemy, including:
    -   `Platform`: An enumeration of social media platforms (`TWITTER`, `BLUESKY`).
    -   `Credentials`: Stores authentication data for social media platforms, including `platform`, `username`, `auth_data`, `created_at`, and `updated_at`.
    -   `Post`: Represents a post on a social media platform, including `platform_post_id`, `credentials_id`, `content`, `created_at`, and `updated_at`.
    -   `EngagementMetrics`: Stores engagement metrics for posts, including `likes`, `replies`, `reposts`, `views`, `engagement_rate`, and `last_updated`.
    -   `Comment`: Represents a comment on a post, including `platform_comment_id`, `author_username`, `content`, `is_replied_to`, `our_reply_id`, `our_reply_content`, and `replied_at`.
-   `operations.py`: Provides methods for interacting with the database, such as:
    -   Creating, retrieving, and updating credentials using methods like `create_credentials`, `get_credentials`, and `update_credentials`.
    -   Creating and retrieving posts using methods like `create_post` and `get_post`.
    -   Retrieving recent posts using `get_recent_posts`.
    -   Updating engagement metrics using `update_engagement_metrics`.
    -   Creating, retrieving, and marking comments as replied using methods like `create_comment`, `get_unreplied_comments`, and `mark_comment_replied`.

### `src/logging/`

This directory contains the application's comprehensive logging system:

-   **Core Logging Features**:
    -   Structured JSON logging for machine readability
    -   Log rotation (10MB files with 5 backups)
    -   Component-specific loggers with configurable log levels
    -   Console output for development with human-readable format
    -   File output with JSON format for machine processing
    -   Detailed function call logging with parameters and results
    -   Exception tracking with full stack traces

-   **Configuration**:
    -   Log levels configurable via environment variables:
        -   `LOG_LEVEL`: Default log level for all components
        -   Component-specific levels: `CONTENT_LOG_LEVEL`, `SOCIAL_LOG_LEVEL`, `SCHEDULER_LOG_LEVEL`, `DATABASE_LOG_LEVEL`
    -   Log directory configuration in `Config.LOG_DIR`
    -   Application name configuration in `Config.APP_NAME`

-   **Key Components**:
    -   `JSONFormatter`: Custom formatter for structured JSON log output
    -   `setup_logging`: Initializes the logging system with file and console handlers
    -   `log_function_call`: Decorator for automatic function call logging
    -   Component-specific loggers for granular control

-   **Integration**:
    -   Integrated with all major components (content, social, scheduler, database)
    -   Automatic logging of application startup and shutdown
    -   Error tracking across all components
    -   Performance monitoring through function call logging

### `src/scheduler/`

This directory contains files for scheduling and managing tasks:

-   `exceptions.py`: Defines custom exceptions, such as `RateLimitError`, which includes a `retry_after` attribute.
-   `queue_manager.py`: Manages a priority queue of tasks, including:
    -   Adding tasks with priorities (`HIGH`, `MEDIUM`, `LOW`) using `add_task`.
    -   Canceling tasks using `cancel_task`.
    -   Executing tasks concurrently using `asyncio.Semaphore`.
    -   Retrying failed tasks with exponential backoff using `_schedule_retry`.
    -   Tracking task results and status using `task_results` and `get_task_status`.
    -   Provides a method to get the queue status using `get_queue_status`.
-   `task_scheduler.py`: Schedules and executes tasks, including:
    -   Manages platform configurations using `PlatformConfig` (enabled, retry limits, rate limits).
    -   Schedules content generation, reply checking, and metrics collection at specified intervals.
    -   Uses `QueueManager` to manage task execution.
    -   Handles platform-specific errors using `_handle_platform_error`, including rate limits and authentication errors.
    -   Provides methods to update the scheduler configuration and task intervals using `update_config` and `update_interval`.
    -   Includes methods for generating and posting content, checking and handling replies, and collecting metrics.

### `src/social/`

This directory contains files for interacting with social media platforms:

-   `bluesky.py`: Implements a client for interacting with the Bluesky API using the `atproto` library, including:
    -   Setting up authentication using `client.login` with credentials from `Config`.
    -   Posting content using `client.send_post` with optional links.
    -   Retrieving timelines using `client.get_timeline`.
    -   Retrieving post threads using `client.get_post_thread`.
    -   Liking posts using `client.like`.
    -   Replying to posts using `client.send_post` with a `reply_to` parameter.
    -   Fetching an author's feed using `client.get_author_feed`.
-   `twitter.py`: Implements a client for interacting with the Twitter API using `twitter_openapi_python` and `tweepy_authlib`, including:
    -   Setting up authentication using cookie-based authentication with `CookieSessionUserHandler`.
    -   Loading existing cookies from a JSON file or creating new cookies if they don't exist.
    -   Validating cookie structure and contents.
    -   Posting content using `client.get_post_api().post_create_tweet`.
    -   Retrieving timelines using `client.get_user_api().get_home_timeline`.
    -   Retrieving tweet threads using `client.get_tweet_api().get_tweet_detail`.
    -   Liking tweets using `client.get_tweet_api().favorite_tweet`.
    -   Replying to tweets using `client.get_post_api().post_create_tweet` with a `reply_tweet_id` parameter.
    -   Fetching an author's feed using `client.get_user_api().get_user_by_screen_name` and `client.get_tweet_api().get_user_tweets`.
    -   Includes a `retry_on_failure` decorator for handling API call failures.

## Overall Architecture

The project uses a modular design, separating concerns into distinct components. The `content` module handles content loading and generation, the `database` module manages data persistence, the `scheduler` module handles task scheduling and execution, the `social` module interacts with social media platforms, and the `logging` module provides a comprehensive logging system. The `config` module provides configuration settings for the entire project.
