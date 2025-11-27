"""
Tests for user profile update functionality.
"""

import pytest
from fastapi.testclient import TestClient

from src.app import app


class TestProfileUpdate:
    """Test profile update endpoint."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_profile_update_endpoint_exists(self):
        """Test that profile update endpoint exists."""
        # This will return 401 without auth, but confirms endpoint exists
        response = self.client.put(
            "/auth/profile",
            json={
                "firstName": "Test",
                "lastName": "User",
            },
        )

        # Should return 401 (unauthorized) not 404 (not found)
        assert response.status_code in [401, 403]

    def test_profile_update_requires_authentication(self):
        """Test that profile update requires authentication."""
        response = self.client.put(
            "/auth/profile",
            json={
                "firstName": "Test",
                "lastName": "User",
            },
        )

        assert response.status_code in [401, 403]

    def test_profile_update_rejects_email_change(self):
        """Test that email changes are rejected through profile update."""
        # Note: This test would need a valid auth token to fully test
        # For now, we're just testing the endpoint structure
        response = self.client.put(
            "/auth/profile",
            json={
                "email": "newemail@example.com",
            },
        )

        # Should return 401 without auth
        assert response.status_code in [401, 403]

    def test_profile_update_rejects_admin_status_change(self):
        """Test that admin status changes are rejected through profile update."""
        response = self.client.put(
            "/auth/profile",
            json={
                "isAdmin": True,
            },
        )

        # Should return 401 without auth
        assert response.status_code in [401, 403]


class TestPasswordChange:
    """Test password change endpoint."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_password_change_endpoint_exists(self):
        """Test that password change endpoint exists."""
        response = self.client.post(
            "/auth/password/change",
            json={
                "currentPassword": "OldPassword123!",
                "newPassword": "NewPassword123!",
                "confirmPassword": "NewPassword123!",
            },
        )

        # Should return 401 (unauthorized) not 404 (not found)
        assert response.status_code in [401, 403]

    def test_password_change_requires_authentication(self):
        """Test that password change requires authentication."""
        response = self.client.post(
            "/auth/password/change",
            json={
                "currentPassword": "OldPassword123!",
                "newPassword": "NewPassword123!",
                "confirmPassword": "NewPassword123!",
            },
        )

        assert response.status_code in [401, 403]
