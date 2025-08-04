"""
Comprehensive tests for person data validation rules.
"""

import pytest
import sys
import os
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from src.models.person import (
    PersonCreate,
    PersonUpdate,
    Address,
    ValidationError,
    ValidationErrorType,
)
from src.services.person_validation_service import (
    PersonValidationService,
    ValidationResult,
)
from src.utils.validation_utils import (
    validate_email_format,
    validate_phone_format,
    validate_date_format,
    validate_zip_code,
    validate_name,
)


class TestComprehensiveValidation:
    """Comprehensive tests for all person data validation rules."""

    @pytest.fixture
    def validation_service(self):
        """Create a PersonValidationService with mocked dependencies."""
        mock_db = Mock()
        mock_db.get_person_by_email = AsyncMock()

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
                postalCode="12345",
                country="USA",
            ),
        )

    # Email validation tests

    @pytest.mark.parametrize(
        "email,is_valid",
        [
            ("valid@example.com", True),
            ("user.name+tag@example.co.uk", True),
            ("user-name@example.org", True),
            ("", False),
            ("invalid", False),
            ("invalid@", False),
            ("@example.com", False),
            ("user@.com", False),
            ("user@example.", False),
            ("user name@example.com", False),
        ],
    )
    def test_email_format_validation(self, email, is_valid):
        """Test email format validation with various inputs."""
        result, _ = validate_email_format(email)
        assert result == is_valid

    @pytest.mark.asyncio
    async def test_email_uniqueness_validation(self, validation_service):
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

    # Phone validation tests

    @pytest.mark.parametrize(
        "phone,is_valid",
        [
            ("+12345678901", True),
            ("1234567890", True),
            ("+44 1234 567890", True),
            ("+1 (234) 567-8901", True),
            ("", False),
            ("123", False),
            ("abcdefghij", False),
            ("+1234567890123456", False),  # Too long
        ],
    )
    def test_phone_format_validation(self, phone, is_valid):
        """Test phone format validation with various inputs."""
        result, _ = validate_phone_format(phone)
        assert result == is_valid

    # Date validation tests

    @pytest.mark.parametrize(
        "date_str,is_valid",
        [
            ("1990-01-01", True),
            ("2000-12-31", True),
            ("", False),
            ("1990/01/01", False),
            ("01-01-1990", False),
            ("1990-13-01", False),  # Invalid month
            ("1990-01-32", False),  # Invalid day
            ("abcd-ef-gh", False),
        ],
    )
    def test_date_format_validation(self, date_str, is_valid):
        """Test date format validation with various inputs."""
        result, _ = validate_date_format(date_str)
        assert result == is_valid

    def test_date_of_birth_validation(self, validation_service):
        """Test date of birth validation with various scenarios."""
        # Valid past date
        assert validation_service.validate_date_of_birth("1990-01-01") is True

        # Future date
        future_date = (
            datetime.now(timezone.utc)
            .replace(year=datetime.now().year + 1)
            .strftime("%Y-%m-%d")
        )
        assert validation_service.validate_date_of_birth(future_date) is False

        # Very old date (unreasonable)
        assert validation_service.validate_date_of_birth("1800-01-01") is False

        # Invalid format
        assert validation_service.validate_date_of_birth("not-a-date") is False

        # Empty or None
        assert validation_service.validate_date_of_birth("") is False
        assert validation_service.validate_date_of_birth(None) is False

    # Address validation tests

    @pytest.mark.parametrize(
        "zip_code,is_valid",
        [
            ("12345", True),
            ("12345-6789", True),
            ("", False),
            ("1234", False),
            ("123456", False),
            ("12345-67890", False),
            ("abcde", False),
        ],
    )
    def test_zip_code_validation(self, zip_code, is_valid):
        """Test ZIP code validation with various inputs."""
        result, _ = validate_zip_code(zip_code)
        assert result == is_valid

    @pytest.mark.asyncio
    async def test_address_validation(self, validation_service, valid_person_data):
        """Test address validation with various scenarios."""
        # Setup - valid address
        result = ValidationResult()
        validation_service._validate_address(valid_person_data.address, result)
        assert result.is_valid is True

        # Setup - missing required fields
        result = ValidationResult()
        incomplete_address = Address(
            street="123 Main St",
            city="",  # Empty city
            state="CA",
            postalCode="12345",
            country="",  # Empty country
        )
        validation_service._validate_address(incomplete_address, result)
        assert result.is_valid is False
        assert len(result.errors) >= 2  # At least 2 errors (city, country)

        # Setup - invalid ZIP code
        result = ValidationResult()
        invalid_zip_address = Address(
            street="123 Main St",
            city="Anytown",
            state="CA",
            postalCode="invalid",  # Invalid ZIP
            country="USA",
        )
        validation_service._validate_address(invalid_zip_address, result)
        assert result.is_valid is False
        assert len(result.errors) >= 1
        assert any(error.field == "address.postal_code" for error in result.errors)

        # Setup - None address
        result = ValidationResult()
        validation_service._validate_address(None, result)
        assert result.is_valid is False
        assert len(result.errors) >= 1
        assert result.errors[0].field == "address"

    # Name validation tests

    @pytest.mark.parametrize(
        "name,is_valid",
        [
            ("John", True),
            ("Mary-Ann", True),
            ("O'Connor", True),
            ("Jean-Claude", True),
            ("", False),
            ("A" * 101, False),  # Too long
            ("John123", False),  # Contains numbers
            ("John@Doe", False),  # Contains special characters
        ],
    )
    def test_name_validation(self, name, is_valid):
        """Test name validation with various inputs."""
        result, _ = validate_name(name)
        assert result == is_valid

    @pytest.mark.asyncio
    async def test_name_fields_validation(self, validation_service):
        """Test name fields validation with various scenarios."""
        # Setup - valid names
        result = ValidationResult()
        validation_service._validate_name_fields("John", "Doe", result)
        assert result.is_valid is True

        # Setup - empty names
        result = ValidationResult()
        validation_service._validate_name_fields("", "", result)
        assert result.is_valid is False
        assert len(result.errors) >= 2  # Both first and last name errors

        # Setup - too long names
        result = ValidationResult()
        long_name = "A" * 101  # 101 characters
        validation_service._validate_name_fields(long_name, long_name, result)
        assert result.is_valid is False
        assert len(result.errors) >= 2  # Both first and last name errors

        # Setup - invalid characters
        result = ValidationResult()
        validation_service._validate_name_fields("John123", "Doe456", result)
        assert result.is_valid is False
        assert len(result.errors) >= 2  # Both first and last name errors

    # Comprehensive validation tests

    @pytest.mark.asyncio
    async def test_comprehensive_person_create_validation(
        self, validation_service, valid_person_data
    ):
        """Test comprehensive validation for person creation."""
        # Setup - valid data
        validation_service.mock_db.get_person_by_email.return_value = (
            None  # Email is unique
        )
        result = await validation_service.validate_person_create(valid_person_data)
        assert result.is_valid is True

        # Setup - all fields invalid
        invalid_person = PersonCreate(
            firstName="",
            lastName="Doe123",  # Invalid format
            email="invalid@email.com",  # Valid format but will be tested by validation service
            phone="123",  # Too short
            dateOfBirth="2099-01-01",  # Future date
            address=Address(
                street="", city="", state="", postalCode="invalid", country=""
            ),
        )
        validation_service.mock_db.get_person_by_email.return_value = None
        result = await validation_service.validate_person_create(invalid_person)
        assert result.is_valid is False
        assert len(result.errors) >= 5  # At least one error for each invalid field

        # Check specific error types
        error_fields = [error.field for error in result.errors]
        error_codes = [error.code for error in result.errors]

        assert "first_name" in error_fields
        assert "last_name" in error_fields
        assert "phone" in error_fields
        assert "date_of_birth" in error_fields
        assert any(field.startswith("address.") for field in error_fields)

        assert ValidationErrorType.REQUIRED_FIELD in error_codes
        assert ValidationErrorType.INVALID_FORMAT in error_codes

    @pytest.mark.asyncio
    async def test_comprehensive_person_update_validation(self, validation_service):
        """Test comprehensive validation for person update."""
        # Setup - valid update
        valid_update = PersonUpdate(
            firstName="Jane",
            lastName="Smith",
            email="jane.smith@example.com",
            phone="+19876543210",
            dateOfBirth="1985-05-15",
        )
        validation_service.mock_db.get_person_by_email.return_value = (
            None  # Email is unique
        )
        result = await validation_service.validate_person_update(
            "test-person-id", valid_update
        )
        assert result.is_valid is True

        # Setup - all fields invalid (but valid enough for Pydantic to create the object)
        invalid_update = PersonUpdate(
            firstName="Jane123",  # Invalid format
            lastName="",  # Empty
            email="invalid@email.com",  # Valid format but will be tested by validation service
            phone="123",  # Too short
            dateOfBirth="2099-01-01",  # Future date
        )
        validation_service.mock_db.get_person_by_email.return_value = None
        result = await validation_service.validate_person_update(
            "test-person-id", invalid_update
        )
        assert result.is_valid is False
        assert len(result.errors) >= 4  # At least one error for each invalid field

        # Check specific error types
        error_fields = [error.field for error in result.errors]

        assert "first_name" in error_fields
        assert "last_name" in error_fields
        assert "phone" in error_fields
        assert "date_of_birth" in error_fields

    @pytest.mark.asyncio
    async def test_partial_update_validation(self, validation_service):
        """Test validation for partial updates (only some fields provided)."""
        # Setup - only update first name (valid)
        partial_update = PersonUpdate(first_name="Jane")
        result = await validation_service.validate_person_update(
            "test-person-id", partial_update
        )
        assert result.is_valid is True

        # Setup - only update email (valid)
        partial_update = PersonUpdate(email="jane.doe@example.com")
        validation_service.mock_db.get_person_by_email.return_value = (
            None  # Email is unique
        )
        result = await validation_service.validate_person_update(
            "test-person-id", partial_update
        )
        assert result.is_valid is True

        # Setup - only update phone (invalid)
        partial_update = PersonUpdate(phone="invalid")
        result = await validation_service.validate_person_update(
            "test-person-id", partial_update
        )
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == "phone"

    @pytest.mark.asyncio
    async def test_validation_result_merging(self):
        """Test merging of validation results."""
        # Create first validation result
        result1 = ValidationResult()
        result1.add_error(
            field="field1",
            message="Error in field1",
            code=ValidationErrorType.REQUIRED_FIELD,
        )

        # Create second validation result
        result2 = ValidationResult()
        result2.add_error(
            field="field2",
            message="Error in field2",
            code=ValidationErrorType.INVALID_FORMAT,
        )

        # Merge results
        result1.merge(result2)

        # Verify merged result
        assert result1.is_valid is False
        assert len(result1.errors) == 2
        assert result1.errors[0].field == "field1"
        assert result1.errors[1].field == "field2"

        # Merge with valid result
        valid_result = ValidationResult()
        result1.merge(valid_result)

        # Verify no change
        assert result1.is_valid is False
        assert len(result1.errors) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
