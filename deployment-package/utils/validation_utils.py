"""
Validation utilities for common validation patterns and functions.
"""

import re
from datetime import datetime, date
from typing import List, Optional, Pattern


def validate_email_format(email: str) -> tuple[bool, Optional[str]]:
    """
    Validate email format using regex pattern.

    Args:
        email: Email address to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return False, "Email is required"

    email = email.strip()

    # Basic email regex pattern
    email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    if not email_pattern.match(email):
        return False, "Invalid email format"

    if len(email) > 254:  # RFC 5321 limit
        return False, "Email address too long"

    return True, None


class ValidationPatterns:
    """Common regex patterns for validation."""

    # Phone number patterns
    US_PHONE = re.compile(
        r"^\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})$"
    )
    INTERNATIONAL_PHONE = re.compile(r"^\+?[1-9]\d{6,14}$")

    # Name patterns
    NAME = re.compile(r"^[a-zA-Z\s\-\'\.]+$")

    # Address patterns
    ZIP_CODE_US = re.compile(r"^\d{5}(-\d{4})?$")
    ZIP_CODE_CANADA = re.compile(r"^[A-Za-z]\d[A-Za-z][ -]?\d[A-Za-z]\d$")

    # General patterns
    ALPHANUMERIC = re.compile(r"^[a-zA-Z0-9]+$")
    ALPHA_ONLY = re.compile(r"^[a-zA-Z]+$")
    NUMERIC_ONLY = re.compile(r"^\d+$")


class PhoneValidator:
    """Phone number validation with multiple format support."""

    @staticmethod
    def validate_phone_format(phone: str) -> tuple[bool, Optional[str]]:
        """
        Validate phone number format with support for multiple formats.

        Args:
            phone: Phone number to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not phone:
            return False, "Phone number is required"

        # Clean the phone number
        cleaned_phone = PhoneValidator.clean_phone_number(phone)

        # Check US phone number format (10 digits)
        if len(cleaned_phone) == 10 and cleaned_phone.isdigit():
            return True, None

        # Check international format (7-15 digits, may start with +)
        if phone.startswith("+"):
            digits_only = re.sub(r"\D", "", phone[1:])  # Remove + and non-digits
            if 7 <= len(digits_only) <= 15:
                return True, None

        # Check if it's just digits in international range
        if 7 <= len(cleaned_phone) <= 15 and cleaned_phone.isdigit():
            return True, None

        return (
            False,
            "Phone number must be 10 digits for US numbers or 7-15 digits for international numbers",
        )

    @staticmethod
    def clean_phone_number(phone: str) -> str:
        """
        Clean phone number by removing formatting characters.

        Args:
            phone: Phone number to clean

        Returns:
            Cleaned phone number with only digits
        """
        if not phone:
            return ""

        # Remove all non-digit characters except +
        if phone.startswith("+"):
            return "+" + re.sub(r"\D", "", phone[1:])
        else:
            return re.sub(r"\D", "", phone)


class DateValidator:
    """Date validation with comprehensive checks."""

    @staticmethod
    def validate_date_format(
        date_str: str, format_str: str = "%Y-%m-%d"
    ) -> tuple[bool, Optional[str]]:
        """
        Validate date format.

        Args:
            date_str: Date string to validate
            format_str: Expected date format

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not date_str:
            return False, "Date is required"

        try:
            datetime.strptime(date_str, format_str)
            return True, None
        except ValueError:
            return False, f"Date must be in {format_str} format"

    @staticmethod
    def validate_date_of_birth(date_str: str) -> tuple[bool, Optional[str]]:
        """
        Validate date of birth with business rules.

        Args:
            date_str: Date of birth string in YYYY-MM-DD format

        Returns:
            Tuple of (is_valid, error_message)
        """
        # First validate format
        is_valid_format, format_error = DateValidator.validate_date_format(date_str)
        if not is_valid_format:
            return False, format_error

        try:
            birth_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            today = date.today()

            # Check if date is in the future
            if birth_date >= today:
                return False, "Date of birth cannot be in the future"

            # Check if date is too far in the past (150 years)
            min_birth_date = date(today.year - 150, today.month, today.day)
            if birth_date < min_birth_date:
                return False, "Date of birth cannot be more than 150 years ago"

            return True, None

        except ValueError as e:
            return False, f"Invalid date: {str(e)}"


class NameValidator:
    """Name validation with cultural sensitivity."""

    @staticmethod
    def validate_name(
        name: str, field_name: str = "Name"
    ) -> tuple[bool, Optional[str]]:
        """
        Validate name field.

        Args:
            name: Name to validate
            field_name: Field name for error messages

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not name:
            return False, f"{field_name} is required"

        name = name.strip()

        if len(name) < 1:
            return False, f"{field_name} cannot be empty"

        if len(name) > 100:
            return False, f"{field_name} cannot exceed 100 characters"

        # Allow letters, spaces, hyphens, apostrophes, and periods
        if not ValidationPatterns.NAME.match(name):
            return (
                False,
                f"{field_name} can only contain letters, spaces, hyphens, apostrophes, and periods",
            )

        # Check for reasonable content (not just spaces/punctuation)
        if not re.search(r"[a-zA-Z]", name):
            return False, f"{field_name} must contain at least one letter"

        return True, None


class AddressValidator:
    """Address validation with country-specific rules."""

    @staticmethod
    def validate_zip_code(
        zip_code: str, country: str = "US"
    ) -> tuple[bool, Optional[str]]:
        """
        Validate ZIP/postal code based on country.

        Args:
            zip_code: ZIP/postal code to validate
            country: Country code (US, CA, etc.)

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not zip_code:
            return False, "ZIP/postal code is required"

        zip_code = zip_code.strip()

        if country.upper() == "US":
            if ValidationPatterns.ZIP_CODE_US.match(zip_code):
                return True, None
            else:
                return False, "US ZIP code must be in format 12345 or 12345-6789"

        elif country.upper() == "CA":
            if ValidationPatterns.ZIP_CODE_CANADA.match(zip_code):
                return True, None
            else:
                return False, "Canadian postal code must be in format A1A 1A1 or A1A1A1"

        else:
            # Generic validation for other countries
            if 3 <= len(zip_code) <= 10:
                return True, None
            else:
                return False, "Postal code must be between 3 and 10 characters"


# Convenience functions for common validations
def is_valid_phone(phone: str) -> bool:
    """Quick phone validation check."""
    is_valid, _ = PhoneValidator.validate_phone_format(phone)
    return is_valid


def is_valid_date_of_birth(date_str: str) -> bool:
    """Quick date of birth validation check."""
    is_valid, _ = DateValidator.validate_date_of_birth(date_str)
    return is_valid


def is_valid_name(name: str) -> bool:
    """Quick name validation check."""
    is_valid, _ = NameValidator.validate_name(name)
    return is_valid


def validate_phone_format(phone: str) -> tuple[bool, Optional[str]]:
    """Alias for PhoneValidator.validate_phone_format for backward compatibility."""
    return PhoneValidator.validate_phone_format(phone)


def validate_date_format(
    date_str: str, format_str: str = "%Y-%m-%d"
) -> tuple[bool, Optional[str]]:
    """Alias for DateValidator.validate_date_format for backward compatibility."""
    return DateValidator.validate_date_format(date_str, format_str)


def validate_zip_code(zip_code: str, country: str = "US") -> tuple[bool, Optional[str]]:
    """Alias for AddressValidator.validate_zip_code for backward compatibility."""
    return AddressValidator.validate_zip_code(zip_code, country)


def validate_name(name: str, field_name: str = "Name") -> tuple[bool, Optional[str]]:
    """Alias for NameValidator.validate_name for backward compatibility."""
    return NameValidator.validate_name(name, field_name)
