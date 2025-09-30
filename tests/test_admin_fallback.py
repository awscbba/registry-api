"""
Test admin service fallback functionality when AWS services are unavailable.
"""

import pytest
from unittest.mock import Mock, patch
from src.services.admin_service import AdminService
from src.services.performance_service import PerformanceService


class TestAdminFallback:
    """Test admin service fallback when database is unavailable."""

    @pytest.mark.asyncio
    async def test_admin_dashboard_fallback_on_database_error(self):
        """Test that admin dashboard returns fallback data when database fails."""
        admin_service = AdminService()

        # Mock repository to raise exception
        with patch.object(
            admin_service.people_repository,
            "list_all",
            side_effect=Exception("Database unavailable"),
        ):
            dashboard_data = await admin_service.get_dashboard_data()

            # Should return fallback data
            assert dashboard_data["dataSource"] == "fallback"
            assert dashboard_data["totalUsers"] == 3
            assert dashboard_data["totalProjects"] == 2
            assert dashboard_data["totalSubscriptions"] == 1
            assert "error" in dashboard_data
            assert "message" in dashboard_data

    @pytest.mark.asyncio
    async def test_admin_dashboard_live_data_when_available(self):
        """Test that admin dashboard returns live data when database is available."""
        admin_service = AdminService()

        # Mock repositories to return data
        mock_people = [Mock(isActive=True), Mock(isActive=True), Mock(isActive=False)]
        mock_projects = [Mock(isActive=True)]
        mock_subscriptions = [Mock(isActive=True)]

        with (
            patch.object(
                admin_service.people_repository, "list_all", return_value=mock_people
            ),
            patch.object(
                admin_service.projects_repository,
                "list_all",
                return_value=mock_projects,
            ),
            patch.object(
                admin_service.subscriptions_repository,
                "list_all",
                return_value=mock_subscriptions,
            ),
        ):

            dashboard_data = await admin_service.get_dashboard_data()

            # Should return live data
            assert dashboard_data["dataSource"] == "live"
            assert dashboard_data["totalUsers"] == 3
            assert dashboard_data["activeUsers"] == 2
            assert dashboard_data["totalProjects"] == 1
            assert dashboard_data["activeProjects"] == 1
            assert dashboard_data["totalSubscriptions"] == 1
            assert dashboard_data["activeSubscriptions"] == 1


class TestPerformanceFallback:
    """Test performance service fallback when AWS services are unavailable."""

    @pytest.mark.asyncio
    async def test_performance_health_fallback_on_error(self):
        """Test that performance health returns fallback data when services fail."""
        performance_service = PerformanceService()

        # Mock system metrics to raise exception
        with patch.object(
            performance_service,
            "_collect_system_metrics",
            side_effect=Exception("AWS unavailable"),
        ):
            health_status = await performance_service.get_health_status()

            # Should return fallback health status
            assert health_status["dataSource"] == "fallback"
            assert health_status["status"] == "degraded"
            assert health_status["overallScore"] == 75.0
            assert "error" in health_status
            assert "message" in health_status
            assert "AWS services temporarily unavailable" in health_status["error"]

    @pytest.mark.asyncio
    async def test_performance_health_live_data_when_available(self):
        """Test that performance health returns live data when services are available."""
        performance_service = PerformanceService()

        # Should return live data (no mocking, real system metrics)
        health_status = await performance_service.get_health_status()

        # Should return live data
        assert health_status.get("dataSource", "live") == "live"
        assert health_status["status"] in ["healthy", "degraded", "unhealthy"]
        assert isinstance(health_status["overallScore"], (int, float))
        assert "components" in health_status
        assert "metrics" in health_status


class TestAdminPanelIntegration:
    """Test admin panel integration with fallback functionality."""

    @pytest.mark.asyncio
    async def test_admin_panel_graceful_degradation(self):
        """Test that admin panel can handle service degradation gracefully."""
        admin_service = AdminService()
        performance_service = PerformanceService()

        # Test dashboard with potential database issues
        dashboard_data = await admin_service.get_dashboard_data()
        assert "totalUsers" in dashboard_data
        assert "totalProjects" in dashboard_data
        assert "totalSubscriptions" in dashboard_data
        assert "dataSource" in dashboard_data

        # Test health status with potential AWS issues
        health_status = await performance_service.get_health_status()
        assert "status" in health_status
        assert "overallScore" in health_status
        assert health_status["status"] in ["healthy", "degraded", "unhealthy"]

        # Both should provide meaningful data regardless of backend status
        assert isinstance(dashboard_data["totalUsers"], int)
        assert isinstance(health_status["overallScore"], (int, float))
