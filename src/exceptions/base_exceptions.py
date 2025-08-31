"""
Enterprise-grade exception handling system.
Provides structured error handling with proper logging and user-safe messages.
"""

from typing import Dict, Any, Optional, List
from enum import Enum
import uuid
from datetime import datetime, timezone


class ErrorCode(str, Enum):
    """Standardized error codes for the application."""

    # Authentication Errors (1000-1999)
    AUTHENTICATION_FAILED = "AUTH_1001"
    INVALID_CREDENTIALS = "AUTH_1002"
    TOKEN_EXPIRED = "AUTH_1003"
    TOKEN_INVALID = "AUTH_1004"
    ACCOUNT_LOCKED = "AUTH_1005"
    PASSWORD_EXPIRED = "AUTH_1006"

    # Authorization Errors (2000-2999)
    INSUFFICIENT_PERMISSIONS = "AUTHZ_2001"
    ACCESS_DENIED = "AUTHZ_2002"
    ROLE_NOT_FOUND = "AUTHZ_2003"
    PERMISSION_DENIED = "AUTHZ_2004"

    # Validation Errors (3000-3999)
    INVALID_INPUT = "VAL_3001"
    MISSING_REQUIRED_FIELD = "VAL_3002"
    INVALID_FORMAT = "VAL_3003"
    VALUE_OUT_OF_RANGE = "VAL_3004"
    DUPLICATE_VALUE = "VAL_3005"

    # Business Logic Errors (4000-4999)
    RESOURCE_NOT_FOUND = "BIZ_4001"
    RESOURCE_ALREADY_EXISTS = "BIZ_4002"
    INVALID_OPERATION = "BIZ_4003"
    BUSINESS_RULE_VIOLATION = "BIZ_4004"
    DEPENDENCY_CONFLICT = "BIZ_4005"

    # System Errors (5000-5999)
    DATABASE_ERROR = "SYS_5001"
    EXTERNAL_SERVICE_ERROR = "SYS_5002"
    CONFIGURATION_ERROR = "SYS_5003"
    INTERNAL_ERROR = "SYS_5004"
    SERVICE_UNAVAILABLE = "SYS_5005"

    # Security Errors (6000-6999)
    SECURITY_VIOLATION = "SEC_6001"
    RATE_LIMIT_EXCEEDED = "SEC_6002"
    SUSPICIOUS_ACTIVITY = "SEC_6003"
    INPUT_SANITIZATION_FAILED = "SEC_6004"


class ErrorSeverity(str, Enum):
    """Error severity levels for monitoring and alerting."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BaseApplicationException(Exception):
    """Base exception class for all application exceptions."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)

        self.error_id = str(uuid.uuid4())
        self.timestamp = datetime.now(timezone.utc)
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.user_message = user_message or self._get_default_user_message()
        self.details = details or {}
        self.cause = cause

    def _get_default_user_message(self) -> str:
        """Get default user-friendly message based on error code."""
        default_messages = {
            ErrorCode.AUTHENTICATION_FAILED: "Authentication failed. Please check your credentials.",
            ErrorCode.INSUFFICIENT_PERMISSIONS: "You don't have permission to perform this action.",
            ErrorCode.INVALID_INPUT: "The provided input is invalid.",
            ErrorCode.RESOURCE_NOT_FOUND: "The requested resource was not found.",
            ErrorCode.DATABASE_ERROR: "A system error occurred. Please try again later.",
            ErrorCode.RATE_LIMIT_EXCEEDED: "Too many requests. Please try again later.",
        }
        return default_messages.get(
            self.error_code, "An error occurred. Please try again."
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging and API responses."""
        return {
            "error_id": self.error_id,
            "timestamp": self.timestamp.isoformat(),
            "error_code": self.error_code.value,
            "severity": self.severity.value,
            "message": self.message,
            "user_message": self.user_message,
            "details": self.details,
            "cause": str(self.cause) if self.cause else None,
        }


class AuthenticationException(BaseApplicationException):
    """Authentication-related exceptions."""

    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: ErrorCode = ErrorCode.AUTHENTICATION_FAILED,
        **kwargs,
    ):
        super().__init__(message, error_code, ErrorSeverity.HIGH, **kwargs)


class AuthorizationException(BaseApplicationException):
    """Authorization-related exceptions."""

    def __init__(
        self,
        message: str = "Access denied",
        error_code: ErrorCode = ErrorCode.INSUFFICIENT_PERMISSIONS,
        **kwargs,
    ):
        super().__init__(message, error_code, ErrorSeverity.HIGH, **kwargs)


class ValidationException(BaseApplicationException):
    """Input validation exceptions."""

    def __init__(
        self,
        message: str = "Validation failed",
        error_code: ErrorCode = ErrorCode.INVALID_INPUT,
        field_errors: Optional[Dict[str, List[str]]] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if field_errors:
            details["field_errors"] = field_errors
        kwargs["details"] = details

        super().__init__(message, error_code, ErrorSeverity.MEDIUM, **kwargs)


class BusinessLogicException(BaseApplicationException):
    """Business logic violation exceptions."""

    def __init__(
        self,
        message: str = "Business rule violation",
        error_code: ErrorCode = ErrorCode.BUSINESS_RULE_VIOLATION,
        **kwargs,
    ):
        super().__init__(message, error_code, ErrorSeverity.MEDIUM, **kwargs)


class ResourceNotFoundException(BaseApplicationException):
    """Resource not found exceptions."""

    def __init__(self, resource_type: str, resource_id: Optional[str] = None, **kwargs):
        message = f"{resource_type} not found"
        if resource_id:
            message += f" with ID: {resource_id}"

        details = kwargs.get("details", {})
        details.update(
            {
                "resource_type": resource_type,
                "resource_id": resource_id,
            }
        )
        kwargs["details"] = details

        super().__init__(
            message, ErrorCode.RESOURCE_NOT_FOUND, ErrorSeverity.LOW, **kwargs
        )


class DuplicateResourceException(BaseApplicationException):
    """Duplicate resource exceptions."""

    def __init__(self, resource_type: str, field: str, value: str, **kwargs):
        message = f"{resource_type} with {field} '{value}' already exists"

        details = kwargs.get("details", {})
        details.update(
            {
                "resource_type": resource_type,
                "field": field,
                "value": value,
            }
        )
        kwargs["details"] = details

        super().__init__(
            message, ErrorCode.RESOURCE_ALREADY_EXISTS, ErrorSeverity.MEDIUM, **kwargs
        )


class DatabaseException(BaseApplicationException):
    """Database operation exceptions."""

    def __init__(self, operation: str, table: Optional[str] = None, **kwargs):
        message = f"Database error during {operation}"
        if table:
            message += f" on table {table}"

        details = kwargs.get("details", {})
        details.update(
            {
                "operation": operation,
                "table": table,
            }
        )
        kwargs["details"] = details

        super().__init__(
            message, ErrorCode.DATABASE_ERROR, ErrorSeverity.HIGH, **kwargs
        )


class SecurityException(BaseApplicationException):
    """Security-related exceptions."""

    def __init__(
        self,
        message: str = "Security violation detected",
        error_code: ErrorCode = ErrorCode.SECURITY_VIOLATION,
        **kwargs,
    ):
        super().__init__(message, error_code, ErrorSeverity.CRITICAL, **kwargs)


class RateLimitException(BaseApplicationException):
    """Rate limiting exceptions."""

    def __init__(self, limit: int, window: str, **kwargs):
        message = f"Rate limit exceeded: {limit} requests per {window}"

        details = kwargs.get("details", {})
        details.update(
            {
                "limit": limit,
                "window": window,
            }
        )
        kwargs["details"] = details

        super().__init__(
            message, ErrorCode.RATE_LIMIT_EXCEEDED, ErrorSeverity.HIGH, **kwargs
        )


class ExternalServiceException(BaseApplicationException):
    """External service integration exceptions."""

    def __init__(self, service_name: str, operation: str, **kwargs):
        message = f"External service error: {service_name} during {operation}"

        details = kwargs.get("details", {})
        details.update(
            {
                "service_name": service_name,
                "operation": operation,
            }
        )
        kwargs["details"] = details

        super().__init__(
            message, ErrorCode.EXTERNAL_SERVICE_ERROR, ErrorSeverity.HIGH, **kwargs
        )
