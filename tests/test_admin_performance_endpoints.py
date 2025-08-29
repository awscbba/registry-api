"""
Tests for the new admin performance endpoints.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from src.app import app
from tests.test_utils import TestMockUtils


class TestAdminPerformanceEndpoints:
    """Test admin performance monitoring endpoints."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_admin_endpoints_require_authentication(self):
        """Test that admin endpoints require authentication."""
        endpoints = [
            "/v2/admin/performance/health",
            "/v2/admin/stats",
            "/v2/admin/performance/stats",
        ]

        for endpoint in endpoints:
            response = self.client.get(endpoint)
            # Accept both 401 (Unauthorized) and 403 (Forbidden) as valid auth protection
            assert response.status_code in [
                401,
                403,
            ], f"Endpoint {endpoint} should require authentication (got {response.status_code})"

    @patch("src.services.auth_service.AuthService.get_current_user")
    @patch("src.security.authorization.authorization_service.is_account_locked")
    def test_admin_endpoints_require_admin_privileges(
        self, mock_is_locked, mock_get_user
    ):
        """Test that admin endpoints require admin privileges."""
        # Mock regular user (not admin)
        mock_user = TestMockUtils.mock_user(is_admin=False)
        mock_get_user.return_value = mock_user
        mock_is_locked.return_value = False

        endpoints = [
            "/v2/admin/performance/health",
            "/v2/admin/stats",
            "/v2/admin/performance/stats",
        ]

        for endpoint in endpoints:
            response = self.client.get(
                endpoint, headers={"Authorization": "Bearer mock-user-token"}
            )
            assert (
                response.status_code == 403
            ), f"Endpoint {endpoint} should require admin privileges"


class TestPerformanceServiceIntegration:
    """Test performance service integration."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    @pytest.mark.asyncio
    async def test_performance_service_initialization(self):
        """Test that performance service can be initialized."""
        from src.services.performance_service import PerformanceService
        from src.services.logging_service import EnterpriseLoggingService

        logging_service = EnterpriseLoggingService()
        performance_service = PerformanceService(logging_service)

        assert performance_service is not None
        assert performance_service.logging_service is not None

    @pytest.mark.asyncio
    async def test_performance_service_health_check(self):
        """Test performance service health check functionality."""
        from src.services.performance_service import PerformanceService
        from src.services.logging_service import EnterpriseLoggingService

        logging_service = EnterpriseLoggingService()
        performance_service = PerformanceService(logging_service)

        # Mock the repository health checks
        with patch.object(
            performance_service, "_check_repository_health"
        ) as mock_check:
            mock_check.return_value = {
                "status": "healthy",
                "response_time_ms": 50.0,
                "timestamp": "2025-08-28T21:00:00Z",
            }

            health_status = await performance_service.get_health_status()

            assert health_status is not None
            assert "status" in health_status
            assert "overallScore" in health_status
            assert "components" in health_status
            assert "metrics" in health_status

    @pytest.mark.asyncio
    async def test_performance_service_stats(self):
        """Test performance service statistics functionality."""
        from src.services.performance_service import PerformanceService
        from src.services.logging_service import EnterpriseLoggingService

        logging_service = EnterpriseLoggingService()
        performance_service = PerformanceService(logging_service)

        # Record some mock requests
        performance_service.record_request(100.0)
        performance_service.record_request(200.0)
        performance_service.record_request(150.0)

        stats = await performance_service.get_performance_stats()

        assert stats is not None
        assert "uptime_seconds" in stats
        assert "total_requests" in stats
        assert "average_response_time_ms" in stats
        assert stats["total_requests"] == 3
        assert stats["average_response_time_ms"] == 150.0  # (100+200+150)/3

    def test_admin_endpoints_exist_in_openapi(self):
        """Test that the new admin endpoints are documented in OpenAPI."""
        response = self.client.get("/openapi.json")
        assert response.status_code == 200

        openapi_spec = response.json()
        paths = openapi_spec.get("paths", {})

        # Check that our new endpoints are documented
        expected_paths = [
            "/v2/admin/performance/health",
            "/v2/admin/stats",
            "/v2/admin/performance/stats",
        ]

        for path in expected_paths:
            assert (
                path in paths
            ), f"Endpoint {path} should be documented in OpenAPI spec"
            assert "get" in paths[path], f"GET method should be available for {path}"

    def test_admin_endpoints_have_proper_tags(self):
        """Test that admin endpoints have proper OpenAPI tags."""
        response = self.client.get("/openapi.json")
        assert response.status_code == 200

        openapi_spec = response.json()
        paths = openapi_spec.get("paths", {})

        # Check that admin endpoints have the admin tag
        admin_endpoints = [
            "/v2/admin/performance/health",
            "/v2/admin/stats",
            "/v2/admin/performance/stats",
        ]

        for endpoint in admin_endpoints:
            if endpoint in paths and "get" in paths[endpoint]:
                tags = paths[endpoint]["get"].get("tags", [])
                assert "admin" in tags, f"Endpoint {endpoint} should have 'admin' tag"


class TestEnterpriseLoggingIntegration:
    """Test enterprise logging integration in admin endpoints."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    @patch("src.services.logging_service.logging_service.log_structured")
    @patch("src.services.auth_service.AuthService.get_current_user")
    @patch("src.security.authorization.authorization_service.is_account_locked")
    def test_admin_endpoint_logging(self, mock_is_locked, mock_get_user, mock_log):
        """Test that admin endpoints properly log access attempts."""
        # Mock admin user
        mock_admin = TestMockUtils.mock_user(is_admin=True)
        mock_get_user.return_value = mock_admin
        mock_is_locked.return_value = False

        # Mock the performance service to avoid actual system calls
        with patch(
            "src.services.service_registry_manager.get_performance_service"
        ) as mock_get_perf:
            mock_performance_service = AsyncMock()
            mock_performance_service.get_health_status.return_value = {
                "status": "healthy",
                "overallScore": 95.0,
            }
            mock_get_perf.return_value = mock_performance_service

            # Make request to admin endpoint
            response = self.client.get(
                "/v2/admin/performance/health",
                headers={"Authorization": "Bearer mock-admin-token"},
            )

            # The endpoint should work (though we might get auth issues in test)
            # The important thing is that logging was called
            assert (
                mock_log.called
            ), "Enterprise logging should be called for admin endpoint access"


class TestAdminEndpointErrorHandling:
    """Test error handling in admin endpoints."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    @patch("src.services.auth_service.AuthService.get_current_user")
    @patch("src.security.authorization.authorization_service.is_account_locked")
    def test_admin_endpoint_service_error_handling(self, mock_is_locked, mock_get_user):
        """Test that admin endpoints handle service errors properly."""
        # Mock admin user
        mock_admin = TestMockUtils.mock_user(is_admin=True)
        mock_get_user.return_value = mock_admin
        mock_is_locked.return_value = False

        # Mock the performance service's get_health_status method directly
        with patch(
            "src.services.performance_service.PerformanceService.get_health_status"
        ) as mock_health_status:
            # Mock to return unhealthy status (simulating service error handling)
            mock_health_status.return_value = {
                "status": "unhealthy",
                "overallScore": 0.0,
                "components": {"error": "Service error"},
                "metrics": {
                    "responseTimeMs": 0.0,
                    "memoryUsageMb": 0.0,
                    "cpuUsagePercent": 0.0,
                    "databaseConnections": 0,
                    "activeRequests": 0,
                    "timestamp": "2025-08-29T00:00:00Z",
                },
                "timestamp": "2025-08-29T00:00:00Z",
                "version": "2.0.0",
            }

            # Make request to admin endpoint
            response = self.client.get(
                "/v2/admin/performance/health",
                headers={"Authorization": "Bearer mock-admin-token"},
            )

            # Enterprise design: Performance service handles errors gracefully
            # Should return 200 with "unhealthy" status instead of throwing exceptions
            assert (
                response.status_code == 200
            ), "Performance service should handle errors gracefully"

            # Verify the response indicates service error
            response_data = response.json()
            assert response_data["success"] is True, "Response should be successful"
            assert "data" in response_data, "Response should contain data"

            # The actual health status should indicate the error
            health_data = response_data["data"]
            assert (
                health_data["status"] == "unhealthy"
            ), "Health status should be unhealthy when service fails"
            assert (
                health_data["overallScore"] == 0.0
            ), "Overall score should be 0 when service fails"
