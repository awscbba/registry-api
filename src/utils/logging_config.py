"""
Standardized logging configuration for consistent log formatting across all Lambda functions.
"""

import logging
import json
import sys
from typing import Dict, Any, Optional
from datetime import datetime, timezone


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""

        # Base log structure
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields from the record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
                "exc_info",
                "exc_text",
                "stack_info",
            }:
                extra_fields[key] = value

        if extra_fields:
            log_entry["context"] = extra_fields

        return json.dumps(log_entry, default=str)


class APILogger:
    """Standardized logger for API operations."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_logger()

    def _setup_logger(self):
        """Setup logger with structured formatting."""
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def info(self, message: str, **context):
        """Log info message with context."""
        self.logger.info(message, extra=context)

    def warning(self, message: str, **context):
        """Log warning message with context."""
        self.logger.warning(message, extra=context)

    def error(self, message: str, **context):
        """Log error message with context."""
        self.logger.error(message, extra=context)

    def debug(self, message: str, **context):
        """Log debug message with context."""
        self.logger.debug(message, extra=context)

    def log_api_request(
        self,
        method: str,
        path: str,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        **additional_context,
    ):
        """Log API request with standardized format."""
        context = {
            "event_type": "api_request",
            "http_method": method,
            "path": path,
            "user_id": user_id,
            "request_id": request_id,
            **additional_context,
        }
        self.info(f"{method} {path}", **context)

    def log_api_response(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: Optional[float] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        **additional_context,
    ):
        """Log API response with standardized format."""
        context = {
            "event_type": "api_response",
            "http_method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "user_id": user_id,
            "request_id": request_id,
            **additional_context,
        }
        self.info(f"{method} {path} -> {status_code}", **context)

    def log_database_operation(
        self,
        operation: str,
        table: str,
        success: bool = True,
        duration_ms: Optional[float] = None,
        record_id: Optional[str] = None,
        **additional_context,
    ):
        """Log database operation with standardized format."""
        context = {
            "event_type": "database_operation",
            "operation": operation,
            "table": table,
            "success": success,
            "duration_ms": duration_ms,
            "record_id": record_id,
            **additional_context,
        }

        if success:
            self.info(f"Database {operation} on {table}", **context)
        else:
            self.error(f"Database {operation} failed on {table}", **context)

    def log_security_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        success: bool = True,
        **additional_context,
    ):
        """Log security event with standardized format."""
        context = {
            "event_type": "security_event",
            "security_event_type": event_type,
            "user_id": user_id,
            "ip_address": ip_address,
            "success": success,
            **additional_context,
        }

        level = "info" if success else "warning"
        getattr(self, level)(f"Security event: {event_type}", **context)


def get_logger(name: str) -> APILogger:
    """Get a standardized logger instance."""
    return APILogger(name)


# Pre-configured loggers for different components
def get_handler_logger(handler_name: str) -> APILogger:
    """Get logger for API handlers."""
    return get_logger(f"handler.{handler_name}")


def get_service_logger(service_name: str) -> APILogger:
    """Get logger for services."""
    return get_logger(f"service.{service_name}")


def get_middleware_logger(middleware_name: str) -> APILogger:
    """Get logger for middleware."""
    return get_logger(f"middleware.{middleware_name}")
