"""
Tests for authentication service.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.auth_service import AuthService
from src.models.auth import LoginRequest, AccountLockout
from src.models.person import Person, Address


@pytest_asyncio.fixture
async def auth_service():
    """Create an AuthService instance for testing."""
    service = AuthService()
    # Initialize the service to set up dependencies
    await service.initialize()
    return service


@pytest.fixture
def sample_person():
    """Create a sample person for testing."""
    return Person(
        id="test-person-id",
        firstName="John",
        lastName="Doe",
        email="john.doe@example.com",
        phone="+1234567890",
        dateOfBirth="1990-01-01",
        address=Address(
            street="123 Main St",
            city="Anytown",
            state="CA",
            postalCode="12345",
            country="USA",
        ),
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_person_with_password(sample_person):
    """Create a sample person with password for testing."""
    # Generate a proper bcrypt hash of "TestPassword123!"
    import bcrypt

    password = "TestPassword123!"
    sample_person.password_hash = bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")
    sample_person.require_password_change = False
    sample_person.is_active = True
    return sample_person


class TestAuthService:
    """Test cases for AuthService."""

    @pytest.mark.asyncio
    async def test_authenticate_user_success(
        self, auth_service, sample_person_with_password
    ):
        """Test successful user authentication."""
        login_request = LoginRequest(
            email="john.doe@example.com", password="TestPassword123!"
        )

        # Mock the database service methods
        with (
            patch.object(
                auth_service.db_service, "get_person_by_email", new_callable=AsyncMock
            ) as mock_get_person,
            patch.object(
                auth_service.db_service, "get_account_lockout", new_callable=AsyncMock
            ) as mock_get_lockout,
            patch.object(
                auth_service.db_service, "save_account_lockout", new_callable=AsyncMock
            ) as mock_save_lockout,
            patch.object(
                auth_service.db_service, "clear_account_lockout", new_callable=AsyncMock
            ) as mock_clear_lockout,
            patch.object(
                auth_service.db_service, "update_last_login", new_callable=AsyncMock
            ) as mock_update_login,
            patch.object(
                auth_service.db_service, "log_security_event", new_callable=AsyncMock
            ) as mock_log_event,
        ):

            mock_get_person.return_value = sample_person_with_password
            mock_get_lockout.return_value = None  # No lockout

            success, response, error = await auth_service.authenticate_user(
                login_request, "192.168.1.1", "test-agent"
            )

            assert success is True
            assert response is not None
            assert error is None
            assert response.access_token is not None
            assert response.refresh_token is not None
            assert response.user["email"] == "john.doe@example.com"
            assert response.require_password_change is False

            # Verify method calls
            mock_get_person.assert_called_once_with("john.doe@example.com")
            mock_get_lockout.assert_called_once_with("test-person-id")
            mock_clear_lockout.assert_called_once_with("test-person-id")
            mock_update_login.assert_called_once()

            # Verify security event logging
            mock_log_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_email(self, auth_service):
        """Test authentication with invalid email."""
        login_request = LoginRequest(
            email="nonexistent@example.com", password="TestPassword123!"
        )

        with (
            patch.object(
                auth_service.db_service, "get_person_by_email", new_callable=AsyncMock
            ) as mock_get_person,
            patch.object(
                auth_service, "_log_security_event", new_callable=AsyncMock
            ) as mock_log_event,
        ):

            mock_get_person.return_value = None

            success, response, error = await auth_service.authenticate_user(
                login_request, "192.168.1.1", "test-agent"
            )

            assert success is False
            assert response is None
            assert error == "Invalid email or password"

            # Verify security event logging
            mock_log_event.assert_called_once()
            log_call = mock_log_event.call_args[1]
            assert log_call["action"] == "LOGIN_FAILED"
            assert log_call["success"] is False
            assert log_call["details"]["reason"] == "user_not_found"

    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_password(
        self, auth_service, sample_person_with_password
    ):
        """Test authentication with invalid password."""
        login_request = LoginRequest(
            email="john.doe@example.com", password="WrongPassword123!"
        )

        with (
            patch.object(
                auth_service.db_service, "get_person_by_email", new_callable=AsyncMock
            ) as mock_get_person,
            patch.object(
                auth_service, "_check_account_lockout", new_callable=AsyncMock
            ) as mock_check_lockout,
            patch.object(
                auth_service, "_record_failed_attempt", new_callable=AsyncMock
            ) as mock_record_failed,
            patch.object(
                auth_service, "_log_security_event", new_callable=AsyncMock
            ) as mock_log_event,
        ):

            mock_get_person.return_value = sample_person_with_password
            mock_check_lockout.return_value = (False, None)

            success, response, error = await auth_service.authenticate_user(
                login_request, "192.168.1.1", "test-agent"
            )

            assert success is False
            assert response is None
            assert error == "Invalid email or password"

            # Verify failed attempt was recorded
            mock_record_failed.assert_called_once_with("test-person-id", "192.168.1.1")

            # Verify security event logging
            mock_log_event.assert_called_once()
            log_call = mock_log_event.call_args[1]
            assert log_call["action"] == "LOGIN_FAILED"
            assert log_call["success"] is False
            assert log_call["details"]["reason"] == "invalid_password"

    @pytest.mark.asyncio
    async def test_authenticate_user_account_locked(
        self, auth_service, sample_person_with_password
    ):
        """Test authentication with locked account."""
        login_request = LoginRequest(
            email="john.doe@example.com", password="TestPassword123!"
        )

        locked_until = datetime.now(timezone.utc) + timedelta(minutes=10)
        lockout_info = AccountLockout(
            person_id="test-person-id",
            failed_attempts=5,
            locked_until=locked_until,
            last_attempt_at=datetime.now(timezone.utc),
            ip_addresses=["192.168.1.1"],
        )

        with (
            patch.object(
                auth_service.db_service, "get_person_by_email", new_callable=AsyncMock
            ) as mock_get_person,
            patch.object(
                auth_service, "_check_account_lockout", new_callable=AsyncMock
            ) as mock_check_lockout,
            patch.object(
                auth_service, "_log_security_event", new_callable=AsyncMock
            ) as mock_log_event,
        ):

            mock_get_person.return_value = sample_person_with_password
            mock_check_lockout.return_value = (True, lockout_info)

            success, response, error = await auth_service.authenticate_user(
                login_request, "192.168.1.1", "test-agent"
            )

            assert success is False
            assert response is None
            assert "Account is temporarily locked" in error

            # Verify security event logging
            mock_log_event.assert_called_once()
            log_call = mock_log_event.call_args[1]
            assert log_call["action"] == "LOGIN_FAILED"
            assert log_call["success"] is False
            assert log_call["details"]["reason"] == "account_locked"

    @pytest.mark.asyncio
    async def test_authenticate_user_no_password_set(self, auth_service, sample_person):
        """Test authentication when user has no password set."""
        login_request = LoginRequest(
            email="john.doe@example.com", password="TestPassword123!"
        )

        with (
            patch.object(
                auth_service.db_service, "get_person_by_email", new_callable=AsyncMock
            ) as mock_get_person,
            patch.object(
                auth_service, "_check_account_lockout", new_callable=AsyncMock
            ) as mock_check_lockout,
            patch.object(
                auth_service, "_log_security_event", new_callable=AsyncMock
            ) as mock_log_event,
        ):

            mock_get_person.return_value = sample_person  # No password_hash attribute
            mock_check_lockout.return_value = (False, None)

            success, response, error = await auth_service.authenticate_user(
                login_request, "192.168.1.1", "test-agent"
            )

            assert success is False
            assert response is None
            assert error == "Account not set up for login"

            # Verify security event logging
            mock_log_event.assert_called_once()
            log_call = mock_log_event.call_args[1]
            assert log_call["action"] == "LOGIN_FAILED"
            assert log_call["success"] is False
            assert log_call["details"]["reason"] == "no_password_set"

    @pytest.mark.asyncio
    async def test_authenticate_user_inactive_account(
        self, auth_service, sample_person_with_password
    ):
        """Test authentication with inactive account."""
        login_request = LoginRequest(
            email="john.doe@example.com", password="TestPassword123!"
        )

        sample_person_with_password.is_active = False

        with (
            patch.object(
                auth_service.db_service, "get_person_by_email", new_callable=AsyncMock
            ) as mock_get_person,
            patch.object(
                auth_service, "_check_account_lockout", new_callable=AsyncMock
            ) as mock_check_lockout,
            patch.object(
                auth_service, "_log_security_event", new_callable=AsyncMock
            ) as mock_log_event,
        ):

            mock_get_person.return_value = sample_person_with_password
            mock_check_lockout.return_value = (False, None)

            success, response, error = await auth_service.authenticate_user(
                login_request, "192.168.1.1", "test-agent"
            )

            assert success is False
            assert response is None
            assert error == "Account is deactivated"

            # Verify security event logging
            mock_log_event.assert_called_once()
            log_call = mock_log_event.call_args[1]
            assert log_call["action"] == "LOGIN_FAILED"
            assert log_call["success"] is False
            assert log_call["details"]["reason"] == "account_inactive"

    @pytest.mark.asyncio
    async def test_record_failed_attempt_triggers_lockout(self, auth_service):
        """Test that recording failed attempts triggers account lockout."""
        person_id = "test-person-id"
        ip_address = "192.168.1.1"

        # Mock existing lockout info with 4 failed attempts
        existing_lockout = AccountLockout(
            person_id=person_id,
            failed_attempts=4,
            last_attempt_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            ip_addresses=[ip_address],
        )

        with (
            patch.object(
                auth_service.db_service, "get_account_lockout", new_callable=AsyncMock
            ) as mock_get_lockout,
            patch.object(
                auth_service.db_service, "save_account_lockout", new_callable=AsyncMock
            ) as mock_save_lockout,
            patch.object(
                auth_service, "_log_security_event", new_callable=AsyncMock
            ) as mock_log_event,
        ):

            mock_get_lockout.return_value = existing_lockout

            await auth_service._record_failed_attempt(person_id, ip_address)

            # Verify lockout was saved with 5 attempts and locked_until set
            mock_save_lockout.assert_called_once()
            saved_lockout = mock_save_lockout.call_args[0][0]
            assert saved_lockout.failed_attempts == 5
            assert saved_lockout.locked_until is not None
            assert saved_lockout.locked_until > datetime.now(timezone.utc)

            # Verify account lockout event was logged
            mock_log_event.assert_called_once()
            log_call = mock_log_event.call_args[1]
            assert log_call["action"] == "ACCOUNT_LOCKED"
            assert log_call["success"] is True

    @pytest.mark.asyncio
    async def test_unlock_account(self, auth_service):
        """Test manual account unlock functionality."""
        person_id = "test-person-id"
        admin_user_id = "admin-user-id"

        with (
            patch.object(
                auth_service.db_service, "clear_account_lockout", new_callable=AsyncMock
            ) as mock_clear_lockout,
            patch.object(
                auth_service, "_log_security_event", new_callable=AsyncMock
            ) as mock_log_event,
        ):

            result = await auth_service.unlock_account(person_id, admin_user_id)

            assert result is True
            mock_clear_lockout.assert_called_once_with(person_id)

            # Verify unlock event was logged
            mock_log_event.assert_called_once()
            log_call = mock_log_event.call_args[1]
            assert log_call["action"] == "ACCOUNT_UNLOCKED"
            assert log_call["success"] is True
            assert log_call["details"]["unlocked_by"] == admin_user_id
