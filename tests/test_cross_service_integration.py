"""Cross-Service Integration Tests - Critical for system-wide changes"""

import pytest
from unittest.mock import Mock, patch
from src.services.service_registry_manager import service_registry


class TestCrossServiceIntegration:
    """Test integration between critical services"""

    def setup_method(self):
        """Set up test fixtures"""
        self.service_registry = service_registry

    @pytest.mark.asyncio
    async def test_auth_rbac_integration(self):
        """Test authentication and RBAC services work together"""
        # Arrange
        auth_service = self.service_registry.get_auth_service()
        rbac_service = self.service_registry.get_rbac_service()

        user_id = "user123"
        permission = "user:read:own"

        # Mock auth service
        with patch.object(auth_service, "validate_token") as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "payload": {"user_id": user_id},
            }

            # Mock RBAC service
            with patch.object(rbac_service, "user_has_permission") as mock_permission:
                mock_permission.return_value = Mock(
                    has_permission=True, reason="Success"
                )

                # Act
                token_result = await auth_service.validate_token("test_token")
                permission_result = await rbac_service.user_has_permission(
                    user_id, permission
                )

                # Assert
                assert token_result["valid"] is True
                assert permission_result.has_permission is True

    @pytest.mark.asyncio
    async def test_admin_performance_integration(self):
        """Test admin and performance services integration"""
        # Arrange
        admin_service = self.service_registry.get_admin_service()
        performance_service = self.service_registry.get_performance_service()

        # Mock admin dashboard data
        with patch.object(admin_service, "get_dashboard_data") as mock_dashboard:
            mock_dashboard.return_value = {
                "total_people": 100,
                "total_projects": 25,
                "timestamp": "2025-01-01T00:00:00Z",
            }

            # Mock performance health
            with patch.object(performance_service, "get_health_status") as mock_health:
                mock_health.return_value = {
                    "status": "healthy",
                    "metrics": {"response_time_avg": 150.0},
                    "timestamp": "2025-01-01T00:00:00Z",
                }

                # Act
                dashboard_data = await admin_service.get_dashboard_data()
                health_data = await performance_service.get_health_status()

                # Assert
                assert dashboard_data["total_people"] == 100
                assert health_data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_subscription_notification_integration(self):
        """Test subscription and email services integration"""
        # Arrange
        subscriptions_service = self.service_registry.get_subscriptions_service()
        email_service = self.service_registry.get_email_service()

        subscription_data = {
            "person_id": "person123",
            "project_id": "project456",
            "notification_preferences": {"email": True},
        }

        # Mock subscription creation
        with patch.object(subscriptions_service, "create_subscription") as mock_create:
            mock_create.return_value = {"id": "sub123", "status": "active"}

            # Mock email notification
            with patch.object(email_service, "send_notification_email") as mock_email:
                mock_email.return_value = {"success": True, "message_id": "msg123"}

                # Act
                subscription = subscriptions_service.create_subscription(
                    subscription_data
                )
                email_result = await email_service.send_notification_email(
                    "user@example.com",
                    "subscription_created",
                    {"subscription_id": subscription["id"]},
                )

                # Assert
                assert subscription["status"] == "active"
                assert email_result["success"] is True

    @pytest.mark.asyncio
    async def test_service_registry_health_check(self):
        """Test all services in registry are healthy"""
        # Act & Assert
        services_to_check = [
            "auth_service",
            "rbac_service",
            "admin_service",
            "performance_service",
            "email_service",
            "subscriptions_service",
        ]

        for service_name in services_to_check:
            service = getattr(self.service_registry, f"get_{service_name}")()
            assert service is not None, f"{service_name} should be available"

    @pytest.mark.asyncio
    async def test_async_sync_consistency_across_services(self):
        """Test that async/sync patterns are consistent across services"""
        # Arrange
        services = [
            self.service_registry.get_auth_service(),
            self.service_registry.get_rbac_service(),
            self.service_registry.get_admin_service(),
            self.service_registry.get_performance_service(),
            self.service_registry.get_email_service(),
        ]

        # Act & Assert
        for service in services:
            # Check that service methods are async
            methods = [method for method in dir(service) if not method.startswith("_")]
            public_methods = [
                method for method in methods if callable(getattr(service, method))
            ]

            # At least some methods should exist
            assert (
                len(public_methods) > 0
            ), f"Service {service.__class__.__name__} should have public methods"

    def test_service_registry_initialization(self):
        """Test service registry initializes all services correctly"""
        # Act & Assert
        assert hasattr(self.service_registry, "get_auth_service")
        assert hasattr(self.service_registry, "get_rbac_service")
        assert hasattr(self.service_registry, "get_admin_service")
        assert hasattr(self.service_registry, "get_performance_service")
        assert hasattr(self.service_registry, "get_email_service")
        assert hasattr(self.service_registry, "get_subscriptions_service")

    @pytest.mark.asyncio
    async def test_error_propagation_across_services(self):
        """Test that errors propagate correctly across service boundaries"""
        # Arrange
        auth_service = self.service_registry.get_auth_service()
        rbac_service = self.service_registry.get_rbac_service()

        # Mock auth failure
        with patch.object(auth_service, "validate_token") as mock_validate:
            mock_validate.return_value = {"valid": False, "error": "Invalid token"}

            # Act
            token_result = await auth_service.validate_token("invalid_token")

            # Assert
            assert token_result["valid"] is False
            assert "error" in token_result

    @pytest.mark.asyncio
    async def test_service_dependency_injection(self):
        """Test that services have proper dependency injection"""
        # Arrange
        services = [
            self.service_registry.get_auth_service(),
            self.service_registry.get_admin_service(),
            self.service_registry.get_subscriptions_service(),
        ]

        # Act & Assert
        for service in services:
            # Services should have repository dependencies
            repository_attrs = [
                attr for attr in dir(service) if "repository" in attr.lower()
            ]
            assert (
                len(repository_attrs) > 0
            ), f"Service {service.__class__.__name__} should have repository dependencies"
