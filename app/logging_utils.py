"""
Structured JSON logging utilities for the Lyftr AI webhook API.
"""
import json
import logging
import sys
import uuid
from datetime import datetime
from typing import Any, Optional
from app.config import config


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs JSON per line."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "method"):
            log_data["method"] = record.method
        if hasattr(record, "path"):
            log_data["path"] = record.path
        if hasattr(record, "status"):
            log_data["status"] = record.status
        if hasattr(record, "latency_ms"):
            log_data["latency_ms"] = record.latency_ms
        if hasattr(record, "message_id"):
            log_data["message_id"] = record.message_id
        if hasattr(record, "dup"):
            log_data["dup"] = record.dup
        if hasattr(record, "result"):
            log_data["result"] = record.result
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def setup_logging() -> logging.Logger:
    """Set up structured JSON logging."""
    logger = logging.getLogger("lyftr-api")
    logger.setLevel(config.LOG_LEVEL)
    
    # Remove existing handlers
    logger.handlers = []
    
    # JSON handler for stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    
    return logger


def get_logger() -> logging.Logger:
    """Get the configured logger."""
    return logging.getLogger("lyftr-api")


class LogContext:
    """Helper to add structured context to logs."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_request(
        self,
        request_id: str,
        method: str,
        path: str,
        status: int,
        latency_ms: float,
        **kwargs: Any,
    ) -> None:
        """Log an HTTP request with context."""
        record = self.logger.makeRecord(
            name="lyftr-api",
            level=logging.INFO,
            fn="",
            lno=0,
            msg=f"{method} {path} {status}",
            args=(),
            exc_info=None,
        )
        record.request_id = request_id
        record.method = method
        record.path = path
        record.status = status
        record.latency_ms = latency_ms
        
        # Add extra fields
        for key, value in kwargs.items():
            setattr(record, key, value)
        
        self.logger.handle(record)
    
    def log_webhook(
        self,
        request_id: str,
        message_id: Optional[str],
        is_duplicate: bool,
        result: str,
        status: int,
        latency_ms: float,
    ) -> None:
        """Log a webhook request with specific context."""
        record = self.logger.makeRecord(
            name="lyftr-api",
            level=logging.INFO,
            fn="",
            lno=0,
            msg=f"POST /webhook {status}",
            args=(),
            exc_info=None,
        )
        record.request_id = request_id
        record.method = "POST"
        record.path = "/webhook"
        record.status = status
        record.latency_ms = latency_ms
        record.message_id = message_id
        record.dup = is_duplicate
        record.result = result
        
        self.logger.handle(record)


def create_request_id() -> str:
    """Create a unique request ID."""
    return str(uuid.uuid4())
