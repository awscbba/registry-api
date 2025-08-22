"""
Tests for JWT utilities.
"""

import pytest
import jwt
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from src.utils.jwt_utils import JWTManager, JWTConfig, create_tokens_for_user


class TestJWTManager:
    """Test cases for JWTManager."""

    def test_create_access_token(self):
        """Test creating an access token."""
        subject = "test-user-id"
        user_data = {
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
        }

        token = JWTManager.create_access_token(subject, user_data)

        # Verify token is a string
        assert isinstance(token, str)

        # Decode and verify token contents
        payload = jwt.decode(
            token, JWTConfig.SECRET_KEY, algorithms=[JWTConfig.ALGORITHM]
        )
        assert payload["sub"] == subject
        assert payload["type"] == "access"
        assert payload["email"] == user_data["email"]
        assert payload["first_name"] == user_data["first_name"]
        assert payload["last_name"] == user_data["last_name"]
        assert "exp" in payload
        assert "iat" in payload

    def test_create_access_token_with_custom_expiry(self):
        """Test creating an access token with custom expiry."""
        subject = "test-user-id"
        user_data = {"email": "test@example.com"}
        custom_expiry = timedelta(minutes=30)

        token = JWTManager.create_access_token(subject, user_data, custom_expiry)

        # Decode and verify expiry
        payload = jwt.decode(
            token, JWTConfig.SECRET_KEY, algorithms=[JWTConfig.ALGORITHM]
        )
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        expected_exp = datetime.now(timezone.utc) + custom_expiry

        # Allow 1 second tolerance for timing differences
        assert abs((exp_time - expected_exp).total_seconds()) < 1

    def test_create_refresh_token(self):
        """Test creating a refresh token."""
        subject = "test-user-id"

        token = JWTManager.create_refresh_token(subject)

        # Verify token is a string
        assert isinstance(token, str)

        # Decode and verify token contents
        payload = jwt.decode(
            token, JWTConfig.SECRET_KEY, algorithms=[JWTConfig.ALGORITHM]
        )
        assert payload["sub"] == subject
        assert payload["type"] == "refresh"
        assert "exp" in payload
        assert "iat" in payload

        # Verify expiry is set to 7 days
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        expected_exp = datetime.now(timezone.utc) + timedelta(days=7)

        # Allow 1 second tolerance for timing differences
        assert abs((exp_time - expected_exp).total_seconds()) < 1

    def test_verify_token_valid(self):
        """Test verifying a valid token."""
        subject = "test-user-id"
        user_data = {"email": "test@example.com"}

        token = JWTManager.create_access_token(subject, user_data)
        payload = JWTManager.verify_token(token)

        assert payload is not None
        assert payload["sub"] == subject
        assert payload["email"] == user_data["email"]
        assert payload["type"] == "access"

    def test_verify_token_expired(self):
        """Test verifying an expired token."""
        subject = "test-user-id"
        user_data = {"email": "test@example.com"}

        # Create token that expires immediately
        expired_token = JWTManager.create_access_token(
            subject, user_data, timedelta(seconds=-1)
        )

        payload = JWTManager.verify_token(expired_token)
        assert payload is None

    def test_verify_token_invalid(self):
        """Test verifying an invalid token."""
        invalid_token = "invalid.token.here"

        payload = JWTManager.verify_token(invalid_token)
        assert payload is None

    def test_verify_token_wrong_secret(self):
        """Test verifying a token with wrong secret."""
        # Create token with different secret
        payload = {
            "sub": "test-user-id",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "type": "access",
        }
        wrong_token = jwt.encode(payload, "wrong-secret", algorithm=JWTConfig.ALGORITHM)

        result = JWTManager.verify_token(wrong_token)
        assert result is None

    def test_get_token_subject_valid(self):
        """Test extracting subject from valid token."""
        subject = "test-user-id"
        user_data = {"email": "test@example.com"}

        token = JWTManager.create_access_token(subject, user_data)
        extracted_subject = JWTManager.get_token_subject(token)

        assert extracted_subject == subject

    def test_get_token_subject_invalid(self):
        """Test extracting subject from invalid token."""
        invalid_token = "invalid.token.here"

        subject = JWTManager.get_token_subject(invalid_token)
        assert subject is None

    def test_is_token_expired_valid(self):
        """Test checking if valid token is expired."""
        subject = "test-user-id"
        user_data = {"email": "test@example.com"}

        token = JWTManager.create_access_token(subject, user_data)
        is_expired = JWTManager.is_token_expired(token)

        assert is_expired is False

    def test_is_token_expired_expired(self):
        """Test checking if expired token is expired."""
        subject = "test-user-id"
        user_data = {"email": "test@example.com"}

        # Create token that expires immediately
        expired_token = JWTManager.create_access_token(
            subject, user_data, timedelta(seconds=-1)
        )

        is_expired = JWTManager.is_token_expired(expired_token)
        assert is_expired is True

    def test_is_token_expired_invalid(self):
        """Test checking if invalid token is expired."""
        invalid_token = "invalid.token.here"

        is_expired = JWTManager.is_token_expired(invalid_token)
        assert is_expired is True


class TestCreateTokensForUser:
    """Test cases for create_tokens_for_user convenience function."""

    def test_create_tokens_for_user(self):
        """Test creating both access and refresh tokens for a user."""
        user_id = "test-user-id"
        user_data = {
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
        }

        tokens = create_tokens_for_user(user_id, user_data)

        # Verify response structure
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "token_type" in tokens
        assert "expires_in" in tokens

        assert tokens["token_type"] == "bearer"
        assert tokens["expires_in"] == JWTConfig.ACCESS_TOKEN_EXPIRE_MINUTES * 60

        # Verify access token
        access_payload = JWTManager.verify_token(tokens["access_token"])
        assert access_payload is not None
        assert access_payload["sub"] == user_id
        assert access_payload["type"] == "access"
        assert access_payload["email"] == user_data["email"]

        # Verify refresh token
        refresh_payload = JWTManager.verify_token(tokens["refresh_token"])
        assert refresh_payload is not None
        assert refresh_payload["sub"] == user_id
        assert refresh_payload["type"] == "refresh"


class TestJWTConfig:
    """Test cases for JWT configuration."""

    def test_jwt_config_defaults(self):
        """Test JWT configuration default values."""
        assert JWTConfig.ALGORITHM == "HS256"
        assert JWTConfig.ACCESS_TOKEN_EXPIRE_MINUTES == 60
        assert JWTConfig.REFRESH_TOKEN_EXPIRE_DAYS == 7
        assert JWTConfig.SECRET_KEY is not None
        assert len(JWTConfig.SECRET_KEY) > 0

    @patch.dict("os.environ", {"JWT_SECRET": "test-secret-key"})
    def test_jwt_config_from_env(self):
        """Test JWT configuration from environment variable."""
        # Need to reload the module to pick up the environment variable
        import importlib
        from src.utils import jwt_utils

        importlib.reload(jwt_utils)

        assert jwt_utils.JWTConfig.SECRET_KEY == "test-secret-key"
