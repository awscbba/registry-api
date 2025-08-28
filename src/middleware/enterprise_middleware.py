"""
Enterprise middleware for error handling, logging, and security.
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..exceptions.error_handler import error_handler
from ..exceptions.base_exceptions import BaseApplicationException
from ..services.logging_service import (
    logging_service,
    RequestContext,
    LogLevel,
    LogCategory,
)
from ..models.rbac import RoleType


class EnterpriseMiddleware(BaseHTTPMiddleware):
    """Enterprise middleware for comprehensive request processing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with enterprise features."""

        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Start timing
        start_time = time.time()

        # Extract user context (if available)
        user_id = getattr(request.state, "user_id", None)
        user_roles = getattr(request.state, "user_roles", [])

        # Create request context
        context = RequestContext(
            request_id=request_id,
            user_id=user_id,
            user_roles=user_roles,
            ip_address=self._get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            path=request.url.path,
            method=request.method,
        )

        # Store context in request state
        request.state.context = context

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log successful request
            logging_service.log_api_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                user_id=user_id,
                context=context,
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except BaseApplicationException as exc:
            # Handle application exceptions
            duration_ms = (time.time() - start_time) * 1000

            response = error_handler.handle_application_exception(request, exc)

            # Log failed request
            logging_service.log_api_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                user_id=user_id,
                context=context,
                details={"error_code": exc.error_code.value},
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as exc:
            # Handle unexpected exceptions
            duration_ms = (time.time() - start_time) * 1000

            response = error_handler.handle_generic_exception(request, exc)

            # Log failed request
            logging_service.log_api_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                user_id=user_id,
                context=context,
                details={"exception_type": type(exc).__name__},
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""

        # Check for forwarded headers (load balancer/proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to direct connection
        if hasattr(request.client, "host"):
            return request.client.host

        return "unknown"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""

        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Basic rate limiting middleware."""

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}  # In production, use Redis or similar

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting."""

        # Get client identifier
        client_id = self._get_client_identifier(request)

        # Check rate limit
        if self._is_rate_limited(client_id):
            # Log rate limit violation
            logging_service.log_security_event(
                event_type="rate_limit_exceeded",
                severity="medium",
                details={
                    "client_id": client_id,
                    "path": request.url.path,
                    "method": request.method,
                },
            )

            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please try again later.",
                    },
                },
            )

        # Record request
        self._record_request(client_id)

        return await call_next(request)

    def _get_client_identifier(self, request: Request) -> str:
        """Get client identifier for rate limiting."""

        # Use user ID if authenticated
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        # Use IP address for anonymous requests
        ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if not ip:
            ip = getattr(request.client, "host", "unknown")

        return f"ip:{ip}"

    def _is_rate_limited(self, client_id: str) -> bool:
        """Check if client is rate limited."""

        current_time = time.time()
        window_start = current_time - 60  # 1 minute window

        # Clean old entries
        if client_id in self.request_counts:
            self.request_counts[client_id] = [
                timestamp
                for timestamp in self.request_counts[client_id]
                if timestamp > window_start
            ]

        # Check current count
        current_count = len(self.request_counts.get(client_id, []))
        return current_count >= self.requests_per_minute

    def _record_request(self, client_id: str):
        """Record a request for rate limiting."""

        current_time = time.time()

        if client_id not in self.request_counts:
            self.request_counts[client_id] = []

        self.request_counts[client_id].append(current_time)
