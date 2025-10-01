"""
Test admin service error handling when AWS services are unavailable.
Current behavior: repositories fail silently and return empty lists, causing zero metrics.
"""

import pytest
from unittest.mock import Mock, patch
from src.services.admin_service import AdminService
from src.services.performance_service import PerformanceService


class TestAdminErrorHandling:
    """Test admin service behavior when database is unavailable."""

    @pytest.mark.asyncio
    async def test_admin_dashboard_returns_zeros_when_repositories_fail_silently(self):
        """Test that admin dashboard returns zeros when repositories fail silently."""
        admin_service = AdminService()

        # Mock repository to raise exception (simulating AWS credential issues)
        with patch.object(
            admin_service.people_repository,
            "list_all",
            side_effect=Exception("Database unavailable"),
        ):
            # Should now raise exception instead of returning zeros (improved behavior)
            with pytest.raises(Exception) as exc_info:
                dashboard_data = admin_service.get_dashboard_data()

            # Verify it's a database exception with proper error details
            assert "Database error" in str(exc_info.value)

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

            dashboard_data = admin_service.get_dashboard_data()

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


class TestCurrentBehaviorDocumentation:
    """Document current behavior for debugging production issues."""

    @pytest.mark.asyncio
    async def test_admin_panel_shows_errors_on_database_issues(self):
        """Test that admin panel shows proper errors when database is unavailable (improved behavior)."""
        admin_service = AdminService()

        # Mock database failure
        with patch.object(
            admin_service.people_repository,
            "list_all",
            side_effect=Exception("Database connection failed"),
        ):
            # Should now raise exception with proper error details (improved behavior)
            with pytest.raises(Exception) as exc_info:
                dashboard_data = admin_service.get_dashboard_data()

            # Verify it's a database exception with proper error details
            assert "Database error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_performance_service_shows_real_status(self):
        """Test that performance service shows real system status."""
        performance_service = PerformanceService()

        # Test health status
        health_status = await performance_service.get_health_status()

        # Should provide real status information
        assert health_status["status"] in ["healthy", "degraded", "unhealthy"]
        assert isinstance(health_status["overallScore"], (int, float))

        # If there's an error, it should be clearly indicated in components
        if health_status["status"] == "unhealthy":
            # Check that error details are available in components
            components = health_status.get("components", {})
            has_error_details = any(
                "error" in component for component in components.values()
            )
            assert (
                has_error_details
            ), "Unhealthy status should include error details in components"
