"""
Performance Middleware - Automatically track request performance metrics.
Integrates with PerformanceMetricsService to provide comprehensive monitoring.
"""

import time
import uuid
import asyncio
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..services.service_registry_manager import service_manager
from ..utils.logging_config import get_handler_logger


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic performance tracking and monitoring."""

    def __init__(self, app, enable_detailed_logging: bool = False):
        super().__init__(app)
        self.logger = get_handler_logger("performance_middleware")
        self.enable_detailed_logging = enable_detailed_logging

        # Performance tracking settings
        self.track_request_size = True
        self.track_response_size = True
        self.exclude_paths = {"/health", "/docs", "/openapi.json", "/redoc"}

        self.logger.info("Performance middleware initialized")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and track performance metrics."""
        # Skip tracking for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Generate request ID for tracking
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # Add request context
        request.state.request_id = request_id
        request.state.start_time = start_time

        # Get request size if enabled
        request_size = None
        if self.track_request_size:
            request_size = await self._get_request_size(request)

        # Get user context if available
        user_id = None
        if hasattr(request.state, "current_user"):
            user_id = getattr(request.state.current_user, "id", None)

        try:
            # Process the request
            response = await call_next(request)

            # Calculate response time
            end_time = time.time()
            response_time = end_time - start_time

            # Get response size if enabled
            response_size = None
            if self.track_response_size:
                response_size = self._get_response_size(response)

            # Add performance headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{response_time:.6f}"
            response.headers["X-Process-Time-MS"] = f"{response_time * 1000:.2f}"

            # Track metrics asynchronously
            asyncio.create_task(
                self._track_request_metrics(
                    request=request,
                    response_time=response_time,
                    status_code=response.status_code,
                    user_id=user_id,
                    request_size=request_size,
                    response_size=response_size,
                )
            )

            # Log detailed information if enabled
            if self.enable_detailed_logging:
                self.logger.info(
                    f"Request processed: {request.method} {request.url.path} - "
                    f"{response_time:.3f}s - {response.status_code}",
                    extra={
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "response_time": response_time,
                        "status_code": response.status_code,
                        "user_id": user_id,
                    },
                )

            return response

        except Exception as e:
            # Handle errors and still track metrics
            end_time = time.time()
            response_time = end_time - start_time

            # Track error metrics
            asyncio.create_task(
                self._track_request_metrics(
                    request=request,
                    response_time=response_time,
                    status_code=500,
                    user_id=user_id,
                    request_size=request_size,
                    response_size=None,
                    error=str(e),
                )
            )

            self.logger.error(
                f"Request error: {request.method} {request.url.path} - "
                f"{response_time:.3f}s - Error: {str(e)}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "response_time": response_time,
                    "error": str(e),
                },
            )

            # Re-raise the exception
            raise

    async def _track_request_metrics(
        self,
        request: Request,
        response_time: float,
        status_code: int,
        user_id: Optional[str] = None,
        request_size: Optional[int] = None,
        response_size: Optional[int] = None,
        error: Optional[str] = None,
    ):
        """Track request metrics using the performance metrics service."""
        try:
            # Get performance metrics service
            performance_service = service_manager.get_service("performance_metrics")

            if performance_service:
                await performance_service.track_request(
                    endpoint=request.url.path,
                    method=request.method,
                    response_time=response_time,
                    status_code=status_code,
                    user_id=user_id,
                    request_size=request_size,
                    response_size=response_size,
                )

        except Exception as e:
            self.logger.error(f"Error tracking request metrics: {str(e)}")

    async def _get_request_size(self, request: Request) -> Optional[int]:
        """Get the size of the request body."""
        try:
            # Check Content-Length header first
            content_length = request.headers.get("content-length")
            if content_length:
                return int(content_length)

            # For requests without Content-Length, we can't easily get size
            # without consuming the body, so we'll skip it
            return None

        except Exception as e:
            self.logger.debug(f"Error getting request size: {str(e)}")
            return None

    def _get_response_size(self, response: Response) -> Optional[int]:
        """Get the size of the response body."""
        try:
            # Check Content-Length header
            content_length = response.headers.get("content-length")
            if content_length:
                return int(content_length)

            # For streaming responses or responses without Content-Length,
            # we can't easily determine size
            return None

        except Exception as e:
            self.logger.debug(f"Error getting response size: {str(e)}")
            return None


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Lightweight middleware for basic request timing without full metrics tracking."""

    def __init__(self, app):
        super().__init__(app)
        self.logger = get_handler_logger("request_timing_middleware")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add basic timing information to requests."""
        start_time = time.time()
        request.state.start_time = start_time

        try:
            response = await call_next(request)

            # Calculate and add timing header
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = f"{process_time:.6f}"

            return response

        except Exception as e:
            # Log timing even for errors
            process_time = time.time() - start_time
            self.logger.debug(
                f"Request failed after {process_time:.3f}s: {request.method} {request.url.path}"
            )
            raise


class PerformanceHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add performance-related headers to responses."""

    def __init__(self, app, include_server_timing: bool = True):
        super().__init__(app)
        self.include_server_timing = include_server_timing
        self.logger = get_handler_logger("performance_headers_middleware")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add performance headers to responses."""
        start_time = time.time()

        # Track different phases of request processing
        phases = {"middleware": 0, "handler": 0, "total": 0}

        middleware_start = time.time()

        try:
            # Process request
            handler_start = time.time()
            phases["middleware"] = handler_start - middleware_start

            response = await call_next(request)

            handler_end = time.time()
            phases["handler"] = handler_end - handler_start
            phases["total"] = handler_end - start_time

            # Add performance headers
            response.headers["X-Response-Time-Total"] = f"{phases['total']:.6f}"
            response.headers["X-Response-Time-MS"] = f"{phases['total'] * 1000:.2f}"

            if self.include_server_timing:
                # Add Server-Timing header for browser dev tools
                server_timing_parts = [
                    f"total;dur={phases['total'] * 1000:.2f}",
                    f"handler;dur={phases['handler'] * 1000:.2f}",
                    f"middleware;dur={phases['middleware'] * 1000:.2f}",
                ]
                response.headers["Server-Timing"] = ", ".join(server_timing_parts)

            # Add cache control headers for performance
            if request.url.path.startswith("/admin/"):
                response.headers["Cache-Control"] = (
                    "no-cache, no-store, must-revalidate"
                )
            elif request.url.path.startswith("/api/"):
                response.headers["Cache-Control"] = "public, max-age=300"  # 5 minutes

            return response

        except Exception as e:
            # Add timing info even for errors
            error_time = time.time() - start_time
            self.logger.debug(f"Request error after {error_time:.3f}s: {str(e)}")
            raise


# Utility functions for performance monitoring


def get_current_request_metrics(request: Request) -> dict:
    """Get current request performance metrics."""
    if not hasattr(request.state, "start_time"):
        return {}

    current_time = time.time()
    elapsed_time = current_time - request.state.start_time

    return {
        "request_id": getattr(request.state, "request_id", None),
        "elapsed_time": elapsed_time,
        "start_time": request.state.start_time,
        "method": request.method,
        "path": request.url.path,
    }


async def log_slow_request_warning(request: Request, threshold_seconds: float = 1.0):
    """Log a warning if request is taking too long."""
    metrics = get_current_request_metrics(request)

    if metrics.get("elapsed_time", 0) > threshold_seconds:
        logger = get_handler_logger("slow_request_monitor")
        logger.warning(
            f"Slow request detected: {metrics['method']} {metrics['path']} - "
            f"{metrics['elapsed_time']:.3f}s",
            extra=metrics,
        )


class SlowRequestMonitorMiddleware(BaseHTTPMiddleware):
    """Middleware to monitor and alert on slow requests."""

    def __init__(self, app, threshold_seconds: float = 2.0):
        super().__init__(app)
        self.threshold_seconds = threshold_seconds
        self.logger = get_handler_logger("slow_request_monitor")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Monitor request processing time and alert on slow requests."""
        start_time = time.time()

        try:
            response = await call_next(request)

            # Check if request was slow
            process_time = time.time() - start_time
            if process_time > self.threshold_seconds:
                self.logger.warning(
                    f"Slow request: {request.method} {request.url.path} - {process_time:.3f}s",
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "response_time": process_time,
                        "threshold": self.threshold_seconds,
                        "status_code": response.status_code,
                    },
                )

            return response

        except Exception as e:
            process_time = time.time() - start_time
            if process_time > self.threshold_seconds:
                self.logger.warning(
                    f"Slow request (with error): {request.method} {request.url.path} - "
                    f"{process_time:.3f}s - Error: {str(e)}",
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "response_time": process_time,
                        "threshold": self.threshold_seconds,
                        "error": str(e),
                    },
                )
            raise
