"""
Enterprise error handler with structured logging and monitoring integration.
"""

import logging
import traceback
from typing import Dict, Any, Optional, Union
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from .base_exceptions import (
    BaseApplicationException,
    ErrorCode,
    ErrorSeverity,
    AuthenticationException,
    AuthorizationException,
    ValidationException,
    ResourceNotFoundException,
    DatabaseException,
    SecurityException,
    RateLimitException,
)
from ..security.audit_logger import audit_logger, AuditEventType


class EnterpriseErrorHandler:
    """Enterprise-grade error handler with comprehensive logging and monitoring."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def handle_application_exception(
        self,
        request: Request,
        exc: BaseApplicationException,
    ) -> JSONResponse:
        """Handle application-specific exceptions."""

        # Log the exception with full context
        self._log_exception(request, exc)

        # Determine HTTP status code
        status_code = self._get_http_status_code(exc)

        # Create response
        response_data = {
            "success": False,
            "error": {
                "code": exc.error_code.value,
                "message": exc.user_message,
                "error_id": exc.error_id,
                "timestamp": exc.timestamp.isoformat(),
            },
        }

        # Add details for development/debugging (exclude in production)
        if self._should_include_details(exc):
            response_data["error"]["details"] = exc.details

        return JSONResponse(status_code=status_code, content=response_data)

    def handle_http_exception(
        self,
        request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        """Handle FastAPI HTTP exceptions."""

        # Log HTTP exceptions
        self.logger.warning(
            f"HTTP Exception: {exc.status_code} - {exc.detail}",
            extra={
                "status_code": exc.status_code,
                "detail": exc.detail,
                "path": request.url.path,
                "method": request.method,
            },
        )

        # Convert to standard format
        response_data = {
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": str(exc.detail),
                "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
            },
        }

        return JSONResponse(status_code=exc.status_code, content=response_data)

    def handle_generic_exception(
        self,
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Handle unexpected exceptions."""

        # Log the unexpected exception with full traceback
        self.logger.error(
            f"Unexpected exception: {type(exc).__name__}: {str(exc)}",
            extra={
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "traceback": traceback.format_exc(),
                "path": request.url.path,
                "method": request.method,
            },
        )

        # Log security event for unexpected errors
        audit_logger.log_event(
            event_type=AuditEventType.SYSTEM_ERROR,
            details={
                "exception_type": type(exc).__name__,
                "path": request.url.path,
                "method": request.method,
            },
        )

        # Return generic error response
        response_data = {
            "success": False,
            "error": {
                "code": ErrorCode.INTERNAL_ERROR.value,
                "message": "An internal error occurred. Please try again later.",
                "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
            },
        }

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=response_data
        )

    def _log_exception(
        self,
        request: Request,
        exc: BaseApplicationException,
    ) -> None:
        """Log exception with appropriate level and context."""

        # Determine log level based on severity
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL,
        }.get(exc.severity, logging.ERROR)

        # Extract user context
        user_id = getattr(request.state, "user_id", None)

        # Log with structured data
        self.logger.log(
            log_level,
            f"Application Exception: {exc.error_code.value} - {exc.message}",
            extra={
                "error_id": exc.error_id,
                "error_code": exc.error_code.value,
                "severity": exc.severity.value,
                "user_id": user_id,
                "path": request.url.path,
                "method": request.method,
                "details": exc.details,
                "cause": str(exc.cause) if exc.cause else None,
            },
        )

        # Log security events for high-severity errors
        if exc.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            audit_logger.log_security_event(
                event_type=AuditEventType.SYSTEM_ERROR,
                user_id=user_id,
                details={
                    "error_code": exc.error_code.value,
                    "severity": exc.severity.value,
                    "path": request.url.path,
                    "method": request.method,
                },
            )

    def _get_http_status_code(self, exc: BaseApplicationException) -> int:
        """Map application exceptions to HTTP status codes."""

        status_map = {
            # Authentication errors
            AuthenticationException: status.HTTP_401_UNAUTHORIZED,
            # Authorization errors
            AuthorizationException: status.HTTP_403_FORBIDDEN,
            # Validation errors
            ValidationException: status.HTTP_400_BAD_REQUEST,
            # Resource not found
            ResourceNotFoundException: status.HTTP_404_NOT_FOUND,
            # Database errors
            DatabaseException: status.HTTP_500_INTERNAL_SERVER_ERROR,
            # Security errors
            SecurityException: status.HTTP_403_FORBIDDEN,
            # Rate limiting
            RateLimitException: status.HTTP_429_TOO_MANY_REQUESTS,
        }

        # Check by exception type
        for exc_type, status_code in status_map.items():
            if isinstance(exc, exc_type):
                return status_code

        # Check by error code
        error_code_map = {
            ErrorCode.AUTHENTICATION_FAILED: status.HTTP_401_UNAUTHORIZED,
            ErrorCode.INVALID_CREDENTIALS: status.HTTP_401_UNAUTHORIZED,
            ErrorCode.TOKEN_EXPIRED: status.HTTP_401_UNAUTHORIZED,
            ErrorCode.TOKEN_INVALID: status.HTTP_401_UNAUTHORIZED,
            ErrorCode.ACCOUNT_LOCKED: status.HTTP_423_LOCKED,
            ErrorCode.INSUFFICIENT_PERMISSIONS: status.HTTP_403_FORBIDDEN,
            ErrorCode.ACCESS_DENIED: status.HTTP_403_FORBIDDEN,
            ErrorCode.INVALID_INPUT: status.HTTP_400_BAD_REQUEST,
            ErrorCode.MISSING_REQUIRED_FIELD: status.HTTP_400_BAD_REQUEST,
            ErrorCode.INVALID_FORMAT: status.HTTP_400_BAD_REQUEST,
            ErrorCode.DUPLICATE_VALUE: status.HTTP_409_CONFLICT,
            ErrorCode.RESOURCE_NOT_FOUND: status.HTTP_404_NOT_FOUND,
            ErrorCode.RESOURCE_ALREADY_EXISTS: status.HTTP_409_CONFLICT,
            ErrorCode.RATE_LIMIT_EXCEEDED: status.HTTP_429_TOO_MANY_REQUESTS,
        }

        return error_code_map.get(exc.error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _should_include_details(self, exc: BaseApplicationException) -> bool:
        """Determine if exception details should be included in response."""

        # Include details for validation errors (field errors are useful)
        if isinstance(exc, ValidationException):
            return True

        # Include details for low-severity errors
        if exc.severity == ErrorSeverity.LOW:
            return True

        # TODO: Check environment (include details in development, exclude in production)
        # For now, include details for debugging
        return True

    def create_validation_exception(
        self,
        message: str,
        field_errors: Optional[Dict[str, list]] = None,
    ) -> ValidationException:
        """Create a validation exception with field errors."""

        return ValidationException(
            message=message,
            field_errors=field_errors,
            user_message="Please check your input and try again.",
        )

    def create_not_found_exception(
        self,
        resource_type: str,
        resource_id: Optional[str] = None,
    ) -> ResourceNotFoundException:
        """Create a resource not found exception."""

        return ResourceNotFoundException(
            resource_type=resource_type,
            resource_id=resource_id,
            user_message=f"The requested {resource_type.lower()} was not found.",
        )

    def create_permission_denied_exception(
        self,
        action: str,
        resource: Optional[str] = None,
    ) -> AuthorizationException:
        """Create a permission denied exception."""

        message = f"Permission denied for action: {action}"
        if resource:
            message += f" on resource: {resource}"

        return AuthorizationException(
            message=message,
            error_code=ErrorCode.PERMISSION_DENIED,
            user_message="You don't have permission to perform this action.",
        )


# Global error handler instance
error_handler = EnterpriseErrorHandler()
