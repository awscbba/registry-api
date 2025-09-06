"""Tests for Auth Service - Critical authentication functionality"""

import pytest
from unittest.mock import Mock, patch
from src.services.auth_service import AuthService


class TestAuthService:
    """Test Auth Service functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.auth_service = AuthService()
        self.auth_service.people_repository = Mock()

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self):
        """Test successful user authentication"""
        # Arrange
        email = "user@example.com"
        password = "correct_password"

        mock_user = Mock()
        mock_user.id = "user123"
        mock_user.email = email
        mock_user.password_hash = "hashed_password"

        self.auth_service.people_repository.get_by_email.return_value = mock_user

        with (
            patch("src.utils.password_utils.verify_password", return_value=True),
            patch("src.utils.jwt_utils.generate_token", return_value="jwt_token_123"),
        ):

            # Act
            result = await self.auth_service.authenticate_user(email, password)

            # Assert
            assert result["success"] is True
            assert result["token"] == "jwt_token_123"
            assert result["user_id"] == "user123"

    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_email(self):
        """Test authentication with invalid email"""
        # Arrange
        email = "nonexistent@example.com"
        password = "password"

        self.auth_service.people_repository.get_by_email.return_value = None

        # Act & Assert
        with pytest.raises(Exception):
            await self.auth_service.authenticate_user(email, password)

    @pytest.mark.asyncio
    async def test_validate_token_success(self):
        """Test successful token validation"""
        # Arrange
        token = "valid_jwt_token"
        expected_payload = {"user_id": "user123", "email": "user@example.com"}

        with patch("src.utils.jwt_utils.decode_token", return_value=expected_payload):

            # Act
            result = await self.auth_service.validate_token(token)

            # Assert
            assert result["valid"] is True
            assert result["payload"] == expected_payload

    @pytest.mark.asyncio
    async def test_validate_token_invalid(self):
        """Test validation of invalid token"""
        # Arrange
        token = "invalid_jwt_token"

        with patch(
            "src.utils.jwt_utils.decode_token", side_effect=Exception("Invalid token")
        ):

            # Act
            result = await self.auth_service.validate_token(token)

            # Assert
            assert result["valid"] is False
            assert "error" in result

    def test_auth_service_initialization(self):
        """Test auth service initializes correctly"""
        # Act
        service = AuthService()

        # Assert
        assert hasattr(service, "people_repository")
