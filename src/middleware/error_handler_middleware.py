"""
Comprehensive error handling middleware for the People Register API.
Provides centralized error handling, logging, and response formatting.
"""

import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import uuid

from ..models.error_handling import (
    APIException,
    ErrorResponse,
    SecurityErrorResponse,
    ErrorContext,
    ErrorCode,
    ErrorCategory,
    get_http_status_code,
)
from ..services.logging_service import logging_service
from ..services.rate_limiting_service import rate_limiting_service, RateLimitType


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware for comprehensive error handling and logging."""

    def __init__(self, app):
        super().__init__(app)
        self.sensitive_paths = {
            "/auth/login",
            "/auth/password",
            "/people/{person_id}/password",
            "/auth/password/validate",
            "/admin/password/force-change",
            "/admin/password/generate-temporary",
        }

    async def dispatch(self, request: Request, call_next):
        """Process request and handle any errors that occur."""
        start_time = datetime.utcnow()
        request_id = str(uuid.uuid4())

        # Create error context
        context = self._create_error_context(request, request_id)

        # Add request ID to request state for use in handlers
        request.state.request_id = request_id
        request.state.error_context = context

        try:
            # Check rate limits for sensitive endpoints
            if self._is_sensitive_endpoint(request.url.path):
                await self._check_rate_limits(request, context)

            # Process request
            response = await call_next(request)

            # Log successful API access
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            await self._log_api_access(
                request, context, response.status_code, response_time
            )

            return response

        except APIException as api_exc:
            # Handle our custom API exceptions
            return await self._handle_api_exception(api_exc, context)

        except HTTPException as http_exc:
            # Handle FastAPI HTTP exceptions
            return await self._handle_http_exception(http_exc, context)

        except Exception as exc:
            # Handle unexpected exceptions
            return await self._handle_unexpected_exception(exc, context)

    def _create_error_context(self, request: Request, request_id: str) -> ErrorContext:
        """Create error context from request."""
        # Extract user ID from request state if available
        user_id = None
        if hasattr(request.state, "current_user") and request.state.current_user:
            user_id = request.state.current_user.id

        return ErrorContext(
            request_id=request_id,
            user_id=user_id,
            ip_address=self._get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            path=str(request.url.path),
            method=request.method,
            additional_data={
                "query_params": dict(request.query_params),
                "headers": dict(request.headers),
            },
        )

    def _get_client_ip(self, request: Request) -> str:
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

    def _is_sensitive_endpoint(self, path: str) -> bool:
        """Check if endpoint is sensitive and requires rate limiting."""
        # Check exact matches first
        if path in self.sensitive_paths:
            return True

        # Check pattern matches
        if "/password" in path:
            return True
        if "/auth/" in path:
            return True

        return False

    async def _check_rate_limits(self, request: Request, context: ErrorContext):
        """Check rate limits for sensitive endpoints."""
        try:
            # Determine rate limit type based on endpoint
            rate_limit_type = self._get_rate_limit_type(request.url.path)
            if not rate_limit_type:
                return

            # Use IP address as identifier for most endpoints
            identifier = context.ip_address

            # For user-specific endpoints, use user ID if available
            if context.user_id and rate_limit_type in [RateLimitType.PASSWORD_CHANGE]:
                identifier = context.user_id

            # Check rate limit
            result = await rate_limiting_service.check_rate_limit(
                rate_limit_type, identifier, context
            )

            if not result.allowed:
                # Create rate limit exception
                raise APIException(
                    error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
                    message=f"Rate limit exceeded. Try again in {result.retry_after_seconds} seconds.",
                    context=context,
                    retry_after=result.retry_after_seconds,
                    blocked_until=result.blocked_until,
                )

        except APIException:
            raise
        except Exception as e:
            # Log rate limiting error but don't block request
            await logging_service.log_structured(
                level="ERROR",
                category="RATE_LIMITING",
                message=f"Rate limiting check failed: {str(e)}",
                context=context,
            )

    def _get_rate_limit_type(self, path: str) -> Optional[RateLimitType]:
        """Determine rate limit type based on endpoint path."""
        if "/auth/login" in path:
            return RateLimitType.LOGIN_ATTEMPTS
        elif "/password" in path:
            return RateLimitType.PASSWORD_CHANGE
        elif "/people" in path and "POST" in path:
            return RateLimitType.PERSON_CREATION
        elif "/people" in path and "PUT" in path:
            return RateLimitType.PERSON_UPDATES
        elif "/verify-email" in path:
            return RateLimitType.EMAIL_VERIFICATION
        elif "/search" in path:
            return RateLimitType.SEARCH_REQUESTS
        else:
            return RateLimitType.API_REQUESTS

    async def _handle_api_exception(
        self, exc: APIException, context: ErrorContext
    ) -> JSONResponse:
        """Handle custom API exceptions."""
        try:
            # Log the exception
            await logging_service.log_error(exc, context)

            # Create error response
            error_response = exc.to_error_response()

            # Create JSON response with appropriate status code
            response_data = error_response.model_dump()

            # Add rate limiting headers if applicable
            headers = {}
            if exc.retry_after:
                headers["Retry-After"] = str(exc.retry_after)

            if exc.blocked_until:
                headers["X-Blocked-Until"] = exc.blocked_until.isoformat()

            return JSONResponse(
                status_code=exc.http_status, content=response_data, headers=headers
            )

        except Exception as e:
            # Fallback error handling
            return await self._create_fallback_error_response(str(e), context)

    async def _handle_http_exception(
        self, exc: HTTPException, context: ErrorContext
    ) -> JSONResponse:
        """Handle FastAPI HTTP exceptions."""
        try:
            # Convert HTTP exception to API exception
            error_code = self._map_http_status_to_error_code(exc.status_code)

            api_exc = APIException(
                error_code=error_code,
                message=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
                context=context,
            )

            # Log the exception
            await logging_service.log_error(api_exc, context)

            # Create error response
            error_response = api_exc.to_error_response()

            return JSONResponse(
                status_code=exc.status_code, content=error_response.model_dump()
            )

        except Exception as e:
            # Fallback error handling
            return await self._create_fallback_error_response(str(e), context)

    async def _handle_unexpected_exception(
        self, exc: Exception, context: ErrorContext
    ) -> JSONResponse:
        """Handle unexpected exceptions."""
        try:
            # Create API exception for unexpected error
            api_exc = APIException(
                error_code=ErrorCode.INTERNAL_SERVER_ERROR,
                message="An unexpected error occurred",
                context=context,
            )

            # Log the exception with stack trace
            await logging_service.log_structured(
                level="CRITICAL",
                category="ERROR_HANDLING",
                message=f"Unexpected exception: {str(exc)}",
                context=context,
                additional_data={
                    "exception_type": type(exc).__name__,
                    "stack_trace": traceback.format_exc(),
                },
            )

            # Create error response (don't expose internal error details)
            error_response = ErrorResponse(
                error=ErrorCode.INTERNAL_SERVER_ERROR,
                category=ErrorCategory.INTERNAL_SERVER,
                message="An unexpected error occurred. Please try again later.",
                request_id=context.request_id,
                path=context.path,
                method=context.method,
                ip_address=context.ip_address,
            )

            return JSONResponse(status_code=500, content=error_response.model_dump())

        except Exception as e:
            # Ultimate fallback
            return await self._create_fallback_error_response(str(e), context)

    def _map_http_status_to_error_code(self, status_code: int) -> ErrorCode:
        """Map HTTP status codes to error codes."""
        mapping = {
            400: ErrorCode.INVALID_FORMAT,
            401: ErrorCode.INVALID_CREDENTIALS,
            403: ErrorCode.INSUFFICIENT_PERMISSIONS,
            404: ErrorCode.RESOURCE_NOT_FOUND,
            409: ErrorCode.DUPLICATE_VALUE,
            429: ErrorCode.RATE_LIMIT_EXCEEDED,
            500: ErrorCode.INTERNAL_SERVER_ERROR,
        }
        return mapping.get(status_code, ErrorCode.INTERNAL_SERVER_ERROR)

    async def _create_fallback_error_response(
        self, error_message: str, context: ErrorContext
    ) -> JSONResponse:
        """Create a fallback error response when error handling fails."""
        try:
            # Log the fallback error
            await logging_service.log_structured(
                level="CRITICAL",
                category="ERROR_HANDLING",
                message=f"Error handling failed: {error_message}",
                context=context,
            )
        except Exception:
            # Even logging failed, just continue
            pass

        # Create minimal error response
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": context.request_id,
            },
        )

    async def _log_api_access(
        self,
        request: Request,
        context: ErrorContext,
        status_code: int,
        response_time_ms: float,
    ):
        """Log API access for monitoring."""
        try:
            await logging_service.log_api_access(
                endpoint=context.path,
                method=context.method,
                context=context,
                status_code=status_code,
                response_time_ms=response_time_ms,
            )
        except Exception as e:
            # Don't fail request if logging fails
            pass


# Helper functions for use in handlers
def get_error_context(request: Request) -> ErrorContext:
    """Get error context from request state."""
    if hasattr(request.state, "error_context"):
        return request.state.error_context

    # Create minimal context if not available
    return ErrorContext(
        request_id=str(uuid.uuid4()),
        ip_address="unknown",
        path=str(request.url.path),
        method=request.method,
    )


def create_validation_exception(
    message: str, field_errors: Dict[str, str], context: ErrorContext
) -> APIException:
    """Create a validation exception with field-specific errors."""
    from ..models.error_handling import ValidationErrorDetail, ErrorCode

    details = [
        ValidationErrorDetail(
            field=field, message=error_msg, code=ErrorCode.INVALID_FORMAT
        )
        for field, error_msg in field_errors.items()
    ]

    return APIException(
        error_code=ErrorCode.INVALID_FORMAT,
        message=message,
        details=details,
        context=context,
    )


def create_security_exception(
    error_code: ErrorCode,
    message: str,
    context: ErrorContext,
    security_event_id: Optional[str] = None,
) -> APIException:
    """Create a security-related exception."""
    return APIException(
        error_code=error_code,
        message=message,
        context=context,
        security_event_id=security_event_id,
    )
