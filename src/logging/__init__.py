import logging
import logging.handlers
import os
import json
from pathlib import Path
from datetime import datetime
from functools import wraps

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        if hasattr(record, "extra"):
            log_obj.update(record.extra)
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

def setup_logging(app_name="botitibot"):
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Console handler with colored output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    
    # File handler with JSON formatting and rotation
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / f"{app_name}.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(JSONFormatter())
    
    # Add handlers to root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Create component loggers
    components = ['content', 'social', 'scheduler', 'database']
    loggers = {}
    
    for component in components:
        logger = logging.getLogger(f"{app_name}.{component}")
        logger.setLevel(logging.INFO)
        loggers[component] = logger
    
    return loggers

def log_function_call(logger):
    """Decorator to log function calls with parameters and return values"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.debug(
                f"Calling {func_name}",
                extra={
                    "function": func_name,
                    "args": str(args),
                    "kwargs": str(kwargs)
                }
            )
            try:
                result = func(*args, **kwargs)
                logger.debug(
                    f"{func_name} completed successfully",
                    extra={
                        "function": func_name,
                        "result": str(result)
                    }
                )
                return result
            except Exception as e:
                logger.error(
                    f"Error in {func_name}",
                    exc_info=True,
                    extra={
                        "function": func_name,
                        "error": str(e)
                    }
                )
                raise
        return wrapper
    return decorator
