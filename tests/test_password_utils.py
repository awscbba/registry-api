"""
Tests for password utilities.
"""

import pytest
import re
from src.utils.password_utils import (
    PasswordValidator,
    PasswordHasher,
    PasswordGenerator,
    PasswordHistoryManager,
    PasswordPolicy,
    hash_and_validate_password,
    generate_and_hash_password,
)


class TestPasswordValidator:
    """Test password validation functionality."""

    def test_valid_password(self):
        """Test that a valid password passes validation."""
        password = "SecurePass123!"
        is_valid, errors = PasswordValidator.validate_password(password)
        assert is_valid is True
        assert len(errors) == 0

    def test_password_too_short(self):
        """Test that short passwords are rejected."""
        password = "Short1!"
        is_valid, errors = PasswordValidator.validate_password(password)
        assert is_valid is False
        assert any("at least 8 characters" in error for error in errors)

    def test_password_missing_uppercase(self):
        """Test that passwords without uppercase are rejected."""
        password = "lowercase123!"
        is_valid, errors = PasswordValidator.validate_password(password)
        assert is_valid is False
        assert any("uppercase letter" in error for error in errors)

    def test_password_missing_lowercase(self):
        """Test that passwords without lowercase are rejected."""
        password = "UPPERCASE123!"
        is_valid, errors = PasswordValidator.validate_password(password)
        assert is_valid is False
        assert any("lowercase letter" in error for error in errors)

    def test_password_missing_number(self):
        """Test that passwords without numbers are rejected."""
        password = "NoNumbers!"
        is_valid, errors = PasswordValidator.validate_password(password)
        assert is_valid is False
        assert any("number" in error for error in errors)

    def test_password_missing_special_char(self):
        """Test that passwords without special characters are rejected."""
        password = "NoSpecial123"
        is_valid, errors = PasswordValidator.validate_password(password)
        assert is_valid is False
        assert any("special character" in error for error in errors)

    def test_password_multiple_errors(self):
        """Test that multiple validation errors are returned."""
        password = "bad"
        is_valid, errors = PasswordValidator.validate_password(password)
        assert is_valid is False
        assert len(errors) >= 4  # Should have multiple errors

    def test_check_password_reuse_empty_history(self):
        """Test password reuse check with empty history."""
        password = "NewPassword123!"
        is_reused = PasswordValidator.check_password_reuse(password, [])
        assert is_reused is False

    def test_check_password_reuse_not_in_history(self):
        """Test password reuse check with password not in history."""
        password = "NewPassword123!"
        old_hash = PasswordHasher.hash_password("OldPassword123!")
        history = [old_hash]
        is_reused = PasswordValidator.check_password_reuse(password, history)
        assert is_reused is False

    def test_check_password_reuse_in_history(self):
        """Test password reuse check with password in history."""
        password = "ReusedPassword123!"
        old_hash = PasswordHasher.hash_password(password)
        history = [old_hash]
        is_reused = PasswordValidator.check_password_reuse(password, history)
        assert is_reused is True


class TestPasswordHasher:
    """Test password hashing functionality."""

    def test_hash_password(self):
        """Test that password hashing works."""
        password = "TestPassword123!"
        hashed = PasswordHasher.hash_password(password)

        # Should be a string
        assert isinstance(hashed, str)
        # Should not be the original password
        assert hashed != password
        # Should start with bcrypt identifier
        assert hashed.startswith("$2b$")

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "TestPassword123!"
        hashed = PasswordHasher.hash_password(password)

        is_valid = PasswordHasher.verify_password(password, hashed)
        assert is_valid is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = PasswordHasher.hash_password(password)

        is_valid = PasswordHasher.verify_password(wrong_password, hashed)
        assert is_valid is False

    def test_verify_password_invalid_hash(self):
        """Test password verification with invalid hash."""
        password = "TestPassword123!"
        invalid_hash = "invalid_hash"

        is_valid = PasswordHasher.verify_password(password, invalid_hash)
        assert is_valid is False

    def test_hash_same_password_different_results(self):
        """Test that hashing the same password twice gives different results."""
        password = "TestPassword123!"
        hash1 = PasswordHasher.hash_password(password)
        hash2 = PasswordHasher.hash_password(password)

        # Hashes should be different due to different salts
        assert hash1 != hash2
        # But both should verify correctly
        assert PasswordHasher.verify_password(password, hash1)
        assert PasswordHasher.verify_password(password, hash2)


class TestPasswordGenerator:
    """Test password generation functionality."""

    def test_generate_secure_password_default_length(self):
        """Test password generation with default length."""
        password = PasswordGenerator.generate_secure_password()
        assert len(password) == 12

    def test_generate_secure_password_custom_length(self):
        """Test password generation with custom length."""
        password = PasswordGenerator.generate_secure_password(16)
        assert len(password) == 16

    def test_generate_secure_password_minimum_length(self):
        """Test that minimum length is enforced."""
        password = PasswordGenerator.generate_secure_password(4)  # Too short
        assert len(password) == PasswordPolicy.MIN_LENGTH

    def test_generated_password_meets_policy(self):
        """Test that generated passwords meet security policy."""
        password = PasswordGenerator.generate_secure_password()
        is_valid, errors = PasswordValidator.validate_password(password)
        assert is_valid is True
        assert len(errors) == 0

    def test_generated_passwords_are_different(self):
        """Test that multiple generated passwords are different."""
        password1 = PasswordGenerator.generate_secure_password()
        password2 = PasswordGenerator.generate_secure_password()
        assert password1 != password2

    def test_generated_password_contains_required_chars(self):
        """Test that generated password contains all required character types."""
        password = PasswordGenerator.generate_secure_password()

        # Check for uppercase
        assert re.search(r"[A-Z]", password) is not None
        # Check for lowercase
        assert re.search(r"[a-z]", password) is not None
        # Check for digit
        assert re.search(r"\d", password) is not None
        # Check for special character
        special_chars = re.escape(PasswordPolicy.SPECIAL_CHARS)
        assert re.search(f"[{special_chars}]", password) is not None


class TestPasswordHistoryManager:
    """Test password history management functionality."""

    def test_add_to_history_empty(self):
        """Test adding to empty history."""
        new_hash = "hash1"
        history = PasswordHistoryManager.add_to_history([], new_hash)
        assert history == [new_hash]

    def test_add_to_history_none(self):
        """Test adding to None history."""
        new_hash = "hash1"
        history = PasswordHistoryManager.add_to_history(None, new_hash)
        assert history == [new_hash]

    def test_add_to_history_existing(self):
        """Test adding to existing history."""
        existing_history = ["hash1", "hash2"]
        new_hash = "hash3"
        history = PasswordHistoryManager.add_to_history(existing_history, new_hash)
        assert history == [new_hash, "hash1", "hash2"]

    def test_add_to_history_limit(self):
        """Test that history is limited to prevent reuse count."""
        # Create history at the limit
        existing_history = [
            f"hash{i}" for i in range(PasswordPolicy.PREVENT_REUSE_COUNT)
        ]
        new_hash = "new_hash"

        history = PasswordHistoryManager.add_to_history(existing_history, new_hash)

        # Should still be at the limit
        assert len(history) == PasswordPolicy.PREVENT_REUSE_COUNT
        # New hash should be first
        assert history[0] == new_hash
        # Oldest hash should be removed
        assert f"hash{PasswordPolicy.PREVENT_REUSE_COUNT - 1}" not in history

    def test_can_use_password_new(self):
        """Test that new passwords can be used."""
        password = "NewPassword123!"
        history = []
        can_use, error = PasswordHistoryManager.can_use_password(password, history)
        assert can_use is True
        assert error == ""

    def test_can_use_password_reused(self):
        """Test that reused passwords cannot be used."""
        password = "ReusedPassword123!"
        old_hash = PasswordHasher.hash_password(password)
        history = [old_hash]

        can_use, error = PasswordHistoryManager.can_use_password(password, history)
        assert can_use is False
        assert "Cannot reuse" in error


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_hash_and_validate_password_valid(self):
        """Test hash and validate with valid password."""
        password = "ValidPassword123!"
        is_valid, hashed, errors = hash_and_validate_password(password)

        assert is_valid is True
        assert hashed != ""
        assert hashed != password
        assert len(errors) == 0
        assert PasswordHasher.verify_password(password, hashed)

    def test_hash_and_validate_password_invalid(self):
        """Test hash and validate with invalid password."""
        password = "bad"
        is_valid, hashed, errors = hash_and_validate_password(password)

        assert is_valid is False
        assert hashed == ""
        assert len(errors) > 0

    def test_hash_and_validate_password_with_history_reused(self):
        """Test hash and validate with password in history."""
        password = "ReusedPassword123!"
        old_hash = PasswordHasher.hash_password(password)
        history = [old_hash]

        is_valid, hashed, errors = hash_and_validate_password(password, history)

        assert is_valid is False
        assert hashed == ""
        assert len(errors) == 1
        assert "Cannot reuse" in errors[0]

    def test_hash_and_validate_password_with_history_new(self):
        """Test hash and validate with new password and history."""
        password = "NewPassword123!"
        old_hash = PasswordHasher.hash_password("OldPassword123!")
        history = [old_hash]

        is_valid, hashed, errors = hash_and_validate_password(password, history)

        assert is_valid is True
        assert hashed != ""
        assert len(errors) == 0

    def test_generate_and_hash_password(self):
        """Test generate and hash password function."""
        plain, hashed = generate_and_hash_password()

        # Plain password should meet policy
        is_valid, errors = PasswordValidator.validate_password(plain)
        assert is_valid is True
        assert len(errors) == 0

        # Hashed password should verify
        assert PasswordHasher.verify_password(plain, hashed)

        # Should be different strings
        assert plain != hashed

    def test_generate_and_hash_password_custom_length(self):
        """Test generate and hash password with custom length."""
        plain, hashed = generate_and_hash_password(16)

        assert len(plain) == 16
        assert PasswordHasher.verify_password(plain, hashed)


class TestPasswordPolicy:
    """Test password policy configuration."""

    def test_policy_constants(self):
        """Test that policy constants are set correctly."""
        assert PasswordPolicy.MIN_LENGTH == 8
        assert PasswordPolicy.REQUIRE_UPPERCASE is True
        assert PasswordPolicy.REQUIRE_LOWERCASE is True
        assert PasswordPolicy.REQUIRE_NUMBERS is True
        assert PasswordPolicy.REQUIRE_SPECIAL_CHARS is True
        assert PasswordPolicy.PREVENT_REUSE_COUNT == 5
        assert len(PasswordPolicy.SPECIAL_CHARS) > 0
