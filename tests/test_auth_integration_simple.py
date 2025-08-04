"""
Simple integration tests for authentication functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from datetime import datetime, timezone
import os

# Set environment variables to avoid AWS connection issues
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_SECURITY_TOKEN"] = "testing"
os.environ["AWS_SESSION_TOKEN"] = "testing"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

from src.handlers.people_handler import app
from src.utils.jwt_utils import JWTManager


class TestAuthIntegrationSimple:
    """Simple integration tests for authentication."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    def test_health_endpoint_no_auth_required(self, client):
        """Test that health endpoint doesn't require authentication."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "people-register-api"

    def test_login_endpoint_exists(self, client):
        """Test that login endpoint exists and validates input."""
        # Test with missing data
        response = client.post("/auth/login", json={})
        assert response.status_code == 422  # Validation error

        # Test with invalid email format
        response = client.post(
            "/auth/login", json={"email": "invalid-email", "password": "password"}
        )
        assert response.status_code == 422  # Validation error

        # Test with valid format but will fail authentication (expected)
        response = client.post(
            "/auth/login", json={"email": "test@example.com", "password": "password"}
        )
        # This will fail with 401 or 500 due to database issues, but endpoint exists
        assert response.status_code in [401, 500]

    def test_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token."""
        response = client.get("/auth/me")
        # Should return 403 because FastAPI security dependency fails
        assert response.status_code == 403

    def test_protected_endpoint_with_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token."""
        headers = {"Authorization": "Bearer invalid.token.here"}
        response = client.get("/auth/me", headers=headers)
        assert response.status_code == 401

    def test_protected_endpoint_with_expired_token(self, client):
        """Test accessing protected endpoint with expired token."""
        # Create an expired token
        from datetime import datetime, timedelta, timezone
        import jwt
        from src.utils.jwt_utils import JWTConfig

        expired_payload = {
            "sub": "test-user-id",
            "exp": datetime.now(timezone.utc)
            - timedelta(hours=1),  # Expired 1 hour ago
            "type": "access",
        }
        expired_token = jwt.encode(
            expired_payload, JWTConfig.SECRET_KEY, algorithm=JWTConfig.ALGORITHM
        )
        headers = {"Authorization": f"Bearer {expired_token}"}

        response = client.get("/auth/me", headers=headers)
        assert response.status_code == 401

    def test_protected_endpoint_with_refresh_token(self, client):
        """Test accessing protected endpoint with refresh token (should fail)."""
        refresh_token = JWTManager.create_refresh_token("test-user-id")
        headers = {"Authorization": f"Bearer {refresh_token}"}

        response = client.get("/auth/me", headers=headers)
        assert response.status_code == 401

    def test_jwt_token_creation_and_validation(self):
        """Test JWT token creation and validation directly."""
        user_data = {
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
        }

        # Create tokens
        tokens = JWTManager.create_access_token("test-user-id", user_data)
        assert isinstance(tokens, str)

        # Validate token
        payload = JWTManager.verify_token(tokens)
        assert payload is not None
        assert payload["sub"] == "test-user-id"
        assert payload["email"] == "test@example.com"
        assert payload["first_name"] == "Test"
        assert payload["last_name"] == "User"
        assert payload["type"] == "access"

    def test_jwt_token_expiration_check(self):
        """Test JWT token expiration checking."""
        # Create a valid token
        user_data = {"email": "test@example.com"}
        token = JWTManager.create_access_token("test-user-id", user_data)

        # Should not be expired
        assert not JWTManager.is_token_expired(token)

        # Test with invalid token
        assert JWTManager.is_token_expired("invalid.token.here")

    def test_jwt_subject_extraction(self):
        """Test extracting subject from JWT token."""
        user_data = {"email": "test@example.com"}
        token = JWTManager.create_access_token("test-user-id", user_data)

        subject = JWTManager.get_token_subject(token)
        assert subject == "test-user-id"

        # Test with invalid token
        subject = JWTManager.get_token_subject("invalid.token.here")
        assert subject is None

    def test_people_endpoints_require_auth(self, client):
        """Test that people management endpoints require authentication."""
        # Test GET /people
        response = client.get("/people")
        assert response.status_code == 403  # No auth header

        # Test GET /people/{id}
        response = client.get("/people/test-id")
        assert response.status_code == 403  # No auth header

        # Test POST /people
        response = client.post(
            "/people",
            json={
                "firstName": "Test",
                "lastName": "User",
                "email": "test@example.com",
                "phone": "+1234567890",
                "dateOfBirth": "1990-01-01",
                "address": {
                    "street": "123 Main St",
                    "city": "Test City",
                    "state": "TS",
                    "postalCode": "12345",
                    "country": "Test Country",
                },
            },
        )
        assert response.status_code == 403  # No auth header

        # Test PUT /people/{id}
        response = client.put("/people/test-id", json={"firstName": "Updated"})
        assert response.status_code == 403  # No auth header

        # Test DELETE /people/{id}
        response = client.delete("/people/test-id")
        assert response.status_code == 403  # No auth header
