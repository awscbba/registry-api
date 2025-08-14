"""
Tests for Phase 2 Service Monitoring - Metrics Service.

Validates metrics collection, performance monitoring,
alerting, and analytics functionality.
"""

import pytest
import asyncio
import time
import sys
import os
from unittest.mock import patch, MagicMock, AsyncMock

# Add the parent directory to the path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.metrics_service import (
    MetricsService,
    MetricsCollector,
    monitor_performance,
)


class TestMetricsCollector:
    """Test the MetricsCollector class."""

    def setup_method(self):
        """Set up test environment."""
        self.collector = MetricsCollector()

    def test_metrics_collector_initialization(self):
        """Test that MetricsCollector initializes correctly."""
        assert self.collector.request_count == {}
        assert self.collector.response_times == {}
        assert self.collector.error_count == {}
        assert self.collector.active_requests == 0
        assert self.collector.start_time is not None

    def test_record_request(self):
        """Test recording request metrics."""
        self.collector.record_request("/test", "GET", 200, 150.5)

        key = "GET:/test"
        assert self.collector.request_count[key] == 1
        assert len(self.collector.response_times[key]) == 1
        assert self.collector.response_times[key][0] == 150.5
        assert self.collector.error_count[key] == 0

    def test_record_error_request(self):
        """Test recording error request metrics."""
        self.collector.record_request("/test", "POST", 500, 200.0)

        key = "POST:/test"
        assert self.collector.request_count[key] == 1
        assert self.collector.error_count[key] == 1

    def test_active_requests_tracking(self):
        """Test active request tracking."""
        assert self.collector.active_requests == 0

        self.collector.increment_active_requests()
        assert self.collector.active_requests == 1

        self.collector.increment_active_requests()
        assert self.collector.active_requests == 2

        self.collector.decrement_active_requests()
        assert self.collector.active_requests == 1

        self.collector.decrement_active_requests()
        assert self.collector.active_requests == 0

        # Test that it doesn't go below 0
        self.collector.decrement_active_requests()
        assert self.collector.active_requests == 0

    def test_get_metrics(self):
        """Test getting metrics summary."""
        # Add some test data
        self.collector.record_request("/api/test", "GET", 200, 100.0)
        self.collector.record_request("/api/test", "GET", 200, 150.0)
        self.collector.record_request("/api/test", "POST", 500, 200.0)
        self.collector.increment_active_requests()

        metrics = self.collector.get_metrics()

        assert "total_requests" in metrics
        assert "total_errors" in metrics
        assert "error_rate" in metrics
        assert "active_requests" in metrics
        assert "uptime_seconds" in metrics
        assert "uptime_formatted" in metrics
        assert "request_count_by_endpoint" in metrics
        assert "error_count_by_endpoint" in metrics
        assert "avg_response_times" in metrics
        assert "timestamp" in metrics

        assert metrics["total_requests"] == 3
        assert metrics["total_errors"] == 1
        assert metrics["error_rate"] == 33.33333333333333  # 1/3 * 100
        assert metrics["active_requests"] == 1

    def test_response_time_limit(self):
        """Test that response times are limited to max_response_times."""
        endpoint = "/test"
        method = "GET"
        key = f"{method}:{endpoint}"

        # Add more than max_response_times entries
        for i in range(1200):  # More than the default 1000
            self.collector.record_request(endpoint, method, 200, float(i))

        # Should only keep the last 1000
        assert len(self.collector.response_times[key]) == 1000
        # Should have the most recent values
        assert self.collector.response_times[key][-1] == 1199.0


class TestMetricsService:
    """Test the MetricsService class."""

    def setup_method(self):
        """Set up test environment."""
        self.metrics_service = MetricsService()

    @pytest.mark.asyncio
    async def test_metrics_service_initialization(self):
        """Test that MetricsService initializes correctly."""
        assert self.metrics_service.service_name == "metrics"
        assert self.metrics_service.collector is not None
        assert "error_rate_percent" in self.metrics_service.alert_thresholds
        assert "avg_response_time_ms" in self.metrics_service.alert_thresholds
        assert "active_requests" in self.metrics_service.alert_thresholds

    @pytest.mark.asyncio
    async def test_get_current_metrics(self):
        """Test getting current metrics."""
        # Add some test data
        self.metrics_service.collector.record_request("/test", "GET", 200, 100.0)

        metrics = await self.metrics_service.get_current_metrics()

        assert "total_requests" in metrics
        assert "performance_grade" in metrics
        assert "health_status" in metrics
        assert "timestamp" in metrics
        assert metrics["total_requests"] == 1

    @pytest.mark.asyncio
    async def test_get_performance_analytics(self):
        """Test getting performance analytics."""
        analytics = await self.metrics_service.get_performance_analytics(24)

        assert "period_hours" in analytics
        assert "current_metrics" in analytics
        assert "trends" in analytics
        assert "recommendations" in analytics
        assert "timestamp" in analytics
        assert analytics["period_hours"] == 24

    @pytest.mark.asyncio
    async def test_check_alerts_no_alerts(self):
        """Test alert checking with no alerts."""
        # Add normal metrics
        self.metrics_service.collector.record_request("/test", "GET", 200, 100.0)

        alerts = await self.metrics_service.check_alerts()

        assert isinstance(alerts, list)
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_check_alerts_high_error_rate(self):
        """Test alert checking with high error rate."""
        # Add metrics with high error rate
        for i in range(10):
            status = 500 if i < 6 else 200  # 60% error rate
            self.metrics_service.collector.record_request("/test", "GET", status, 100.0)

        alerts = await self.metrics_service.check_alerts()

        assert len(alerts) > 0
        error_rate_alert = next((a for a in alerts if a["type"] == "error_rate"), None)
        assert error_rate_alert is not None
        assert error_rate_alert["severity"] in ["warning", "critical"]

    @pytest.mark.asyncio
    async def test_check_alerts_high_response_time(self):
        """Test alert checking with high response time."""
        # Add metrics with high response time
        self.metrics_service.collector.record_request(
            "/test", "GET", 200, 2000.0
        )  # 2 seconds

        alerts = await self.metrics_service.check_alerts()

        response_time_alert = next(
            (a for a in alerts if a["type"] == "response_time"), None
        )
        assert response_time_alert is not None
        assert response_time_alert["severity"] in ["warning", "critical"]

    @pytest.mark.asyncio
    async def test_check_alerts_high_load(self):
        """Test alert checking with high load."""
        # Simulate high load
        for i in range(60):
            self.metrics_service.collector.increment_active_requests()

        alerts = await self.metrics_service.check_alerts()

        high_load_alert = next((a for a in alerts if a["type"] == "high_load"), None)
        assert high_load_alert is not None
        assert high_load_alert["severity"] == "warning"

    @pytest.mark.asyncio
    async def test_get_alerts_history(self):
        """Test getting alerts history."""
        # Trigger some alerts first
        for i in range(10):
            self.metrics_service.collector.record_request("/test", "GET", 500, 100.0)

        await self.metrics_service.check_alerts()  # This should create alerts

        history = await self.metrics_service.get_alerts_history(10)

        assert isinstance(history, list)
        # Should have at least one alert from the high error rate
        assert len(history) > 0

    @pytest.mark.asyncio
    async def test_get_endpoint_metrics_specific(self):
        """Test getting metrics for specific endpoint."""
        # Add test data
        self.metrics_service.collector.record_request("/api/test", "GET", 200, 100.0)
        self.metrics_service.collector.record_request("/api/test", "POST", 500, 150.0)
        self.metrics_service.collector.record_request("/api/other", "GET", 200, 120.0)

        metrics = await self.metrics_service.get_endpoint_metrics("/api/test")

        assert "endpoint" in metrics
        assert "data" in metrics
        assert "timestamp" in metrics
        assert metrics["endpoint"] == "/api/test"

        # Should only have data for endpoints containing "/api/test"
        for key in metrics["data"].keys():
            assert "/api/test" in key

    @pytest.mark.asyncio
    async def test_get_endpoint_metrics_all(self):
        """Test getting metrics for all endpoints."""
        # Add test data
        self.metrics_service.collector.record_request("/api/test", "GET", 200, 100.0)
        self.metrics_service.collector.record_request("/api/other", "POST", 200, 150.0)

        metrics = await self.metrics_service.get_endpoint_metrics()

        assert "all_endpoints" in metrics
        assert "timestamp" in metrics

        # Should have data for both endpoints
        assert "GET:/api/test" in metrics["all_endpoints"]
        assert "POST:/api/other" in metrics["all_endpoints"]

        # Check data structure
        endpoint_data = metrics["all_endpoints"]["GET:/api/test"]
        assert "requests" in endpoint_data
        assert "errors" in endpoint_data
        assert "avg_response_time" in endpoint_data
        assert "error_rate" in endpoint_data

    def test_calculate_performance_grade(self):
        """Test performance grade calculation."""
        # Test with good metrics
        good_metrics = {
            "error_rate": 1.0,
            "avg_response_times": {"GET:/test": 200.0},
            "active_requests": 5,
        }
        grade = self.metrics_service._calculate_performance_grade(good_metrics)
        assert grade in ["A", "B"]

        # Test with poor metrics
        poor_metrics = {
            "error_rate": 15.0,
            "avg_response_times": {"GET:/test": 3000.0},
            "active_requests": 100,
        }
        grade = self.metrics_service._calculate_performance_grade(poor_metrics)
        assert grade in ["D", "F"]

    def test_determine_health_status(self):
        """Test health status determination."""
        # Test healthy status
        healthy_metrics = {"error_rate": 2.0, "active_requests": 10}
        status = self.metrics_service._determine_health_status(healthy_metrics)
        assert status == "healthy"

        # Test warning status
        warning_metrics = {"error_rate": 7.0, "active_requests": 60}
        status = self.metrics_service._determine_health_status(warning_metrics)
        assert status == "warning"

        # Test critical status
        critical_metrics = {"error_rate": 15.0, "active_requests": 150}
        status = self.metrics_service._determine_health_status(critical_metrics)
        assert status == "critical"

    def test_generate_recommendations(self):
        """Test recommendation generation."""
        # Test with high error rate
        high_error_metrics = {
            "error_rate": 8.0,
            "avg_response_times": {"GET:/test": 200.0},
            "active_requests": 10,
        }
        recommendations = self.metrics_service._generate_recommendations(
            high_error_metrics
        )
        assert len(recommendations) > 0
        assert any("error rate" in rec.lower() for rec in recommendations)

        # Test with slow endpoints
        slow_metrics = {
            "error_rate": 1.0,
            "avg_response_times": {"GET:/slow": 2000.0},
            "active_requests": 10,
        }
        recommendations = self.metrics_service._generate_recommendations(slow_metrics)
        assert any("slow endpoints" in rec.lower() for rec in recommendations)

        # Test with optimal metrics
        optimal_metrics = {
            "error_rate": 0.5,
            "avg_response_times": {"GET:/test": 100.0},
            "active_requests": 5,
        }
        recommendations = self.metrics_service._generate_recommendations(
            optimal_metrics
        )
        assert any("optimal" in rec.lower() for rec in recommendations)

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test metrics service health check."""
        health = await self.metrics_service.health_check()

        assert "healthy" in health
        assert "status" in health
        assert "metrics_available" in health
        assert "collector_active" in health
        assert "last_check" in health

        assert health["healthy"] is True
        assert health["status"] == "operational"
        assert health["collector_active"] is True


class TestMonitorPerformanceDecorator:
    """Test the monitor_performance decorator."""

    def setup_method(self):
        """Set up test environment."""
        # Import the global collector to check metrics
        from src.services.metrics_service import metrics_collector

        self.collector = metrics_collector

        # Reset collector state for clean tests
        self.collector.request_count.clear()
        self.collector.response_times.clear()
        self.collector.error_count.clear()
        self.collector.active_requests = 0

    @pytest.mark.asyncio
    async def test_monitor_async_function(self):
        """Test monitoring async function."""

        @monitor_performance
        async def test_async_function():
            await asyncio.sleep(0.01)  # Small delay
            return "success"

        result = await test_async_function()
        assert result == "success"

        # Check that metrics were recorded
        metrics = self.collector.get_metrics()
        assert metrics["total_requests"] > 0

    def test_monitor_sync_function(self):
        """Test monitoring sync function."""

        @monitor_performance
        def test_sync_function():
            time.sleep(0.01)  # Small delay
            return "success"

        result = test_sync_function()
        assert result == "success"

        # Check that metrics were recorded
        metrics = self.collector.get_metrics()
        assert metrics["total_requests"] > 0

    @pytest.mark.asyncio
    async def test_monitor_function_with_exception(self):
        """Test monitoring function that raises exception."""

        @monitor_performance
        async def test_failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await test_failing_function()

        # Check that error metrics were recorded
        metrics = self.collector.get_metrics()
        assert metrics["total_errors"] > 0
