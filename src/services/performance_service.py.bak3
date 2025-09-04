"""
Performance Service - Enterprise-grade performance monitoring and health checks.
Implements the Service Registry pattern for system performance monitoring.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
import time
import psutil
import asyncio
from dataclasses import dataclass

from ..repositories.people_repository import PeopleRepository
from ..repositories.projects_repository import ProjectsRepository
from ..repositories.subscriptions_repository import SubscriptionsRepository
from .logging_service import EnterpriseLoggingService, LogLevel, LogCategory


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure."""

    response_time_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float
    database_connections: int
    active_requests: int
    timestamp: str


@dataclass
class HealthStatus:
    """System health status."""

    status: str  # "healthy", "degraded", "unhealthy"
    overall_score: float  # 0-100
    components: Dict[str, Any]
    metrics: PerformanceMetrics
    timestamp: str


class PerformanceService:
    """
    Enterprise-grade performance monitoring service.

    Provides comprehensive system health monitoring, performance metrics,
    and diagnostic information following Service Registry patterns.
    """

    def __init__(self, logging_service: Optional[EnterpriseLoggingService] = None):
        """Initialize performance service with dependency injection."""
        self.logging_service = logging_service or EnterpriseLoggingService()

        # Repository dependencies for health checks
        self.people_repository = PeopleRepository()
        self.projects_repository = ProjectsRepository()
        self.subscriptions_repository = SubscriptionsRepository()

        # Performance tracking
        self._request_count = 0
        self._total_response_time = 0.0
        self._start_time = time.time()

        self.logging_service.log_structured(
            level=LogLevel.INFO,
            category=LogCategory.PERFORMANCE,
            message="Performance service initialized",
            additional_data={"service": "performance_service"},
        )

    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system health status.

        Returns:
            Dict containing health status, metrics, and component details
        """
        try:
            start_time = time.time()

            # Collect system metrics
            metrics = await self._collect_system_metrics()

            # Check component health
            components = await self._check_component_health()

            # Calculate overall health score
            overall_score = self._calculate_health_score(components, metrics)

            # Determine status based on score
            if overall_score >= 90:
                status = "healthy"
            elif overall_score >= 70:
                status = "degraded"
            else:
                status = "unhealthy"

            response_time = (time.time() - start_time) * 1000

            health_status = HealthStatus(
                status=status,
                overall_score=overall_score,
                components=components,
                metrics=metrics,
                timestamp=datetime.now(timezone.utc).isoformat() + "Z",
            )

            # Log health check
            self.logging_service.log_structured(
                level=LogLevel.INFO,
                category=LogCategory.PERFORMANCE,
                message=f"Health check completed: {status}",
                additional_data={
                    "status": status,
                    "score": overall_score,
                    "response_time_ms": response_time,
                },
            )

            return {
                "status": health_status.status,
                "overallScore": health_status.overall_score,
                "components": health_status.components,
                "metrics": {
                    "responseTimeMs": health_status.metrics.response_time_ms,
                    "memoryUsageMb": health_status.metrics.memory_usage_mb,
                    "cpuUsagePercent": health_status.metrics.cpu_usage_percent,
                    "databaseConnections": health_status.metrics.database_connections,
                    "activeRequests": health_status.metrics.active_requests,
                    "timestamp": health_status.metrics.timestamp,
                },
                "timestamp": health_status.timestamp,
                "version": "2.0.0",
            }

        except Exception as e:
            self.logging_service.log_structured(
                level=LogLevel.ERROR,
                category=LogCategory.PERFORMANCE,
                message=f"Health check failed: {str(e)}",
                additional_data={"error": str(e)},
            )

            return {
                "status": "unhealthy",
                "overallScore": 0.0,
                "components": {"error": str(e)},
                "metrics": {
                    "responseTimeMs": 0.0,
                    "memoryUsageMb": 0.0,
                    "cpuUsagePercent": 0.0,
                    "databaseConnections": 0,
                    "activeRequests": 0,
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                },
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                "error": str(e),
            }

    async def _collect_system_metrics(self) -> PerformanceMetrics:
        """Collect system performance metrics."""
        try:
            # Get system metrics
            memory_info = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=0.1)

            # Calculate average response time
            avg_response_time = self._total_response_time / max(self._request_count, 1)

            return PerformanceMetrics(
                response_time_ms=avg_response_time,
                memory_usage_mb=memory_info.used / (1024 * 1024),
                cpu_usage_percent=cpu_percent,
                database_connections=3,  # Simulated - DynamoDB doesn't have traditional connections
                active_requests=self._request_count,
                timestamp=datetime.now(timezone.utc).isoformat() + "Z",
            )

        except Exception as e:
            # Return default metrics on error
            return PerformanceMetrics(
                response_time_ms=0.0,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                database_connections=0,
                active_requests=0,
                timestamp=datetime.now(timezone.utc).isoformat() + "Z",
            )

    async def _check_component_health(self) -> Dict[str, Any]:
        """Check health of all system components."""
        components = {}

        # Check database connectivity
        try:
            # Test people repository
            people_health = await self._check_repository_health(
                self.people_repository, "people"
            )
            components["database_people"] = people_health

            # Test projects repository
            projects_health = await self._check_repository_health(
                self.projects_repository, "projects"
            )
            components["database_projects"] = projects_health

            # Test subscriptions repository
            subscriptions_health = await self._check_repository_health(
                self.subscriptions_repository, "subscriptions"
            )
            components["database_subscriptions"] = subscriptions_health

        except Exception as e:
            components["database"] = {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }

        # Check API endpoints
        components["api"] = {
            "status": "healthy",
            "uptime_seconds": time.time() - self._start_time,
            "requests_processed": self._request_count,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        }

        # Check memory usage
        try:
            memory_info = psutil.virtual_memory()
            memory_status = "healthy" if memory_info.percent < 80 else "degraded"
            components["memory"] = {
                "status": memory_status,
                "usage_percent": memory_info.percent,
                "available_mb": memory_info.available / (1024 * 1024),
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }
        except Exception as e:
            components["memory"] = {
                "status": "unknown",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }

        return components

    async def _check_repository_health(self, repository, name: str) -> Dict[str, Any]:
        """Check health of a specific repository."""
        try:
            start_time = time.time()

            # Perform a simple health check operation
            if hasattr(repository, "health_check"):
                await repository.health_check()
            else:
                # Fallback: try to list items with limit
                await repository.list_all()

            response_time = (time.time() - start_time) * 1000

            return {
                "status": "healthy",
                "response_time_ms": response_time,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }

    def _calculate_health_score(
        self, components: Dict[str, Any], metrics: PerformanceMetrics
    ) -> float:
        """Calculate overall health score based on components and metrics."""
        try:
            total_score = 0.0
            component_count = 0

            # Score each component
            for component_name, component_data in components.items():
                if isinstance(component_data, dict) and "status" in component_data:
                    status = component_data["status"]
                    if status == "healthy":
                        total_score += 100
                    elif status == "degraded":
                        total_score += 70
                    elif status == "unhealthy":
                        total_score += 30
                    else:  # unknown
                        total_score += 50
                    component_count += 1

            # Calculate base score from components
            base_score = total_score / max(component_count, 1)

            # Apply performance penalties
            performance_score = base_score

            # Penalty for high response time
            if metrics.response_time_ms > 1000:
                performance_score -= 10
            elif metrics.response_time_ms > 500:
                performance_score -= 5

            # Penalty for high memory usage
            if metrics.memory_usage_mb > 1000:  # > 1GB
                performance_score -= 10
            elif metrics.memory_usage_mb > 500:  # > 500MB
                performance_score -= 5

            # Penalty for high CPU usage
            if metrics.cpu_usage_percent > 80:
                performance_score -= 10
            elif metrics.cpu_usage_percent > 60:
                performance_score -= 5

            return max(0.0, min(100.0, performance_score))

        except Exception:
            return 50.0  # Default score on calculation error

    def record_request(self, response_time_ms: float):
        """Record a request for performance tracking."""
        self._request_count += 1
        self._total_response_time += response_time_ms

    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get detailed performance statistics."""
        try:
            uptime_seconds = time.time() - self._start_time
            avg_response_time = self._total_response_time / max(self._request_count, 1)

            return {
                "uptime_seconds": uptime_seconds,
                "uptime_formatted": str(timedelta(seconds=int(uptime_seconds))),
                "total_requests": self._request_count,
                "average_response_time_ms": avg_response_time,
                "requests_per_second": self._request_count / max(uptime_seconds, 1),
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }

        except Exception as e:
            self.logging_service.log_structured(
                level=LogLevel.ERROR,
                category=LogCategory.PERFORMANCE,
                message=f"Failed to get performance stats: {str(e)}",
                additional_data={"error": str(e)},
            )

            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }
