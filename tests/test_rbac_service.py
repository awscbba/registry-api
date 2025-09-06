"""Tests for RBAC Service - Critical authorization functionality"""

import pytest
from unittest.mock import Mock, patch
from src.services.rbac_service import RBACService
from src.models.rbac import RoleType


class TestRBACService:
    """Test RBAC Service functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.rbac_service = RBACService()
        self.rbac_service.roles_repository = Mock()

    @pytest.mark.asyncio
    async def test_get_user_roles_success(self):
        """Test getting user roles successfully"""
        # Arrange
        user_id = "user123"
        expected_roles = [RoleType.USER]
        self.rbac_service.roles_repository.get_user_roles.return_value = expected_roles

        # Act
        result = await self.rbac_service.get_user_roles(user_id)

        # Assert
        assert result == expected_roles
        self.rbac_service.roles_repository.get_user_roles.assert_called_once_with(
            user_id
        )

    @pytest.mark.asyncio
    async def test_user_has_permission_success(self):
        """Test user permission check success"""
        # Arrange
        user_id = "user123"
        permission = "user:read:own"
        self.rbac_service.roles_repository.get_user_roles.return_value = [RoleType.USER]

        with patch("src.models.rbac.user_has_permission", return_value=True):
            # Act
            result = await self.rbac_service.user_has_permission(user_id, permission)

            # Assert
            assert result.has_permission is True

    @pytest.mark.asyncio
    async def test_user_has_permission_denied(self):
        """Test user permission check denied"""
        # Arrange
        user_id = "user123"
        permission = "admin:write:all"
        self.rbac_service.roles_repository.get_user_roles.return_value = [RoleType.USER]

        with patch("src.models.rbac.user_has_permission", return_value=False):
            # Act
            result = await self.rbac_service.user_has_permission(user_id, permission)

            # Assert
            assert result.has_permission is False

    @pytest.mark.asyncio
    async def test_user_is_admin_true(self):
        """Test user is admin check - true"""
        # Arrange
        user_id = "admin123"
        self.rbac_service.roles_repository.get_user_roles.return_value = [
            RoleType.ADMIN
        ]

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
        self.rbac_service.roles_repository.get_user_roles.return_value = [RoleType.USER]

        with patch("src.models.rbac.is_admin_role", return_value=False):
            # Act
            result = await self.rbac_service.user_is_admin(user_id)

            # Assert
            assert result is False

    def test_rbac_service_initialization(self):
        """Test RBAC service initializes correctly"""
        # Act
        service = RBACService()

        # Assert
        assert hasattr(service, "roles_repository")
