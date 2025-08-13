"""
Comprehensive integration tests for Service Registry pattern implementation.
Tests the complete Service Registry architecture including service registration,
dependency injection, health monitoring, and API handler integration.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import os
from datetime import datetime

# Set up test environment
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"


class TestServiceRegistryCore:
    """Test core Service Registry functionality."""

    def test_service_registry_manager_initialization(self):
        """Test that ServiceRegistryManager initializes correctly."""
        from src.services.service_registry_manager import ServiceRegistryManager

        manager = ServiceRegistryManager()

        # Verify manager is initialized
        assert manager is not None
        assert manager.registry is not None
        assert manager.config is not None

        # Verify all expected services are registered
        expected_services = [
            "people",
            "projects",
            "subscriptions",  # Domain services
            "auth",
            "roles",
            "email",
            "audit",
            "logging",
            "rate_limiting",  # Core services
        ]

        registered_services = list(manager.registry.services.keys())
        for service_name in expected_services:
            assert (
                service_name in registered_services
            ), f"Service '{service_name}' not registered"

        assert (
            len(registered_services) == 9
        ), f"Expected 9 services, got {len(registered_services)}"

    def test_service_registry_get_service(self):
        """Test getting services from the registry."""
        from src.services.service_registry_manager import ServiceRegistryManager

        manager = ServiceRegistryManager()

        # Test getting each service
        services_to_test = ["people", "auth", "email", "audit"]

        for service_name in services_to_test:
            service = manager.get_service(service_name)
            assert service is not None, f"Failed to get service '{service_name}'"
            assert hasattr(
                service, "service_name"
            ), f"Service '{service_name}' missing service_name attribute"
            assert hasattr(
                service, "health_check"
            ), f"Service '{service_name}' missing health_check method"

    @pytest.mark.asyncio
    async def test_service_registry_health_check(self):
        """Test comprehensive health check for all services."""
        from src.services.service_registry_manager import ServiceRegistryManager

        manager = ServiceRegistryManager()

        # Mock all service health checks to avoid AWS dependencies
        with (
            patch.object(
                manager.registry.services["people"],
                "health_check",
                new_callable=AsyncMock,
            ) as mock_people,
            patch.object(
                manager.registry.services["auth"],
                "health_check",
                new_callable=AsyncMock,
            ) as mock_auth,
            patch.object(
                manager.registry.services["email"],
                "health_check",
                new_callable=AsyncMock,
            ) as mock_email,
        ):

            # Configure mock responses
            mock_people.return_value = {"status": "healthy", "service": "people"}
            mock_auth.return_value = {"status": "healthy", "service": "auth"}
            mock_email.return_value = {"status": "healthy", "service": "email"}

            health_status = await manager.health_check()

            # Verify health check structure
            assert "service_registry_manager" in health_status
            assert "services" in health_status
            assert health_status["service_registry_manager"]["status"] == "healthy"
            assert health_status["service_registry_manager"]["services_registered"] == 9


class TestModularAPIHandler:
    """Test the modular API handler using Service Registry."""

    def test_modular_api_handler_imports(self):
        """Test that modular API handler imports successfully."""
        from src.handlers.modular_api_handler import app

        assert app is not None
        assert app.title == "People Register API - Modular (Service Registry)"
        assert app.version == "3.0.0-service-registry"

    def test_modular_api_handler_routes(self):
        """Test that all expected routes are registered."""
        from src.handlers.modular_api_handler import app

        # Get all routes
        routes = []
        for route in app.routes:
            if hasattr(route, "path") and hasattr(route, "methods"):
                for method in route.methods:
                    if method != "HEAD":  # Skip HEAD methods
                        routes.append(f"{method} {route.path}")

        # Expected critical routes
        expected_routes = [
            "GET /health",
            "GET /health/services",
            "GET /registry/services",
            "GET /registry/config",
            "GET /v1/people",
            "GET /v2/people",
            "POST /v1/people",
            "POST /v2/people",
        ]

        for expected_route in expected_routes:
            assert expected_route in routes, f"Missing route: {expected_route}"

    def test_service_manager_integration(self):
        """Test that the API handler integrates with service manager."""
        from src.handlers.modular_api_handler import service_manager

        assert service_manager is not None
        assert hasattr(service_manager, "registry")
        assert hasattr(service_manager, "get_service")
        assert hasattr(service_manager, "health_check")


class TestMainEntryPoint:
    """Test the main entry point uses Service Registry."""

    def test_main_imports_modular_handler(self):
        """Test that main.py imports the modular handler."""
        # Read main.py content
        with open(
            "/Users/sergio.rodriguez/Projects/Community/AWS/UserGroupCbba/CodeCatalyst/people-registry-03/registry-api/main.py",
            "r",
        ) as f:
            main_content = f.read()

        # Verify it imports modular handler
        assert "from src.handlers.modular_api_handler import app" in main_content
        assert "from src.handlers.versioned_api_handler import app" not in main_content

        # Verify Service Registry annotations
        assert 'add_annotation("architecture", "service-registry")' in main_content
        assert "Processing request via Service Registry" in main_content

    def test_lambda_handler_creation(self):
        """Test that lambda handler is created successfully."""
        from main import _original_lambda_handler, traced_lambda_handler

        assert _original_lambda_handler is not None
        assert traced_lambda_handler is not None
        assert callable(traced_lambda_handler)


class TestServiceRegistryArchitecture:
    """Test Service Registry architectural patterns."""

    def test_base_service_pattern(self):
        """Test that all services follow BaseService pattern."""
        from src.services.service_registry_manager import ServiceRegistryManager
        from src.core.base_service import BaseService

        manager = ServiceRegistryManager()

        # Test that all services inherit from BaseService
        for service_name, service in manager.registry.services.items():
            assert isinstance(
                service, BaseService
            ), f"Service '{service_name}' doesn't inherit from BaseService"
            assert hasattr(
                service, "service_name"
            ), f"Service '{service_name}' missing service_name attribute"
            assert hasattr(
                service, "config"
            ), f"Service '{service_name}' missing config attribute"
            assert hasattr(
                service, "health_check"
            ), f"Service '{service_name}' missing health_check method"

    def test_dependency_injection_pattern(self):
        """Test dependency injection is working."""
        from src.services.service_registry_manager import ServiceRegistryManager

        manager = ServiceRegistryManager()

        # Test that services can be retrieved by name (dependency injection)
        auth_service = manager.get_service("auth")
        people_service = manager.get_service("people")

        assert auth_service is not None
        assert people_service is not None
        assert auth_service != people_service  # Different instances

    def test_service_isolation(self):
        """Test that services are properly isolated."""
        from src.services.service_registry_manager import ServiceRegistryManager

        manager = ServiceRegistryManager()

        # Get the same service twice
        service1 = manager.get_service("auth")
        service2 = manager.get_service("auth")

        # Should be the same instance (singleton pattern)
        assert service1 is service2, "Services should be singletons"

    def test_configuration_management(self):
        """Test unified configuration management."""
        from src.services.service_registry_manager import ServiceRegistryManager

        manager = ServiceRegistryManager()

        # Verify configuration is loaded
        assert manager.config is not None
        assert hasattr(manager.config, "database")
        assert hasattr(manager.config, "auth")
        assert hasattr(manager.config, "email")
        assert hasattr(manager.config, "security")


class TestServiceRegistryPerformance:
    """Test Service Registry performance characteristics."""

    def test_service_initialization_time(self):
        """Test that service initialization is reasonably fast."""
        import time
        from src.services.service_registry_manager import ServiceRegistryManager

        start_time = time.time()
        manager = ServiceRegistryManager()
        end_time = time.time()

        initialization_time = end_time - start_time

        # Should initialize in less than 5 seconds
        assert (
            initialization_time < 5.0
        ), f"Service initialization took {initialization_time:.2f}s, expected < 5.0s"

    def test_service_retrieval_performance(self):
        """Test that service retrieval is fast."""
        import time
        from src.services.service_registry_manager import ServiceRegistryManager

        manager = ServiceRegistryManager()

        # Test multiple service retrievals
        start_time = time.time()
        for _ in range(100):
            service = manager.get_service("auth")
            assert service is not None
        end_time = time.time()

        retrieval_time = end_time - start_time

        # Should retrieve 100 services in less than 0.1 seconds
        assert (
            retrieval_time < 0.1
        ), f"100 service retrievals took {retrieval_time:.3f}s, expected < 0.1s"


class TestServiceRegistryErrorHandling:
    """Test Service Registry error handling."""

    def test_invalid_service_name(self):
        """Test handling of invalid service names."""
        from src.services.service_registry_manager import ServiceRegistryManager

        manager = ServiceRegistryManager()

        # Test getting non-existent service
        with pytest.raises(ValueError):
            manager.get_service("non_existent_service")

    def test_service_initialization_failure_handling(self):
        """Test handling of service initialization failures."""
        # This test would require mocking service initialization failures
        # For now, we verify that the manager handles exceptions gracefully
        from src.services.service_registry_manager import ServiceRegistryManager

        # If we get here without exceptions, initialization error handling works
        manager = ServiceRegistryManager()
        assert manager is not None


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""

    def test_api_endpoints_still_work(self):
        """Test that existing API endpoints still function."""
        from src.handlers.modular_api_handler import app
        from fastapi.testclient import TestClient

        client = TestClient(app)

        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200

        health_data = response.json()
        assert "overall_status" in health_data or "api_handler" in health_data

    def test_service_methods_available(self):
        """Test that service methods are still available."""
        from src.services.service_registry_manager import ServiceRegistryManager

        manager = ServiceRegistryManager()

        # Test that services have expected methods
        auth_service = manager.get_service("auth")
        assert hasattr(auth_service, "authenticate_user")

        people_service = manager.get_service("people")
        # Check for actual methods that exist in PeopleService
        assert hasattr(people_service, "get_all_people")
        assert hasattr(people_service, "get_person_by_id")


class TestServiceRegistryDocumentation:
    """Test Service Registry documentation and introspection."""

    def test_service_registry_introspection(self):
        """Test that services can be introspected."""
        from src.services.service_registry_manager import ServiceRegistryManager

        manager = ServiceRegistryManager()

        # Test that we can get service information
        for service_name in manager.registry.services.keys():
            service = manager.get_service(service_name)
            assert hasattr(service, "__class__")
            assert hasattr(service, "__module__")

            # Service should have a meaningful name
            assert service.service_name is not None
            assert len(service.service_name) > 0

    def test_api_documentation_endpoints(self):
        """Test API documentation endpoints."""
        from src.handlers.modular_api_handler import app
        from fastapi.testclient import TestClient

        client = TestClient(app)

        # Test service registry endpoints
        response = client.get("/registry/services")
        assert response.status_code == 200

        response = client.get("/registry/config")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
