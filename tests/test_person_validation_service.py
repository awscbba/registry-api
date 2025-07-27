"""
Unit tests for PersonValidationService.
"""
import pytest
import sys
import os
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from src.models.person import (
    PersonCreate, PersonUpdate, Address, ValidationError, ValidationErrorType
)
from src.services.person_validation_service import PersonValidationService, ValidationResult


class TestPersonValidationService:
    """Test suite for PersonValidationService."""

    @pytest.fixture
    def validation_service(self):
        """Create a PersonValidationService with mocked dependencies."""
        # Create a mock database service
        mock_db = Mock()
        mock_db.get_person_by_email = AsyncMock()

        # Create the validation service with the mock
        service = PersonValidationService(mock_db)
        service.mock_db = mock_db  # Store reference for test access
        return service

    @pytest.fixture
    def valid_person_data(self):
        """Create valid person data for testing."""
        return PersonCreate(
            firstName="John",
            lastName="Doe",
            email="john.doe@example.com",
            phone="+12345678901",
            dateOfBirth="1990-01-01",
            address=Address(
                street="123 Main St",
                city="Anytown",
                state="CA",
                zipCode="12345",
                country="USA"
            )
        )

    @pytest.fixture
    def valid_update_data(self):
        """Create valid person update data for testing."""
        return PersonUpdate(
            first_name="Jane",
            last_name="Smith",
            phone="+19876543210"
        )

    @pytest.mark.asyncio
    async def test_validate_person_create_valid(self, validation_service, valid_person_data):
        """Test validation of valid person creation data."""
        # Setup
        validation_service.mock_db.get_person_by_email.return_value = None  # Email is unique

        # Execute
        result = await validation_service.validate_person_create(valid_person_data)

        # Verify
        assert result.is_valid is True
        assert len(result.errors) == 0
        validation_service.mock_db.get_person_by_email.assert_called_once_with(valid_person_data.email)

    @pytest.mark.asyncio
    async def test_validate_person_create_missing_required_fields(self, validation_service):
        """Test validation with missing required fields."""
        # Setup - create a valid object first, then test validation logic
        # The validation service should check for empty strings and None values
        incomplete_data = PersonCreate(
            firstName="",  # Empty first name - should be caught by validation service
            lastName="Doe",
            email="john.doe@example.com",
            phone="",  # Empty phone - should be caught by validation service
            dateOfBirth="1990-01-01",
            address=Address(
                street="123 Main St",
                city="Anytown",
                state="CA",
                zipCode="12345",  # Use the alias
                country="USA"
            )
        )

        # Execute
        result = await validation_service.validate_person_create(incomplete_data)

        # Verify - validation service should catch empty strings
        assert result.is_valid is False
        assert len(result.errors) >= 2  # At least 2 errors (first_name, phone)

        # Check specific errors
        error_fields = [error.field for error in result.errors]
        assert "first_name" in error_fields
        assert "phone" in error_fields

    @pytest.mark.asyncio
    async def test_validate_person_create_duplicate_email(self, validation_service, valid_person_data):
        """Test validation with duplicate email."""
        # Setup - email already exists
        validation_service.mock_db.get_person_by_email.return_value = Mock()  # Email exists

        # Execute
        result = await validation_service.validate_person_create(valid_person_data)

        # Verify
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == "email"
        assert result.errors[0].code == ValidationErrorType.DUPLICATE_VALUE
        validation_service.mock_db.get_person_by_email.assert_called_once_with(valid_person_data.email)

    @pytest.mark.asyncio
    async def test_validate_person_create_invalid_phone(self, validation_service, valid_person_data):
        """Test validation with invalid phone format."""
        # Setup - invalid phone format
        valid_person_data.phone = "not-a-phone"
        validation_service.mock_db.get_person_by_email.return_value = None

        # Execute
        result = await validation_service.validate_person_create(valid_person_data)

        # Verify
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == "phone"
        assert result.errors[0].code == ValidationErrorType.PHONE_FORMAT

    @pytest.mark.asyncio
    async def test_validate_person_create_invalid_date(self, validation_service, valid_person_data):
        """Test validation with invalid date format."""
        # Setup - invalid date format
        valid_person_data.date_of_birth = "not-a-date"
        validation_service.mock_db.get_person_by_email.return_value = None

        # Execute
        result = await validation_service.validate_person_create(valid_person_data)

        # Verify
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == "date_of_birth"
        assert result.errors[0].code == ValidationErrorType.DATE_FORMAT

    @pytest.mark.asyncio
    async def test_validate_person_create_future_date(self, validation_service, valid_person_data):
        """Test validation with future date of birth."""
        # Setup - future date
        future_date = datetime.now(timezone.utc).replace(year=datetime.now().year + 1).strftime("%Y-%m-%d")
        valid_person_data.date_of_birth = future_date
        validation_service.mock_db.get_person_by_email.return_value = None

        # Execute
        result = await validation_service.validate_person_create(valid_person_data)

        # Verify
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == "date_of_birth"
        assert result.errors[0].code == ValidationErrorType.DATE_FORMAT

    @pytest.mark.asyncio
    async def test_validate_person_create_invalid_address(self, validation_service, valid_person_data):
        """Test validation with incomplete address."""
        # Setup - incomplete address with empty fields
        valid_person_data.address = Address(
            street="123 Main St",
            city="",  # Empty city - should be caught by validation
            state="CA",
            zipCode="12345",  # Use the alias
            country=""  # Empty country - should be caught by validation
        )
        validation_service.mock_db.get_person_by_email.return_value = None

        # Execute
        result = await validation_service.validate_person_create(valid_person_data)

        # Verify
        assert result.is_valid is False
        assert len(result.errors) >= 2  # At least 2 errors (city, country)

        # Check specific errors
        error_fields = [error.field for error in result.errors]
        assert "address.city" in error_fields
        assert "address.country" in error_fields

    @pytest.mark.asyncio
    async def test_validate_person_update_valid(self, validation_service, valid_update_data):
        """Test validation of valid person update data."""
        # Setup
        person_id = "test-person-id"

        # Execute
        result = await validation_service.validate_person_update(person_id, valid_update_data)

        # Verify
        assert result.is_valid is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_validate_person_update_email_change(self, validation_service, valid_update_data):
        """Test validation of email change in update."""
        # Setup
        person_id = "test-person-id"
        valid_update_data.email = "new.email@example.com"
        validation_service.mock_db.get_person_by_email.return_value = None  # Email is unique

        # Execute
        result = await validation_service.validate_person_update(person_id, valid_update_data)

        # Verify
        assert result.is_valid is True
        assert len(result.errors) == 0
        validation_service.mock_db.get_person_by_email.assert_called_once_with(
            valid_update_data.email
        )

    @pytest.mark.asyncio
    async def test_validate_person_update_duplicate_email(self, validation_service, valid_update_data):
        """Test validation of duplicate email in update."""
        # Setup
        person_id = "test-person-id"
        valid_update_data.email = "existing.email@example.com"
        validation_service.mock_db.get_person_by_email.return_value = Mock()  # Email exists

        # Execute
        result = await validation_service.validate_person_update(person_id, valid_update_data)

        # Verify
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == "email"
        assert result.errors[0].code == ValidationErrorType.DUPLICATE_VALUE
        validation_service.mock_db.get_person_by_email.assert_called_once_with(
            valid_update_data.email
        )

    @pytest.mark.asyncio
    async def test_validate_person_update_invalid_phone(self, validation_service, valid_update_data):
        """Test validation of invalid phone in update."""
        # Setup
        person_id = "test-person-id"
        valid_update_data.phone = "not-a-phone"

        # Execute
        result = await validation_service.validate_person_update(person_id, valid_update_data)

        # Verify
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == "phone"
        assert result.errors[0].code == ValidationErrorType.PHONE_FORMAT

    @pytest.mark.asyncio
    async def test_validate_email_uniqueness(self, validation_service):
        """Test email uniqueness validation."""
        # Setup
        email = "test@example.com"
        person_id = "test-person-id"

        # Test 1: Email is unique
        validation_service.mock_db.get_person_by_email.return_value = None
        is_unique = await validation_service.validate_email_uniqueness(email)
        assert is_unique is True

        # Test 2: Email exists but belongs to the same person
        mock_person = Mock()
        mock_person.id = person_id
        validation_service.mock_db.get_person_by_email.return_value = mock_person
        is_unique = await validation_service.validate_email_uniqueness(email, person_id)
        assert is_unique is True

        # Test 3: Email exists and belongs to a different person
        mock_person.id = "different-person-id"
        validation_service.mock_db.get_person_by_email.return_value = mock_person
        is_unique = await validation_service.validate_email_uniqueness(email, person_id)
        assert is_unique is False

    @pytest.mark.asyncio
    async def test_validate_phone_format(self, validation_service):
        """Test phone format validation."""
        # Valid US phone number
        assert validation_service.validate_phone_format("+12345678901") is True
        assert validation_service.validate_phone_format("1234567890") is True

        # Valid international phone number
        assert validation_service.validate_phone_format("+441234567890") is True

        # Invalid phone numbers
        assert validation_service.validate_phone_format("123") is False  # Too short
        assert validation_service.validate_phone_format("not-a-phone") is False  # Non-numeric
        assert validation_service.validate_phone_format("") is False  # Empty
        assert validation_service.validate_phone_format(None) is False  # None

    @pytest.mark.asyncio
    async def test_validate_date_of_birth(self, validation_service):
        """Test date of birth validation."""
        # Valid past date
        assert validation_service.validate_date_of_birth("1990-01-01") is True

        # Invalid dates
        assert validation_service.validate_date_of_birth("not-a-date") is False  # Invalid format
        assert validation_service.validate_date_of_birth("") is False  # Empty
        assert validation_service.validate_date_of_birth(None) is False  # None

        # Future date
        future_date = datetime.now(timezone.utc).replace(year=datetime.now().year + 1).strftime("%Y-%m-%d")
        assert validation_service.validate_date_of_birth(future_date) is False

        # Very old date (unreasonable)
        assert validation_service.validate_date_of_birth("1800-01-01") is False

    def test_validation_result(self):
        """Test ValidationResult class functionality."""
        # Create a new validation result
        result = ValidationResult()
        assert result.is_valid is True
        assert len(result.errors) == 0

        # Add an error
        result.add_error(
            field="test_field",
            message="Test error message",
            code=ValidationErrorType.REQUIRED_FIELD
        )
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == "test_field"
        assert result.errors[0].message == "Test error message"
        assert result.errors[0].code == ValidationErrorType.REQUIRED_FIELD

        # Merge with another result
        other_result = ValidationResult()
        other_result.add_error(
            field="other_field",
            message="Other error message",
            code=ValidationErrorType.INVALID_FORMAT
        )

        result.merge(other_result)
        assert result.is_valid is False
        assert len(result.errors) == 2
        assert result.errors[1].field == "other_field"

        # Merge with valid result
        valid_result = ValidationResult()
        result.merge(valid_result)
        assert result.is_valid is False  # Still invalid
        assert len(result.errors) == 2  # No new errors


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
