import logging
import logging.handlers
import os
import json
import threading
from pathlib import Path
from datetime import datetime
from functools import wraps
from typing import Dict, Any, Optional

class LogLevelManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(LogLevelManager, cls).__new__(cls)
                cls._instance._component_levels = {}
            return cls._instance

    def set_component_level(self, component: str, level: int) -> None:
        """Set logging level for a specific component at runtime"""
        logger = logging.getLogger(f"botitibot.{component}")
        logger.setLevel(level)
        self._component_levels[component] = level

    def get_component_level(self, component: str) -> int:
        """Get current logging level for a component"""
        return self._component_levels.get(component, logging.INFO)

class StructuredJSONFormatter(logging.Formatter):
    def __init__(self):
        super().__init__()
        self.default_msec_format = '%s.%03d'

    def format(self, record) -> str:
        log_obj = {
            "timestamp": self.formatTime(record, self.default_msec_format),
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "thread_name": record.threadName,
            "process": record.process,
            "message": record.getMessage(),
        }

        # Add structured context if available
        if hasattr(record, 'context'):
            log_obj['context'] = record.context

        # Add task-specific information if available
        if hasattr(record, 'task_id'):
            log_obj['task'] = {
                'id': record.task_id,
                'name': getattr(record, 'task_name', None),
                'status': getattr(record, 'task_status', None)
            }

        # Add exception information if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Add any extra attributes
        if hasattr(record, 'extra'):
            log_obj.update(record.extra)

        return json.dumps(log_obj)

def setup_logging(
    app_name: str = "botitibot",
    log_dir: Optional[Path] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG
) -> Dict[str, logging.Logger]:
    """
    Setup comprehensive logging system with rotation and component-specific loggers
    """
    # Create logs directory if not specified or doesn't exist
    if log_dir is None:
        log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture all levels, let handlers filter

    # Console handler with colored output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)

    # Main JSON file handler with rotation
    main_file_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / f"{app_name}.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    main_file_handler.setLevel(file_level)
    main_file_handler.setFormatter(StructuredJSONFormatter())

    # Error-specific JSON file handler
    error_file_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / f"{app_name}_error.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(StructuredJSONFormatter())

    # Add handlers to root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(main_file_handler)
    root_logger.addHandler(error_file_handler)

    # Create component loggers
    components = ['content', 'social', 'scheduler', 'database']
    loggers = {}

    for component in components:
        logger = logging.getLogger(f"{app_name}.{component}")
        logger.setLevel(logging.INFO)  # Default level, can be changed at runtime
        
        # Component-specific file handler
        component_file_handler = logging.handlers.RotatingFileHandler(
            filename=log_dir / f"{app_name}_{component}.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        component_file_handler.setLevel(file_level)
        component_file_handler.setFormatter(StructuredJSONFormatter())
        logger.addHandler(component_file_handler)
        
        loggers[component] = logger

    return loggers

def log_task(logger, task_id: str, task_name: str):
    """Decorator to log task execution with detailed context"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            
            # Prepare context for structured logging
            context = {
                'task_start_time': start_time.isoformat(),
                'args': str(args),
                'kwargs': str(kwargs)
            }

            logger.info(
                f"Starting task {task_name}",
                extra={
                    'context': context,
                    'task_id': task_id,
                    'task_name': task_name,
                    'task_status': 'started'
                }
            )

            try:
                result = func(*args, **kwargs)
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                context.update({
                    'task_end_time': end_time.isoformat(),
                    'duration_seconds': duration,
                    'success': True
                })

                logger.info(
                    f"Task {task_name} completed successfully",
                    extra={
                        'context': context,
                        'task_id': task_id,
                        'task_name': task_name,
                        'task_status': 'completed'
                    }
                )
                return result

            except Exception as e:
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                context.update({
                    'task_end_time': end_time.isoformat(),
                    'duration_seconds': duration,
                    'success': False,
                    'error': str(e)
                })

                logger.error(
                    f"Task {task_name} failed",
                    exc_info=True,
                    extra={
                        'context': context,
                        'task_id': task_id,
                        'task_name': task_name,
                        'task_status': 'failed'
                    }
                )
                raise

        return wrapper
    return decorator

def log_function_call(logger):
    """Decorator to log function calls with parameters and return values"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            start_time = datetime.now()

            context = {
                'function_start_time': start_time.isoformat(),
                'args': str(args),
                'kwargs': str(kwargs)
            }

            logger.debug(
                f"Calling {func_name}",
                extra={
                    'context': context,
                    'function': func_name
                }
            )

            try:
                result = func(*args, **kwargs)
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                context.update({
                    'function_end_time': end_time.isoformat(),
                    'duration_seconds': duration,
                    'success': True
                })

                logger.debug(
                    f"{func_name} completed successfully",
                    extra={
                        'context': context,
                        'function': func_name,
                        'result': str(result)
                    }
                )
                return result

            except Exception as e:
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                context.update({
                    'function_end_time': end_time.isoformat(),
                    'duration_seconds': duration,
                    'success': False,
                    'error': str(e)
                })

                logger.error(
                    f"Error in {func_name}",
                    exc_info=True,
                    extra={
                        'context': context,
                        'function': func_name
                    }
                )
                raise

        return wrapper
    return decorator
