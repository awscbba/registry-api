"""
Utility functions for API handlers to integrate with enhanced error handling and logging.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import Request

from ..models.error_handling import (
    APIException, ErrorContext, ErrorCode, ValidationErrorDetail
)
from ..models.security_event import SecurityEventType
from ..services.logging_service import logging_service
from ..services.rate_limiting_service import (
    rate_limiting_service, RateLimitType, create_rate_limit_exception
)
from ..middleware.rate_limit_middleware import detect_suspicious_activity


def create_error_context(
    request: Request,
    user_id: Optional[str] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> ErrorContext:
    """Create error context from request and user information."""
    # Try to get context from middleware first
    if hasattr(request.state, 'error_context'):
        context = request.state.error_context
        if user_id and not context.user_id:
            context.user_id = user_id
        if additional_data:
            context.additional_data.update(additional_data)
        return context

    # Create new context if not available from middleware
    return ErrorContext(
        request_id=getattr(request.state, 'request_id', 'unknown'),
        user_id=user_id,
        ip_address=_get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        path=str(request.url.path),
        method=request.method,
        additional_data=additional_data or {}
    )


def _get_client_ip(request: Request) -> str:
    """Extract client IP address from request."""
    # Check for forwarded headers first
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip

    # Fallback to client host
    if request.client:
        return request.client.host

    return "unknown"


async def log_person_operation_with_context(
    operation: str,
    person_id: str,
    request: Request,
    user_id: Optional[str] = None,
    success: bool = True,
    details: Optional[Dict[str, Any]] = None
):
    """Log person operations with proper context."""
    context = create_error_context(request, user_id, details)
    await logging_service.log_person_operation(
        operation=operation,
        person_id=person_id,
        context=context,
        success=success,
        details=details
    )


async def log_authentication_with_context(
    event_type: str,
    user_email: Optional[str],
    request: Request,
    success: bool = True,
    failure_reason: Optional[str] = None
):
    """Log authentication events with proper context."""
    context = create_error_context(request)
    await logging_service.log_authentication_event(
        event_type=event_type,
        user_email=user_email,
        context=context,
        success=success,
        failure_reason=failure_reason
    )


async def log_password_event_with_context(
    event_type: str,
    person_id: str,
    request: Request,
    success: bool = True,
    details: Optional[Dict[str, Any]] = None
):
    """Log password events with proper context."""
    context = create_error_context(request, person_id, details)
    await logging_service.log_password_event(
        event_type=event_type,
        person_id=person_id,
        context=context,
        success=success,
        details=details
    )


async def log_security_event_with_context(
    event_type: SecurityEventType,
    request: Request,
    user_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> str:
    """Log security events with proper context."""
    context = create_error_context(request, user_id, details)
    return await logging_service.log_security_event(
        event_type=event_type,
        context=context,
        details=details
    )


async def check_rate_limit_for_endpoint(
    limit_type: RateLimitType,
    request: Request,
    user_id: Optional[str] = None
):
    """Check rate limits for an endpoint and raise exception if exceeded."""
    context = create_error_context(request, user_id)

    # Use IP address as default identifier
    identifier = context.ip_address

    # Use user ID for user-specific rate limits
    if user_id and limit_type in [RateLimitType.PASSWORD_CHANGE, RateLimitType.PERSON_UPDATES]:
        identifier = user_id

    # Check rate limit
    result = await rate_limiting_service.check_rate_limit(limit_type, identifier, context)

    if not result.allowed:
        raise create_rate_limit_exception(result, context)


def create_person_not_found_exception(person_id: str, request: Request) -> APIException:
    """Create a standardized person not found exception."""
    context = create_error_context(request)
    return APIException(
        error_code=ErrorCode.PERSON_NOT_FOUND,
        message=f"Person with ID {person_id} not found",
        context=context
    )


def create_validation_exception_from_errors(
    field_errors: Dict[str, str],
    request: Request,
    user_id: Optional[str] = None
) -> APIException:
    """Create validation exception from field errors."""
    context = create_error_context(request, user_id)

    details = [
        ValidationErrorDetail(
            field=field,
            message=error_msg,
            code=ErrorCode.INVALID_FORMAT
        )
        for field, error_msg in field_errors.items()
    ]

    return APIException(
        error_code=ErrorCode.INVALID_FORMAT,
        message="The request contains invalid data",
        details=details,
        context=context
    )


def create_authentication_exception(
    message: str = "Authentication failed",
    request: Optional[Request] = None
) -> APIException:
    """Create authentication exception."""
    context = create_error_context(request) if request else None
    return APIException(
        error_code=ErrorCode.INVALID_CREDENTIALS,
        message=message,
        context=context
    )


def create_authorization_exception(
    message: str = "Access denied",
    request: Optional[Request] = None,
    user_id: Optional[str] = None
) -> APIException:
    """Create authorization exception."""
    context = create_error_context(request, user_id) if request else None
    return APIException(
        error_code=ErrorCode.INSUFFICIENT_PERMISSIONS,
        message=message,
        context=context
    )


def create_password_policy_exception(
    message: str,
    request: Request,
    user_id: Optional[str] = None
) -> APIException:
    """Create password policy violation exception."""
    context = create_error_context(request, user_id)
    return APIException(
        error_code=ErrorCode.PASSWORD_POLICY_VIOLATION,
        message=message,
        context=context
    )


def create_email_already_exists_exception(
    email: str,
    request: Request,
    user_id: Optional[str] = None
) -> APIException:
    """Create email already exists exception."""
    context = create_error_context(request, user_id)
    return APIException(
        error_code=ErrorCode.EMAIL_ALREADY_EXISTS,
        message=f"Email address {email} is already in use",
        context=context
    )


def create_account_locked_exception(
    request: Request,
    blocked_until: Optional[datetime] = None,
    user_id: Optional[str] = None
) -> APIException:
    """Create account locked exception."""
    context = create_error_context(request, user_id)
    message = "Account is temporarily locked due to security concerns"

    if blocked_until:
        message += f" until {blocked_until.isoformat()}"

    return APIException(
        error_code=ErrorCode.ACCOUNT_LOCKED,
        message=message,
        context=context,
        blocked_until=blocked_until
    )


def create_password_change_required_exception(
    request: Request,
    user_id: Optional[str] = None
) -> APIException:
    """Create password change required exception."""
    context = create_error_context(request, user_id)
    return APIException(
        error_code=ErrorCode.PASSWORD_CHANGE_REQUIRED,
        message="Password change is required before accessing this resource",
        context=context
    )


def create_referential_integrity_exception(
    resource_type: str,
    related_records: List[Dict[str, Any]],
    request: Request,
    user_id: Optional[str] = None
) -> APIException:
    """Create referential integrity violation exception."""
    context = create_error_context(request, user_id)
    return APIException(
        error_code=ErrorCode.REFERENTIAL_INTEGRITY_VIOLATION,
        message=f"Cannot delete {resource_type} due to existing related records",
        context=context
    )


async def handle_service_error(
    error: Exception,
    operation: str,
    request: Request,
    user_id: Optional[str] = None
) -> APIException:
    """Handle service layer errors and convert to appropriate API exceptions."""
    context = create_error_context(request, user_id)

    # Log the service error
    await logging_service.log_structured(
        level="ERROR",
        category="PERSON_OPERATIONS",
        message=f"Service error in {operation}: {str(error)}",
        context=context,
        additional_data={"operation": operation, "error_type": type(error).__name__}
    )

    # Convert to appropriate API exception
    if "not found" in str(error).lower():
        return APIException(
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            message=str(error),
            context=context
        )
    elif "already exists" in str(error).lower() or "duplicate" in str(error).lower():
        return APIException(
            error_code=ErrorCode.DUPLICATE_VALUE,
            message=str(error),
            context=context
        )
    elif "validation" in str(error).lower() or "invalid" in str(error).lower():
        return APIException(
            error_code=ErrorCode.INVALID_FORMAT,
            message=str(error),
            context=context
        )
    else:
        return APIException(
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            message="An unexpected error occurred",
            context=context
        )


# Audit logging helpers
async def log_person_list_access(
    request: Request,
    user_id: str,
    count: int,
    limit: int,
    success: bool = True
):
    """Log person list access for audit purposes."""
    context = create_error_context(request, user_id)
    details = {"count": count, "limit": limit, "success": success}

    await logging_service.log_audit_event(
        action="LIST_PEOPLE",
        resource_type="person",
        resource_id="multiple",
        context=context,
        success=success,
        after_state=details
    )


async def log_person_access(
    person_id: str,
    request: Request,
    user_id: str,
    success: bool = True
):
    """Log individual person access for audit purposes."""
    context = create_error_context(request, user_id)

    await logging_service.log_audit_event(
        action="GET_PERSON",
        resource_type="person",
        resource_id=person_id,
        context=context,
        success=success
    )


async def log_person_update_audit(
    person_id: str,
    request: Request,
    user_id: str,
    before_state: Dict[str, Any],
    after_state: Dict[str, Any],
    success: bool = True
):
    """Log person update for audit trail."""
    context = create_error_context(request, user_id)

    await logging_service.log_audit_event(
        action="UPDATE_PERSON",
        resource_type="person",
        resource_id=person_id,
        context=context,
        before_state=before_state,
        after_state=after_state,
        success=success
    )


async def log_person_deletion_audit(
    person_id: str,
    request: Request,
    user_id: str,
    before_state: Dict[str, Any],
    success: bool = True
):
    """Log person deletion for audit trail."""
    context = create_error_context(request, user_id)

    await logging_service.log_audit_event(
        action="DELETE_PERSON",
        resource_type="person",
        resource_id=person_id,
        context=context,
        before_state=before_state,
        success=success
    )
