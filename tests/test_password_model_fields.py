"""
Unit tests for password fields in Person models.

This test suite specifically tests the bug fix where PersonCreate and PersonUpdate
models were missing password_hash fields, causing passwords to be generated but not saved.
"""

import pytest
from src.models.person import PersonCreate, PersonUpdate, Person


class TestPasswordModelFields:
    """Test that password fields are properly defined in all Person models."""

    def test_person_model_has_password_fields(self):
        """Test that Person model has password_hash and password_salt fields."""
        # Arrange
        person_data = {
            "id": "test-123",
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
            "createdAt": "2025-01-01T00:00:00",
            "updatedAt": "2025-01-01T00:00:00",
            "password_hash": "hashed_password_123",
            "password_salt": "salt_456"
        }

        # Act
        person = Person(**person_data)

        # Assert
        assert hasattr(person, "password_hash")
        assert hasattr(person, "password_salt")
        assert person.password_hash == "hashed_password_123"
        assert person.password_salt == "salt_456"

    def test_person_create_has_password_fields(self):
        """Test that PersonCreate model has password_hash and password_salt fields."""
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
            "password_hash": "hashed_password_create",
            "password_salt": "salt_create"
        }

        # Act
        person_create = PersonCreate(**person_data)

        # Assert
        assert hasattr(person_create, "password_hash")
        assert hasattr(person_create, "password_salt")
        assert person_create.password_hash == "hashed_password_create"
        assert person_create.password_salt == "salt_create"

    def test_person_update_has_password_fields(self):
        """Test that PersonUpdate model has password_hash and password_salt fields."""
        # Arrange
        update_data = {
            "firstName": "Updated",
            "password_hash": "hashed_password_update",
            "password_salt": "salt_update"
        }

        # Act
        person_update = PersonUpdate(**update_data)

        # Assert
        assert hasattr(person_update, "password_hash")
        assert hasattr(person_update, "password_salt")
        assert person_update.password_hash == "hashed_password_update"
        assert person_update.password_salt == "salt_update"

    def test_person_create_password_fields_optional(self):
        """Test that password fields are optional in PersonCreate."""
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

        # Act
        person_create = PersonCreate(**person_data)

        # Assert
        assert hasattr(person_create, "password_hash")
        assert hasattr(person_create, "password_salt")
        assert person_create.password_hash is None
        assert person_create.password_salt is None

    def test_person_update_password_fields_optional(self):
        """Test that password fields are optional in PersonUpdate."""
        # Arrange
        update_data = {
            "firstName": "Updated Name"
        }

        # Act
        person_update = PersonUpdate(**update_data)

        # Assert
        assert hasattr(person_update, "password_hash")
        assert hasattr(person_update, "password_salt")
        assert person_update.password_hash is None
        assert person_update.password_salt is None

    def test_password_fields_excluded_from_dict(self):
        """Test that password fields are excluded from model dict output (security)."""
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
            "password_hash": "secret_password",
            "password_salt": "secret_salt"
        }

        # Act
        person_create = PersonCreate(**person_data)
        person_dict = person_create.model_dump()

        # Assert
        assert "password_hash" not in person_dict
        assert "password_salt" not in person_dict
        assert person_create.password_hash == "secret_password"  # Still accessible directly
        assert person_create.password_salt == "secret_salt"  # Still accessible directly

    def test_person_update_only_password_change(self):
        """Test that PersonUpdate can be used to change only password."""
        # Arrange
        update_data = {
            "password_hash": "new_hashed_password"
        }

        # Act
        person_update = PersonUpdate(**update_data)

        # Assert
        assert person_update.password_hash == "new_hashed_password"
        assert person_update.first_name is None  # Other fields remain None
        assert person_update.last_name is None
        assert person_update.email is None

    def test_regression_password_fields_exist(self):
        """Regression test: Ensure password fields exist in all models.
        
        This test specifically prevents the bug where password_hash fields
        were missing from PersonCreate and PersonUpdate models, causing
        passwords to be generated but not saved to the database.
        """
        # Test PersonCreate
        person_create_fields = PersonCreate.model_fields.keys()
        assert "password_hash" in person_create_fields, "PersonCreate missing password_hash field"
        assert "password_salt" in person_create_fields, "PersonCreate missing password_salt field"

        # Test PersonUpdate  
        person_update_fields = PersonUpdate.model_fields.keys()
        assert "password_hash" in person_update_fields, "PersonUpdate missing password_hash field"
        assert "password_salt" in person_update_fields, "PersonUpdate missing password_salt field"

        # Test Person
        person_fields = Person.model_fields.keys()
        assert "password_hash" in person_fields, "Person missing password_hash field"
        assert "password_salt" in person_fields, "Person missing password_salt field"


if __name__ == "__main__":
    pytest.main([__file__])
