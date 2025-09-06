"""Tests for Auth Service - Critical service with 0% coverage"""

import pytest
from unittest.mock import Mock, patch
from src.services.auth_service import AuthService
from src.exceptions.base_exceptions import AuthenticationException


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
        with pytest.raises(AuthenticationException) as exc_info:
            await self.auth_service.authenticate_user(email, password)

        assert "Invalid credentials" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_password(self):
        """Test authentication with invalid password"""
        # Arrange
        email = "user@example.com"
        password = "wrong_password"

        mock_user = Mock()
        mock_user.email = email
        mock_user.password_hash = "hashed_password"

        self.auth_service.people_repository.get_by_email.return_value = mock_user

        with patch("src.utils.password_utils.verify_password", return_value=False):

            # Act & Assert
            with pytest.raises(AuthenticationException) as exc_info:
                await self.auth_service.authenticate_user(email, password)

            assert "Invalid credentials" in str(exc_info.value)

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

    @pytest.mark.asyncio
    async def test_refresh_token_success(self):
        """Test successful token refresh"""
        # Arrange
        old_token = "old_jwt_token"
        user_payload = {"user_id": "user123", "email": "user@example.com"}

        with (
            patch("src.utils.jwt_utils.decode_token", return_value=user_payload),
            patch("src.utils.jwt_utils.generate_token", return_value="new_jwt_token"),
        ):

            # Act
            result = await self.auth_service.refresh_token(old_token)

            # Assert
            assert result["success"] is True
            assert result["token"] == "new_jwt_token"

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self):
        """Test refresh with invalid token"""
        # Arrange
        old_token = "invalid_token"

        with patch(
            "src.utils.jwt_utils.decode_token", side_effect=Exception("Invalid token")
        ):

            # Act & Assert
            with pytest.raises(AuthenticationException):
                await self.auth_service.refresh_token(old_token)

    @pytest.mark.asyncio
    async def test_logout_user_success(self):
        """Test successful user logout"""
        # Arrange
        token = "jwt_token"

        with patch("src.utils.jwt_utils.blacklist_token") as mock_blacklist:

            # Act
            result = await self.auth_service.logout_user(token)

            # Assert
            assert result["success"] is True
            mock_blacklist.assert_called_once_with(token)

    def test_auth_service_initialization(self):
        """Test auth service initializes correctly"""
        # Act
        service = AuthService()

        # Assert
        assert hasattr(service, "people_repository")

    @pytest.mark.asyncio
    async def test_get_user_from_token_success(self):
        """Test getting user from valid token"""
        # Arrange
        token = "valid_token"
        user_payload = {"user_id": "user123", "email": "user@example.com"}

        mock_user = Mock()
        mock_user.id = "user123"
        mock_user.email = "user@example.com"

        self.auth_service.people_repository.get_by_id.return_value = mock_user

        with patch("src.utils.jwt_utils.decode_token", return_value=user_payload):

            # Act
            result = await self.auth_service.get_user_from_token(token)

            # Assert
            assert result.id == "user123"
            assert result.email == "user@example.com"

    @pytest.mark.asyncio
    async def test_authentication_error_handling(self):
        """Test error handling in authentication"""
        # Arrange
        email = "user@example.com"
        password = "password"

        self.auth_service.people_repository.get_by_email.side_effect = Exception(
            "Database error"
        )

        # Act & Assert
        with pytest.raises(AuthenticationException):
            await self.auth_service.authenticate_user(email, password)
