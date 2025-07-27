"""
Comprehensive error handling models and utilities for the People Register API.
Provides structured error responses, logging, and error categorization.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum
import uuid
import traceback


class ErrorCategory(str, Enum):
    """Categories of errors for better organization and handling."""

    VALIDATION = "VALIDATION"
    AUTHENTICATION = "AUTHENTICATION"
    AUTHORIZATION = "AUTHORIZATION"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    RATE_LIMIT = "RATE_LIMIT"
    SECURITY = "SECURITY"
    BUSINESS_LOGIC = "BUSINESS_LOGIC"
    EXTERNAL_SERVICE = "EXTERNAL_SERVICE"
    INTERNAL_SERVER = "INTERNAL_SERVER"


class ErrorCode(str, Enum):
    """Specific error codes for machine-readable error identification."""

    # Validation errors
    REQUIRED_FIELD = "REQUIRED_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"
    INVALID_LENGTH = "INVALID_LENGTH"
    INVALID_VALUE = "INVALID_VALUE"
    DUPLICATE_VALUE = "DUPLICATE_VALUE"

    # Authentication errors
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    INVALID_TOKEN = "INVALID_TOKEN"
    EXPIRED_TOKEN = "EXPIRED_TOKEN"
    MISSING_TOKEN = "MISSING_TOKEN"

    # Authorization errors
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    ACCOUNT_INACTIVE = "ACCOUNT_INACTIVE"
    PASSWORD_CHANGE_REQUIRED = "PASSWORD_CHANGE_REQUIRED"

    # Resource errors
    PERSON_NOT_FOUND = "PERSON_NOT_FOUND"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"

    # Conflict errors
    EMAIL_ALREADY_EXISTS = "EMAIL_ALREADY_EXISTS"
    REFERENTIAL_INTEGRITY_VIOLATION = "REFERENTIAL_INTEGRITY_VIOLATION"

    # Rate limiting
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    TOO_MANY_REQUESTS = "TOO_MANY_REQUESTS"

    # Security errors
    SUSPICIOUS_ACTIVITY = "SUSPICIOUS_ACTIVITY"
    BRUTE_FORCE_DETECTED = "BRUTE_FORCE_DETECTED"
    INVALID_CURRENT_PASSWORD = "INVALID_CURRENT_PASSWORD"
    PASSWORD_POLICY_VIOLATION = "PASSWORD_POLICY_VIOLATION"

    # Business logic errors
    PASSWORD_UPDATE_FAILED = "PASSWORD_UPDATE_FAILED"
    EMAIL_VERIFICATION_FAILED = "EMAIL_VERIFICATION_FAILED"
    DELETION_BLOCKED = "DELETION_BLOCKED"

    # External service errors
    EMAIL_SERVICE_ERROR = "EMAIL_SERVICE_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"

    # Internal server errors
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"


class ValidationErrorDetail(BaseModel):
    """Detailed validation error information."""

    field: str = Field(description="The field that failed validation")
    message: str = Field(description="Human-readable error message")
    code: ErrorCode = Field(description="Machine-readable error code")
    value: Optional[str] = Field(
        None, description="The invalid value that was provided"
    )
    constraint: Optional[str] = Field(
        None, description="The validation constraint that was violated"
    )


class ErrorResponse(BaseModel):
    """Standardized error response model for all API errors."""

    error: ErrorCode = Field(description="Machine-readable error code")
    category: ErrorCategory = Field(description="Error category for classification")
    message: str = Field(description="Human-readable error message")
    details: Optional[List[ValidationErrorDetail]] = Field(
        None, description="Detailed validation errors"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When the error occurred"
    )
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique request identifier",
    )
    path: Optional[str] = Field(None, description="API path where error occurred")
    method: Optional[str] = Field(None, description="HTTP method used")
    user_id: Optional[str] = Field(
        None, description="ID of authenticated user (if applicable)"
    )
    ip_address: Optional[str] = Field(None, description="Client IP address")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class SecurityErrorResponse(ErrorResponse):
    """Enhanced error response for security-related errors."""

    security_event_id: Optional[str] = Field(
        None, description="Associated security event ID"
    )
    blocked_until: Optional[datetime] = Field(
        None, description="When the block/lock expires"
    )
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retry")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ErrorContext(BaseModel):
    """Context information for error logging and debugging."""

    request_id: str
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    path: Optional[str] = None
    method: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    additional_data: Dict[str, Any] = Field(default_factory=dict)


class ErrorLogEntry(BaseModel):
    """Structured error log entry for comprehensive error tracking."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    error_code: ErrorCode
    category: ErrorCategory
    message: str
    context: ErrorContext
    stack_trace: Optional[str] = None
    severity: str = Field(default="ERROR")  # ERROR, WARNING, CRITICAL
    resolved: bool = Field(default=False)
    resolution_notes: Optional[str] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# Error code to category mapping
ERROR_CATEGORY_MAPPING = {
    # Validation errors
    ErrorCode.REQUIRED_FIELD: ErrorCategory.VALIDATION,
    ErrorCode.INVALID_FORMAT: ErrorCategory.VALIDATION,
    ErrorCode.INVALID_LENGTH: ErrorCategory.VALIDATION,
    ErrorCode.INVALID_VALUE: ErrorCategory.VALIDATION,
    ErrorCode.DUPLICATE_VALUE: ErrorCategory.VALIDATION,
    # Authentication errors
    ErrorCode.INVALID_CREDENTIALS: ErrorCategory.AUTHENTICATION,
    ErrorCode.INVALID_TOKEN: ErrorCategory.AUTHENTICATION,
    ErrorCode.EXPIRED_TOKEN: ErrorCategory.AUTHENTICATION,
    ErrorCode.MISSING_TOKEN: ErrorCategory.AUTHENTICATION,
    # Authorization errors
    ErrorCode.INSUFFICIENT_PERMISSIONS: ErrorCategory.AUTHORIZATION,
    ErrorCode.ACCOUNT_LOCKED: ErrorCategory.AUTHORIZATION,
    ErrorCode.ACCOUNT_INACTIVE: ErrorCategory.AUTHORIZATION,
    ErrorCode.PASSWORD_CHANGE_REQUIRED: ErrorCategory.AUTHORIZATION,
    # Resource errors
    ErrorCode.PERSON_NOT_FOUND: ErrorCategory.NOT_FOUND,
    ErrorCode.RESOURCE_NOT_FOUND: ErrorCategory.NOT_FOUND,
    # Conflict errors
    ErrorCode.EMAIL_ALREADY_EXISTS: ErrorCategory.CONFLICT,
    ErrorCode.REFERENTIAL_INTEGRITY_VIOLATION: ErrorCategory.CONFLICT,
    # Rate limiting
    ErrorCode.RATE_LIMIT_EXCEEDED: ErrorCategory.RATE_LIMIT,
    ErrorCode.TOO_MANY_REQUESTS: ErrorCategory.RATE_LIMIT,
    # Security errors
    ErrorCode.SUSPICIOUS_ACTIVITY: ErrorCategory.SECURITY,
    ErrorCode.BRUTE_FORCE_DETECTED: ErrorCategory.SECURITY,
    ErrorCode.INVALID_CURRENT_PASSWORD: ErrorCategory.SECURITY,
    ErrorCode.PASSWORD_POLICY_VIOLATION: ErrorCategory.SECURITY,
    # Business logic errors
    ErrorCode.PASSWORD_UPDATE_FAILED: ErrorCategory.BUSINESS_LOGIC,
    ErrorCode.EMAIL_VERIFICATION_FAILED: ErrorCategory.BUSINESS_LOGIC,
    ErrorCode.DELETION_BLOCKED: ErrorCategory.BUSINESS_LOGIC,
    # External service errors
    ErrorCode.EMAIL_SERVICE_ERROR: ErrorCategory.EXTERNAL_SERVICE,
    ErrorCode.DATABASE_ERROR: ErrorCategory.EXTERNAL_SERVICE,
    # Internal server errors
    ErrorCode.INTERNAL_SERVER_ERROR: ErrorCategory.INTERNAL_SERVER,
    ErrorCode.CONFIGURATION_ERROR: ErrorCategory.INTERNAL_SERVER,
}


def get_error_category(error_code: ErrorCode) -> ErrorCategory:
    """Get the category for a given error code."""
    return ERROR_CATEGORY_MAPPING.get(error_code, ErrorCategory.INTERNAL_SERVER)


# HTTP status code mapping for error codes
HTTP_STATUS_MAPPING = {
    # 400 Bad Request
    ErrorCode.REQUIRED_FIELD: 400,
    ErrorCode.INVALID_FORMAT: 400,
    ErrorCode.INVALID_LENGTH: 400,
    ErrorCode.INVALID_VALUE: 400,
    ErrorCode.PASSWORD_POLICY_VIOLATION: 400,
    ErrorCode.EMAIL_VERIFICATION_FAILED: 400,
    ErrorCode.PASSWORD_UPDATE_FAILED: 400,
    # 401 Unauthorized
    ErrorCode.INVALID_CREDENTIALS: 401,
    ErrorCode.INVALID_TOKEN: 401,
    ErrorCode.EXPIRED_TOKEN: 401,
    ErrorCode.MISSING_TOKEN: 401,
    ErrorCode.INVALID_CURRENT_PASSWORD: 401,
    # 403 Forbidden
    ErrorCode.INSUFFICIENT_PERMISSIONS: 403,
    ErrorCode.ACCOUNT_LOCKED: 403,
    ErrorCode.ACCOUNT_INACTIVE: 403,
    ErrorCode.PASSWORD_CHANGE_REQUIRED: 403,
    ErrorCode.SUSPICIOUS_ACTIVITY: 403,
    ErrorCode.BRUTE_FORCE_DETECTED: 403,
    # 404 Not Found
    ErrorCode.PERSON_NOT_FOUND: 404,
    ErrorCode.RESOURCE_NOT_FOUND: 404,
    # 409 Conflict
    ErrorCode.EMAIL_ALREADY_EXISTS: 409,
    ErrorCode.DUPLICATE_VALUE: 409,
    ErrorCode.REFERENTIAL_INTEGRITY_VIOLATION: 409,
    ErrorCode.DELETION_BLOCKED: 409,
    # 429 Too Many Requests
    ErrorCode.RATE_LIMIT_EXCEEDED: 429,
    ErrorCode.TOO_MANY_REQUESTS: 429,
    # 500 Internal Server Error
    ErrorCode.INTERNAL_SERVER_ERROR: 500,
    ErrorCode.CONFIGURATION_ERROR: 500,
    ErrorCode.EMAIL_SERVICE_ERROR: 500,
    ErrorCode.DATABASE_ERROR: 500,
}


def get_http_status_code(error_code: ErrorCode) -> int:
    """Get the appropriate HTTP status code for an error code."""
    return HTTP_STATUS_MAPPING.get(error_code, 500)


class APIException(Exception):
    """Custom exception class for API errors with structured error information."""

    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        details: Optional[List[ValidationErrorDetail]] = None,
        context: Optional[ErrorContext] = None,
        security_event_id: Optional[str] = None,
        blocked_until: Optional[datetime] = None,
        retry_after: Optional[int] = None,
    ):
        self.error_code = error_code
        self.message = message
        self.details = details or []
        self.context = context
        self.security_event_id = security_event_id
        self.blocked_until = blocked_until
        self.retry_after = retry_after
        self.category = get_error_category(error_code)
        self.http_status = get_http_status_code(error_code)

        super().__init__(message)

    def to_error_response(self) -> Union[ErrorResponse, SecurityErrorResponse]:
        """Convert exception to structured error response."""
        base_data = {
            "error": self.error_code,
            "category": self.category,
            "message": self.message,
            "details": self.details,
            "request_id": (
                self.context.request_id if self.context else str(uuid.uuid4())
            ),
            "path": self.context.path if self.context else None,
            "method": self.context.method if self.context else None,
            "user_id": self.context.user_id if self.context else None,
            "ip_address": self.context.ip_address if self.context else None,
        }

        # Use SecurityErrorResponse for security-related errors
        if self.category == ErrorCategory.SECURITY or self.security_event_id:
            return SecurityErrorResponse(
                **base_data,
                security_event_id=self.security_event_id,
                blocked_until=self.blocked_until,
                retry_after=self.retry_after,
            )

        return ErrorResponse(**base_data)

    def to_log_entry(self) -> ErrorLogEntry:
        """Convert exception to structured log entry."""
        return ErrorLogEntry(
            error_code=self.error_code,
            category=self.category,
            message=self.message,
            context=self.context or ErrorContext(request_id=str(uuid.uuid4())),
            stack_trace=traceback.format_exc(),
            severity="CRITICAL" if self.category == ErrorCategory.SECURITY else "ERROR",
        )


# Convenience functions for creating common exceptions
def validation_error(
    message: str,
    details: List[ValidationErrorDetail],
    context: Optional[ErrorContext] = None,
) -> APIException:
    """Create a validation error exception."""
    return APIException(
        error_code=(
            ErrorCode.REQUIRED_FIELD if not details else ErrorCode.INVALID_FORMAT
        ),
        message=message,
        details=details,
        context=context,
    )


def authentication_error(
    message: str = "Authentication failed", context: Optional[ErrorContext] = None
) -> APIException:
    """Create an authentication error exception."""
    return APIException(
        error_code=ErrorCode.INVALID_CREDENTIALS, message=message, context=context
    )


def authorization_error(
    message: str = "Access denied", context: Optional[ErrorContext] = None
) -> APIException:
    """Create an authorization error exception."""
    return APIException(
        error_code=ErrorCode.INSUFFICIENT_PERMISSIONS, message=message, context=context
    )


def not_found_error(
    resource: str = "Resource", context: Optional[ErrorContext] = None
) -> APIException:
    """Create a not found error exception."""
    return APIException(
        error_code=ErrorCode.RESOURCE_NOT_FOUND,
        message=f"{resource} not found",
        context=context,
    )


def rate_limit_error(
    message: str = "Rate limit exceeded",
    retry_after: int = 60,
    context: Optional[ErrorContext] = None,
) -> APIException:
    """Create a rate limit error exception."""
    return APIException(
        error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
        message=message,
        context=context,
        retry_after=retry_after,
    )


def security_error(
    error_code: ErrorCode,
    message: str,
    security_event_id: Optional[str] = None,
    blocked_until: Optional[datetime] = None,
    context: Optional[ErrorContext] = None,
) -> APIException:
    """Create a security error exception."""
    return APIException(
        error_code=error_code,
        message=message,
        context=context,
        security_event_id=security_event_id,
        blocked_until=blocked_until,
    )
