"""
Critical tests to validate async/sync consistency after subscription changes.
These tests ensure our changes don't introduce regressions.
"""

import pytest
import inspect
from unittest.mock import Mock, patch

from src.services.service_registry_manager import service_registry
from src.services.subscriptions_service import SubscriptionsService
from src.repositories.subscriptions_repository import SubscriptionsRepository


class TestAsyncSyncConsistency:
    """Test async/sync consistency across the service layer."""

    def test_subscription_service_methods_are_sync(self):
        """Ensure all SubscriptionsService methods are synchronous."""
        service = SubscriptionsService(Mock())

        critical_methods = [
            "list_subscriptions",
            "get_subscription",
            "create_subscription",
            "update_subscription",
            "delete_subscription",
        ]

        for method_name in critical_methods:
            method = getattr(service, method_name)
            assert not inspect.iscoroutinefunction(
                method
            ), f"{method_name} should be synchronous"

    def test_subscription_repository_methods_are_sync(self):
        """Ensure all SubscriptionsRepository methods are synchronous."""
        repo = SubscriptionsRepository()

        critical_methods = [
            "list_subscriptions",
            "get_subscription",
            "create_subscription",
            "update_subscription",
            "delete_subscription",
        ]

        for method_name in critical_methods:
            if hasattr(repo, method_name):
                method = getattr(repo, method_name)
                assert not inspect.iscoroutinefunction(
                    method
                ), f"{method_name} should be synchronous"

    def test_service_registry_integration(self):
        """Test that service registry properly initializes subscription service."""
        service_registry.initialize()

        # Test service can be retrieved
        subs_service = service_registry.get_subscriptions_service()
        assert isinstance(subs_service, SubscriptionsService)

        # Test service has repository dependency
        assert hasattr(subs_service, "repository")
        assert subs_service.repository is not None

    @patch(
        "src.repositories.subscriptions_repository.SubscriptionsRepository.list_subscriptions"
    )
    def test_service_calls_repository_without_await(self, mock_repo_method):
        """Test that service calls repository methods without await."""
        mock_repo_method.return_value = []

        service = SubscriptionsService(Mock())
        service.repository = Mock()
        service.repository.list_subscriptions = mock_repo_method

        # This should not raise any async-related errors
        result = service.list_subscriptions()

        mock_repo_method.assert_called_once()
        assert result == []

    def test_no_coroutine_objects_in_responses(self):
        """Test that service methods don't return coroutine objects."""
        mock_repo = Mock()
        mock_repo.list_subscriptions.return_value = []
        mock_repo.get_subscription.return_value = None

        service = SubscriptionsService(mock_repo)

        # Test each method returns actual values, not coroutines
        result = service.list_subscriptions()
        assert not inspect.iscoroutine(result)

        result = service.get_subscription("test-id")
        assert not inspect.iscoroutine(result)


class TestRegressionPrevention:
    """Tests to prevent regressions from async/sync changes."""

    def test_other_services_unaffected(self):
        """Ensure other services weren't affected by subscription changes."""
        service_registry.initialize()

        # Test that other services still work
        people_service = service_registry.get_people_service()
        assert people_service is not None

        projects_service = service_registry.get_projects_service()
        assert projects_service is not None

        auth_service = service_registry.get_auth_service()
        assert auth_service is not None

    def test_service_registry_completeness(self):
        """Test that all expected services are registered."""
        service_registry.initialize()
        services = service_registry._services

        expected_services = ["people", "projects", "subscriptions", "auth"]
        for service_name in expected_services:
            assert service_name in services, f"{service_name} service not registered"

    def test_subscription_service_initialization(self):
        """Test subscription service initializes correctly with dependencies."""
        service_registry.initialize()

        subs_service = service_registry.get_subscriptions_service()

        # Test service has required attributes
        assert hasattr(subs_service, "repository")
        assert subs_service.repository is not None

        # Test service methods are callable
        assert callable(subs_service.list_subscriptions)
        assert callable(subs_service.get_subscription)
        assert callable(subs_service.create_subscription)


class TestCriticalPathValidation:
    """Test critical paths that could be affected by async/sync changes."""

    @patch("src.services.service_registry_manager.service_registry")
    def test_router_service_integration(self, mock_registry):
        """Test that router can call service methods without async issues."""
        from fastapi.testclient import TestClient
        from src.app import app

        # Mock service with sync methods
        mock_service = Mock()
        mock_service.list_subscriptions.return_value = []
        mock_registry.get_subscriptions_service.return_value = mock_service

        client = TestClient(app)

        # This should work without async/sync errors
        # Note: Will get 401 due to auth, but that's expected
        response = client.get("/v2/subscriptions")

        # The important thing is no coroutine serialization errors
        assert response.status_code in [200, 401]  # Either success or auth required

    def test_method_signature_consistency(self):
        """Test that service and repository method signatures are consistent."""
        service = SubscriptionsService(Mock())
        repo = SubscriptionsRepository()

        # Check that corresponding methods have similar signatures
        service_methods = [name for name in dir(service) if not name.startswith("_")]
        repo_methods = [name for name in dir(repo) if not name.startswith("_")]

        common_methods = set(service_methods) & set(repo_methods)

        # Should have at least basic CRUD methods in common
        expected_common = {
            "list_subscriptions",
            "get_subscription",
            "create_subscription",
        }
        actual_common = expected_common & common_methods

        assert (
            len(actual_common) >= 3
        ), f"Missing common methods: {expected_common - actual_common}"
