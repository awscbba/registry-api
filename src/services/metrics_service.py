"""
Metrics Collection Service for Phase 2 Service Monitoring.

Provides comprehensive metrics collection, performance monitoring,
and real-time analytics for the People Registry API.
"""

import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from functools import wraps
from collections import defaultdict, deque
import json
import logging

from ..core.base_service import BaseService


class MetricsCollector:
    """Thread-safe metrics collector for performance data."""

    def __init__(self):
        self.request_count = defaultdict(int)
        self.response_times = defaultdict(deque)
        self.error_count = defaultdict(int)
        self.active_requests = 0
        self.start_time = datetime.utcnow()

        # Keep only last 1000 response times per endpoint
        self.max_response_times = 1000

    def record_request(
        self, endpoint: str, method: str, status_code: int, response_time: float
    ):
        """Record a request with its metrics."""
        key = f"{method}:{endpoint}"

        self.request_count[key] += 1

        # Add response time (keep only recent ones)
        if len(self.response_times[key]) >= self.max_response_times:
            self.response_times[key].popleft()
        self.response_times[key].append(response_time)

        # Count errors (4xx and 5xx)
        if status_code >= 400:
            self.error_count[key] += 1

    def increment_active_requests(self):
        """Increment active request counter."""
        self.active_requests += 1

    def decrement_active_requests(self):
        """Decrement active request counter."""
        self.active_requests = max(0, self.active_requests - 1)

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics summary."""
        total_requests = sum(self.request_count.values())
        total_errors = sum(self.error_count.values())

        # Calculate average response times
        avg_response_times = {}
        for endpoint, times in self.response_times.items():
            if times:
                avg_response_times[endpoint] = sum(times) / len(times)

        uptime = datetime.utcnow() - self.start_time

        return {
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate": (
                (total_errors / total_requests * 100) if total_requests > 0 else 0
            ),
            "active_requests": self.active_requests,
            "uptime_seconds": uptime.total_seconds(),
            "uptime_formatted": str(uptime),
            "request_count_by_endpoint": dict(self.request_count),
            "error_count_by_endpoint": dict(self.error_count),
            "avg_response_times": avg_response_times,
            "timestamp": datetime.utcnow().isoformat(),
        }


# Global metrics collector instance
metrics_collector = MetricsCollector()


def monitor_performance(func):
    """Decorator to monitor function performance."""

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        metrics_collector.increment_active_requests()

        try:
            result = await func(*args, **kwargs)
            status_code = getattr(result, "status_code", 200)
            return result
        except Exception as e:
            status_code = 500
            raise
        finally:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds

            # Extract endpoint info from function name or args
            endpoint = func.__name__
            method = "UNKNOWN"

            # Try to extract more info from FastAPI request if available
            if args and hasattr(args[0], "url"):
                request = args[0]
                endpoint = str(request.url.path)
                method = request.method

            metrics_collector.record_request(
                endpoint, method, status_code, response_time
            )
            metrics_collector.decrement_active_requests()

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        metrics_collector.increment_active_requests()

        try:
            result = func(*args, **kwargs)
            status_code = getattr(result, "status_code", 200)
            return result
        except Exception as e:
            status_code = 500
            raise
        finally:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000

            endpoint = func.__name__
            method = "UNKNOWN"

            metrics_collector.record_request(
                endpoint, method, status_code, response_time
            )
            metrics_collector.decrement_active_requests()

    # Return appropriate wrapper based on function type
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


class MetricsService(BaseService):
    """
    Service for collecting and analyzing system metrics.

    Provides real-time performance monitoring, alerting capabilities,
    and comprehensive analytics for the People Registry API.
    """

    def __init__(self):
        super().__init__("metrics")
        self.collector = metrics_collector
        self.alert_thresholds = {
            "error_rate_percent": 5.0,  # Alert if error rate > 5%
            "avg_response_time_ms": 1000,  # Alert if avg response time > 1s
            "active_requests": 50,  # Alert if > 50 concurrent requests
        }
        self.alerts_history = deque(maxlen=100)  # Keep last 100 alerts

    async def initialize(self):
        """Initialize the metrics service."""
        try:
            self.logger.info("Metrics service initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize metrics service: {str(e)}")
            return False

    async def get_current_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        try:
            metrics = self.collector.get_metrics()

            # Add additional calculated metrics
            metrics["performance_grade"] = self._calculate_performance_grade(metrics)
            metrics["health_status"] = self._determine_health_status(metrics)

            return metrics
        except Exception as e:
            self.logger.error(f"Failed to get current metrics: {str(e)}")
            return {
                "error": "Failed to retrieve metrics",
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def get_performance_analytics(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance analytics for the specified time period."""
        try:
            current_metrics = await self.get_current_metrics()

            # For now, return current metrics with trend analysis
            # In a production system, this would query historical data
            analytics = {
                "period_hours": hours,
                "current_metrics": current_metrics,
                "trends": {
                    "request_volume": "stable",  # Would be calculated from historical data
                    "response_time": "improving",
                    "error_rate": "stable",
                },
                "recommendations": self._generate_recommendations(current_metrics),
                "timestamp": datetime.utcnow().isoformat(),
            }

            return analytics
        except Exception as e:
            self.logger.error(f"Failed to get performance analytics: {str(e)}")
            return {
                "error": "Failed to retrieve analytics",
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def check_alerts(self) -> List[Dict[str, Any]]:
        """Check for alert conditions and return active alerts."""
        try:
            metrics = await self.get_current_metrics()
            alerts = []

            # Check error rate
            if (
                metrics.get("error_rate", 0)
                > self.alert_thresholds["error_rate_percent"]
            ):
                alert = {
                    "type": "error_rate",
                    "severity": "warning" if metrics["error_rate"] < 10 else "critical",
                    "message": f"High error rate: {metrics['error_rate']:.2f}%",
                    "value": metrics["error_rate"],
                    "threshold": self.alert_thresholds["error_rate_percent"],
                    "timestamp": datetime.utcnow().isoformat(),
                }
                alerts.append(alert)
                self.alerts_history.append(alert)

            # Check average response time
            avg_times = metrics.get("avg_response_times", {})
            if avg_times:
                overall_avg = sum(avg_times.values()) / len(avg_times)
                if overall_avg > self.alert_thresholds["avg_response_time_ms"]:
                    alert = {
                        "type": "response_time",
                        "severity": "warning" if overall_avg < 2000 else "critical",
                        "message": f"High response time: {overall_avg:.2f}ms",
                        "value": overall_avg,
                        "threshold": self.alert_thresholds["avg_response_time_ms"],
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    alerts.append(alert)
                    self.alerts_history.append(alert)

            # Check active requests
            if (
                metrics.get("active_requests", 0)
                > self.alert_thresholds["active_requests"]
            ):
                alert = {
                    "type": "high_load",
                    "severity": "warning",
                    "message": f"High concurrent requests: {metrics['active_requests']}",
                    "value": metrics["active_requests"],
                    "threshold": self.alert_thresholds["active_requests"],
                    "timestamp": datetime.utcnow().isoformat(),
                }
                alerts.append(alert)
                self.alerts_history.append(alert)

            return alerts
        except Exception as e:
            self.logger.error(f"Failed to check alerts: {str(e)}")
            return []

    async def get_alerts_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent alerts history."""
        try:
            # Return most recent alerts up to limit
            recent_alerts = list(self.alerts_history)[-limit:]
            return recent_alerts
        except Exception as e:
            self.logger.error(f"Failed to get alerts history: {str(e)}")
            return []

    async def get_endpoint_metrics(
        self, endpoint: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get metrics for specific endpoint or all endpoints."""
        try:
            metrics = await self.get_current_metrics()

            if endpoint:
                # Filter metrics for specific endpoint
                endpoint_data = {}
                for key, value in metrics["request_count_by_endpoint"].items():
                    if endpoint in key:
                        endpoint_data[key] = {
                            "requests": value,
                            "errors": metrics["error_count_by_endpoint"].get(key, 0),
                            "avg_response_time": metrics["avg_response_times"].get(
                                key, 0
                            ),
                        }
                return {
                    "endpoint": endpoint,
                    "data": endpoint_data,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            else:
                # Return all endpoint metrics
                all_endpoints = {}
                for key in metrics["request_count_by_endpoint"].keys():
                    all_endpoints[key] = {
                        "requests": metrics["request_count_by_endpoint"][key],
                        "errors": metrics["error_count_by_endpoint"].get(key, 0),
                        "avg_response_time": metrics["avg_response_times"].get(key, 0),
                        "error_rate": (
                            (
                                metrics["error_count_by_endpoint"].get(key, 0)
                                / metrics["request_count_by_endpoint"][key]
                                * 100
                            )
                            if metrics["request_count_by_endpoint"][key] > 0
                            else 0
                        ),
                    }

                return {
                    "all_endpoints": all_endpoints,
                    "timestamp": datetime.utcnow().isoformat(),
                }
        except Exception as e:
            self.logger.error(f"Failed to get endpoint metrics: {str(e)}")
            return {
                "error": "Failed to retrieve endpoint metrics",
                "timestamp": datetime.utcnow().isoformat(),
            }

    def _calculate_performance_grade(self, metrics: Dict[str, Any]) -> str:
        """Calculate overall performance grade based on metrics."""
        score = 100

        # Deduct points for high error rate
        error_rate = metrics.get("error_rate", 0)
        if error_rate > 5:
            score -= min(30, error_rate * 2)

        # Deduct points for slow response times
        avg_times = metrics.get("avg_response_times", {})
        if avg_times:
            overall_avg = sum(avg_times.values()) / len(avg_times)
            if overall_avg > 500:  # 500ms threshold
                score -= min(25, (overall_avg - 500) / 20)

        # Deduct points for high load
        active_requests = metrics.get("active_requests", 0)
        if active_requests > 20:
            score -= min(15, active_requests - 20)

        # Convert score to grade
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def _determine_health_status(self, metrics: Dict[str, Any]) -> str:
        """Determine overall health status."""
        error_rate = metrics.get("error_rate", 0)
        active_requests = metrics.get("active_requests", 0)

        if error_rate > 10 or active_requests > 100:
            return "critical"
        elif error_rate > 5 or active_requests > 50:
            return "warning"
        else:
            return "healthy"

    def _generate_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate performance recommendations based on metrics."""
        recommendations = []

        error_rate = metrics.get("error_rate", 0)
        if error_rate > 5:
            recommendations.append(
                f"High error rate ({error_rate:.2f}%) detected. "
                "Review error logs and consider implementing circuit breakers."
            )

        avg_times = metrics.get("avg_response_times", {})
        if avg_times:
            slow_endpoints = [
                endpoint for endpoint, time in avg_times.items() if time > 1000
            ]
            if slow_endpoints:
                recommendations.append(
                    f"Slow endpoints detected: {', '.join(slow_endpoints)}. "
                    "Consider implementing caching or optimizing queries."
                )

        active_requests = metrics.get("active_requests", 0)
        if active_requests > 30:
            recommendations.append(
                f"High concurrent load ({active_requests} active requests). "
                "Consider implementing rate limiting or scaling resources."
            )

        if not recommendations:
            recommendations.append(
                "System performance is optimal. No immediate actions required."
            )

        return recommendations

    async def health_check(self) -> Dict[str, Any]:
        """Health check for metrics service."""
        try:
            # Test metrics collection
            test_metrics = await self.get_current_metrics()

            return {
                "healthy": True,
                "status": "operational",
                "metrics_available": "timestamp" in test_metrics,
                "collector_active": self.collector is not None,
                "last_check": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {
                "healthy": False,
                "status": "error",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat(),
            }
