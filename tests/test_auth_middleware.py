"""
Tests for authentication middleware functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.middleware.auth_middleware import AuthMiddleware, get_current_user
from src.models.auth import AuthenticatedUser
from src.utils.jwt_utils import JWTManager


class TestAuthMiddleware:
    """Test cases for authentication middleware."""

    @pytest.fixture
    def auth_middleware(self):
        """Create an AuthMiddleware instance for testing."""
        return AuthMiddleware()

    @pytest.fixture
    def valid_token(self):
        """Create a valid JWT token for testing."""
        user_data = {
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
        }
        return JWTManager.create_access_token("test-user-id", user_data)

    @pytest.fixture
    def mock_person(self):
        """Create a mock person object."""
        person = Mock()
        person.id = "test-user-id"
        person.email = "test@example.com"
        person.first_name = "Test"
        person.last_name = "User"
        person.is_active = True
        person.is_admin = False  # Add missing is_admin attribute
        # Ensure account_locked_until is None or not present
        person.account_locked_until = None
        person.require_password_change = False
        person.last_login_at = None
        return person

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(
        self, auth_middleware, valid_token, mock_person
    ):
        """Test getting current user with valid token."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=valid_token
        )

        # Mock the database service
        with patch.object(
            auth_middleware.db_service, "get_person", new_callable=AsyncMock
        ) as mock_get_person:
            mock_get_person.return_value = mock_person

            user = await auth_middleware.get_current_user(credentials)

            assert isinstance(user, AuthenticatedUser)
            assert user.id == "test-user-id"
            assert user.email == "test@example.com"
            assert user.first_name == "Test"
            assert user.last_name == "User"
            assert user.is_active is True
            assert user.is_admin is False  # Check admin status

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, auth_middleware):
        """Test getting current user with invalid token."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid.token.here"
        )

        with pytest.raises(HTTPException) as exc_info:
            await auth_middleware.get_current_user(credentials)

        assert exc_info.value.status_code == 401
        assert "Invalid or expired token" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_expired_token(self, auth_middleware):
        """Test getting current user with expired token."""
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
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=expired_token
        )

        with pytest.raises(HTTPException) as exc_info:
            await auth_middleware.get_current_user(credentials)

        assert exc_info.value.status_code == 401
        assert "Invalid or expired token" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_wrong_token_type(self, auth_middleware):
        """Test getting current user with refresh token instead of access token."""
        refresh_token = JWTManager.create_refresh_token("test-user-id")
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=refresh_token
        )

        with pytest.raises(HTTPException) as exc_info:
            await auth_middleware.get_current_user(credentials)

        assert exc_info.value.status_code == 401
        assert "Invalid token type" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_user_not_found(self, auth_middleware, valid_token):
        """Test getting current user when user doesn't exist in database."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=valid_token
        )

        with patch.object(
            auth_middleware.db_service, "get_person", new_callable=AsyncMock
        ) as mock_get_person:
            mock_get_person.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                await auth_middleware.get_current_user(credentials)

            assert exc_info.value.status_code == 401
            assert "User not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_inactive_account(
        self, auth_middleware, valid_token, mock_person
    ):
        """Test getting current user with inactive account."""
        mock_person.is_active = False
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=valid_token
        )

        with patch.object(
            auth_middleware.db_service, "get_person", new_callable=AsyncMock
        ) as mock_get_person:
            mock_get_person.return_value = mock_person

            with pytest.raises(HTTPException) as exc_info:
                await auth_middleware.get_current_user(credentials)

            assert exc_info.value.status_code == 401
            assert "Account is deactivated" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_optional_user_valid_token(
        self, auth_middleware, valid_token, mock_person
    ):
        """Test getting optional user with valid token."""
        from fastapi import Request

        # Mock request with Authorization header
        request = Mock(spec=Request)
        request.headers = {"Authorization": f"Bearer {valid_token}"}

        with patch.object(
            auth_middleware.db_service, "get_person", new_callable=AsyncMock
        ) as mock_get_person:
            mock_get_person.return_value = mock_person

            user = await auth_middleware.get_optional_user(request)

            assert isinstance(user, AuthenticatedUser)
            assert user.id == "test-user-id"

    @pytest.mark.asyncio
    async def test_get_optional_user_no_token(self, auth_middleware):
        """Test getting optional user with no token."""
        from fastapi import Request

        # Mock request without Authorization header
        request = Mock(spec=Request)
        request.headers = {}

        user = await auth_middleware.get_optional_user(request)
        assert user is None

    @pytest.mark.asyncio
    async def test_get_optional_user_invalid_token(self, auth_middleware):
        """Test getting optional user with invalid token."""
        from fastapi import Request

        # Mock request with invalid Authorization header
        request = Mock(spec=Request)
        request.headers = {"Authorization": "Bearer invalid.token.here"}

        user = await auth_middleware.get_optional_user(request)
        assert user is None


class TestAuthDependencies:
    """Test authentication dependency functions."""

    @pytest.fixture
    def valid_token(self):
        """Create a valid JWT token for testing."""
        user_data = {
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
        }
        return JWTManager.create_access_token("test-user-id", user_data)

    @pytest.fixture
    def mock_person(self):
        """Create a mock person object."""
        person = Mock()
        person.id = "test-user-id"
        person.email = "test@example.com"
        person.first_name = "Test"
        person.last_name = "User"
        person.is_active = True
        person.is_admin = False  # Add missing is_admin attribute
        # Ensure account_locked_until is None or not present
        person.account_locked_until = None
        person.require_password_change = False
        person.last_login_at = None
        return person

    @pytest.mark.asyncio
    async def test_require_no_password_change_success(self, valid_token, mock_person):
        """Test require_no_password_change dependency with user who doesn't need password change."""
        from src.middleware.auth_middleware import require_no_password_change

        # Create authenticated user without password change requirement
        current_user = AuthenticatedUser(
            id="test-user-id",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            require_password_change=False,
        )

        # This should not raise an exception
        result = require_no_password_change(current_user)
        assert result == current_user

    @pytest.mark.asyncio
    async def test_require_no_password_change_blocked(self, valid_token, mock_person):
        """Test require_no_password_change dependency with user who needs password change."""
        from src.middleware.auth_middleware import require_no_password_change

        # Create authenticated user with password change requirement
        current_user = AuthenticatedUser(
            id="test-user-id",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            require_password_change=True,
        )

        with pytest.raises(HTTPException) as exc_info:
            require_no_password_change(current_user)

        assert exc_info.value.status_code == 403
        assert "Password change required" in exc_info.value.detail
