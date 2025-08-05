"""
Comprehensive logging service for the People Register API.
Provides structured logging for all person operations, security events, and system activities.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union
from enum import Enum

from ..models.error_handling import ErrorLogEntry, ErrorContext, APIException
from ..models.security_event import (
    SecurityEvent,
    SecurityEventType,
    SecurityEventSeverity,
    get_default_severity,
)
from ..services.defensive_dynamodb_service import DefensiveDynamoDBService as DynamoDBService


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
    PERSON_OPERATIONS = "PERSON_OPERATIONS"
    PASSWORD_MANAGEMENT = "PASSWORD_MANAGEMENT"
    EMAIL_VERIFICATION = "EMAIL_VERIFICATION"
    SECURITY_EVENTS = "SECURITY_EVENTS"
    API_ACCESS = "API_ACCESS"
    SYSTEM_EVENTS = "SYSTEM_EVENTS"
    ERROR_HANDLING = "ERROR_HANDLING"
    RATE_LIMITING = "RATE_LIMITING"
    AUDIT_TRAIL = "AUDIT_TRAIL"


class StructuredLogEntry:
    """Structured log entry with consistent formatting."""

    def __init__(
        self,
        level: LogLevel,
        category: LogCategory,
        message: str,
        context: Optional[ErrorContext] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ):
        self.id = str(uuid.uuid4())
        self.timestamp = datetime.now(timezone.utc)
        self.level = level
        self.category = category
        self.message = message
        self.context = context
        self.additional_data = additional_data or {}

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
                "ip_address": self.context.ip_address,
                "user_agent": self.context.user_agent,
                "path": self.context.path,
                "method": self.context.method,
                "additional_data": self.context.additional_data,
            }

        if self.additional_data:
            entry["data"] = self.additional_data

        return entry

    def to_json(self) -> str:
        """Convert log entry to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class LoggingService:
    """Comprehensive logging service for structured logging and audit trails."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db_service = DynamoDBService()

        # Configure structured logging format
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Ensure handler exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    async def log_structured(
        self,
        level: Union[LogLevel, str],
        category: Union[LogCategory, str],
        message: str,
        context: Optional[ErrorContext] = None,
        additional_data: Optional[Dict[str, Any]] = None,
        persist_to_db: bool = True,
    ):
        """Log a structured entry with optional database persistence."""
        try:
            # Convert string inputs to enums if necessary
            if isinstance(level, str):
                level = LogLevel(level.upper())
            if isinstance(category, str):
                category = LogCategory(category.upper())

            entry = StructuredLogEntry(
                level, category, message, context, additional_data
            )

            # Log to standard logger
            log_method = getattr(self.logger, level.value.lower())
            log_method(entry.to_json())

            # Persist to database for audit trail (if enabled)
            if persist_to_db:
                await self._persist_log_entry(entry)

        except Exception as e:
            # Fallback logging - don't let logging failures break the application
            self.logger.error(f"Failed to log structured entry: {str(e)}")

    async def log_person_operation(
        self,
        operation: str,
        person_id: str,
        context: ErrorContext,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log person-related operations for audit trail."""
        level = LogLevel.INFO if success else LogLevel.ERROR
        message = f"Person operation: {operation} for person {person_id}"

        additional_data = {
            "operation": operation,
            "person_id": person_id,
            "success": success,
            "details": details or {},
        }

        await self.log_structured(
            level=level,
            category=LogCategory.PERSON_OPERATIONS,
            message=message,
            context=context,
            additional_data=additional_data,
        )

    async def log_authentication_event(
        self,
        event_type: str,
        user_email: Optional[str],
        context: ErrorContext,
        success: bool = True,
        failure_reason: Optional[str] = None,
    ):
        """Log authentication events."""
        level = LogLevel.INFO if success else LogLevel.WARNING
        message = f"Authentication event: {event_type}"

        if not success and failure_reason:
            message += f" - {failure_reason}"

        additional_data = {
            "event_type": event_type,
            "user_email": user_email,
            "success": success,
            "failure_reason": failure_reason,
        }

        await self.log_structured(
            level=level,
            category=LogCategory.AUTHENTICATION,
            message=message,
            context=context,
            additional_data=additional_data,
        )

    async def log_password_event(
        self,
        event_type: str,
        person_id: str,
        context: ErrorContext,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log password-related events."""
        level = LogLevel.INFO if success else LogLevel.WARNING
        message = f"Password event: {event_type} for person {person_id}"

        additional_data = {
            "event_type": event_type,
            "person_id": person_id,
            "success": success,
            "details": details or {},
        }

        await self.log_structured(
            level=level,
            category=LogCategory.PASSWORD_MANAGEMENT,
            message=message,
            context=context,
            additional_data=additional_data,
        )

    async def log_security_event(
        self,
        event_type: SecurityEventType,
        context: ErrorContext,
        severity: Optional[SecurityEventSeverity] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Log security events and create security event record."""
        try:
            # Determine severity
            if severity is None:
                severity = get_default_severity(event_type)

            # Create security event
            security_event = SecurityEvent(
                id=str(uuid.uuid4()),
                event_type=event_type,
                timestamp=datetime.now(timezone.utc),
                severity=severity,
                user_id=context.user_id,
                ip_address=context.ip_address,
                user_agent=context.user_agent,
                details=details or {},
            )

            # Log structured entry
            level = (
                LogLevel.CRITICAL
                if severity == SecurityEventSeverity.CRITICAL
                else LogLevel.WARNING
            )
            message = f"Security event: {event_type.value}"

            additional_data = {
                "security_event_id": security_event.id,
                "event_type": event_type.value,
                "severity": severity.value,
                "details": details or {},
            }

            await self.log_structured(
                level=level,
                category=LogCategory.SECURITY_EVENTS,
                message=message,
                context=context,
                additional_data=additional_data,
            )

            # Persist security event to database
            await self.db_service.log_security_event(security_event)

            return security_event.id

        except Exception as e:
            self.logger.error(f"Failed to log security event: {str(e)}")
            return str(uuid.uuid4())  # Return a placeholder ID

    async def log_api_access(
        self,
        endpoint: str,
        method: str,
        context: ErrorContext,
        status_code: int,
        response_time_ms: Optional[float] = None,
        response_size: Optional[int] = None,
    ):
        """Log API access for monitoring and analytics."""
        level = LogLevel.INFO if status_code < 400 else LogLevel.WARNING
        message = f"API access: {method} {endpoint} - {status_code}"

        additional_data = {
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "response_time_ms": response_time_ms,
            "response_size": response_size,
        }

        await self.log_structured(
            level=level,
            category=LogCategory.API_ACCESS,
            message=message,
            context=context,
            additional_data=additional_data,
            persist_to_db=False,  # High volume, don't persist all API access logs
        )

    async def log_rate_limit_event(
        self,
        endpoint: str,
        context: ErrorContext,
        limit_type: str,
        current_count: int,
        limit: int,
        window_seconds: int,
    ):
        """Log rate limiting events."""
        message = f"Rate limit exceeded: {endpoint} - {current_count}/{limit} in {window_seconds}s"

        additional_data = {
            "endpoint": endpoint,
            "limit_type": limit_type,
            "current_count": current_count,
            "limit": limit,
            "window_seconds": window_seconds,
        }

        await self.log_structured(
            level=LogLevel.WARNING,
            category=LogCategory.RATE_LIMITING,
            message=message,
            context=context,
            additional_data=additional_data,
        )

        # Also create a security event for rate limiting
        await self.log_security_event(
            event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
            context=context,
            severity=SecurityEventSeverity.HIGH,
            details=additional_data,
        )

    async def log_error(
        self, exception: APIException, context: Optional[ErrorContext] = None
    ):
        """Log API exceptions with full context."""
        try:
            # Use context from exception if not provided
            if context is None and exception.context:
                context = exception.context

            message = f"API Error: {exception.error_code.value} - {exception.message}"

            additional_data = {
                "error_code": exception.error_code.value,
                "category": exception.category.value,
                "http_status": exception.http_status,
                "details": (
                    [detail.model_dump() for detail in exception.details]
                    if exception.details
                    else []
                ),
            }

            # Determine log level based on error category
            if exception.category.value in ["SECURITY", "AUTHENTICATION"]:
                level = LogLevel.CRITICAL
            elif exception.category.value in ["AUTHORIZATION", "RATE_LIMIT"]:
                level = LogLevel.WARNING
            else:
                level = LogLevel.ERROR

            await self.log_structured(
                level=level,
                category=LogCategory.ERROR_HANDLING,
                message=message,
                context=context,
                additional_data=additional_data,
            )

            # Create security event for security-related errors
            if exception.category.value == "SECURITY":
                security_event_type = self._map_error_to_security_event(
                    exception.error_code
                )
                if security_event_type:
                    await self.log_security_event(
                        event_type=security_event_type,
                        context=context or ErrorContext(request_id=str(uuid.uuid4())),
                        severity=SecurityEventSeverity.HIGH,
                        details=additional_data,
                    )

        except Exception as e:
            # Fallback logging
            self.logger.error(f"Failed to log API exception: {str(e)}")

    async def log_audit_event(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        context: ErrorContext,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        success: bool = True,
    ):
        """Log audit events for compliance and tracking."""
        message = f"Audit: {action} on {resource_type} {resource_id}"

        additional_data = {
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "success": success,
            "before_state": before_state,
            "after_state": after_state,
        }

        level = LogLevel.INFO if success else LogLevel.ERROR

        await self.log_structured(
            level=level,
            category=LogCategory.AUDIT_TRAIL,
            message=message,
            context=context,
            additional_data=additional_data,
        )

    async def _persist_log_entry(self, entry: StructuredLogEntry):
        """Persist log entry to database for audit trail."""
        try:
            # This would store in a dedicated audit logs table
            # For now, we'll use the existing security events infrastructure
            pass
        except Exception as e:
            self.logger.error(f"Failed to persist log entry: {str(e)}")

    def _map_error_to_security_event(self, error_code) -> Optional[SecurityEventType]:
        """Map error codes to security event types."""
        mapping = {
            "INVALID_CURRENT_PASSWORD": SecurityEventType.LOGIN_FAILED,
            "BRUTE_FORCE_DETECTED": SecurityEventType.BRUTE_FORCE_ATTEMPT,
            "SUSPICIOUS_ACTIVITY": SecurityEventType.SUSPICIOUS_ACTIVITY,
            "ACCOUNT_LOCKED": SecurityEventType.ACCOUNT_LOCKED,
            "RATE_LIMIT_EXCEEDED": SecurityEventType.RATE_LIMIT_EXCEEDED,
        }
        return mapping.get(error_code.value)

    async def get_recent_logs(
        self,
        category: Optional[LogCategory] = None,
        level: Optional[LogLevel] = None,
        hours: int = 24,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retrieve recent log entries for monitoring dashboard."""
        try:
            # This would query the audit logs table
            # For now, return empty list
            return []
        except Exception as e:
            self.logger.error(f"Failed to retrieve recent logs: {str(e)}")
            return []


# Global logging service instance
logging_service = LoggingService()


# Convenience functions for common logging operations
async def log_person_created(person_id: str, context: ErrorContext):
    """Log person creation event."""
    await logging_service.log_person_operation(
        "CREATE", person_id, context, success=True
    )


async def log_person_updated(
    person_id: str, context: ErrorContext, updated_fields: List[str]
):
    """Log person update event."""
    details = {"updated_fields": updated_fields}
    await logging_service.log_person_operation(
        "UPDATE", person_id, context, success=True, details=details
    )


async def log_person_deleted(person_id: str, context: ErrorContext):
    """Log person deletion event."""
    await logging_service.log_person_operation(
        "DELETE", person_id, context, success=True
    )


async def log_person_accessed(person_id: str, context: ErrorContext):
    """Log person access event."""
    await logging_service.log_person_operation(
        "ACCESS", person_id, context, success=True
    )


async def log_login_success(user_email: str, context: ErrorContext):
    """Log successful login."""
    await logging_service.log_authentication_event(
        "LOGIN", user_email, context, success=True
    )


async def log_login_failure(user_email: str, context: ErrorContext, reason: str):
    """Log failed login attempt."""
    await logging_service.log_authentication_event(
        "LOGIN", user_email, context, success=False, failure_reason=reason
    )


async def log_password_changed(person_id: str, context: ErrorContext):
    """Log password change event."""
    await logging_service.log_password_event(
        "PASSWORD_CHANGED", person_id, context, success=True
    )


async def log_password_change_failed(
    person_id: str, context: ErrorContext, reason: str
):
    """Log failed password change attempt."""
    details = {"failure_reason": reason}
    await logging_service.log_password_event(
        "PASSWORD_CHANGE_FAILED", person_id, context, success=False, details=details
    )
