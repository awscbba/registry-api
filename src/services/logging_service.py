"""
Enterprise logging service with structured logging, audit trails, and monitoring integration.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union
from enum import Enum

from ..core.config import config
from ..models.rbac import RoleType


class LogLevel(str, Enum):
    """Log levels for structured logging."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(str, Enum):
    """Categories of log entries for better organization."""

    AUTHENTICATION = "AUTHENTICATION"
    AUTHORIZATION = "AUTHORIZATION"
    USER_OPERATIONS = "USER_OPERATIONS"
    PROJECT_OPERATIONS = "PROJECT_OPERATIONS"
    SUBSCRIPTION_OPERATIONS = "SUBSCRIPTION_OPERATIONS"
    PASSWORD_MANAGEMENT = "PASSWORD_MANAGEMENT"
    EMAIL_OPERATIONS = "EMAIL_OPERATIONS"
    SECURITY_EVENTS = "SECURITY_EVENTS"
    API_ACCESS = "API_ACCESS"
    SYSTEM_EVENTS = "SYSTEM_EVENTS"
    ERROR_HANDLING = "ERROR_HANDLING"
    RATE_LIMITING = "RATE_LIMITING"
    AUDIT_TRAIL = "AUDIT_TRAIL"
    PERFORMANCE = "PERFORMANCE"
    DATABASE_OPERATIONS = "DATABASE_OPERATIONS"


class RequestContext:
    """Request context for logging."""

    def __init__(
        self,
        request_id: str,
        user_id: Optional[str] = None,
        user_roles: Optional[List[RoleType]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        path: Optional[str] = None,
        method: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ):
        self.request_id = request_id
        self.user_id = user_id
        self.user_roles = user_roles or []
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.path = path
        self.method = method
        self.additional_data = additional_data or {}


class StructuredLogEntry:
    """Structured log entry with consistent formatting."""

    def __init__(
        self,
        level: LogLevel,
        category: LogCategory,
        message: str,
        context: Optional[RequestContext] = None,
        additional_data: Optional[Dict[str, Any]] = None,
        performance_data: Optional[Dict[str, Any]] = None,
    ):
        self.id = str(uuid.uuid4())
        self.timestamp = datetime.now(timezone.utc)
        self.level = level
        self.category = category
        self.message = message
        self.context = context
        self.additional_data = additional_data or {}
        self.performance_data = performance_data or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary for JSON serialization."""
        entry = {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "category": self.category.value,
            "message": self.message,
        }

        if self.context:
            entry["context"] = {
                "request_id": self.context.request_id,
                "user_id": self.context.user_id,
                "user_roles": [role.value for role in self.context.user_roles],
                "ip_address": self.context.ip_address,
                "user_agent": self.context.user_agent,
                "path": self.context.path,
                "method": self.context.method,
                "additional_data": self.context.additional_data,
            }

        if self.additional_data:
            entry["data"] = self.additional_data

        if self.performance_data:
            entry["performance"] = self.performance_data

        return entry

    def to_json(self) -> str:
        """Convert log entry to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class EnterpriseLoggingService:
    """Enterprise logging service with structured logging and audit capabilities."""

    def __init__(self):
        self.logger = logging.getLogger("enterprise_logger")
        self._setup_logger()

    def _setup_logger(self):
        """Setup structured logging configuration."""

        # Set log level based on environment
        if config.debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)

        # Create formatter for structured logging
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Add console handler if not already present
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log_structured(
        self,
        level: LogLevel,
        category: LogCategory,
        message: str,
        context: Optional[RequestContext] = None,
        additional_data: Optional[Dict[str, Any]] = None,
        performance_data: Optional[Dict[str, Any]] = None,
    ):
        """Log a structured entry."""

        entry = StructuredLogEntry(
            level=level,
            category=category,
            message=message,
            context=context,
            additional_data=additional_data,
            performance_data=performance_data,
        )

        # Log as JSON for structured logging systems
        log_level = getattr(logging, level.value)
        self.logger.log(log_level, entry.to_json())

    def log_authentication_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        success: bool = True,
        context: Optional[RequestContext] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log authentication events."""

        message = f"Authentication {event_type}: {'Success' if success else 'Failed'}"
        level = LogLevel.INFO if success else LogLevel.WARNING

        additional_data = {
            "event_type": event_type,
            "success": success,
            "user_id": user_id,
            **(details or {}),
        }

        self.log_structured(
            level=level,
            category=LogCategory.AUTHENTICATION,
            message=message,
            context=context,
            additional_data=additional_data,
        )

    def log_authorization_event(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
        success: bool = True,
        context: Optional[RequestContext] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log authorization events."""

        message = f"Authorization {action} on {resource_type}: {'Granted' if success else 'Denied'}"
        level = LogLevel.INFO if success else LogLevel.WARNING

        additional_data = {
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "user_id": user_id,
            "success": success,
            **(details or {}),
        }

        self.log_structured(
            level=level,
            category=LogCategory.AUTHORIZATION,
            message=message,
            context=context,
            additional_data=additional_data,
        )

    def log_data_operation(
        self,
        operation: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
        success: bool = True,
        context: Optional[RequestContext] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log data operations (CRUD)."""

        message = (
            f"Data {operation} on {resource_type}: {'Success' if success else 'Failed'}"
        )
        level = LogLevel.INFO if success else LogLevel.ERROR

        # Map resource type to category
        category_map = {
            "user": LogCategory.USER_OPERATIONS,
            "person": LogCategory.USER_OPERATIONS,
            "project": LogCategory.PROJECT_OPERATIONS,
            "subscription": LogCategory.SUBSCRIPTION_OPERATIONS,
        }
        category = category_map.get(resource_type.lower(), LogCategory.SYSTEM_EVENTS)

        additional_data = {
            "operation": operation,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "user_id": user_id,
            "success": success,
            **(details or {}),
        }

        self.log_structured(
            level=level,
            category=category,
            message=message,
            context=context,
            additional_data=additional_data,
        )

    def log_security_event(
        self,
        event_type: str,
        severity: str = "medium",
        user_id: Optional[str] = None,
        context: Optional[RequestContext] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log security events."""

        message = f"Security Event: {event_type}"

        # Map severity to log level
        level_map = {
            "low": LogLevel.INFO,
            "medium": LogLevel.WARNING,
            "high": LogLevel.ERROR,
            "critical": LogLevel.CRITICAL,
        }
        level = level_map.get(severity.lower(), LogLevel.WARNING)

        additional_data = {
            "event_type": event_type,
            "severity": severity,
            "user_id": user_id,
            **(details or {}),
        }

        self.log_structured(
            level=level,
            category=LogCategory.SECURITY_EVENTS,
            message=message,
            context=context,
            additional_data=additional_data,
        )

    def log_performance_metric(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
        context: Optional[RequestContext] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log performance metrics."""

        message = f"Performance: {operation} completed in {duration_ms:.2f}ms"
        level = LogLevel.INFO

        performance_data = {
            "operation": operation,
            "duration_ms": duration_ms,
            "success": success,
        }

        additional_data = {
            "operation": operation,
            "success": success,
            **(details or {}),
        }

        self.log_structured(
            level=level,
            category=LogCategory.PERFORMANCE,
            message=message,
            context=context,
            additional_data=additional_data,
            performance_data=performance_data,
        )

    def log_database_operation(
        self,
        operation: str,
        table: str,
        duration_ms: Optional[float] = None,
        success: bool = True,
        context: Optional[RequestContext] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log database operations."""

        message = (
            f"Database {operation} on {table}: {'Success' if success else 'Failed'}"
        )
        level = LogLevel.INFO if success else LogLevel.ERROR

        additional_data = {
            "operation": operation,
            "table": table,
            "success": success,
            **(details or {}),
        }

        performance_data = {}
        if duration_ms is not None:
            performance_data["duration_ms"] = duration_ms
            message += f" ({duration_ms:.2f}ms)"

        self.log_structured(
            level=level,
            category=LogCategory.DATABASE_OPERATIONS,
            message=message,
            context=context,
            additional_data=additional_data,
            performance_data=performance_data,
        )

    def log_api_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        user_id: Optional[str] = None,
        context: Optional[RequestContext] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log API requests."""

        message = f"API {method} {path} - {status_code} ({duration_ms:.2f}ms)"

        # Determine log level based on status code
        if status_code < 400:
            level = LogLevel.INFO
        elif status_code < 500:
            level = LogLevel.WARNING
        else:
            level = LogLevel.ERROR

        additional_data = {
            "method": method,
            "path": path,
            "status_code": status_code,
            "user_id": user_id,
            **(details or {}),
        }

        performance_data = {
            "duration_ms": duration_ms,
            "status_code": status_code,
        }

        self.log_structured(
            level=level,
            category=LogCategory.API_ACCESS,
            message=message,
            context=context,
            additional_data=additional_data,
            performance_data=performance_data,
        )


# Global logging service instance
logging_service = EnterpriseLoggingService()
