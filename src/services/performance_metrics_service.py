"""
Performance Metrics Service - Monitor and track system performance metrics.
Provides real-time performance monitoring, alerting, and analytics.
"""

import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque

from ..core.base_service import BaseService
from ..utils.logging_config import get_handler_logger


class PerformanceMetricsService(BaseService):
    """Service for tracking and analyzing system performance metrics."""

    def __init__(self):
        super().__init__("performance_metrics_service")
        self.logger = get_handler_logger("performance_metrics_service")

        # Performance data storage (in production, this would be a time-series database)
        self.metrics_store: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.endpoint_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "total_requests": 0,
                "total_response_time": 0.0,
                "min_response_time": float("inf"),
                "max_response_time": 0.0,
                "error_count": 0,
                "last_request": None,
            }
        )

        # Performance thresholds
        self.thresholds = {
            "response_time_warning": 0.5,  # 500ms
            "response_time_critical": 1.0,  # 1000ms
            "error_rate_warning": 0.05,  # 5%
            "error_rate_critical": 0.10,  # 10%
        }

        # Alert tracking
        self.active_alerts: List[Dict[str, Any]] = []

        self.logger.info("Performance metrics service initialized")

    async def initialize(self):
        """Initialize the performance metrics service."""
        try:
            # Start background tasks
            asyncio.create_task(self._cleanup_old_metrics())
            asyncio.create_task(self._performance_analysis_task())

            self.logger.info("Performance metrics service initialized successfully")
            return True
        except Exception as e:
            self.logger.error(
                f"Failed to initialize performance metrics service: {str(e)}"
            )
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the performance metrics service."""
        try:
            total_endpoints = len(self.endpoint_stats)
            total_requests = sum(
                stats["total_requests"] for stats in self.endpoint_stats.values()
            )
            active_alerts_count = len(self.active_alerts)

            return {
                "service": "performance_metrics_service",
                "status": "healthy",
                "total_endpoints_tracked": total_endpoints,
                "total_requests_tracked": total_requests,
                "active_alerts": active_alerts_count,
                "metrics_stored": sum(
                    len(metrics) for metrics in self.metrics_store.values()
                ),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            self.logger.error(
                f"Performance metrics service health check failed: {str(e)}"
            )
            return {
                "service": "performance_metrics_service",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def track_request(
        self,
        endpoint: str,
        method: str,
        response_time: float,
        status_code: int,
        user_id: Optional[str] = None,
        request_size: Optional[int] = None,
        response_size: Optional[int] = None,
    ):
        """Track a request's performance metrics."""
        try:
            timestamp = datetime.utcnow()

            # Create metric entry
            metric_entry = {
                "endpoint": endpoint,
                "method": method,
                "response_time": response_time,
                "status_code": status_code,
                "timestamp": timestamp,
                "user_id": user_id,
                "request_size": request_size,
                "response_size": response_size,
                "is_error": status_code >= 400,
            }

            # Store in metrics store
            metric_key = f"{method}:{endpoint}"
            self.metrics_store[metric_key].append(metric_entry)

            # Update endpoint statistics
            stats = self.endpoint_stats[metric_key]
            stats["total_requests"] += 1
            stats["total_response_time"] += response_time
            stats["min_response_time"] = min(stats["min_response_time"], response_time)
            stats["max_response_time"] = max(stats["max_response_time"], response_time)
            stats["last_request"] = timestamp

            if status_code >= 400:
                stats["error_count"] += 1

            # Check for performance alerts
            await self._check_performance_alerts(metric_key, metric_entry)

            self.logger.debug(
                f"Tracked request: {method} {endpoint} - {response_time:.3f}s - {status_code}"
            )

        except Exception as e:
            self.logger.error(f"Error tracking request metrics: {str(e)}")

    async def get_performance_dashboard(
        self, time_window_minutes: int = 60
    ) -> Dict[str, Any]:
        """Get comprehensive performance dashboard data."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)

            # Calculate overall metrics
            all_recent_metrics = []
            for metrics in self.metrics_store.values():
                recent_metrics = [m for m in metrics if m["timestamp"] > cutoff_time]
                all_recent_metrics.extend(recent_metrics)

            if not all_recent_metrics:
                return {
                    "message": "No recent metrics available",
                    "time_window_minutes": time_window_minutes,
                    "timestamp": datetime.utcnow().isoformat(),
                }

            # Calculate dashboard metrics
            total_requests = len(all_recent_metrics)
            error_requests = sum(1 for m in all_recent_metrics if m["is_error"])
            response_times = [m["response_time"] for m in all_recent_metrics]

            avg_response_time = sum(response_times) / len(response_times)
            error_rate = error_requests / total_requests if total_requests > 0 else 0

            # Get slowest endpoints
            slowest_endpoints = await self._get_slowest_endpoints(cutoff_time, limit=10)

            # Get endpoint performance breakdown
            endpoint_breakdown = await self._get_endpoint_breakdown(cutoff_time)

            # Get performance trends
            performance_trends = await self._get_performance_trends(time_window_minutes)

            return {
                "overview": {
                    "total_requests": total_requests,
                    "error_requests": error_requests,
                    "error_rate": round(error_rate * 100, 2),
                    "average_response_time_ms": round(avg_response_time * 1000, 2),
                    "min_response_time_ms": round(min(response_times) * 1000, 2),
                    "max_response_time_ms": round(max(response_times) * 1000, 2),
                    "time_window_minutes": time_window_minutes,
                },
                "slowest_endpoints": slowest_endpoints,
                "endpoint_breakdown": endpoint_breakdown,
                "performance_trends": performance_trends,
                "active_alerts": self.active_alerts,
                "thresholds": self.thresholds,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error getting performance dashboard: {str(e)}")
            return {"error": str(e)}

    async def get_endpoint_metrics(
        self, endpoint: str, method: str = "GET", time_window_minutes: int = 60
    ) -> Dict[str, Any]:
        """Get detailed metrics for a specific endpoint."""
        try:
            metric_key = f"{method}:{endpoint}"
            cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)

            # Get recent metrics for this endpoint
            if metric_key not in self.metrics_store:
                return {
                    "endpoint": endpoint,
                    "method": method,
                    "message": "No metrics available for this endpoint",
                    "timestamp": datetime.utcnow().isoformat(),
                }

            recent_metrics = [
                m
                for m in self.metrics_store[metric_key]
                if m["timestamp"] > cutoff_time
            ]

            if not recent_metrics:
                return {
                    "endpoint": endpoint,
                    "method": method,
                    "message": "No recent metrics available",
                    "time_window_minutes": time_window_minutes,
                    "timestamp": datetime.utcnow().isoformat(),
                }

            # Calculate endpoint-specific metrics
            response_times = [m["response_time"] for m in recent_metrics]
            error_count = sum(1 for m in recent_metrics if m["is_error"])

            # Calculate percentiles
            sorted_times = sorted(response_times)
            p50_index = int(len(sorted_times) * 0.5)
            p95_index = int(len(sorted_times) * 0.95)
            p99_index = int(len(sorted_times) * 0.99)

            return {
                "endpoint": endpoint,
                "method": method,
                "time_window_minutes": time_window_minutes,
                "total_requests": len(recent_metrics),
                "error_count": error_count,
                "error_rate": round(error_count / len(recent_metrics) * 100, 2),
                "response_times": {
                    "average_ms": round(
                        sum(response_times) / len(response_times) * 1000, 2
                    ),
                    "min_ms": round(min(response_times) * 1000, 2),
                    "max_ms": round(max(response_times) * 1000, 2),
                    "p50_ms": round(sorted_times[p50_index] * 1000, 2),
                    "p95_ms": round(sorted_times[p95_index] * 1000, 2),
                    "p99_ms": round(sorted_times[p99_index] * 1000, 2),
                },
                "recent_requests": [
                    {
                        "timestamp": m["timestamp"].isoformat(),
                        "response_time_ms": round(m["response_time"] * 1000, 2),
                        "status_code": m["status_code"],
                        "is_error": m["is_error"],
                    }
                    for m in recent_metrics[-20:]  # Last 20 requests
                ],
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error getting endpoint metrics: {str(e)}")
            return {"error": str(e)}

    async def get_performance_alerts(self) -> List[Dict[str, Any]]:
        """Get current performance alerts."""
        return self.active_alerts.copy()

    async def clear_alerts(self, alert_ids: Optional[List[str]] = None) -> int:
        """Clear performance alerts."""
        try:
            if alert_ids is None:
                # Clear all alerts
                cleared_count = len(self.active_alerts)
                self.active_alerts.clear()
            else:
                # Clear specific alerts
                original_count = len(self.active_alerts)
                self.active_alerts = [
                    alert
                    for alert in self.active_alerts
                    if alert.get("id") not in alert_ids
                ]
                cleared_count = original_count - len(self.active_alerts)

            self.logger.info(f"Cleared {cleared_count} performance alerts")
            return cleared_count

        except Exception as e:
            self.logger.error(f"Error clearing alerts: {str(e)}")
            return 0

    async def _check_performance_alerts(
        self, metric_key: str, metric_entry: Dict[str, Any]
    ):
        """Check if performance metrics trigger any alerts."""
        try:
            endpoint = metric_entry["endpoint"]
            response_time = metric_entry["response_time"]
            is_error = metric_entry["is_error"]

            # Check response time alerts
            if response_time > self.thresholds["response_time_critical"]:
                await self._create_alert(
                    "response_time_critical",
                    f"Critical response time: {endpoint}",
                    f"Response time {response_time:.3f}s exceeds critical threshold",
                    {"endpoint": endpoint, "response_time": response_time},
                )
            elif response_time > self.thresholds["response_time_warning"]:
                await self._create_alert(
                    "response_time_warning",
                    f"High response time: {endpoint}",
                    f"Response time {response_time:.3f}s exceeds warning threshold",
                    {"endpoint": endpoint, "response_time": response_time},
                )

            # Check error rate alerts (calculate recent error rate)
            recent_metrics = list(self.metrics_store[metric_key])[
                -100:
            ]  # Last 100 requests
            if len(recent_metrics) >= 10:  # Only check if we have enough data
                error_rate = sum(1 for m in recent_metrics if m["is_error"]) / len(
                    recent_metrics
                )

                if error_rate > self.thresholds["error_rate_critical"]:
                    await self._create_alert(
                        "error_rate_critical",
                        f"Critical error rate: {endpoint}",
                        f"Error rate {error_rate:.1%} exceeds critical threshold",
                        {"endpoint": endpoint, "error_rate": error_rate},
                    )
                elif error_rate > self.thresholds["error_rate_warning"]:
                    await self._create_alert(
                        "error_rate_warning",
                        f"High error rate: {endpoint}",
                        f"Error rate {error_rate:.1%} exceeds warning threshold",
                        {"endpoint": endpoint, "error_rate": error_rate},
                    )

        except Exception as e:
            self.logger.error(f"Error checking performance alerts: {str(e)}")

    async def _create_alert(
        self, alert_type: str, title: str, description: str, metadata: Dict[str, Any]
    ):
        """Create a new performance alert."""
        try:
            alert_id = f"{alert_type}_{int(time.time())}"

            # Check if similar alert already exists (avoid spam)
            similar_alerts = [
                alert
                for alert in self.active_alerts
                if alert["type"] == alert_type
                and alert["metadata"].get("endpoint") == metadata.get("endpoint")
            ]

            if similar_alerts:
                # Update existing alert instead of creating new one
                similar_alerts[0]["count"] = similar_alerts[0].get("count", 1) + 1
                similar_alerts[0]["last_occurrence"] = datetime.utcnow().isoformat()
                return

            alert = {
                "id": alert_id,
                "type": alert_type,
                "title": title,
                "description": description,
                "metadata": metadata,
                "created_at": datetime.utcnow().isoformat(),
                "count": 1,
                "severity": "critical" if "critical" in alert_type else "warning",
            }

            self.active_alerts.append(alert)

            # Limit number of active alerts
            if len(self.active_alerts) > 100:
                self.active_alerts = self.active_alerts[-100:]

            self.logger.warning(f"Performance alert created: {title}")

        except Exception as e:
            self.logger.error(f"Error creating alert: {str(e)}")

    async def _get_slowest_endpoints(
        self, cutoff_time: datetime, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get the slowest endpoints within the time window."""
        try:
            endpoint_avg_times = {}

            for metric_key, metrics in self.metrics_store.items():
                recent_metrics = [m for m in metrics if m["timestamp"] > cutoff_time]
                if recent_metrics:
                    avg_time = sum(m["response_time"] for m in recent_metrics) / len(
                        recent_metrics
                    )
                    endpoint_avg_times[metric_key] = {
                        "average_response_time_ms": round(avg_time * 1000, 2),
                        "request_count": len(recent_metrics),
                        "endpoint": recent_metrics[0]["endpoint"],
                        "method": recent_metrics[0]["method"],
                    }

            # Sort by average response time and return top N
            sorted_endpoints = sorted(
                endpoint_avg_times.items(),
                key=lambda x: x[1]["average_response_time_ms"],
                reverse=True,
            )

            return [data for _, data in sorted_endpoints[:limit]]

        except Exception as e:
            self.logger.error(f"Error getting slowest endpoints: {str(e)}")
            return []

    async def _get_endpoint_breakdown(self, cutoff_time: datetime) -> Dict[str, Any]:
        """Get performance breakdown by endpoint."""
        try:
            breakdown = {}

            for metric_key, metrics in self.metrics_store.items():
                recent_metrics = [m for m in metrics if m["timestamp"] > cutoff_time]
                if recent_metrics:
                    response_times = [m["response_time"] for m in recent_metrics]
                    error_count = sum(1 for m in recent_metrics if m["is_error"])

                    breakdown[metric_key] = {
                        "total_requests": len(recent_metrics),
                        "average_response_time_ms": round(
                            sum(response_times) / len(response_times) * 1000, 2
                        ),
                        "error_count": error_count,
                        "error_rate": round(error_count / len(recent_metrics) * 100, 2),
                    }

            return breakdown

        except Exception as e:
            self.logger.error(f"Error getting endpoint breakdown: {str(e)}")
            return {}

    async def _get_performance_trends(
        self, time_window_minutes: int
    ) -> List[Dict[str, Any]]:
        """Get performance trends over time."""
        try:
            # Create time buckets (5-minute intervals)
            bucket_size_minutes = 5
            num_buckets = time_window_minutes // bucket_size_minutes

            trends = []
            current_time = datetime.utcnow()

            for i in range(num_buckets):
                bucket_start = current_time - timedelta(
                    minutes=(i + 1) * bucket_size_minutes
                )
                bucket_end = current_time - timedelta(minutes=i * bucket_size_minutes)

                # Collect metrics for this time bucket
                bucket_metrics = []
                for metrics in self.metrics_store.values():
                    bucket_data = [
                        m
                        for m in metrics
                        if bucket_start <= m["timestamp"] < bucket_end
                    ]
                    bucket_metrics.extend(bucket_data)

                if bucket_metrics:
                    response_times = [m["response_time"] for m in bucket_metrics]
                    error_count = sum(1 for m in bucket_metrics if m["is_error"])

                    trends.append(
                        {
                            "timestamp": bucket_start.isoformat(),
                            "total_requests": len(bucket_metrics),
                            "average_response_time_ms": round(
                                sum(response_times) / len(response_times) * 1000, 2
                            ),
                            "error_count": error_count,
                            "error_rate": round(
                                error_count / len(bucket_metrics) * 100, 2
                            ),
                        }
                    )

            return list(reversed(trends))  # Return chronologically

        except Exception as e:
            self.logger.error(f"Error getting performance trends: {str(e)}")
            return []

    async def _cleanup_old_metrics(self):
        """Background task to clean up old metrics."""
        while True:
            try:
                cutoff_time = datetime.utcnow() - timedelta(
                    hours=24
                )  # Keep 24 hours of data

                for metric_key in list(self.metrics_store.keys()):
                    metrics = self.metrics_store[metric_key]
                    # Filter out old metrics
                    recent_metrics = deque(
                        (m for m in metrics if m["timestamp"] > cutoff_time),
                        maxlen=1000,
                    )
                    self.metrics_store[metric_key] = recent_metrics

                # Clean up empty metric stores
                empty_keys = [k for k, v in self.metrics_store.items() if len(v) == 0]
                for key in empty_keys:
                    del self.metrics_store[key]
                    if key in self.endpoint_stats:
                        del self.endpoint_stats[key]

                self.logger.debug("Cleaned up old performance metrics")

                # Sleep for 1 hour before next cleanup
                await asyncio.sleep(3600)

            except Exception as e:
                self.logger.error(f"Error in metrics cleanup task: {str(e)}")
                await asyncio.sleep(300)  # Shorter sleep on error

    async def _performance_analysis_task(self):
        """Background task for continuous performance analysis."""
        while True:
            try:
                # Perform periodic performance analysis
                await self._analyze_performance_patterns()

                # Sleep for 10 minutes before next analysis
                await asyncio.sleep(600)

            except Exception as e:
                self.logger.error(f"Error in performance analysis task: {str(e)}")
                await asyncio.sleep(300)

    async def _analyze_performance_patterns(self):
        """Analyze performance patterns and generate insights."""
        try:
            # This could include:
            # - Detecting performance degradation trends
            # - Identifying peak usage patterns
            # - Suggesting optimization opportunities
            # - Predicting capacity needs

            self.logger.debug("Performance pattern analysis completed")

        except Exception as e:
            self.logger.error(f"Error in performance pattern analysis: {str(e)}")
