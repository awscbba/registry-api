"""
Test auth endpoints including password reset functionality.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from src.app import app


class TestAuthEndpoints:
    """Test authentication endpoints."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_forgot_password_endpoint_exists(self):
        """Test that forgot password endpoint exists and returns proper response."""
        response = self.client.post(
            "/auth/forgot-password", json={"email": "test@example.com"}
        )

        # Should return 200 even if email doesn't exist (security best practice)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message" in data["data"]
        assert "email" in data["data"]

    def test_validate_reset_token_endpoint_exists(self):
        """Test that validate reset token endpoint exists."""
        # Test with invalid token
        response = self.client.get("/auth/validate-reset-token/invalid-token")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "valid" in data["data"]
        assert data["data"]["valid"] is False

    def test_reset_password_endpoint_exists(self):
        """Test that reset password endpoint exists."""
        response = self.client.post(
            "/auth/reset-password",
            json={
                "token": "invalid-token",
                "newPassword": "newpassword123",
                "confirmPassword": "newpassword123",
            },
        )

        # Should return 400 for invalid token
        assert response.status_code == 400
        data = response.json()
        assert "Invalid or expired reset token" in data["detail"]

    def test_reset_password_validation(self):
        """Test password reset validation."""
        # Test password mismatch
        response = self.client.post(
            "/auth/reset-password",
            json={
                "token": "some-token",
                "newPassword": "password123",
                "confirmPassword": "different123",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert "do not match" in data["detail"]

    def test_existing_auth_endpoints_still_work(self):
        """Test that existing auth endpoints still work."""
        # Test login endpoint exists
        response = self.client.post(
            "/auth/login", json={"email": "test@example.com", "password": "password"}
        )
        # Should return 401 for invalid credentials (not 404)
        assert response.status_code == 401

        # Test validate endpoint exists (should return 401 without token)
        response = self.client.get("/auth/validate")
        assert response.status_code == 403  # No authorization header
