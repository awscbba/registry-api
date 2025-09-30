"""
Test admin service error handling when AWS services are unavailable.
Enterprise-grade systems should fail fast and show proper errors, not fake data.
"""

import pytest
from unittest.mock import Mock, patch
from src.services.admin_service import AdminService
from src.services.performance_service import PerformanceService
from src.exceptions.base_exceptions import DatabaseException


class TestAdminErrorHandling:
    """Test admin service proper error handling when database is unavailable."""

    @pytest.mark.asyncio
    async def test_admin_dashboard_raises_exception_on_database_error(self):
        """Test that admin dashboard raises proper exception when database fails."""
        admin_service = AdminService()

        # Mock repository to raise exception
        with patch.object(
            admin_service.people_repository,
            "list_all",
            side_effect=Exception("Database unavailable"),
        ):
            with pytest.raises(DatabaseException):
                await admin_service.get_dashboard_data()

            # Should raise DatabaseException (proper enterprise behavior)

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
            assert dashboard_data["totalUsers"] == 3
            assert dashboard_data["activeUsers"] == 2
            assert dashboard_data["totalProjects"] == 1
            assert dashboard_data["activeProjects"] == 1
            assert dashboard_data["totalSubscriptions"] == 1
            assert dashboard_data["activeSubscriptions"] == 1


class TestPerformanceErrorHandling:
    """Test performance service proper error handling when AWS services are unavailable."""

    @pytest.mark.asyncio
    async def test_performance_health_returns_unhealthy_on_error(self):
        """Test that performance health returns unhealthy status when services fail."""
        performance_service = PerformanceService()

        # Mock system metrics to raise exception
        with patch.object(
            performance_service,
            "_collect_system_metrics",
            side_effect=Exception("AWS unavailable"),
        ):
            health_status = await performance_service.get_health_status()

            # Should return unhealthy status, not fake data
            assert health_status["status"] == "unhealthy"
            assert health_status["overallScore"] == 0.0
            assert "error" in health_status
            assert "AWS unavailable" in health_status["error"]

    @pytest.mark.asyncio
    async def test_performance_health_live_data_when_available(self):
        """Test that performance health returns live data when services are available."""
        performance_service = PerformanceService()

        # Should return live data (no mocking, real system metrics)
        health_status = await performance_service.get_health_status()

        # Should return live data
        assert health_status["status"] in ["healthy", "degraded", "unhealthy"]
        assert isinstance(health_status["overallScore"], (int, float))
        assert "components" in health_status
        assert "metrics" in health_status


class TestEnterpriseErrorBehavior:
    """Test enterprise-grade error behavior - fail fast, don't show fake data."""

    @pytest.mark.asyncio
    async def test_admin_panel_fails_fast_on_database_issues(self):
        """Test that admin panel fails fast when database is unavailable."""
        admin_service = AdminService()

        # Mock database failure
        with patch.object(
            admin_service.people_repository,
            "list_all",
            side_effect=Exception("Database connection failed"),
        ):
            # Should raise exception, not return fake data
            with pytest.raises(DatabaseException):
                await admin_service.get_dashboard_data()

    @pytest.mark.asyncio
    async def test_performance_service_shows_real_status(self):
        """Test that performance service shows real system status."""
        performance_service = PerformanceService()

        # Test health status
        health_status = await performance_service.get_health_status()

        # Should provide real status information
        assert health_status["status"] in ["healthy", "degraded", "unhealthy"]
        assert isinstance(health_status["overallScore"], (int, float))

        # If there's an error, it should be clearly indicated
        if health_status["status"] == "unhealthy":
            assert "error" in health_status

        # Should never show fake/fallback data indicators
        assert (
            "dataSource" not in health_status
            or health_status.get("dataSource") != "fallback"
        )
