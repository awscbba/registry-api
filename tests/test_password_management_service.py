"""
Comprehensive tests for PasswordManagementService.
"""

import pytest
import sys
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone
import asyncio

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from src.models.person import (
    Person,
    PasswordUpdateRequest,
    PasswordUpdateResponse,
    Address,
)
from src.services.password_management_service import PasswordManagementService
from src.utils.password_utils import PasswordHasher


class TestPasswordManagementService:
    """Test suite for PasswordManagementService."""

    @pytest.fixture
    def mock_person(self):
        """Create a mock person for testing."""
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
            password_hash=PasswordHasher.hash_password("CurrentPassword123!"),
            password_history=[],
        )

    @pytest.fixture
    def password_service(self):
        """Create PasswordManagementService instance with mocked dependencies."""
        with patch(
            "src.services.password_management_service.DynamoDBService"
        ) as mock_db_class:
            mock_db = Mock()
            mock_db.get_person = AsyncMock()
            mock_db.log_security_event = AsyncMock()
            mock_db.table = Mock()
            mock_db.table.update_item = Mock()
            mock_db_class.return_value = mock_db

            service = PasswordManagementService()
            service.mock_db = mock_db  # Store reference for test access
            return service

    @pytest.mark.asyncio
    async def test_successful_password_update(self, password_service, mock_person):
        """Test successful password update flow."""
        # Setup
        password_service.mock_db.get_person.return_value = mock_person

        password_request = PasswordUpdateRequest(
            current_password="CurrentPassword123!",
            new_password="NewPassword456@",
            confirm_password="NewPassword456@",
        )

        # Execute
        success, response, error = await password_service.update_password(
            person_id="test-person-id",
            password_request=password_request,
            ip_address="127.0.0.1",
            user_agent="test-agent",
        )

        # Verify
        assert success is True
        assert response.success is True
        assert response.require_reauth is True
        assert error is None
        assert "Password updated successfully" in response.message

        # Verify database interactions
        password_service.mock_db.get_person.assert_called_once_with("test-person-id")
        password_service.mock_db.table.update_item.assert_called_once()
        password_service.mock_db.log_security_event.assert_called()

    @pytest.mark.asyncio
    async def test_invalid_current_password(self, password_service, mock_person):
        """Test password update with invalid current password."""
        # Setup
        password_service.mock_db.get_person.return_value = mock_person

        password_request = PasswordUpdateRequest(
            current_password="WrongPassword123!",
            new_password="NewPassword456@",
            confirm_password="NewPassword456@",
        )

        # Execute
        success, response, error = await password_service.update_password(
            person_id="test-person-id", password_request=password_request
        )

        # Verify
        assert success is False
        assert response.success is False
        assert "Current password is incorrect" in response.message
        assert error == "Current password is incorrect"

        # Verify no password update occurred
        password_service.mock_db.table.update_item.assert_not_called()

    @pytest.mark.asyncio
    async def test_weak_new_password(self, password_service, mock_person):
        """Test password update with weak new password."""
        # Setup
        password_service.mock_db.get_person.return_value = mock_person

        password_request = PasswordUpdateRequest(
            current_password="CurrentPassword123!",
            new_password="weakpass",  # Passes length but fails complexity
            confirm_password="weakpass",
        )

        # Execute
        success, response, error = await password_service.update_password(
            person_id="test-person-id", password_request=password_request
        )

        # Verify
        assert success is False
        assert response.success is False
        assert "Password must contain" in response.message

        # Verify no password update occurred
        password_service.mock_db.table.update_item.assert_not_called()

    @pytest.mark.asyncio
    async def test_password_reuse_prevention(self, password_service, mock_person):
        """Test password reuse prevention."""
        # Setup - person with password history
        old_password_hash = PasswordHasher.hash_password("OldPassword123!")
        mock_person.password_history = [old_password_hash]
        password_service.mock_db.get_person.return_value = mock_person

        password_request = PasswordUpdateRequest(
            current_password="CurrentPassword123!",
            new_password="OldPassword123!",  # Reusing old password
            confirm_password="OldPassword123!",
        )

        # Execute
        success, response, error = await password_service.update_password(
            person_id="test-person-id", password_request=password_request
        )

        # Verify
        assert success is False
        assert response.success is False
        assert "Cannot reuse any of the last" in response.message

        # Verify no password update occurred
        password_service.mock_db.table.update_item.assert_not_called()

    @pytest.mark.asyncio
    async def test_person_not_found(self, password_service):
        """Test password update when person doesn't exist."""
        # Setup
        password_service.mock_db.get_person.return_value = None

        password_request = PasswordUpdateRequest(
            current_password="CurrentPassword123!",
            new_password="NewPassword456@",
            confirm_password="NewPassword456@",
        )

        # Execute
        success, response, error = await password_service.update_password(
            person_id="nonexistent-id", password_request=password_request
        )

        # Verify
        assert success is False
        assert response.success is False
        assert "Person not found" in response.message
        assert error == "Person not found"

    @pytest.mark.asyncio
    async def test_validate_password_change_request_success(
        self, password_service, mock_person
    ):
        """Test successful password change request validation."""
        # Setup
        password_service.mock_db.get_person.return_value = mock_person

        # Execute
        is_valid, error_msg = await password_service.validate_password_change_request(
            person_id="test-person-id", current_password="CurrentPassword123!"
        )

        # Verify
        assert is_valid is True
        assert error_msg is None

    @pytest.mark.asyncio
    async def test_validate_password_change_request_invalid(
        self, password_service, mock_person
    ):
        """Test password change request validation with invalid password."""
        # Setup
        password_service.mock_db.get_person.return_value = mock_person

        # Execute
        is_valid, error_msg = await password_service.validate_password_change_request(
            person_id="test-person-id", current_password="WrongPassword123!"
        )

        # Verify
        assert is_valid is False
        assert error_msg == "Current password is incorrect"

    @pytest.mark.asyncio
    async def test_force_password_change(self, password_service, mock_person):
        """Test admin force password change functionality."""
        # Setup
        password_service.mock_db.get_person.return_value = mock_person

        # Execute
        success, error_msg = await password_service.force_password_change(
            person_id="test-person-id", admin_user_id="admin-id", ip_address="127.0.0.1"
        )

        # Verify
        assert success is True
        assert error_msg is None

        # Verify database update was called
        password_service.mock_db.table.update_item.assert_called()
        password_service.mock_db.log_security_event.assert_called()

    @pytest.mark.asyncio
    async def test_generate_temporary_password(self, password_service, mock_person):
        """Test temporary password generation."""
        # Setup
        password_service.mock_db.get_person.return_value = mock_person

        # Execute
        success, temp_password, error_msg = (
            await password_service.generate_temporary_password(
                person_id="test-person-id", admin_user_id="admin-id", length=12
            )
        )

        # Verify
        assert success is True
        assert temp_password is not None
        assert len(temp_password) == 12
        assert error_msg is None

        # Verify password meets complexity requirements
        assert any(c.isupper() for c in temp_password)
        assert any(c.islower() for c in temp_password)
        assert any(c.isdigit() for c in temp_password)
        assert any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in temp_password)

        # Verify database update was called
        password_service.mock_db.table.update_item.assert_called()
        password_service.mock_db.log_security_event.assert_called()

    @pytest.mark.asyncio
    async def test_check_password_history(self, password_service, mock_person):
        """Test password history checking."""
        # Setup - person with password history
        old_password_hash = PasswordHasher.hash_password("OldPassword123!")
        mock_person.password_history = [old_password_hash]
        password_service.mock_db.get_person.return_value = mock_person

        # Test with reused password
        can_use, error_msg = await password_service.check_password_history(
            person_id="test-person-id", password="OldPassword123!"
        )

        assert can_use is False
        assert "Cannot reuse any of the last" in error_msg

        # Test with new password
        can_use, error_msg = await password_service.check_password_history(
            person_id="test-person-id", password="NewPassword456@"
        )

        assert can_use is True
        assert error_msg is None

    @pytest.mark.asyncio
    async def test_security_event_logging(self, password_service, mock_person):
        """Test that security events are properly logged."""
        # Setup
        password_service.mock_db.get_person.return_value = mock_person

        password_request = PasswordUpdateRequest(
            current_password="CurrentPassword123!",
            new_password="NewPassword456@",
            confirm_password="NewPassword456@",
        )

        # Execute
        await password_service.update_password(
            person_id="test-person-id",
            password_request=password_request,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        # Verify security event was logged
        password_service.mock_db.log_security_event.assert_called()

        # Get the logged event
        call_args = password_service.mock_db.log_security_event.call_args[0][0]
        assert call_args.person_id == "test-person-id"
        assert call_args.action == "PASSWORD_UPDATED"
        assert call_args.success is True
        assert call_args.ip_address == "192.168.1.1"
        assert call_args.user_agent == "Mozilla/5.0"

    @pytest.mark.asyncio
    async def test_database_error_handling(self, password_service, mock_person):
        """Test handling of database errors."""
        # Setup - mock database error
        password_service.mock_db.get_person.return_value = mock_person
        password_service.mock_db.table.update_item.side_effect = Exception(
            "Database error"
        )

        password_request = PasswordUpdateRequest(
            current_password="CurrentPassword123!",
            new_password="NewPassword456@",
            confirm_password="NewPassword456@",
        )

        # Execute
        success, response, error = await password_service.update_password(
            person_id="test-person-id", password_request=password_request
        )

        # Verify error handling
        assert success is False
        assert response.success is False
        assert "Failed to update password" in response.message
        assert error == "Failed to update password"

    @pytest.mark.asyncio
    async def test_password_confirmation_mismatch(self):
        """Test password confirmation mismatch validation."""
        # This should be caught by the Pydantic model validation
        with pytest.raises(ValueError, match="Passwords do not match"):
            PasswordUpdateRequest(
                current_password="CurrentPassword123!",
                new_password="NewPassword456@",
                confirm_password="DifferentPassword789#",
            )

    @pytest.mark.asyncio
    async def test_concurrent_password_updates(self, password_service, mock_person):
        """Test handling of concurrent password update attempts."""
        # Setup
        password_service.mock_db.get_person.return_value = mock_person

        password_request = PasswordUpdateRequest(
            current_password="CurrentPassword123!",
            new_password="NewPassword456@",
            confirm_password="NewPassword456@",
        )

        # Execute concurrent updates
        tasks = [
            password_service.update_password("test-person-id", password_request)
            for _ in range(3)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # At least one should succeed (depending on implementation)
        # This test documents the expected behavior for concurrent updates
        successful_updates = sum(
            1 for result in results if not isinstance(result, Exception) and result[0]
        )
        assert successful_updates >= 1


class TestPasswordManagementServiceEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def password_service(self):
        """Create PasswordManagementService instance with mocked dependencies."""
        with patch(
            "src.services.password_management_service.DynamoDBService"
        ) as mock_db_class:
            mock_db = Mock()
            mock_db.get_person = AsyncMock()
            mock_db.log_security_event = AsyncMock()
            mock_db.table = Mock()
            mock_db.table.update_item = Mock()
            mock_db_class.return_value = mock_db

            service = PasswordManagementService()
            service.mock_db = mock_db
            return service

    @pytest.mark.asyncio
    async def test_person_without_password_hash(self, password_service):
        """Test handling person without existing password hash."""
        # Setup - person without password
        person_without_password = Person(
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
            # No password_hash field
        )

        password_service.mock_db.get_person.return_value = person_without_password

        password_request = PasswordUpdateRequest(
            current_password="AnyPassword123!",
            new_password="NewPassword456@",
            confirm_password="NewPassword456@",
        )

        # Execute
        success, response, error = await password_service.update_password(
            person_id="test-person-id", password_request=password_request
        )

        # Verify
        assert success is False
        assert "Current password is incorrect" in response.message

    @pytest.mark.asyncio
    async def test_empty_password_history(self, password_service):
        """Test handling of empty password history."""
        person = Person(
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
            password_hash=PasswordHasher.hash_password("CurrentPassword123!"),
            password_history=[],  # Empty list instead of None
        )

        password_service.mock_db.get_person.return_value = person

        # Test password history check with None history
        can_use, error_msg = await password_service.check_password_history(
            person_id="test-person-id", password="AnyPassword123!"
        )

        assert can_use is True
        assert error_msg is None

    @pytest.mark.asyncio
    async def test_maximum_password_length(self, password_service):
        """Test handling of very long passwords."""
        person = Person(
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
            password_hash=PasswordHasher.hash_password("CurrentPassword123!"),
            password_history=[],
        )

        password_service.mock_db.get_person.return_value = person

        # Very long password (1000 characters)
        long_password = "ValidPassword123!" * 60  # ~1000 chars

        password_request = PasswordUpdateRequest(
            current_password="CurrentPassword123!",
            new_password=long_password,
            confirm_password=long_password,
        )

        # Execute
        success, response, error = await password_service.update_password(
            person_id="test-person-id", password_request=password_request
        )

        # Should handle long passwords gracefully
        assert success is True or "too long" in response.message.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
