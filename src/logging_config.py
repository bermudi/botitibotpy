import os
import logging
import logging.handlers
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

class StructuredLogger:
    """Custom logger that ensures all logs have consistent structured format"""
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        
    def _format_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Format context dictionary for logging"""
        if not context:
            return {}
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'logger': self.logger.name,
            **context
        }
        
    def debug(self, msg: str, extra: Dict[str, Any] = None):
        """Log debug message with context"""
        self.logger.debug(msg, extra={'context': self._format_context(extra.get('context', {}))})
        
    def info(self, msg: str, extra: Dict[str, Any] = None):
        """Log info message with context"""
        self.logger.info(msg, extra={'context': self._format_context(extra.get('context', {}))})
        
    def warning(self, msg: str, extra: Dict[str, Any] = None):
        """Log warning message with context"""
        self.logger.warning(msg, extra={'context': self._format_context(extra.get('context', {}))})
        
    def error(self, msg: str, extra: Dict[str, Any] = None, exc_info: bool = False):
        """Log error message with context and optional exception info"""
        self.logger.error(msg, extra={'context': self._format_context(extra.get('context', {}))}, exc_info=exc_info)

class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs logs in JSON format"""
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string"""
        import json
        
        output = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        if hasattr(record, 'context'):
            output['context'] = record.context
            
        if record.exc_info:
            output['exc_info'] = self.formatException(record.exc_info)
            
        return json.dumps(output)

def setup_logging(
    log_dir: str = 'logs',
    max_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    log_level: int = logging.INFO,
    component_levels: Dict[str, int] = None
) -> None:
    """Setup application-wide logging configuration
    
    Args:
        log_dir: Directory to store log files
        max_size: Maximum size of each log file before rotation (bytes)
        backup_count: Number of backup files to keep
        log_level: Default logging level
        component_levels: Dict of component names to their specific log levels
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Create formatters
    json_formatter = JSONFormatter()
    
    # Setup handlers
    handlers = {
        # Main log file with rotation
        'main': logging.handlers.RotatingFileHandler(
            filename=log_path / 'botitibot.log',
            maxBytes=max_size,
            backupCount=backup_count,
            encoding='utf-8'
        ),
        # Error log file with rotation
        'error': logging.handlers.RotatingFileHandler(
            filename=log_path / 'error.log',
            maxBytes=max_size,
            backupCount=backup_count,
            encoding='utf-8'
        ),
        # Console output
        'console': logging.StreamHandler()
    }
    
    # Configure handlers
    handlers['main'].setFormatter(json_formatter)
    handlers['error'].setFormatter(json_formatter)
    handlers['error'].setLevel(logging.ERROR)
    handlers['console'].setFormatter(json_formatter)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Add handlers to root logger
    for handler in handlers.values():
        root_logger.addHandler(handler)
    
    # Configure component-specific levels
    if component_levels:
        for component, level in component_levels.items():
            logging.getLogger(component).setLevel(level)
            
    # Create archive directory for old logs
    archive_path = log_path / 'archive'
    archive_path.mkdir(exist_ok=True)
    
def archive_logs(log_dir: str = 'logs', max_age_days: int = 30) -> None:
    """Archive old log files
    
    Args:
        log_dir: Directory containing log files
        max_age_days: Maximum age of log files before archiving
    """
    import shutil
    from datetime import datetime, timedelta
    
    log_path = Path(log_dir)
    archive_path = log_path / 'archive'
    cutoff_date = datetime.now() - timedelta(days=max_age_days)
    
    for log_file in log_path.glob('*.log.*'):
        # Skip current log files
        if not log_file.name.endswith('.log'):
            continue
            
        # Check file modification time
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        if mtime < cutoff_date:
            # Create archive directory with timestamp
            archive_dir = archive_path / mtime.strftime('%Y-%m')
            archive_dir.mkdir(exist_ok=True)
            
            # Compress and move file
            archive_file = archive_dir / f"{log_file.name}.gz"
            with open(log_file, 'rb') as f_in:
                import gzip
                with gzip.open(archive_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
                    
            # Remove original file
            log_file.unlink()
            
def cleanup_archives(log_dir: str = 'logs', max_archives: int = 12) -> None:
    """Clean up old archive directories
    
    Args:
        log_dir: Directory containing log files
        max_archives: Maximum number of monthly archives to keep
    """
    log_path = Path(log_dir)
    archive_path = log_path / 'archive'
    
    if not archive_path.exists():
        return
        
    # Get list of archive directories sorted by name (YYYY-MM format)
    archives = sorted(
        [d for d in archive_path.iterdir() if d.is_dir()],
        reverse=True
    )
    
    # Remove oldest archives beyond the limit
    for archive in archives[max_archives:]:
        shutil.rmtree(archive)
