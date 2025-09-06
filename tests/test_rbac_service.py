"""Tests for RBAC Service - Critical service with 0% coverage"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.services.rbac_service import RBACService
from src.models.rbac import RoleAssignmentRequest, PermissionResult
from src.exceptions.base_exceptions import BusinessLogicException


class TestRBACService:
    """Test RBAC Service functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_roles_repo = Mock()
        self.rbac_service = RBACService()
        self.rbac_service.roles_repository = self.mock_roles_repo

    @pytest.mark.asyncio
    async def test_get_user_roles_success(self):
        """Test getting user roles successfully"""
        # Arrange
        user_id = "user123"
        expected_roles = ["user", "moderator"]
        self.mock_roles_repo.get_user_roles.return_value = expected_roles

        # Act
        result = await self.rbac_service.get_user_roles(user_id)

        # Assert
        assert result == expected_roles
        self.mock_roles_repo.get_user_roles.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_user_has_permission_success(self):
        """Test user permission check success"""
        # Arrange
        user_id = "user123"
        permission = "user:read:own"
        self.mock_roles_repo.get_user_roles.return_value = ["user"]

        with patch("src.models.rbac.user_has_permission", return_value=True):
            # Act
            result = await self.rbac_service.user_has_permission(user_id, permission)

            # Assert
            assert result.has_permission is True
            assert "success" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_user_has_permission_denied(self):
        """Test user permission check denied"""
        # Arrange
        user_id = "user123"
        permission = "admin:write:all"
        self.mock_roles_repo.get_user_roles.return_value = ["user"]

        with patch("src.models.rbac.user_has_permission", return_value=False):
            # Act
            result = await self.rbac_service.user_has_permission(user_id, permission)

            # Assert
            assert result.has_permission is False

    @pytest.mark.asyncio
    async def test_assign_role_success(self):
        """Test role assignment success"""
        # Arrange
        request = RoleAssignmentRequest(
            target_email="user@example.com", role_type="moderator"
        )
        assigned_by = "admin123"

        # Mock dependencies
        self.mock_roles_repo.get_user_roles.return_value = ["admin"]
        self.mock_roles_repo.get_user_by_email.return_value = Mock(id="user456")
        self.mock_roles_repo.assign_role.return_value = True

        with patch("src.models.rbac.can_assign_role", return_value=True):
            # Act
            result = await self.rbac_service.assign_role(request, assigned_by)

            # Assert
            assert result.success is True
            self.mock_roles_repo.assign_role.assert_called_once()

    @pytest.mark.asyncio
    async def test_assign_role_insufficient_permissions(self):
        """Test role assignment with insufficient permissions"""
        # Arrange
        request = RoleAssignmentRequest(
            target_email="user@example.com", role_type="admin"
        )
        assigned_by = "user123"

        self.mock_roles_repo.get_user_roles.return_value = ["user"]

        with patch("src.models.rbac.can_assign_role", return_value=False):
            # Act & Assert
            with pytest.raises(BusinessLogicException):
                await self.rbac_service.assign_role(request, assigned_by)

    @pytest.mark.asyncio
    async def test_user_is_admin_true(self):
        """Test user is admin check - true"""
        # Arrange
        user_id = "admin123"
        self.mock_roles_repo.get_user_roles.return_value = ["admin"]

        with patch("src.models.rbac.is_admin_role", return_value=True):
            # Act
            result = await self.rbac_service.user_is_admin(user_id)

            # Assert
            assert result is True

    @pytest.mark.asyncio
    async def test_user_is_admin_false(self):
        """Test user is admin check - false"""
        # Arrange
        user_id = "user123"
        self.mock_roles_repo.get_user_roles.return_value = ["user"]

        with patch("src.models.rbac.is_admin_role", return_value=False):
            # Act
            result = await self.rbac_service.user_is_admin(user_id)

            # Assert
            assert result is False

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in RBAC operations"""
        # Arrange
        user_id = "user123"
        self.mock_roles_repo.get_user_roles.side_effect = Exception("Database error")

        # Act
        result = await self.rbac_service.user_has_permission(user_id, "test:permission")

        # Assert
        assert result.has_permission is False
        assert "error" in result.reason.lower()
