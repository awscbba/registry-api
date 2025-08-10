"""
Tests for admin authorization middleware.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.middleware.admin_middleware import (
    require_admin_access,
    require_super_admin_access,
    AdminAuthorizationError,
    AdminActionLogger,
    verify_admin_or_self_access,
)
from src.models.auth import AuthenticatedUser


class TestAdminMiddleware:
    """Test cases for admin authorization middleware."""

    @pytest.fixture
    def regular_user(self):
        """Create a regular (non-admin) user."""
        return AuthenticatedUser(
            id="regular-user-id",
            email="user@example.com",
            first_name="Regular",
            last_name="User",
            is_admin=False,
            is_active=True,
        )

    @pytest.fixture
    def admin_user(self):
        """Create an admin user."""
        return AuthenticatedUser(
            id="admin-user-id",
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            is_admin=True,
            is_active=True,
        )

    @pytest.fixture
    def super_admin_user(self):
        """Create a super admin user."""
        return AuthenticatedUser(
            id="super-admin-user-id",
            email="admin@cbba.cloud.org.bo",
            first_name="Super",
            last_name="Admin",
            is_admin=True,
            is_active=True,
        )

    @pytest.mark.asyncio
    async def test_require_admin_access_success(self, admin_user):
        """Test require_admin_access with valid admin user."""
        result = await require_admin_access(admin_user)
        assert result == admin_user

    @pytest.mark.asyncio
    async def test_require_admin_access_no_user(self):
        """Test require_admin_access with no user."""
        with pytest.raises(AdminAuthorizationError) as exc_info:
            await require_admin_access(None)

        assert exc_info.value.status_code == 403
        assert "Authentication required" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_require_admin_access_regular_user(self, regular_user):
        """Test require_admin_access with regular user."""
        with pytest.raises(AdminAuthorizationError) as exc_info:
            await require_admin_access(regular_user)

        assert exc_info.value.status_code == 403
        assert "Admin access required" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_require_super_admin_access_success(self, super_admin_user):
        """Test require_super_admin_access with valid super admin user."""
        result = await require_super_admin_access(super_admin_user)
        assert result == super_admin_user

    @pytest.mark.asyncio
    async def test_require_super_admin_access_regular_admin(self, admin_user):
        """Test require_super_admin_access with regular admin user."""
        with pytest.raises(AdminAuthorizationError) as exc_info:
            await require_super_admin_access(admin_user)

        assert exc_info.value.status_code == 403
        assert "Super admin access required" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_verify_admin_or_self_access_admin(self, admin_user):
        """Test verify_admin_or_self_access with admin user accessing any user."""
        result = await verify_admin_or_self_access("any-user-id", admin_user)
        assert result == admin_user

    @pytest.mark.asyncio
    async def test_verify_admin_or_self_access_self(self, regular_user):
        """Test verify_admin_or_self_access with user accessing their own data."""
        result = await verify_admin_or_self_access(regular_user.id, regular_user)
        assert result == regular_user

    @pytest.mark.asyncio
    async def test_verify_admin_or_self_access_unauthorized(self, regular_user):
        """Test verify_admin_or_self_access with user accessing other user's data."""
        with pytest.raises(AdminAuthorizationError) as exc_info:
            await verify_admin_or_self_access("other-user-id", regular_user)

        assert exc_info.value.status_code == 403
        assert "You can only access your own data" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_admin_action_logger(self, admin_user):
        """Test AdminActionLogger functionality."""
        with patch("src.middleware.admin_middleware.logger") as mock_logger:
            await AdminActionLogger.log_admin_action(
                action="TEST_ACTION",
                admin_user=admin_user,
                target_resource="test_resource",
                target_id="test-id",
                details={"test": "data"},
                success=True,
            )

            # Verify logger was called
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert "Admin action: TEST_ACTION" in call_args[0][0]

            # Check extra data
            extra_data = call_args[1]["extra"]
            assert extra_data["action"] == "TEST_ACTION"
            assert extra_data["admin_user_id"] == admin_user.id
            assert extra_data["admin_user_email"] == admin_user.email
            assert extra_data["target_resource"] == "test_resource"
            assert extra_data["target_id"] == "test-id"
            assert extra_data["success"] is True
            assert extra_data["test"] == "data"

    @pytest.mark.asyncio
    async def test_admin_action_logger_failure(self, admin_user):
        """Test AdminActionLogger with failed action."""
        with patch("src.middleware.admin_middleware.logger") as mock_logger:
            await AdminActionLogger.log_admin_action(
                action="FAILED_ACTION", admin_user=admin_user, success=False
            )

            # Verify error logger was called
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert "Failed admin action: FAILED_ACTION" in call_args[0][0]


class TestAdminAuthorizationError:
    """Test cases for AdminAuthorizationError."""

    def test_default_error(self):
        """Test AdminAuthorizationError with default message."""
        error = AdminAuthorizationError()
        assert error.status_code == 403
        assert "Admin access required" in error.detail
        assert error.headers == {"WWW-Authenticate": "Bearer"}

    def test_custom_error(self):
        """Test AdminAuthorizationError with custom message."""
        custom_message = "Custom admin error message"
        error = AdminAuthorizationError(custom_message)
        assert error.status_code == 403
        assert error.detail == custom_message
        assert error.headers == {"WWW-Authenticate": "Bearer"}
