"""
Person validation service for comprehensive data validation.
"""

import re
from datetime import datetime, date
from typing import List, Optional, Tuple
from ..models.person import (
    PersonCreate,
    PersonUpdate,
    ValidationError,
    ValidationErrorType,
)
from ..utils.password_utils import PasswordValidator


class ValidationResult:
    """Result of a validation operation."""

    def __init__(self, is_valid: bool = True, errors: List[ValidationError] = None):
        self.is_valid = is_valid
        self.errors = errors or []

    def add_error(
        self, field: str, message: str, code: ValidationErrorType, value: str = None
    ):
        """Add a validation error."""
        self.errors.append(
            ValidationError(field=field, message=message, code=code, value=value)
        )
        self.is_valid = False

    def merge(self, other: "ValidationResult"):
        """Merge another validation result into this one."""
        if not other.is_valid:
            self.is_valid = False
            self.errors.extend(other.errors)


class PersonValidationService:
    """Service for validating person data with comprehensive rules."""

    def __init__(self, dynamodb_service=None):
        self.dynamodb_service = dynamodb_service
        self.password_validator = PasswordValidator()

    async def validate_person_create(
        self, person_data: PersonCreate
    ) -> ValidationResult:
        """
        Validate person creation data.

        Args:
            person_data: The person data to validate

        Returns:
            ValidationResult with any errors found
        """
        result = ValidationResult()

        # Validate required fields
        self._validate_required_fields(person_data, result)

        # Validate email format and uniqueness
        await self._validate_email(person_data.email, result)

        # Validate phone format
        self._validate_phone_format(person_data.phone, result)

        # Validate date of birth
        self._validate_date_of_birth(person_data.date_of_birth, result)

        # Validate address
        self._validate_address(person_data.address, result)

        # Validate name fields
        self._validate_name_fields(
            person_data.first_name, person_data.last_name, result
        )

        return result

    async def validate_person_update(
        self, person_id: str, person_data: PersonUpdate
    ) -> ValidationResult:
        """
        Validate person update data.

        Args:
            person_id: ID of the person being updated
            person_data: The person data to validate

        Returns:
            ValidationResult with any errors found
        """
        result = ValidationResult()

        # Validate email if provided
        if person_data.email is not None:
            await self._validate_email(
                person_data.email, result, exclude_person_id=person_id
            )

        # Validate phone if provided
        if person_data.phone is not None:
            self._validate_phone_format(person_data.phone, result)

        # Validate date of birth if provided
        if person_data.date_of_birth is not None:
            self._validate_date_of_birth(person_data.date_of_birth, result)

        # Validate address if provided
        if person_data.address is not None:
            self._validate_address(person_data.address, result)

        # Validate name fields if provided
        if person_data.first_name is not None or person_data.last_name is not None:
            self._validate_name_fields(
                person_data.first_name, person_data.last_name, result, allow_none=True
            )

        return result

    async def validate_email_uniqueness(
        self, email: str, exclude_person_id: str = None
    ) -> bool:
        """
        Check if email is unique in the system.

        Args:
            email: Email address to check
            exclude_person_id: Person ID to exclude from uniqueness check

        Returns:
            True if email is unique, False otherwise
        """
        if not self.dynamodb_service:
            return True  # Skip validation if no database service available

        try:
            # Check if email exists in the system
            existing_person = await self.dynamodb_service.get_person_by_email(email)

            if existing_person is None:
                return True  # Email is unique

            # If excluding a specific person ID, check if it's the same person
            if exclude_person_id and existing_person.id == exclude_person_id:
                return True  # Same person, so email is still "unique" for them

            return False  # Email already exists for a different person

        except Exception:
            # If we can't check uniqueness, assume it's not unique for safety
            return False

    def validate_phone_format(self, phone: str) -> bool:
        """
        Validate phone number format.

        Args:
            phone: Phone number to validate

        Returns:
            True if phone format is valid, False otherwise
        """
        if not phone:
            return False

        # Remove all non-digit characters for validation
        digits_only = re.sub(r"\D", "", phone)

        # Check for valid US phone number (10 digits) or international (7-15 digits)
        if len(digits_only) == 10:
            # US phone number format
            return True
        elif 7 <= len(digits_only) <= 15:
            # International phone number format
            return True

        return False

    def validate_date_of_birth(self, date_str: str) -> bool:
        """
        Validate date of birth format and value.

        Args:
            date_str: Date string in YYYY-MM-DD format

        Returns:
            True if date is valid, False otherwise
        """
        if not date_str:
            return False

        try:
            # Parse the date
            birth_date = datetime.strptime(date_str, "%Y-%m-%d").date()

            # Check if date is in the past
            today = date.today()
            if birth_date >= today:
                return False

            # Check if date is reasonable (not too far in the past)
            # Assuming maximum age of 150 years
            min_birth_date = date(today.year - 150, today.month, today.day)
            if birth_date < min_birth_date:
                return False

            return True

        except ValueError:
            return False

    def validate_password(self, password: str) -> Tuple[bool, List[str]]:
        """
        Validate password against security policy.

        Args:
            password: Password to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        return self.password_validator.validate_password(password)

    def _validate_required_fields(
        self, person_data: PersonCreate, result: ValidationResult
    ):
        """Validate that all required fields are present and not empty."""
        required_fields = {
            "first_name": "First name",
            "last_name": "Last name",
            "email": "Email address",
            "phone": "Phone number",
            "date_of_birth": "Date of birth",
            "address": "Address",
        }

        for field_name, display_name in required_fields.items():
            value = getattr(person_data, field_name, None)
            if not value or (isinstance(value, str) and not value.strip()):
                result.add_error(
                    field=field_name,
                    message=f"{display_name} is required",
                    code=ValidationErrorType.REQUIRED_FIELD,
                )

    async def _validate_email(
        self, email: str, result: ValidationResult, exclude_person_id: str = None
    ):
        """Validate email format and uniqueness."""
        if not email:
            result.add_error(
                field="email",
                message="Email address is required",
                code=ValidationErrorType.REQUIRED_FIELD,
            )
            return

        # Email format validation is handled by EmailStr type in Pydantic
        # Check uniqueness
        is_unique = await self.validate_email_uniqueness(email, exclude_person_id)
        if not is_unique:
            result.add_error(
                field="email",
                message="Email address is already in use",
                code=ValidationErrorType.DUPLICATE_VALUE,
                value=email,
            )

    def _validate_phone_format(self, phone: str, result: ValidationResult):
        """Validate phone number format."""
        if not phone:
            result.add_error(
                field="phone",
                message="Phone number is required",
                code=ValidationErrorType.REQUIRED_FIELD,
            )
            return

        if not self.validate_phone_format(phone):
            result.add_error(
                field="phone",
                message="Phone number format is invalid. Use 10 digits for US numbers or 7-15 digits for international numbers",
                code=ValidationErrorType.PHONE_FORMAT,
                value=phone,
            )

    def _validate_date_of_birth(self, date_str: str, result: ValidationResult):
        """Validate date of birth format and value."""
        if not date_str:
            result.add_error(
                field="date_of_birth",
                message="Date of birth is required",
                code=ValidationErrorType.REQUIRED_FIELD,
            )
            return

        if not self.validate_date_of_birth(date_str):
            result.add_error(
                field="date_of_birth",
                message="Date of birth must be a valid past date in YYYY-MM-DD format",
                code=ValidationErrorType.DATE_FORMAT,
                value=date_str,
            )

    def _validate_address(self, address, result: ValidationResult):
        """Validate address fields."""
        if not address:
            result.add_error(
                field="address",
                message="Address is required",
                code=ValidationErrorType.REQUIRED_FIELD,
            )
            return

        # Validate required address fields
        required_address_fields = {
            "street": "Street address",
            "city": "City",
            "state": "State",
            "zip_code": "ZIP code",
            "country": "Country",
        }

        for field_name, display_name in required_address_fields.items():
            value = getattr(address, field_name, None)
            if not value or (isinstance(value, str) and not value.strip()):
                result.add_error(
                    field=f"address.{field_name}",
                    message=f"{display_name} is required",
                    code=ValidationErrorType.REQUIRED_FIELD,
                )

        # Validate ZIP code format (basic validation)
        if hasattr(address, "zip_code") and address.zip_code:
            zip_code = address.zip_code.strip()
            # US ZIP code format (5 digits or 5+4 format)
            if not re.match(r"^\d{5}(-\d{4})?$", zip_code):
                result.add_error(
                    field="address.zip_code",
                    message="ZIP code must be in format 12345 or 12345-6789",
                    code=ValidationErrorType.INVALID_FORMAT,
                    value=zip_code,
                )

    def _validate_name_fields(
        self,
        first_name: str,
        last_name: str,
        result: ValidationResult,
        allow_none: bool = False,
    ):
        """Validate name fields for length and content."""
        if not allow_none:
            if not first_name or not first_name.strip():
                result.add_error(
                    field="first_name",
                    message="First name is required",
                    code=ValidationErrorType.REQUIRED_FIELD,
                )

            if not last_name or not last_name.strip():
                result.add_error(
                    field="last_name",
                    message="Last name is required",
                    code=ValidationErrorType.REQUIRED_FIELD,
                )

        # Validate name length and content if provided
        for field_name, name_value in [
            ("first_name", first_name),
            ("last_name", last_name),
        ]:
            if name_value is not None:
                name_value = name_value.strip()

                if len(name_value) < 1:
                    result.add_error(
                        field=field_name,
                        message=f'{field_name.replace("_", " ").title()} cannot be empty',
                        code=ValidationErrorType.INVALID_LENGTH,
                        value=name_value,
                    )
                elif len(name_value) > 100:
                    result.add_error(
                        field=field_name,
                        message=f'{field_name.replace("_", " ").title()} cannot exceed 100 characters',
                        code=ValidationErrorType.INVALID_LENGTH,
                        value=name_value,
                    )
                elif not re.match(r"^[a-zA-Z\s\-\'\.]+$", name_value):
                    result.add_error(
                        field=field_name,
                        message=f'{field_name.replace("_", " ").title()} can only contain letters, spaces, hyphens, apostrophes, and periods',
                        code=ValidationErrorType.INVALID_FORMAT,
                        value=name_value,
                    )
