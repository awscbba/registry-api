"""
Comprehensive tests for the database-driven roles system.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock, Mock

from src.models.roles import (
    RoleType,
    Permission,
    UserRole,
    RoleAssignmentRequest,
    get_role_permissions,
    has_permission,
    is_admin_role,
    is_super_admin_role,
)
from src.services.roles_service import RolesService
from src.middleware.admin_middleware_v2 import (
    require_admin_access,
    require_super_admin_access,
    require_permission,
)


class TestRoleModels:
    """Test role model functionality."""

    def test_role_permissions(self):
        """Test that roles have correct permissions."""
        # Test USER role permissions
        user_permissions = get_role_permissions(RoleType.USER)
        assert Permission.READ_OWN_PROFILE in user_permissions
        assert Permission.UPDATE_OWN_PROFILE in user_permissions
        assert Permission.READ_PROJECTS in user_permissions
        assert Permission.MANAGE_ROLES not in user_permissions

        # Test ADMIN role permissions
        admin_permissions = get_role_permissions(RoleType.ADMIN)
        assert Permission.READ_ALL_USERS in admin_permissions
        assert Permission.UPDATE_ANY_USER in admin_permissions
        assert Permission.MANAGE_ROLES not in admin_permissions  # Only super admin

        # Test SUPER_ADMIN role permissions
        super_admin_permissions = get_role_permissions(RoleType.SUPER_ADMIN)
        assert Permission.MANAGE_ROLES in super_admin_permissions
        assert Permission.SYSTEM_CONFIG in super_admin_permissions
        assert len(super_admin_permissions) == len(Permission)  # All permissions

    def test_has_permission(self):
        """Test permission checking logic."""
        # User with USER role
        user_roles = [RoleType.USER]
        assert has_permission(user_roles, Permission.READ_OWN_PROFILE)
        assert not has_permission(user_roles, Permission.READ_ALL_USERS)

        # User with ADMIN role
        admin_roles = [RoleType.ADMIN]
        assert has_permission(admin_roles, Permission.READ_ALL_USERS)
        assert not has_permission(admin_roles, Permission.MANAGE_ROLES)

        # User with SUPER_ADMIN role
        super_admin_roles = [RoleType.SUPER_ADMIN]
        assert has_permission(super_admin_roles, Permission.MANAGE_ROLES)
        assert has_permission(super_admin_roles, Permission.READ_OWN_PROFILE)

        # User with multiple roles
        multiple_roles = [RoleType.USER, RoleType.ADMIN]
        assert has_permission(multiple_roles, Permission.READ_OWN_PROFILE)
        assert has_permission(multiple_roles, Permission.READ_ALL_USERS)

    def test_role_type_checks(self):
        """Test role type checking functions."""
        assert is_admin_role(RoleType.ADMIN)
        assert is_admin_role(RoleType.SUPER_ADMIN)
        assert not is_admin_role(RoleType.USER)
        assert not is_admin_role(RoleType.MODERATOR)

        assert is_super_admin_role(RoleType.SUPER_ADMIN)
        assert not is_super_admin_role(RoleType.ADMIN)
        assert not is_super_admin_role(RoleType.USER)


class TestRolesService:
    """Test the roles service functionality."""

    @pytest.fixture
    def roles_service(self):
        """Create a roles service instance with mocked DynamoDB."""
        service = RolesService()
        # Mock the table.query method instead of dynamodb_service
        service.table = Mock()
        return service

    @pytest.mark.asyncio
    async def test_get_user_roles_success(self, roles_service):
        """Test successful user role retrieval."""
        # Mock DynamoDB response
        mock_response = {
            "Items": [
                {
                    "user_id": "user123",
                    "role_type": "admin",
                    "is_active": True,
                    "expires_at": None,
                },
                {
                    "user_id": "user123",
                    "role_type": "user",
                    "is_active": True,
                    "expires_at": None,
                },
            ]
        }
        roles_service.table.query.return_value = mock_response

        # Test the method
        roles = await roles_service.get_user_roles("user123")

        # Verify results
        assert len(roles) == 2
        assert RoleType.ADMIN in roles
        assert RoleType.USER in roles

        # Verify DynamoDB was called correctly
        roles_service.table.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_roles_expired(self, roles_service):
        """Test that expired roles are filtered out."""
        # Mock DynamoDB response with expired role
        expired_date = (datetime.utcnow() - timedelta(days=1)).isoformat()
        mock_response = {
            "Items": [
                {
                    "user_id": "user123",
                    "role_type": "admin",
                    "is_active": True,
                    "expires_at": expired_date,  # Expired
                },
                {
                    "user_id": "user123",
                    "role_type": "user",
                    "is_active": True,
                    "expires_at": None,  # No expiration
                },
            ]
        }
        roles_service.table.query.return_value = mock_response

        # Test the method
        roles = await roles_service.get_user_roles("user123")

        # Verify only non-expired role is returned
        assert len(roles) == 1
        assert RoleType.USER in roles
        assert RoleType.ADMIN not in roles

    @pytest.mark.asyncio
    async def test_get_user_roles_no_roles_assigns_default(self, roles_service):
        """Test that default USER role is assigned when no roles exist."""
        # Mock empty DynamoDB response
        roles_service.table.query.return_value = {"Items": []}
        roles_service.assign_default_user_role = AsyncMock()

        # Test the method
        roles = await roles_service.get_user_roles("user123")

        # Verify default role is returned and assigned
        assert len(roles) == 1
        assert RoleType.USER in roles
        roles_service.assign_default_user_role.assert_called_once_with("user123")

    @pytest.mark.asyncio
    async def test_user_has_permission(self, roles_service):
        """Test permission checking."""
        # Mock get_user_roles to return ADMIN role
        roles_service.get_user_roles = AsyncMock(return_value=[RoleType.ADMIN])

        # Test permission check
        has_perm = await roles_service.user_has_permission(
            "user123", Permission.READ_ALL_USERS
        )
        assert has_perm

        # Test permission user doesn't have
        has_perm = await roles_service.user_has_permission(
            "user123", Permission.MANAGE_ROLES
        )
        assert not has_perm

    @pytest.mark.asyncio
    async def test_user_is_admin(self, roles_service):
        """Test admin role checking."""
        # Mock get_user_roles to return ADMIN role
        roles_service.get_user_roles = AsyncMock(return_value=[RoleType.ADMIN])

        is_admin = await roles_service.user_is_admin("user123")
        assert is_admin

        # Test with non-admin role
        roles_service.get_user_roles = AsyncMock(return_value=[RoleType.USER])
        is_admin = await roles_service.user_is_admin("user123")
        assert not is_admin

    @pytest.mark.asyncio
    async def test_user_is_super_admin(self, roles_service):
        """Test super admin role checking."""
        # Mock get_user_roles to return SUPER_ADMIN role
        roles_service.get_user_roles = AsyncMock(return_value=[RoleType.SUPER_ADMIN])

        is_super_admin = await roles_service.user_is_super_admin("user123")
        assert is_super_admin

        # Test with admin but not super admin
        roles_service.get_user_roles = AsyncMock(return_value=[RoleType.ADMIN])
        is_super_admin = await roles_service.user_is_super_admin("user123")
        assert not is_super_admin

    @pytest.mark.asyncio
    async def test_assign_role_success(self, roles_service):
        """Test successful role assignment."""
        # Mock helper methods
        roles_service._get_user_id_by_email = AsyncMock(return_value="user123")
        roles_service.table.put_item = Mock()

        # Create assignment request
        request = RoleAssignmentRequest(
            user_email="test@example.com",
            role_type=RoleType.ADMIN,
            notes="Test assignment",
        )

        # Test assignment
        response = await roles_service.assign_role(request, "admin123")

        # Verify success
        assert response.success
        assert "successfully assigned" in response.message
        assert response.user_role is not None
        assert response.user_role.role_type == RoleType.ADMIN

        # Verify DynamoDB was called
        roles_service.table.put_item.assert_called_once()

    @pytest.mark.asyncio
    async def test_assign_role_user_not_found(self, roles_service):
        """Test role assignment when user doesn't exist."""
        # Mock user not found
        roles_service._get_user_id_by_email = AsyncMock(return_value=None)

        # Create assignment request
        request = RoleAssignmentRequest(
            user_email="nonexistent@example.com", role_type=RoleType.ADMIN
        )

        # Test assignment
        response = await roles_service.assign_role(request, "admin123")

        # Verify failure
        assert not response.success
        assert "not found" in response.message

    @pytest.mark.asyncio
    async def test_revoke_role_success(self, roles_service):
        """Test successful role revocation."""
        # Mock helper methods
        roles_service._get_user_id_by_email = AsyncMock(return_value="user123")
        roles_service.table.update_item = Mock()

        # Test revocation
        response = roles_service.revoke_role(
            "test@example.com", RoleType.ADMIN, "admin123"
        )

        # Verify success
        assert response.success
        assert "successfully revoked" in response.message

        # Verify DynamoDB was called
        roles_service.table.update_item.assert_called_once()


class TestAdminMiddleware:
    """Test the updated admin middleware."""

    @pytest.fixture
    def mock_roles_service(self):
        """Mock the roles service."""
        with patch("src.middleware.admin_middleware_v2.roles_service") as mock:
            # Configure methods to return values directly (not coroutines)
            mock.user_is_admin = Mock()
            mock.user_is_super_admin = Mock()
            mock.user_has_permission = Mock()
            yield mock

    @pytest.mark.asyncio
    async def test_require_admin_access_success(self, mock_roles_service):
        """Test successful admin access."""
        # Mock user and roles service
        mock_user = {"id": "user123", "email": "admin@example.com"}
        mock_roles_service.user_is_admin = AsyncMock(return_value=True)

        # Test the middleware
        result = await require_admin_access(mock_user)

        # Verify success
        assert result == mock_user
        mock_roles_service.user_is_admin.assert_called_once_with("user123")

    @pytest.mark.asyncio
    async def test_require_admin_access_denied(self, mock_roles_service):
        """Test admin access denied for non-admin user."""
        # Mock user and roles service
        mock_user = {"id": "user123", "email": "user@example.com"}
        mock_roles_service.user_is_admin = AsyncMock(return_value=False)

        # Test the middleware - should raise exception
        with pytest.raises(Exception) as exc_info:
            await require_admin_access(mock_user)

        assert exc_info.value.status_code == 403
        assert "Insufficient privileges" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_require_super_admin_access_success(self, mock_roles_service):
        """Test successful super admin access."""
        # Mock user and roles service
        mock_user = {"id": "user123", "email": "superadmin@example.com"}
        mock_roles_service.user_is_admin = AsyncMock(return_value=True)
        mock_roles_service.user_is_super_admin = AsyncMock(return_value=True)

        # Test the middleware
        result = await require_super_admin_access(mock_user)

        # Verify success
        assert result == mock_user
        mock_roles_service.user_is_super_admin.assert_called_once_with("user123")

    @pytest.mark.asyncio
    async def test_require_super_admin_access_denied(self, mock_roles_service):
        """Test super admin access denied for regular admin."""
        # Mock user and roles service
        mock_user = {"id": "user123", "email": "admin@example.com"}
        mock_roles_service.user_is_admin = AsyncMock(return_value=True)
        mock_roles_service.user_is_super_admin = AsyncMock(return_value=False)

        # Test the middleware - should raise exception
        with pytest.raises(Exception) as exc_info:
            await require_super_admin_access(mock_user)

        assert exc_info.value.status_code == 403
        assert "Super admin access required" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_require_permission_success(self, mock_roles_service):
        """Test successful permission check."""
        # Mock user and roles service
        mock_user = {"id": "user123", "email": "user@example.com"}
        mock_roles_service.user_has_permission = AsyncMock(return_value=True)

        # Create permission checker
        permission_checker = await require_permission(Permission.READ_ALL_USERS)

        # Test the permission checker
        result = await permission_checker(mock_user)

        # Verify success
        assert result == mock_user
        mock_roles_service.user_has_permission.assert_called_once_with(
            "user123", Permission.READ_ALL_USERS
        )

    @pytest.mark.asyncio
    async def test_require_permission_denied(self, mock_roles_service):
        """Test permission denied."""
        # Mock user and roles service
        mock_user = {"id": "user123", "email": "user@example.com"}
        mock_roles_service.user_has_permission = AsyncMock(return_value=False)

        # Create permission checker
        permission_checker = await require_permission(Permission.READ_ALL_USERS)

        # Test the permission checker - should raise exception
        with pytest.raises(Exception) as exc_info:
            await permission_checker(mock_user)

        assert exc_info.value.status_code == 403
        assert "read_all_users" in str(exc_info.value.detail)


class TestIntegration:
    """Integration tests for the complete roles system."""

    @pytest.mark.asyncio
    async def test_complete_role_assignment_flow(self):
        """Test the complete flow from role assignment to permission checking."""
        # This would be a more complex integration test
        # that tests the entire flow with a real or more realistic mock database
        pass

    @pytest.mark.asyncio
    async def test_migration_scenario(self):
        """Test the migration from hardcoded admins to database roles."""
        # This would test the migration script functionality
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
