"""
Password utilities for secure password hashing, validation, and generation.
"""

import bcrypt
import secrets
import string
import re
from typing import List, Tuple
from datetime import datetime


class PasswordPolicy:
    """Password security policy configuration."""

    MIN_LENGTH = 8
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_NUMBERS = True
    REQUIRE_SPECIAL_CHARS = True
    PREVENT_REUSE_COUNT = 5
    SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"


class PasswordValidator:
    """Validates passwords against security policy."""

    @staticmethod
    def validate_password(password: str) -> Tuple[bool, List[str]]:
        """
        Validate password against security policy.

        Args:
            password: The password to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check minimum length
        if len(password) < PasswordPolicy.MIN_LENGTH:
            errors.append(
                f"Password must be at least {PasswordPolicy.MIN_LENGTH} characters long"
            )

        # Check for uppercase letter
        if PasswordPolicy.REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")

        # Check for lowercase letter
        if PasswordPolicy.REQUIRE_LOWERCASE and not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")

        # Check for number
        if PasswordPolicy.REQUIRE_NUMBERS and not re.search(r"\d", password):
            errors.append("Password must contain at least one number")

        # Check for special character
        if PasswordPolicy.REQUIRE_SPECIAL_CHARS:
            special_char_pattern = f"[{re.escape(PasswordPolicy.SPECIAL_CHARS)}]"
            if not re.search(special_char_pattern, password):
                errors.append("Password must contain at least one special character")

        return len(errors) == 0, errors

    @staticmethod
    def check_password_reuse(password: str, password_history: List[str]) -> bool:
        """
        Check if password has been used recently.

        Args:
            password: The new password to check
            password_history: List of previous password hashes

        Returns:
            True if password is reused (should be rejected), False if it's new
        """
        if not password_history:
            return False

        for old_hash in password_history:
            if PasswordHasher.verify_password(password, old_hash):
                return True
        return False


class PasswordHasher:
    """Handles secure password hashing and verification."""

    # Use 12 rounds for bcrypt (secure but not too slow)
    SALT_ROUNDS = 12

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt with salt.

        Args:
            password: The plain text password to hash

        Returns:
            The hashed password as a string
        """
        # Generate salt and hash password
        salt = bcrypt.gensalt(rounds=PasswordHasher.SALT_ROUNDS)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            password: The plain text password to verify
            hashed_password: The stored hash to verify against

        Returns:
            True if password matches, False otherwise
        """
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"), hashed_password.encode("utf-8")
            )
        except (ValueError, TypeError):
            return False


class PasswordGenerator:
    """Generates secure random passwords."""

    @staticmethod
    def generate_secure_password(length: int = 12) -> str:
        """
        Generate a secure random password that meets policy requirements.

        Args:
            length: Length of password to generate (minimum 8)

        Returns:
            A secure random password
        """
        if length < PasswordPolicy.MIN_LENGTH:
            length = PasswordPolicy.MIN_LENGTH

        # Ensure we have at least one character from each required category
        password_chars = []

        # Add required character types
        if PasswordPolicy.REQUIRE_UPPERCASE:
            password_chars.append(secrets.choice(string.ascii_uppercase))

        if PasswordPolicy.REQUIRE_LOWERCASE:
            password_chars.append(secrets.choice(string.ascii_lowercase))

        if PasswordPolicy.REQUIRE_NUMBERS:
            password_chars.append(secrets.choice(string.digits))

        if PasswordPolicy.REQUIRE_SPECIAL_CHARS:
            password_chars.append(secrets.choice(PasswordPolicy.SPECIAL_CHARS))

        # Fill remaining length with random characters from all allowed sets
        all_chars = string.ascii_letters + string.digits + PasswordPolicy.SPECIAL_CHARS
        remaining_length = length - len(password_chars)

        for _ in range(remaining_length):
            password_chars.append(secrets.choice(all_chars))

        # Shuffle the password to avoid predictable patterns
        secrets.SystemRandom().shuffle(password_chars)

        return "".join(password_chars)


class PasswordHistoryManager:
    """Manages password history for reuse prevention."""

    @staticmethod
    def add_to_history(current_history: List[str], new_password_hash: str) -> List[str]:
        """
        Add a new password hash to history and maintain the limit.

        Args:
            current_history: Current password history list
            new_password_hash: New password hash to add

        Returns:
            Updated password history list
        """
        if current_history is None:
            current_history = []

        # Add new hash to the beginning
        updated_history = [new_password_hash] + current_history

        # Keep only the last N passwords
        return updated_history[: PasswordPolicy.PREVENT_REUSE_COUNT]

    @staticmethod
    def can_use_password(
        password: str, password_history: List[str]
    ) -> Tuple[bool, str]:
        """
        Check if a password can be used (not in recent history).

        Args:
            password: The password to check
            password_history: List of recent password hashes

        Returns:
            Tuple of (can_use, error_message)
        """
        if PasswordValidator.check_password_reuse(password, password_history or []):
            return (
                False,
                f"Cannot reuse any of the last {PasswordPolicy.PREVENT_REUSE_COUNT} passwords",
            )
        return True, ""


# Convenience functions for common operations
def hash_and_validate_password(
    password: str, password_history: List[str] = None
) -> Tuple[bool, str, List[str]]:
    """
    Validate and hash a password in one operation.

    Args:
        password: The password to validate and hash
        password_history: Optional password history for reuse checking

    Returns:
        Tuple of (is_valid, hashed_password_or_empty, list_of_errors)
    """
    # Validate password policy
    is_valid, errors = PasswordValidator.validate_password(password)
    if not is_valid:
        return False, "", errors

    # Check password reuse if history provided
    if password_history:
        can_use, reuse_error = PasswordHistoryManager.can_use_password(
            password, password_history
        )
        if not can_use:
            return False, "", [reuse_error]

    # Hash the password
    hashed_password = PasswordHasher.hash_password(password)
    return True, hashed_password, []


def generate_and_hash_password(length: int = 12) -> Tuple[str, str]:
    """
    Generate a secure password and return both plain and hashed versions.

    Args:
        length: Length of password to generate

    Returns:
        Tuple of (plain_password, hashed_password)
    """
    plain_password = PasswordGenerator.generate_secure_password(length)
    hashed_password = PasswordHasher.hash_password(plain_password)
    return plain_password, hashed_password
