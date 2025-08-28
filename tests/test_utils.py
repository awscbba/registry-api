"""
Test utilities for authentication and mocking.
"""

import jwt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from unittest.mock import MagicMock

from src.models.rbac import RoleType, Permission


class TestAuthUtils:
    """Utilities for test authentication."""

    # Use a test-specific JWT secret
    TEST_JWT_SECRET = "test-jwt-secret-for-testing-only"
    TEST_JWT_ALGORITHM = "HS256"

    @classmethod
    def create_test_token(
        cls,
        user_id: str = "test-user-id",
        email: str = "test@example.com",
        roles: list = None,
        expires_in_hours: int = 1,
    ) -> str:
        """Create a test JWT token."""
        if roles is None:
            roles = [RoleType.USER.value]

        now = datetime.utcnow()
        payload = {
            "sub": user_id,
            "email": email,
            "roles": roles,
            "iat": now,
            "exp": now + timedelta(hours=expires_in_hours),
        }

        return jwt.encode(
            payload, cls.TEST_JWT_SECRET, algorithm=cls.TEST_JWT_ALGORITHM
        )

    @classmethod
    def create_admin_token(
        cls, user_id: str = "admin-user-id", email: str = "admin@example.com"
    ) -> str:
        """Create a test admin JWT token."""
        return cls.create_test_token(
            user_id=user_id,
            email=email,
            roles=[RoleType.ADMIN.value, RoleType.USER.value],
        )

    @classmethod
    def get_auth_headers(cls, token: Optional[str] = None) -> Dict[str, str]:
        """Get authorization headers for tests."""
        if token is None:
            token = cls.create_test_token()

        return {"Authorization": f"Bearer {token}"}

    @classmethod
    def get_admin_headers(cls) -> Dict[str, str]:
        """Get admin authorization headers for tests."""
        token = cls.create_admin_token()
        return {"Authorization": f"Bearer {token}"}


class TestMockUtils:
    """Utilities for mocking in tests."""

    @staticmethod
    def mock_user(
        user_id: str = "test-user-id",
        email: str = "test@example.com",
        is_admin: bool = False,
        is_active: bool = True,
    ) -> MagicMock:
        """Create a mock user object."""
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email = email
        mock_user.isAdmin = is_admin
        mock_user.isActive = is_active
        mock_user.firstName = "Test"
        mock_user.lastName = "User"
        return mock_user

    @staticmethod
    def mock_permission_result(
        has_permission: bool = True, reason: str = ""
    ) -> MagicMock:
        """Create a mock permission result."""
        mock_result = MagicMock()
        mock_result.has_permission = has_permission
        mock_result.reason = reason
        return mock_result

    @staticmethod
    def setup_auth_mocks(
        mock_get_user,
        mock_get_roles,
        mock_user_permission,
        mock_is_locked,
        user_id: str = "test-user-id",
        roles: list = None,
        has_permission: bool = True,
        is_locked: bool = False,
    ):
        """Set up common authentication mocks."""
        if roles is None:
            roles = [RoleType.USER]

        # Mock user
        mock_get_user.return_value = TestMockUtils.mock_user(user_id=user_id)

        # Mock roles
        mock_get_roles.return_value = roles

        # Mock permission check
        mock_user_permission.return_value = TestMockUtils.mock_permission_result(
            has_permission
        )

        # Mock account not locked
        mock_is_locked.return_value = is_locked


def patch_auth_service():
    """Decorator to patch auth service for tests."""
    from unittest.mock import patch

    def decorator(func):
        @patch("src.services.auth_service.AuthService.verify_token")
        @patch("src.services.auth_service.AuthService.get_current_user")
        @patch("src.services.rbac_service.rbac_service.get_user_roles")
        @patch("src.services.rbac_service.rbac_service.user_has_permission")
        @patch("src.security.authorization.authorization_service.is_account_locked")
        def wrapper(
            self,
            mock_is_locked,
            mock_user_permission,
            mock_get_roles,
            mock_get_user,
            mock_verify_token,
            *args,
            **kwargs,
        ):
            # Set up default mocks
            TestMockUtils.setup_auth_mocks(
                mock_get_user, mock_get_roles, mock_user_permission, mock_is_locked
            )

            # Mock token verification
            mock_verify_token.return_value = {
                "sub": "test-user-id",
                "email": "test@example.com",
            }

            return func(self, *args, **kwargs)

        return wrapper

    return decorator


def patch_auth_service_admin():
    """Decorator to patch auth service for admin tests."""
    from unittest.mock import patch

    def decorator(func):
        @patch("src.services.auth_service.AuthService.verify_token")
        @patch("src.services.auth_service.AuthService.get_current_user")
        @patch("src.services.rbac_service.rbac_service.get_user_roles")
        @patch("src.services.rbac_service.rbac_service.user_has_permission")
        @patch("src.security.authorization.authorization_service.is_account_locked")
        def wrapper(
            self,
            mock_is_locked,
            mock_user_permission,
            mock_get_roles,
            mock_get_user,
            mock_verify_token,
            *args,
            **kwargs,
        ):
            # Set up admin mocks
            TestMockUtils.setup_auth_mocks(
                mock_get_user,
                mock_get_roles,
                mock_user_permission,
                mock_is_locked,
                user_id="admin-user-id",
                roles=[RoleType.ADMIN, RoleType.USER],
            )

            # Mock admin user
            mock_get_user.return_value = TestMockUtils.mock_user(
                user_id="admin-user-id", email="admin@example.com", is_admin=True
            )

            # Mock token verification
            mock_verify_token.return_value = {
                "sub": "admin-user-id",
                "email": "admin@example.com",
            }

            return func(self, *args, **kwargs)

        return wrapper

    return decorator
