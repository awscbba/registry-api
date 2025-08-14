"""
Focused validation tests for Service Registry implementation.
Tests core functionality without AWS dependencies.
"""

import pytest
import os
import sys

# Add the parent directory to the path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up test environment
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"


class TestServiceRegistryValidation:
    """Core validation tests for Service Registry implementation."""

    def test_service_registry_manager_exists_and_initializes(self):
        """Test that ServiceRegistryManager can be imported and initialized."""
        from src.services.service_registry_manager import ServiceRegistryManager

        manager = ServiceRegistryManager()
        assert manager is not None
        assert manager.registry is not None

    def test_all_expected_services_are_registered(self):
        """Test that all expected services are registered."""
        from src.services.service_registry_manager import ServiceRegistryManager

        manager = ServiceRegistryManager()

        expected_services = {
            "people",
            "projects",
            "subscriptions",  # Domain services
            "auth",
            "roles",
            "email",
            "audit",
            "logging",
            "rate_limiting",  # Core services
            "metrics",
            "cache",
            "performance_metrics",
            "database_optimization",  # Performance services
            "project_administration",  # Administration services
        }

        registered_services = set(manager.registry.services.keys())

        # Check that all expected services are present
        missing_services = expected_services - registered_services
        assert len(missing_services) == 0, f"Missing services: {missing_services}"

        # Check that we have exactly the expected number
        assert (
            len(registered_services) == 14
        ), f"Expected 14 services, got {len(registered_services)}"

    def test_services_inherit_from_base_service(self):
        """Test that all services properly inherit from BaseService."""
        from src.services.service_registry_manager import ServiceRegistryManager
        from src.core.base_service import BaseService

        manager = ServiceRegistryManager()

        for service_name, service in manager.registry.services.items():
            assert isinstance(
                service, BaseService
            ), f"Service '{service_name}' doesn't inherit from BaseService"
            assert hasattr(
                service, "service_name"
            ), f"Service '{service_name}' missing service_name"
            assert hasattr(
                service, "health_check"
            ), f"Service '{service_name}' missing health_check method"

    def test_service_retrieval_works(self):
        """Test that services can be retrieved by name."""
        from src.services.service_registry_manager import ServiceRegistryManager

        manager = ServiceRegistryManager()

        # Test retrieving each service
        for service_name in ["auth", "people", "email"]:
            service = manager.get_service(service_name)
            assert service is not None, f"Failed to retrieve service '{service_name}'"
            # Service names may have "_service" suffix
            assert (
                service_name in service.service_name
            ), f"Service name mismatch for '{service_name}'"

    def test_modular_api_handler_imports_successfully(self):
        """Test that the modular API handler imports without errors."""
        from src.handlers.modular_api_handler import app

        assert app is not None
        assert app.title == "People Registry API"
        assert app.version == "2.0.0"

    def test_main_entry_point_uses_modular_handler(self):
        """Test that main.py uses the modular handler."""
        import os

        # Get the project root directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        main_py_path = os.path.join(project_root, "main.py")

        # Read main.py to verify it imports the correct handler
        with open(main_py_path, "r") as f:
            main_content = f.read()

        # Should import modular handler, not versioned handler
        assert "from src.handlers.modular_api_handler import app" in main_content
        assert "from src.handlers.versioned_api_handler import app" not in main_content

        # Should have Service Registry annotations
        assert "service-registry" in main_content

    def test_lambda_handler_can_be_created(self):
        """Test that the Lambda handler can be created."""
        from main import _original_lambda_handler, traced_lambda_handler

        assert _original_lambda_handler is not None
        assert traced_lambda_handler is not None
        assert callable(traced_lambda_handler)

    def test_service_registry_singleton_behavior(self):
        """Test that services behave as singletons."""
        from src.services.service_registry_manager import ServiceRegistryManager

        manager = ServiceRegistryManager()

        # Get the same service multiple times
        service1 = manager.get_service("auth")
        service2 = manager.get_service("auth")

        # Should be the same instance
        assert service1 is service2, "Services should be singletons"

    def test_service_registry_error_handling(self):
        """Test error handling for invalid service names."""
        from src.services.service_registry_manager import ServiceRegistryManager

        manager = ServiceRegistryManager()

        # Should raise ValueError for non-existent service
        with pytest.raises(ValueError, match="not registered"):
            manager.get_service("non_existent_service")

    def test_service_registry_performance_basic(self):
        """Test basic performance characteristics."""
        import time
        from src.services.service_registry_manager import ServiceRegistryManager

        # Test initialization time
        start_time = time.time()
        manager = ServiceRegistryManager()
        init_time = time.time() - start_time

        assert init_time < 5.0, f"Initialization took {init_time:.2f}s, expected < 5.0s"

        # Test service retrieval time
        start_time = time.time()
        for _ in range(100):
            service = manager.get_service("auth")
            assert service is not None
        retrieval_time = time.time() - start_time

        assert (
            retrieval_time < 0.1
        ), f"100 retrievals took {retrieval_time:.3f}s, expected < 0.1s"

    def test_api_handler_has_expected_routes(self):
        """Test that the API handler has expected routes."""
        from src.handlers.modular_api_handler import app

        # Get all route paths
        route_paths = []
        for route in app.routes:
            if hasattr(route, "path"):
                route_paths.append(route.path)

        # Should have essential routes
        essential_routes = ["/health", "/health/services"]
        for route in essential_routes:
            assert route in route_paths, f"Missing essential route: {route}"

    def test_service_registry_architecture_complete(self):
        """Test that the Service Registry architecture is complete."""
        from src.services.service_registry_manager import ServiceRegistryManager
        from src.handlers.modular_api_handler import service_manager

        # ServiceRegistryManager should be available
        manager = ServiceRegistryManager()
        assert manager is not None

        # Modular handler should use service manager
        assert service_manager is not None
        assert hasattr(service_manager, "registry")
        assert len(service_manager.registry.services) == 14


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
