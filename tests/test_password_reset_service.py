"""
Tests for Password Reset Service

Tests password reset functionality including token generation,
validation, email sending, and password updates.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
import uuid

from src.services.password_reset_service import PasswordResetService
from src.models.password_reset import (
    PasswordResetRequest,
    PasswordResetValidation,
    PasswordResetResponse,
    PasswordResetToken,
)
from src.models.person import Person


class TestPasswordResetService:
    """Test cases for PasswordResetService."""

    @pytest.fixture
    def mock_db_service(self):
        """Mock database service."""
        mock = AsyncMock()
        return mock

    @pytest.fixture
    def mock_email_service(self):
        """Mock email service."""
        mock = AsyncMock()
        return mock

    @pytest.fixture
    def password_reset_service(self, mock_db_service, mock_email_service):
        """Create password reset service with mocked dependencies."""
        return PasswordResetService(mock_db_service, mock_email_service)

    @pytest.fixture
    def sample_person(self):
        """Sample person for testing."""
        return Person(
            id="test-person-id",
            firstName="John",
            lastName="Doe",
            email="john.doe@example.com",
            phone="1234567890",
            dateOfBirth="1990-01-01",
            address={
                "street": "123 Main St",
                "city": "Test City",
                "state": "Test State",
                "postalCode": "12345",
                "country": "Test Country",
            },
            createdAt=datetime.now(timezone.utc),
            updatedAt=datetime.now(timezone.utc),
            is_active=True,
        )

    @pytest.mark.asyncio
    async def test_initiate_password_reset_success(
        self, password_reset_service, mock_db_service, mock_email_service, sample_person
    ):
        """Test successful password reset initiation."""
        # Setup
        request = PasswordResetRequest(
            email="john.doe@example.com",
            ip_address="192.168.1.1",
            user_agent="Test Browser",
        )

        mock_db_service.get_person_by_email.return_value = sample_person
        mock_email_service.send_password_reset_email.return_value = Mock(success=True)

        # Mock rate limiting
        with patch(
            "src.services.password_reset_service.check_password_reset_rate_limit"
        ) as mock_rate_limit:
            mock_rate_limit.return_value = Mock(allowed=True)

            # Mock token saving
            with patch.object(password_reset_service, "_save_reset_token") as mock_save:
                # Mock the db_service to return a successful response with person data
                mock_db_service.get_person_by_email.return_value = {
                    "success": True,
                    "data": {
                        "id": "test-id",
                        "email": "john.doe@example.com",
                        "firstName": "John",
                        "first_name": "John",
                        "is_active": True,
                    },
                }

                # Execute
                result = await password_reset_service.initiate_password_reset(request)

                # Verify
                assert result.success is True
                assert "you will receive a password reset link" in result.message
                mock_db_service.get_person_by_email.assert_called_once_with(
                    "john.doe@example.com"
                )
                mock_email_service.send_password_reset_email.assert_called_once()
                mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_initiate_password_reset_nonexistent_email(
        self, password_reset_service, mock_db_service, mock_email_service
    ):
        """Test password reset for non-existent email (should still return success for security)."""
        # Setup
        request = PasswordResetRequest(email="nonexistent@example.com")
        mock_db_service.get_person_by_email.return_value = None

        # Mock rate limiting
        with patch(
            "src.services.password_reset_service.check_password_reset_rate_limit"
        ) as mock_rate_limit:
            mock_rate_limit.return_value = Mock(allowed=True)

            # Execute
            result = await password_reset_service.initiate_password_reset(request)

            # Verify - should return success for security (don't reveal if email exists)
            assert result.success is True
            assert "you will receive a password reset link" in result.message
            mock_email_service.send_password_reset_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_initiate_password_reset_rate_limited(
        self, password_reset_service, mock_db_service
    ):
        """Test password reset when rate limited."""
        # Setup
        request = PasswordResetRequest(email="test@example.com")

        # Mock rate limiting - blocked
        with patch(
            "src.services.password_reset_service.check_password_reset_rate_limit"
        ) as mock_rate_limit:
            mock_rate_limit.return_value = Mock(allowed=False, retry_after=300)

            # Execute
            result = await password_reset_service.initiate_password_reset(request)

            # Verify
            assert result.success is False
            assert "Too many password reset attempts" in result.message
            mock_db_service.get_person_by_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_reset_token_valid(self, password_reset_service):
        """Test validation of valid reset token."""
        # Setup
        token = "test-token-123"
        token_record = PasswordResetToken(
            reset_token=token,
            person_id="test-person-id",
            email="test@example.com",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            is_used=False,
        )

        with patch.object(password_reset_service, "_get_reset_token") as mock_get:
            mock_get.return_value = token_record

            # Execute
            is_valid, returned_token = (
                await password_reset_service.validate_reset_token(token)
            )

            # Verify
            assert is_valid is True
            assert returned_token == token_record

    @pytest.mark.asyncio
    async def test_validate_reset_token_expired(self, password_reset_service):
        """Test validation of expired reset token."""
        # Setup
        token = "expired-token-123"
        token_record = PasswordResetToken(
            reset_token=token,
            person_id="test-person-id",
            email="test@example.com",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),  # Expired
            is_used=False,
        )

        with patch.object(password_reset_service, "_get_reset_token") as mock_get:
            mock_get.return_value = token_record

            # Execute
            is_valid, returned_token = (
                await password_reset_service.validate_reset_token(token)
            )

            # Verify
            assert is_valid is False
            assert returned_token is None

    @pytest.mark.asyncio
    async def test_validate_reset_token_already_used(self, password_reset_service):
        """Test validation of already used reset token."""
        # Setup
        token = "used-token-123"
        token_record = PasswordResetToken(
            reset_token=token,
            person_id="test-person-id",
            email="test@example.com",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            is_used=True,  # Already used
        )

        with patch.object(password_reset_service, "_get_reset_token") as mock_get:
            mock_get.return_value = token_record

            # Execute
            is_valid, returned_token = (
                await password_reset_service.validate_reset_token(token)
            )

            # Verify
            assert is_valid is False
            assert returned_token is None

    @pytest.mark.asyncio
    async def test_complete_password_reset_success(
        self, password_reset_service, mock_db_service, sample_person
    ):
        """Test successful password reset completion."""
        # Setup
        validation = PasswordResetValidation(
            reset_token="valid-token-123",
            new_password="newpassword123",
        )

        token_record = PasswordResetToken(
            reset_token="valid-token-123",
            person_id="test-person-id",
            email="test@example.com",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            is_used=False,
        )

        mock_db_service.get_person.return_value = sample_person

        with patch.object(
            password_reset_service, "validate_reset_token"
        ) as mock_validate:
            mock_validate.return_value = (True, token_record)

            with patch.object(
                password_reset_service, "_mark_token_used"
            ) as mock_mark_used:
                # Execute
                result = await password_reset_service.complete_password_reset(
                    validation
                )

                # Verify
                assert result.success is True
                assert "Password has been reset successfully" in result.message
                mock_db_service.update_person.assert_called_once()
                mock_mark_used.assert_called_once_with("valid-token-123")

    @pytest.mark.asyncio
    async def test_complete_password_reset_invalid_token(self, password_reset_service):
        """Test password reset with invalid token."""
        # Setup
        validation = PasswordResetValidation(
            reset_token="invalid-token-123",
            new_password="newpassword123",
        )

        with patch.object(
            password_reset_service, "validate_reset_token"
        ) as mock_validate:
            mock_validate.return_value = (False, None)

            # Execute
            result = await password_reset_service.complete_password_reset(validation)

            # Verify
            assert result.success is False
            assert "Invalid or expired reset token" in result.message
            assert result.token_valid is False

    @pytest.mark.asyncio
    async def test_complete_password_reset_weak_password(self, password_reset_service):
        """Test password reset with weak password."""
        # Setup
        validation = PasswordResetValidation(
            reset_token="valid-token-123",
            new_password="weak",  # Too short
        )

        token_record = PasswordResetToken(
            reset_token="valid-token-123",
            person_id="test-person-id",
            email="test@example.com",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            is_used=False,
        )

        with patch.object(
            password_reset_service, "validate_reset_token"
        ) as mock_validate:
            mock_validate.return_value = (True, token_record)

            # Execute
            result = await password_reset_service.complete_password_reset(validation)

            # Verify
            assert result.success is False
            assert "Password must be at least 8 characters" in result.message
            assert result.token_valid is True

    def test_password_reset_models(self):
        """Test password reset model validation."""
        # Test PasswordResetRequest
        request = PasswordResetRequest(email="test@example.com")
        assert request.email == "test@example.com"

        # Test PasswordResetValidation
        validation = PasswordResetValidation(
            reset_token="token123",
            new_password="password123",
        )
        assert validation.reset_token == "token123"
        assert validation.new_password == "password123"

        # Test PasswordResetResponse
        response = PasswordResetResponse(
            success=True,
            message="Success",
            token_valid=True,
        )
        assert response.success is True
        assert response.message == "Success"
        assert response.token_valid is True
