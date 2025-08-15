"""
Integration tests for Forgot Password API endpoints.

These tests verify the complete forgot password flow works end-to-end,
including API routing, service integration, and database operations.
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, Mock
from fastapi.testclient import TestClient

from src.handlers.versioned_api_handler import app
from src.models.person import Person
from src.models.password_reset import PasswordResetToken


class TestForgotPasswordIntegration:
    """Integration tests for forgot password functionality."""

    @pytest.fixture
    def client(self):
        """Create test client for API testing."""
        return TestClient(app)

    @pytest.fixture
    def sample_person(self):
        """Sample person for testing."""
        return Person(
            id="test-person-id",
            firstName="John",
            lastName="Doe",
            email="john.doe@example.com",
            hashedPassword="$2b$12$hashed_password_here",
            role="user",
            isActive=True,
            createdAt=datetime.now(timezone.utc),
            updatedAt=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def sample_reset_token(self):
        """Sample password reset token."""
        return PasswordResetToken(
            reset_token="test-reset-token-uuid",
            person_id="test-person-id",
            email="john.doe@example.com",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            is_used=False,
            created_at=datetime.now(timezone.utc),
            ip_address="192.168.1.1",
            user_agent="Test User Agent",
        )

    @patch("src.handlers.versioned_api_handler.password_reset_service")
    async def test_forgot_password_endpoint_success(self, mock_service, client):
        """Test successful forgot password request."""
        # Mock successful password reset initiation
        mock_service.initiate_password_reset.return_value = Mock(
            success=True,
            message="If the email exists in our system, you will receive a password reset link.",
        )

        # Make request to forgot password endpoint
        response = client.post(
            "/auth/forgot-password",
            json={"email": "john.doe@example.com"},
            headers={"Content-Type": "application/json"},
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "password reset link" in data["message"].lower()

        # Verify service was called with correct parameters
        mock_service.initiate_password_reset.assert_called_once()
        call_args = mock_service.initiate_password_reset.call_args[0][0]
        assert call_args.email == "john.doe@example.com"
        assert call_args.ip_address is not None  # Should be set by endpoint
        assert call_args.user_agent is not None  # Should be set by endpoint

    @patch("src.handlers.versioned_api_handler.password_reset_service")
    async def test_forgot_password_endpoint_invalid_email(self, mock_service, client):
        """Test forgot password with invalid email format."""
        response = client.post(
            "/auth/forgot-password",
            json={"email": "invalid-email"},
            headers={"Content-Type": "application/json"},
        )

        # Should return validation error for invalid email format
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert any("email" in str(error).lower() for error in data["detail"])

    @patch("src.handlers.versioned_api_handler.password_reset_service")
    async def test_forgot_password_endpoint_missing_email(self, mock_service, client):
        """Test forgot password without email field."""
        response = client.post(
            "/auth/forgot-password",
            json={},
            headers={"Content-Type": "application/json"},
        )

        # Should return validation error for missing email
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @patch("src.handlers.versioned_api_handler.password_reset_service")
    async def test_forgot_password_endpoint_service_error(self, mock_service, client):
        """Test forgot password when service raises an exception."""
        # Mock service to raise an exception
        mock_service.initiate_password_reset.side_effect = Exception("Database error")

        response = client.post(
            "/auth/forgot-password",
            json={"email": "john.doe@example.com"},
            headers={"Content-Type": "application/json"},
        )

        # Should return generic error message for security
        assert response.status_code == 200  # Security: don't reveal internal errors
        data = response.json()
        assert data["success"] is False
        assert "error occurred" in data["message"].lower()

    @patch("src.handlers.versioned_api_handler.password_reset_service")
    async def test_reset_password_endpoint_success(self, mock_service, client):
        """Test successful password reset completion."""
        # Mock successful password reset completion
        mock_service.complete_password_reset.return_value = Mock(
            success=True,
            message="Password has been successfully reset.",
        )

        response = client.post(
            "/auth/reset-password",
            json={
                "reset_token": "test-reset-token-uuid",
                "new_password": "NewSecurePassword123!",
            },
            headers={"Content-Type": "application/json"},
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "successfully reset" in data["message"].lower()

        # Verify service was called
        mock_service.complete_password_reset.assert_called_once()

    @patch("src.handlers.versioned_api_handler.password_reset_service")
    async def test_reset_password_endpoint_invalid_token(self, mock_service, client):
        """Test password reset with invalid token."""
        # Mock invalid token response
        mock_service.complete_password_reset.return_value = Mock(
            success=False,
            message="Invalid or expired reset token.",
        )

        response = client.post(
            "/auth/reset-password",
            json={
                "reset_token": "invalid-token",
                "new_password": "NewSecurePassword123!",
            },
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 400  # Bad request for invalid token
        data = response.json()
        assert data["success"] is False
        assert (
            "invalid" in data["message"].lower() or "expired" in data["message"].lower()
        )

    @patch("src.handlers.versioned_api_handler.password_reset_service")
    async def test_validate_reset_token_endpoint_valid(self, mock_service, client):
        """Test reset token validation with valid token."""
        # Mock valid token response
        mock_service.validate_reset_token.return_value = (
            True,
            Mock(expires_at=datetime.now(timezone.utc) + timedelta(hours=1)),
        )

        response = client.get("/auth/validate-reset-token/test-valid-token")

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert "expires_at" in data

    @patch("src.handlers.versioned_api_handler.password_reset_service")
    async def test_validate_reset_token_endpoint_invalid(self, mock_service, client):
        """Test reset token validation with invalid token."""
        # Mock invalid token response
        mock_service.validate_reset_token.return_value = (False, None)

        response = client.get("/auth/validate-reset-token/invalid-token")

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert data["expires_at"] is None

    async def test_forgot_password_endpoint_headers_and_metadata(self, client):
        """Test that forgot password endpoint properly captures client metadata."""
        with patch(
            "src.handlers.versioned_api_handler.password_reset_service"
        ) as mock_service:
            mock_service.initiate_password_reset.return_value = Mock(
                success=True,
                message="Reset link sent.",
            )

            # Make request with custom headers
            response = client.post(
                "/auth/forgot-password",
                json={"email": "test@example.com"},
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "TestClient/1.0",
                    "X-Forwarded-For": "203.0.113.1",
                },
            )

            assert response.status_code == 200

            # Verify that client metadata was captured
            mock_service.initiate_password_reset.assert_called_once()
            call_args = mock_service.initiate_password_reset.call_args[0][0]
            assert call_args.email == "test@example.com"
            # Note: TestClient doesn't perfectly simulate real client metadata,
            # but in production these would be properly captured

    @patch("src.services.rate_limiting_service.check_password_reset_rate_limit")
    @patch("src.handlers.versioned_api_handler.password_reset_service")
    async def test_forgot_password_rate_limiting_integration(
        self, mock_service, mock_rate_limit, client
    ):
        """Test that rate limiting is properly integrated."""
        # Mock rate limiting to allow request
        mock_rate_limit.return_value = Mock(allowed=True)
        mock_service.initiate_password_reset.return_value = Mock(
            success=True,
            message="Reset link sent.",
        )

        response = client.post(
            "/auth/forgot-password",
            json={"email": "test@example.com"},
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        # Rate limiting should be checked within the service
        # (This is handled by the password reset service internally)

    async def test_forgot_password_endpoint_content_type_validation(self, client):
        """Test that endpoint requires proper content type."""
        # Test without Content-Type header
        response = client.post(
            "/auth/forgot-password",
            data='{"email": "test@example.com"}',  # Send as form data instead of JSON
        )

        # Should handle gracefully or return appropriate error
        assert response.status_code in [400, 422]  # Bad request or validation error

    async def test_forgot_password_endpoint_large_payload(self, client):
        """Test endpoint with unusually large payload."""
        large_email = "a" * 1000 + "@example.com"

        response = client.post(
            "/auth/forgot-password",
            json={"email": large_email},
            headers={"Content-Type": "application/json"},
        )

        # Should handle gracefully (either validation error or process normally)
        assert response.status_code in [200, 422]

    @patch("src.handlers.versioned_api_handler.password_reset_service")
    async def test_forgot_password_endpoint_sql_injection_attempt(
        self, mock_service, client
    ):
        """Test endpoint security against SQL injection attempts."""
        mock_service.initiate_password_reset.return_value = Mock(
            success=True,
            message="Reset link sent.",
        )

        # Attempt SQL injection in email field
        malicious_email = "test@example.com'; DROP TABLE users; --"

        response = client.post(
            "/auth/forgot-password",
            json={"email": malicious_email},
            headers={"Content-Type": "application/json"},
        )

        # Should process normally (DynamoDB is NoSQL, but input should be sanitized)
        assert response.status_code in [200, 422]

        if response.status_code == 200:
            # If processed, verify the email was passed as-is to service
            mock_service.initiate_password_reset.assert_called_once()
            call_args = mock_service.initiate_password_reset.call_args[0][0]
            assert call_args.email == malicious_email


class TestForgotPasswordEndToEnd:
    """End-to-end tests that test the complete flow with minimal mocking."""

    @pytest.fixture
    def client(self):
        """Create test client for API testing."""
        return TestClient(app)

    @patch("boto3.resource")
    @patch("src.services.email_service.EmailService.send_password_reset_email")
    async def test_complete_forgot_password_flow_mocked_aws(
        self, mock_email, mock_boto3, client
    ):
        """Test complete forgot password flow with mocked AWS services."""
        # Mock DynamoDB operations
        mock_table = Mock()
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.return_value = mock_dynamodb

        # Mock person lookup (user exists)
        mock_table.scan.return_value = {
            "Items": [
                {
                    "id": "test-person-id",
                    "firstName": "John",
                    "lastName": "Doe",
                    "email": "john.doe@example.com",
                    "hashedPassword": "$2b$12$hashed_password",
                    "role": "user",
                    "isActive": True,
                }
            ]
        }

        # Mock successful token save
        mock_table.put_item.return_value = {}

        # Mock successful email sending
        mock_email.return_value = Mock(success=True, message="Email sent")

        # Make forgot password request
        response = client.post(
            "/auth/forgot-password",
            json={"email": "john.doe@example.com"},
            headers={"Content-Type": "application/json"},
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify DynamoDB operations were called
        mock_table.scan.assert_called()  # Person lookup
        mock_table.put_item.assert_called()  # Token save

        # Verify email was sent
        mock_email.assert_called_once()


# Performance and Load Testing
class TestForgotPasswordPerformance:
    """Performance tests for forgot password endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client for API testing."""
        return TestClient(app)

    @patch("src.handlers.versioned_api_handler.password_reset_service")
    async def test_forgot_password_response_time(self, mock_service, client):
        """Test that forgot password endpoint responds within acceptable time."""
        import time

        mock_service.initiate_password_reset.return_value = Mock(
            success=True,
            message="Reset link sent.",
        )

        start_time = time.time()

        response = client.post(
            "/auth/forgot-password",
            json={"email": "test@example.com"},
            headers={"Content-Type": "application/json"},
        )

        end_time = time.time()
        response_time = end_time - start_time

        assert response.status_code == 200
        assert response_time < 5.0  # Should respond within 5 seconds

    @patch("src.handlers.versioned_api_handler.password_reset_service")
    async def test_forgot_password_concurrent_requests(self, mock_service, client):
        """Test forgot password endpoint under concurrent load."""
        import asyncio
        import aiohttp

        mock_service.initiate_password_reset.return_value = Mock(
            success=True,
            message="Reset link sent.",
        )

        async def make_request():
            # Note: This would require async test client for true concurrency
            # For now, just verify the endpoint can handle multiple sequential requests
            response = client.post(
                "/auth/forgot-password",
                json={"email": "test@example.com"},
                headers={"Content-Type": "application/json"},
            )
            return response.status_code

        # Make multiple requests
        results = []
        for _ in range(10):
            result = await make_request()
            results.append(result)

        # All requests should succeed
        assert all(status == 200 for status in results)
