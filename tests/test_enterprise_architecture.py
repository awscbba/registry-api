"""
Test enterprise architecture components.
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta

from src.models.rbac import RoleType, Permission, RoleAssignmentRequest
from src.services.rbac_service import RBACService
from src.services.logging_service import (
    EnterpriseLoggingService,
    LogLevel,
    LogCategory,
    RequestContext,
)
from src.exceptions.base_exceptions import (
    AuthenticationException,
    AuthorizationException,
    ValidationException,
    ResourceNotFoundException,
    ErrorCode,
)
from src.exceptions.error_handler import EnterpriseErrorHandler


class TestRBACService:
    """Test RBAC service functionality."""

    def setup_method(self):
        """Set up test RBAC service."""
        self.rbac_service = RBACService()

    @pytest.mark.asyncio
    async def test_get_user_roles_default(self):
        """Test getting default user roles."""
        # Mock user exists but no roles assigned
        with patch.object(self.rbac_service.people_repository, "get_by_id") as mock_get:
            mock_user = AsyncMock()
            mock_user.isAdmin = False
            mock_get.return_value = mock_user

            roles = await self.rbac_service.get_user_roles("user123")
            assert RoleType.USER in roles

    @pytest.mark.asyncio
    async def test_get_user_roles_admin(self):
        """Test getting admin user roles."""
        # Mock admin user
        with patch.object(self.rbac_service.people_repository, "get_by_id") as mock_get:
            mock_user = AsyncMock()
            mock_user.isAdmin = True
            mock_get.return_value = mock_user

            roles = await self.rbac_service.get_user_roles("admin123")
            assert RoleType.ADMIN in roles

    @pytest.mark.asyncio
    async def test_user_has_permission_success(self):
        """Test successful permission check."""
        # Mock user with USER role
        with patch.object(self.rbac_service, "get_user_roles") as mock_roles:
            mock_roles.return_value = [RoleType.USER]

            result = await self.rbac_service.user_has_permission(
                "user123", Permission.USER_READ_OWN
            )

            assert result.has_permission is True

    @pytest.mark.asyncio
    async def test_user_has_permission_denied(self):
        """Test denied permission check."""
        # Mock user with USER role trying admin permission
        with patch.object(self.rbac_service, "get_user_roles") as mock_roles:
            mock_roles.return_value = [RoleType.USER]

            result = await self.rbac_service.user_has_permission(
                "user123", Permission.SYSTEM_CONFIG
            )

            assert result.has_permission is False

    @pytest.mark.asyncio
    async def test_assign_role_success(self):
        """Test successful role assignment."""
        # Mock assigner with admin role
        with patch.object(self.rbac_service, "get_user_roles") as mock_roles:
            mock_roles.return_value = [RoleType.ADMIN]

            # Mock target user
            with patch.object(
                self.rbac_service.people_repository, "get_by_email"
            ) as mock_get:
                mock_user = AsyncMock()
                mock_user.id = "target123"
                mock_user.email = "target@example.com"
                mock_get.return_value = mock_user

                # Mock DynamoDB put_item call
                with patch.object(
                    self.rbac_service.roles_repository, "create_role_assignment"
                ) as mock_create:
                    mock_create.return_value = None

                    request = RoleAssignmentRequest(
                        user_email="target@example.com", role_type=RoleType.MODERATOR
                    )

                    result = await self.rbac_service.assign_role(request, "admin123")

                    assert result.success is True
                    assert result.user_role.role_type == RoleType.MODERATOR
                    mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_user_is_admin(self):
        """Test admin check."""
        with patch.object(self.rbac_service, "get_user_roles") as mock_roles:
            mock_roles.return_value = [RoleType.ADMIN]

            is_admin = await self.rbac_service.user_is_admin("admin123")
            assert is_admin is True


class TestEnterpriseLoggingService:
    """Test enterprise logging service."""

    def setup_method(self):
        """Set up test logging service."""
        self.logging_service = EnterpriseLoggingService()

    def test_log_structured(self):
        """Test structured logging."""
        context = RequestContext(
            request_id="req123",
            user_id="user123",
            ip_address="192.168.1.1",
            path="/test",
            method="GET",
        )

        # Should not raise exception
        self.logging_service.log_structured(
            level=LogLevel.INFO,
            category=LogCategory.API_ACCESS,
            message="Test message",
            context=context,
            additional_data={"test": "data"},
        )

    def test_log_authentication_event(self):
        """Test authentication event logging."""
        context = RequestContext(request_id="req123", user_id="user123")

        # Should not raise exception
        self.logging_service.log_authentication_event(
            event_type="login", user_id="user123", success=True, context=context
        )

    def test_log_security_event(self):
        """Test security event logging."""
        # Should not raise exception
        self.logging_service.log_security_event(
            event_type="suspicious_activity",
            severity="high",
            user_id="user123",
            details={"reason": "multiple_failed_logins"},
        )


class TestEnterpriseExceptions:
    """Test enterprise exception system."""

    def test_authentication_exception(self):
        """Test authentication exception."""
        exc = AuthenticationException(
            message="Invalid credentials",
            user_message="Please check your login details",
        )

        assert exc.error_code == ErrorCode.AUTHENTICATION_FAILED
        assert exc.user_message == "Please check your login details"
        assert exc.error_id is not None

    def test_authorization_exception(self):
        """Test authorization exception."""
        exc = AuthorizationException(
            message="Access denied", error_code=ErrorCode.INSUFFICIENT_PERMISSIONS
        )

        assert exc.error_code == ErrorCode.INSUFFICIENT_PERMISSIONS
        assert "permission" in exc.user_message.lower()

    def test_validation_exception(self):
        """Test validation exception."""
        field_errors = {
            "email": ["Invalid email format"],
            "password": ["Password too short"],
        }

        exc = ValidationException(
            message="Validation failed", field_errors=field_errors
        )

        assert exc.error_code == ErrorCode.INVALID_INPUT
        assert exc.details["field_errors"] == field_errors

    def test_resource_not_found_exception(self):
        """Test resource not found exception."""
        exc = ResourceNotFoundException(resource_type="User", resource_id="user123")

        assert exc.error_code == ErrorCode.RESOURCE_NOT_FOUND
        assert "user123" in exc.message
        assert exc.details["resource_type"] == "User"

    def test_exception_to_dict(self):
        """Test exception serialization."""
        exc = ValidationException(
            message="Test validation error", field_errors={"field": ["error"]}
        )

        data = exc.to_dict()

        assert data["error_code"] == ErrorCode.INVALID_INPUT.value
        assert data["message"] == "Test validation error"
        assert data["error_id"] is not None
        assert data["timestamp"] is not None
        assert data["details"]["field_errors"] == {"field": ["error"]}


class TestEnterpriseErrorHandler:
    """Test enterprise error handler."""

    def setup_method(self):
        """Set up test error handler."""
        self.error_handler = EnterpriseErrorHandler()

    def test_create_validation_exception(self):
        """Test validation exception creation."""
        field_errors = {"email": ["Invalid format"]}

        exc = self.error_handler.create_validation_exception(
            message="Validation failed", field_errors=field_errors
        )

        assert isinstance(exc, ValidationException)
        assert exc.details["field_errors"] == field_errors

    def test_create_not_found_exception(self):
        """Test not found exception creation."""
        exc = self.error_handler.create_not_found_exception(
            resource_type="User", resource_id="user123"
        )

        assert isinstance(exc, ResourceNotFoundException)
        assert exc.details["resource_type"] == "User"
        assert exc.details["resource_id"] == "user123"

    def test_create_permission_denied_exception(self):
        """Test permission denied exception creation."""
        exc = self.error_handler.create_permission_denied_exception(
            action="delete", resource="user"
        )

        assert isinstance(exc, AuthorizationException)
        assert exc.error_code == ErrorCode.PERMISSION_DENIED
        assert "delete" in exc.message
        assert "user" in exc.message


class TestEnterpriseIntegration:
    """Test integration between enterprise components."""

    @pytest.mark.asyncio
    async def test_rbac_with_logging(self):
        """Test RBAC service with logging integration."""
        rbac_service = RBACService()

        # Mock user roles
        with patch.object(rbac_service, "get_user_roles") as mock_roles:
            mock_roles.return_value = [RoleType.USER]

            context = RequestContext(request_id="req123", user_id="user123")

            # This should log the permission check
            result = await rbac_service.user_has_permission(
                "user123", Permission.USER_READ_OWN, context=context
            )

            assert result.has_permission is True

    def test_exception_with_logging(self):
        """Test exception handling with logging."""
        # Create exception
        exc = AuthenticationException(message="Login failed", details={"attempts": 3})

        # Exception should have proper structure
        assert exc.error_id is not None
        assert exc.timestamp is not None
        assert exc.details["attempts"] == 3
