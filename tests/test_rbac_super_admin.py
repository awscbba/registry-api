"""Tests for RBAC service super admin functionality."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.services.rbac_service import RBACService
from src.models.rbac import RoleType


class TestRBACServiceSuperAdmin:
    """Test cases for RBAC service super admin detection."""

    def setup_method(self):
        """Set up test fixtures."""
        with (
            patch("src.repositories.people_repository.PeopleRepository"),
            patch("src.repositories.roles_repository.RolesRepository"),
        ):
            self.rbac_service = RBACService()

    @pytest.mark.asyncio
    async def test_user_is_super_admin_with_super_admin_role(self):
        """Test super admin detection when user has super_admin role."""
        # Mock get_user_roles to return super_admin
        self.rbac_service.get_user_roles = AsyncMock(
            return_value=[RoleType.ADMIN, RoleType.SUPER_ADMIN]
        )

        result = await self.rbac_service.user_is_super_admin("test-user-id")

        assert result is True

    @pytest.mark.asyncio
    async def test_user_is_super_admin_without_super_admin_role(self):
        """Test super admin detection when user only has admin role."""
        # Mock get_user_roles to return only admin
        self.rbac_service.get_user_roles = AsyncMock(
            return_value=[RoleType.ADMIN, RoleType.USER]
        )

        result = await self.rbac_service.user_is_super_admin("test-user-id")

        assert result is False

    @pytest.mark.asyncio
    async def test_user_is_super_admin_no_roles(self):
        """Test super admin detection when user has no roles."""
        # Mock get_user_roles to return empty list
        self.rbac_service.get_user_roles = AsyncMock(return_value=[])

        result = await self.rbac_service.user_is_super_admin("test-user-id")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_user_roles_integration(self):
        """Test that get_user_roles properly calls roles repository."""
        # Mock the roles repository
        mock_user_roles = [
            Mock(role_type=RoleType.ADMIN, is_active=True, expires_at=None),
            Mock(role_type=RoleType.SUPER_ADMIN, is_active=True, expires_at=None),
        ]
        self.rbac_service.roles_repository.get_user_roles = Mock(
            return_value=mock_user_roles
        )

        result = await self.rbac_service.get_user_roles("test-user-id")

        # Should return the role types
        assert RoleType.ADMIN in result
        assert RoleType.SUPER_ADMIN in result
        assert len(result) == 2
