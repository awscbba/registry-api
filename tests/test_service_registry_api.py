"""
API endpoint tests for Service Registry implementation.
Tests that all API endpoints work correctly with the Service Registry pattern.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, Mock
import json
import os
import sys

# Add the parent directory to the path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up test environment
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"


class TestServiceRegistryAPIEndpoints:
    """Test Service Registry specific API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client for the modular API handler."""
        from src.handlers.modular_api_handler import app

        return TestClient(app)

    def test_health_endpoint(self, client):
        """Test the main health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "api_handler" in data
        assert data["api_handler"]["version"] == "3.0.0-service-registry"
        assert data["api_handler"]["architecture"] == "modular_service_registry"

    def test_services_health_endpoint(self, client):
        """Test the services health endpoint."""
        response = client.get("/health/services")
        assert response.status_code == 200

        data = response.json()
        assert "service_registry_manager" in data
        assert "services" in data

    def test_registry_services_endpoint(self, client):
        """Test the service registry services endpoint."""
        response = client.get("/registry/services")
        assert response.status_code == 200

        data = response.json()
        assert "service_registry" in data
        assert "total_services" in data["service_registry"]
        assert "services" in data["service_registry"]

        # Should have all 9 services
        assert data["service_registry"]["total_services"] == 11

    def test_registry_config_endpoint(self, client):
        """Test the service registry configuration endpoint."""
        response = client.get("/registry/config")
        assert response.status_code == 200

        data = response.json()
        assert "configuration" in data
        assert "database" in data["configuration"]
        assert "auth" in data["configuration"]
        assert "email" in data["configuration"]
        assert "security" in data["configuration"]


class TestServiceRegistryAPICompatibility:
    """Test API compatibility with Service Registry pattern."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from src.handlers.modular_api_handler import app

        return TestClient(app)

    def test_v1_endpoints_exist(self, client):
        """Test that v1 endpoints still exist for backward compatibility."""
        # Test v1 people endpoint (should exist but may return errors due to mocking)
        response = client.get("/v1/people")
        # We expect either 200 (success) or 500 (AWS service error), but not 404 (not found)
        assert response.status_code != 404, "v1 people endpoint should exist"

    def test_v2_endpoints_exist(self, client):
        """Test that v2 endpoints exist."""
        # Test v2 people endpoint
        response = client.get("/v2/people")
        # We expect either 200 (success) or 500 (AWS service error), but not 404 (not found)
        assert response.status_code != 404, "v2 people endpoint should exist"

    def test_auth_endpoints_exist(self, client):
        """Test that auth endpoints exist."""
        # Test auth login endpoint (POST should exist even if it fails)
        response = client.post(
            "/auth/login", json={"email": "test@example.com", "password": "test"}
        )
        # We expect either 200, 400, 401, or 500, but not 404 (not found)
        assert response.status_code != 404, "auth login endpoint should exist"

    def test_api_versioning_headers(self, client):
        """Test that API versioning is properly handled."""
        response = client.get("/health")
        assert response.status_code == 200

        # Should have proper content type
        assert "application/json" in response.headers.get("content-type", "")


class TestServiceRegistryAPIIntegration:
    """Test API integration with Service Registry services."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from src.handlers.modular_api_handler import app

        return TestClient(app)

    def test_api_uses_service_registry(self, client):
        """Test that API endpoints use the Service Registry."""
        # The fact that we can import and create the client proves integration works
        from src.handlers.modular_api_handler import service_manager

        assert service_manager is not None
        assert hasattr(service_manager, "registry")
        assert len(service_manager.registry.services) == 11

    @patch(
        "src.services.service_registry_manager.ServiceRegistryManager.get_all_people_v1"
    )
    def test_v1_people_endpoint_uses_service_registry(self, mock_get_people, client):
        """Test that v1 people endpoint uses Service Registry."""
        # Mock the service method
        mock_get_people.return_value = {"data": [], "total": 0}

        response = client.get("/v1/people")

        # Should call the service registry method
        mock_get_people.assert_called_once()

    @patch(
        "src.services.service_registry_manager.ServiceRegistryManager.get_all_people_v2"
    )
    def test_v2_people_endpoint_uses_service_registry(self, mock_get_people, client):
        """Test that v2 people endpoint uses Service Registry."""
        # Mock the service method
        mock_get_people.return_value = {"data": [], "total": 0, "version": "v2"}

        response = client.get("/v2/people")

        # Should call the service registry method
        mock_get_people.assert_called_once()


class TestServiceRegistryAPIErrorHandling:
    """Test API error handling with Service Registry."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from src.handlers.modular_api_handler import app

        return TestClient(app)

    def test_service_registry_error_handling(self, client):
        """Test that Service Registry errors are handled gracefully."""
        # Test with invalid endpoint
        response = client.get("/invalid/endpoint")
        assert response.status_code == 404

    def test_health_check_error_handling(self, client):
        """Test health check error handling."""
        with patch(
            "src.services.service_registry_manager.ServiceRegistryManager.health_check"
        ) as mock_health:
            # Mock a health check failure
            mock_health.side_effect = Exception("Service unavailable")

            response = client.get("/health")

            # Should handle the error gracefully
            assert response.status_code in [
                200,
                500,
            ]  # Either works or fails gracefully

    def test_service_unavailable_handling(self, client):
        """Test handling when services are unavailable."""
        with patch(
            "src.services.service_registry_manager.ServiceRegistryManager.get_service"
        ) as mock_get_service:
            # Mock service unavailable
            mock_get_service.side_effect = KeyError("Service not found")

            response = client.get("/registry/services")

            # Should handle the error gracefully
            assert response.status_code in [200, 500]


class TestServiceRegistryAPIPerformance:
    """Test API performance with Service Registry."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from src.handlers.modular_api_handler import app

        return TestClient(app)

    def test_health_endpoint_performance(self, client):
        """Test health endpoint performance."""
        import time

        # Time multiple requests
        start_time = time.time()

        for _ in range(10):
            response = client.get("/health")
            assert response.status_code == 200

        end_time = time.time()
        total_time = end_time - start_time

        # Should handle 10 requests quickly (with service timeouts)
        assert (
            total_time < 15.0
        ), f"10 health requests took {total_time:.3f}s, expected < 15.0s"

    def test_registry_endpoints_performance(self, client):
        """Test registry endpoints performance."""
        import time

        endpoints = ["/registry/services", "/registry/config", "/health/services"]

        start_time = time.time()

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200

        end_time = time.time()
        total_time = end_time - start_time

        # Should handle registry endpoints quickly
        assert (
            total_time < 3.0
        ), f"Registry endpoints took {total_time:.3f}s, expected < 3.0s"


class TestServiceRegistryAPIDocumentation:
    """Test API documentation with Service Registry."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from src.handlers.modular_api_handler import app

        return TestClient(app)

    def test_openapi_schema_generation(self, client):
        """Test that OpenAPI schema is generated correctly."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert schema["info"]["title"] == "People Registry API"

    def test_docs_endpoint_exists(self, client):
        """Test that API docs endpoint exists."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_redoc_endpoint_exists(self, client):
        """Test that ReDoc endpoint exists."""
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


class TestServiceRegistryAPIMetrics:
    """Test API metrics and monitoring with Service Registry."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from src.handlers.modular_api_handler import app

        return TestClient(app)

    def test_service_registry_metrics_in_health(self, client):
        """Test that Service Registry metrics are included in health checks."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "api_handler" in data
        assert "timestamp" in data["api_handler"]
        assert "version" in data["api_handler"]

    def test_service_metrics_in_services_health(self, client):
        """Test that individual service metrics are available."""
        response = client.get("/health/services")
        assert response.status_code == 200

        data = response.json()
        assert "service_registry_manager" in data
        assert "services_registered" in data["service_registry_manager"]

    def test_configuration_metrics(self, client):
        """Test that configuration metrics are available."""
        response = client.get("/registry/config")
        assert response.status_code == 200

        data = response.json()
        assert "timestamp" in data
        assert "configuration" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
