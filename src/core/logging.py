"""
LeadFactory Logging Configuration
Implements structured logging with JSON output for production
"""

import logging
import logging.config
import sys
from datetime import datetime
from typing import Dict, Any
import json

from src.core.config import settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add stack info if present
        if record.stack_info:
            log_entry["stack_info"] = record.stack_info
        
        return json.dumps(log_entry, default=str)


class TextFormatter(logging.Formatter):
    """Enhanced text formatter for development"""
    
    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-15s:%(lineno)-4d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


def setup_logging():
    """Configure application logging"""
    
    # Determine formatter based on environment
    if settings.LOG_FORMAT == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Configure third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)
    
    # Set our application loggers to DEBUG in development
    if settings.is_development:
        logging.getLogger("src").setLevel(logging.DEBUG)
    
    logging.info(f"Logging configured: level={settings.LOG_LEVEL}, format={settings.LOG_FORMAT}")


class StructuredLogger:
    """Enhanced logger with structured logging capabilities"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def _log_with_extra(self, level: int, message: str, **kwargs):
        """Log message with extra structured data"""
        extra_fields = {k: v for k, v in kwargs.items() if k != "exc_info"}
        
        # Create log record with extra fields
        record = self.logger.makeRecord(
            name=self.logger.name,
            level=level,
            fn="",
            lno=0,
            msg=message,
            args=(),
            exc_info=kwargs.get("exc_info"),
        )
        record.extra_fields = extra_fields
        
        self.logger.handle(record)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with structured data"""
        self._log_with_extra(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with structured data"""
        self._log_with_extra(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with structured data"""
        self._log_with_extra(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with structured data"""
        self._log_with_extra(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with structured data"""
        self._log_with_extra(logging.CRITICAL, message, **kwargs)
    
    def log_assessment_start(self, assessment_id: str, lead_id: str, **kwargs):
        """Log assessment start with structured data"""
        self.info(
            "Assessment started",
            assessment_id=assessment_id,
            lead_id=lead_id,
            **kwargs
        )
    
    def log_assessment_complete(self, assessment_id: str, duration_ms: int, **kwargs):
        """Log assessment completion with metrics"""
        self.info(
            "Assessment completed",
            assessment_id=assessment_id,
            duration_ms=duration_ms,
            **kwargs
        )
    
    def log_api_call(self, service: str, endpoint: str, duration_ms: int, status_code: int = None, **kwargs):
        """Log external API call with metrics"""
        self.info(
            f"API call to {service}",
            service=service,
            endpoint=endpoint,
            duration_ms=duration_ms,
            status_code=status_code,
            **kwargs
        )
    
    def log_cost_tracking(self, service: str, cost_cents: int, **kwargs):
        """Log cost tracking information"""
        self.info(
            f"Cost tracking for {service}",
            service=service,
            cost_cents=cost_cents,
            cost_dollars=cost_cents / 100.0,
            **kwargs
        )


def get_logger(name: str) -> StructuredLogger:
    """Get enhanced structured logger instance"""
    return StructuredLogger(name)