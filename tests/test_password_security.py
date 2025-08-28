"""
Test password security utilities and authentication improvements.
"""

import pytest
from src.utils.password_utils import (
    PasswordHasher,
    PasswordValidator,
    PasswordGenerator,
    hash_and_validate_password,
    generate_and_hash_password,
)


class TestPasswordHasher:
    """Test password hashing functionality."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "TestPassword123!"
        hashed = PasswordHasher.hash_password(password)

        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are long
        assert hashed.startswith("$2b$")  # bcrypt format

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "TestPassword123!"
        hashed = PasswordHasher.hash_password(password)

        assert PasswordHasher.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = PasswordHasher.hash_password(password)

        assert PasswordHasher.verify_password(wrong_password, hashed) is False

    def test_verify_password_invalid_hash(self):
        """Test password verification with invalid hash."""
        password = "TestPassword123!"
        invalid_hash = "invalid_hash"

        assert PasswordHasher.verify_password(password, invalid_hash) is False


class TestPasswordValidator:
    """Test password validation functionality."""

    def test_valid_password(self):
        """Test validation of a valid password."""
        password = "TestPassword123!"
        is_valid, errors = PasswordValidator.validate_password(password)

        assert is_valid is True
        assert len(errors) == 0

    def test_password_too_short(self):
        """Test validation of password that's too short."""
        password = "Test1!"
        is_valid, errors = PasswordValidator.validate_password(password)

        assert is_valid is False
        assert any("at least 8 characters" in error for error in errors)

    def test_password_no_uppercase(self):
        """Test validation of password without uppercase."""
        password = "testpassword123!"
        is_valid, errors = PasswordValidator.validate_password(password)

        assert is_valid is False
        assert any("uppercase letter" in error for error in errors)

    def test_password_no_lowercase(self):
        """Test validation of password without lowercase."""
        password = "TESTPASSWORD123!"
        is_valid, errors = PasswordValidator.validate_password(password)

        assert is_valid is False
        assert any("lowercase letter" in error for error in errors)

    def test_password_no_numbers(self):
        """Test validation of password without numbers."""
        password = "TestPassword!"
        is_valid, errors = PasswordValidator.validate_password(password)

        assert is_valid is False
        assert any("number" in error for error in errors)

    def test_password_no_special_chars(self):
        """Test validation of password without special characters."""
        password = "TestPassword123"
        is_valid, errors = PasswordValidator.validate_password(password)

        assert is_valid is False
        assert any("special character" in error for error in errors)


class TestPasswordGenerator:
    """Test password generation functionality."""

    def test_generate_secure_password_default_length(self):
        """Test generating password with default length."""
        password = PasswordGenerator.generate_secure_password()

        assert len(password) == 12

        # Validate the generated password meets requirements
        is_valid, errors = PasswordValidator.validate_password(password)
        assert is_valid is True, f"Generated password failed validation: {errors}"

    def test_generate_secure_password_custom_length(self):
        """Test generating password with custom length."""
        password = PasswordGenerator.generate_secure_password(16)

        assert len(password) == 16

        # Validate the generated password meets requirements
        is_valid, errors = PasswordValidator.validate_password(password)
        assert is_valid is True, f"Generated password failed validation: {errors}"

    def test_generate_secure_password_minimum_length(self):
        """Test generating password with length below minimum."""
        password = PasswordGenerator.generate_secure_password(4)

        # Should use minimum length instead
        assert len(password) == 8

        # Validate the generated password meets requirements
        is_valid, errors = PasswordValidator.validate_password(password)
        assert is_valid is True, f"Generated password failed validation: {errors}"

    def test_generate_multiple_passwords_are_different(self):
        """Test that multiple generated passwords are different."""
        password1 = PasswordGenerator.generate_secure_password()
        password2 = PasswordGenerator.generate_secure_password()

        assert password1 != password2


class TestPasswordUtilityFunctions:
    """Test utility functions."""

    def test_hash_and_validate_password_valid(self):
        """Test hash_and_validate_password with valid password."""
        password = "TestPassword123!"
        is_valid, hashed, errors = hash_and_validate_password(password)

        assert is_valid is True
        assert len(errors) == 0
        assert hashed != password
        assert len(hashed) > 50

        # Verify the hash works
        assert PasswordHasher.verify_password(password, hashed) is True

    def test_hash_and_validate_password_invalid(self):
        """Test hash_and_validate_password with invalid password."""
        password = "weak"
        is_valid, hashed, errors = hash_and_validate_password(password)

        assert is_valid is False
        assert hashed == ""
        assert len(errors) > 0

    def test_generate_and_hash_password(self):
        """Test generate_and_hash_password function."""
        plain, hashed = generate_and_hash_password()

        assert plain != hashed
        assert len(plain) == 12
        assert len(hashed) > 50

        # Verify the hash works
        assert PasswordHasher.verify_password(plain, hashed) is True

        # Verify the plain password is valid
        is_valid, errors = PasswordValidator.validate_password(plain)
        assert is_valid is True, f"Generated password failed validation: {errors}"
