"""
Test configuration and fixtures.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.app import app
from src.models.rbac import RoleType

# Set testing environment variable
os.environ["TESTING"] = "true"


@pytest.fixture(autouse=True)
def mock_auth_for_tests():
    """Automatically mock authentication for all tests."""

    # Mock user object
    mock_user = MagicMock()
    mock_user.id = "test-user-id"
    mock_user.email = "test@example.com"
    mock_user.firstName = "Test"
    mock_user.lastName = "User"
    mock_user.isAdmin = False
    mock_user.isActive = True

    # Mock permission result
    mock_permission_result = MagicMock()
    mock_permission_result.has_permission = True
    mock_permission_result.reason = ""

    with (
        patch(
            "src.services.auth_service.AuthService.get_current_user",
            return_value=mock_user,
        ),
        patch(
            "src.services.rbac_service.rbac_service.get_user_roles",
            return_value=[RoleType.USER],
        ),
        patch(
            "src.services.rbac_service.rbac_service.user_has_permission",
            return_value=mock_permission_result,
        ),
        patch(
            "src.security.authorization.authorization_service.is_account_locked",
            return_value=False,
        ),
        patch(
            "src.services.auth_service.AuthService.verify_token",
            return_value={"sub": "test-user-id", "email": "test@example.com"},
        ),
    ):
        yield


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Authentication headers for tests."""
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def admin_headers():
    """Admin authentication headers for tests."""
    return {"Authorization": "Bearer admin-test-token"}


@pytest.fixture(autouse=True)
def mock_admin_for_admin_tests():
    """Mock admin user for admin tests."""

    # Mock admin user object
    mock_admin_user = MagicMock()
    mock_admin_user.id = "admin-user-id"
    mock_admin_user.email = "admin@example.com"
    mock_admin_user.firstName = "Admin"
    mock_admin_user.lastName = "User"
    mock_admin_user.isAdmin = True
    mock_admin_user.isActive = True

    # This will be used when admin headers are detected
    def get_user_side_effect(token):
        if token == "admin-test-token":
            return mock_admin_user
        else:
            mock_user = MagicMock()
            mock_user.id = "test-user-id"
            mock_user.email = "test@example.com"
            mock_user.firstName = "Test"
            mock_user.lastName = "User"
            mock_user.isAdmin = False
            mock_user.isActive = True
            return mock_user

    def get_roles_side_effect(user_id):
        if user_id == "admin-user-id":
            return [RoleType.ADMIN, RoleType.USER]
        else:
            return [RoleType.USER]

    with (
        patch(
            "src.services.auth_service.AuthService.get_current_user",
            side_effect=get_user_side_effect,
        ),
        patch(
            "src.services.rbac_service.rbac_service.get_user_roles",
            side_effect=get_roles_side_effect,
        ),
    ):
        yield
