"""
Integration tests for password generation functionality.

This test suite ensures that the password generation bug (where passwords were
generated but not saved to database) never happens again.
"""

import pytest
from unittest.mock import MagicMock
from src.models.person import PersonCreate, PersonUpdate, Person
from src.services.email_service import EmailService
from src.utils.password_utils import PasswordHasher


class TestPasswordGenerationIntegration:
    """Test password generation for new and existing users."""

    def test_person_create_model_accepts_password_hash(self):
        """Test that PersonCreate model can accept password_hash field."""
        # Arrange
        person_data = {
            "firstName": "Test",
            "lastName": "User",
            "email": "test@example.com",
            "phone": "1234567890",
            "dateOfBirth": "1990-01-01",
            "address": {
                "street": "123 Test St",
                "city": "Test City",
                "state": "Test State",
                "postalCode": "12345",
                "country": "Test Country"
            },
            "isAdmin": False,
            "password_hash": "hashed_password_123"
        }

        # Act
        person_create = PersonCreate(**person_data)

        # Assert
        assert person_create.password_hash == "hashed_password_123"
        assert hasattr(person_create, "password_hash")

    def test_person_update_model_accepts_password_hash(self):
        """Test that PersonUpdate model can accept password_hash field."""
        # Arrange
        update_data = {
            "firstName": "Updated",
            "password_hash": "new_hashed_password_456"
        }

        # Act
        person_update = PersonUpdate(**update_data)

        # Assert
        assert person_update.password_hash == "new_hashed_password_456"
        assert hasattr(person_update, "password_hash")

    def test_person_create_excludes_password_from_dict(self):
        """Test that password_hash is excluded from model dict (security)."""
        # Arrange
        person_data = {
            "firstName": "Test",
            "lastName": "User", 
            "email": "test@example.com",
            "phone": "1234567890",
            "dateOfBirth": "1990-01-01",
            "address": {
                "street": "123 Test St",
                "city": "Test City",
                "state": "Test State",
                "postalCode": "12345",
                "country": "Test Country"
            },
            "password_hash": "secret_password"
        }

        # Act
        person_create = PersonCreate(**person_data)
        person_dict = person_create.model_dump()

        # Assert
        assert "password_hash" not in person_dict
        assert person_create.password_hash == "secret_password"  # Still accessible directly

    def test_password_hashing_consistency(self):
        """Test that password hashing is consistent between generation and verification."""
        # Arrange
        original_password = "TestPassword123!"
        
        # Act
        hashed_password = PasswordHasher.hash_password(original_password)
        is_valid = PasswordHasher.verify_password(original_password, hashed_password)
        
        # Assert
        assert hashed_password != original_password  # Password should be hashed
        assert is_valid is True  # Verification should work
        assert len(hashed_password) > 20  # Hashed password should be longer

    def test_password_generation_strength(self):
        """Test that generated passwords meet security requirements."""
        # Arrange
        email_service = EmailService()
        
        # Act
        password = email_service.generate_temporary_password()
        
        # Assert
        assert len(password) >= 8  # Minimum length
        assert any(c.isupper() for c in password)  # Has uppercase
        assert any(c.islower() for c in password)  # Has lowercase  
        assert any(c.isdigit() for c in password)  # Has digits
        assert any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)  # Has special chars


class TestPasswordModelValidation:
    """Test password field validation in models."""

    def test_person_create_password_optional(self):
        """Test that password_hash is optional in PersonCreate."""
        # Arrange
        person_data = {
            "firstName": "Test",
            "lastName": "User",
            "email": "test@example.com", 
            "phone": "1234567890",
            "dateOfBirth": "1990-01-01",
            "address": {
                "street": "123 Test St",
                "city": "Test City",
                "state": "Test State",
                "postalCode": "12345",
                "country": "Test Country"
            }
        }

        # Act & Assert - Should not raise exception
        person_create = PersonCreate(**person_data)
        assert person_create.password_hash is None

    def test_person_update_password_optional(self):
        """Test that password_hash is optional in PersonUpdate."""
        # Arrange
        update_data = {
            "firstName": "Updated Name"
        }

        # Act & Assert - Should not raise exception
        person_update = PersonUpdate(**update_data)
        assert person_update.password_hash is None

    def test_person_create_with_password_salt(self):
        """Test that PersonCreate accepts password_salt field."""
        # Arrange
        person_data = {
            "firstName": "Test",
            "lastName": "User",
            "email": "test@example.com",
            "phone": "1234567890", 
            "dateOfBirth": "1990-01-01",
            "address": {
                "street": "123 Test St",
                "city": "Test City",
                "state": "Test State",
                "postalCode": "12345",
                "country": "Test Country"
            },
            "password_hash": "hashed_password",
            "password_salt": "random_salt_123"
        }

        # Act
        person_create = PersonCreate(**person_data)

        # Assert
        assert person_create.password_hash == "hashed_password"
        assert person_create.password_salt == "random_salt_123"

    def test_critical_bug_prevention(self):
        """Critical test: Ensure password fields can be used in person creation workflow.
        
        This test simulates the exact workflow that was broken:
        1. Generate password
        2. Hash password  
        3. Add to person_data dict
        4. Create PersonCreate model
        5. Verify password is accessible for database storage
        """
        # Arrange - Simulate subscription workflow
        email_service = EmailService()
        
        # Step 1: Generate password (this was working)
        temporary_password = email_service.generate_temporary_password()
        
        # Step 2: Hash password (this was working)
        hashed_password = PasswordHasher.hash_password(temporary_password)
        
        # Step 3: Add to person data (this was working)
        person_data = {
            "firstName": "Critical",
            "lastName": "Test",
            "email": "critical@example.com",
            "phone": "1234567890",
            "dateOfBirth": "1990-01-01",
            "address": {
                "street": "123 Critical St",
                "city": "Critical City",
                "state": "Critical State",
                "postalCode": "12345",
                "country": "Critical Country"
            },
            "password_hash": hashed_password  # This was being ignored!
        }
        
        # Step 4: Create PersonCreate model (this was the bug - password_hash was excluded)
        person_create = PersonCreate(**person_data)
        
        # Step 5: Verify password is accessible (this was failing before the fix)
        assert hasattr(person_create, "password_hash"), "PersonCreate must have password_hash field"
        assert person_create.password_hash == hashed_password, "Password hash must be preserved"
        assert person_create.password_hash is not None, "Password hash must not be None"
        assert len(person_create.password_hash) > 20, "Password hash must be properly hashed"
        
        # Additional verification: password should be excluded from dict but accessible directly
        person_dict = person_create.model_dump()
        assert "password_hash" not in person_dict, "Password must be excluded from API responses (security)"
        assert person_create.password_hash == hashed_password, "But password must still be accessible for database storage"


if __name__ == "__main__":
    pytest.main([__file__])
