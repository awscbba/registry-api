"""
Metrics Middleware for automatic performance monitoring.

Automatically collects metrics for all API requests including
response times, status codes, and request patterns.
"""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..services.metrics_service import metrics_collector
from ..utils.logging_config import get_handler_logger

logger = get_handler_logger("metrics_middleware")


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically collect performance metrics for all requests.

    Collects:
    - Request count per endpoint
    - Response times
    - HTTP status codes
    - Error rates
    - Active request tracking
    """

    def __init__(self, app, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics."""

        # Skip metrics collection for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Record request start
        start_time = time.time()
        metrics_collector.increment_active_requests()

        try:
            # Process request
            response = await call_next(request)

            # Calculate response time
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds

            # Record metrics
            metrics_collector.record_request(
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                response_time=response_time,
            )

            # Add performance headers
            response.headers["X-Response-Time"] = f"{response_time:.2f}ms"
            response.headers["X-Request-ID"] = str(id(request))

            return response

        except Exception as e:
            # Record error metrics
            end_time = time.time()
            response_time = (end_time - start_time) * 1000

            metrics_collector.record_request(
                endpoint=request.url.path,
                method=request.method,
                status_code=500,
                response_time=response_time,
            )

            logger.error(
                f"Request failed: {request.method} {request.url.path} - {str(e)}"
            )
            raise

        finally:
            # Always decrement active requests
            metrics_collector.decrement_active_requests()


class MetricsCollectionMiddleware:
    """
    Alternative lightweight metrics collection middleware.

    Can be used as a simple function-based middleware if preferred
    over the class-based approach.
    """

    @staticmethod
    async def collect_metrics(request: Request, call_next: Callable) -> Response:
        """Collect metrics for the request."""

        # Skip certain paths
        skip_paths = ["/docs", "/redoc", "/openapi.json", "/favicon.ico"]
        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)

        start_time = time.time()
        metrics_collector.increment_active_requests()

        try:
            response = await call_next(request)

            # Calculate and record metrics
            response_time = (time.time() - start_time) * 1000
            metrics_collector.record_request(
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                response_time=response_time,
            )

            return response

        except Exception as e:
            # Record error
            response_time = (time.time() - start_time) * 1000
            metrics_collector.record_request(
                endpoint=request.url.path,
                method=request.method,
                status_code=500,
                response_time=response_time,
            )
            raise

        finally:
            metrics_collector.decrement_active_requests()
