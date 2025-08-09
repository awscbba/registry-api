"""
Integration tests for password generation functionality.

This test suite ensures that the password generation bug (where passwords were
generated but not saved to database) never happens again.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
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
                "country": "Test Country",
            },
            "isAdmin": False,
            "password_hash": "hashed_password_123",
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
            "password_hash": "new_hashed_password_456",
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
                "country": "Test Country",
            },
            "password_hash": "secret_password",
        }

        # Act
        person_create = PersonCreate(**person_data)
        person_dict = person_create.model_dump()

        # Assert
        assert "password_hash" not in person_dict
        assert (
            person_create.password_hash == "secret_password"
        )  # Still accessible directly

    @pytest.mark.asyncio
    async def test_new_user_subscription_generates_and_saves_password(self):
        """Test that new user subscription generates password and saves it to database."""
        # Arrange
        mock_db_service = AsyncMock()
        mock_email_service = AsyncMock()

        # Mock no existing person
        mock_db_service.get_person_by_email.return_value = None

        # Mock project exists and has capacity
        mock_db_service.get_project.return_value = {
            "id": "project-123",
            "name": "Test Project",
            "maxParticipants": 10,
        }
        mock_db_service.get_project_subscription_count.return_value = 5

        # Mock person creation
        created_person = Person(
            id="person-123",
            firstName="Test",
            lastName="User",
            email="test@example.com",
            phone="1234567890",
            dateOfBirth="1990-01-01",
            address={
                "street": "123 Test St",
                "city": "Test City",
                "state": "Test State",
                "postalCode": "12345",
                "country": "Test Country",
            },
            isAdmin=False,
            createdAt="2025-01-01T00:00:00",
            updatedAt="2025-01-01T00:00:00",
        )
        mock_db_service.create_person.return_value = created_person

        # Mock subscription creation
        mock_db_service.create_subscription.return_value = {
            "id": "sub-123",
            "projectId": "project-123",
            "personId": "person-123",
            "status": "pending",
        }

        # Mock email service
        mock_email_service.generate_temporary_password.return_value = "TempPass123!"
        mock_email_service.send_welcome_email.return_value = MagicMock(success=True)

        # Act
        with (
            patch("src.handlers.versioned_api_handler.db_service", mock_db_service),
            patch(
                "src.handlers.versioned_api_handler.email_service", mock_email_service
            ),
        ):

            # Import here to use mocked services
            from src.handlers.versioned_api_handler import create_subscription_v2

            subscription_data = {
                "firstName": "Test",
                "lastName": "User",
                "email": "test@example.com",
                "phone": "1234567890",
                "notes": "Test subscription",
            }

            result = await create_subscription_v2("project-123", subscription_data)

        # Assert
        assert result["person_created"] is True
        assert result["temporary_password_generated"] is True

        # Verify person was created with password
        mock_db_service.create_person.assert_called_once()
        person_create_call = mock_db_service.create_person.call_args[0][0]
        assert hasattr(person_create_call, "password_hash")
        assert person_create_call.password_hash is not None

        # Verify password was hashed
        assert person_create_call.password_hash != "TempPass123!"  # Should be hashed

        # Verify email was sent with password
        mock_email_service.send_welcome_email.assert_called_once()
        email_call = mock_email_service.send_welcome_email.call_args[1]
        assert email_call["temporary_password"] == "TempPass123!"

    @pytest.mark.asyncio
    async def test_existing_user_without_password_gets_password(self):
        """Test that existing user without password gets password generated and saved."""
        # Arrange
        mock_db_service = AsyncMock()
        mock_email_service = AsyncMock()

        # Mock existing person without password
        existing_person = Person(
            id="person-456",
            firstName="Existing",
            lastName="User",
            email="existing@example.com",
            phone="1234567890",
            dateOfBirth="1990-01-01",
            address={
                "street": "456 Existing St",
                "city": "Existing City",
                "state": "Existing State",
                "postalCode": "67890",
                "country": "Existing Country",
            },
            isAdmin=False,
            createdAt="2025-01-01T00:00:00",
            updatedAt="2025-01-01T00:00:00",
        )
        # Simulate no password set
        existing_person.password_hash = None

        mock_db_service.get_person_by_email.return_value = existing_person
        mock_db_service.get_existing_subscription.return_value = None

        # Mock project
        mock_db_service.get_project.return_value = {
            "id": "project-456",
            "name": "Test Project",
            "maxParticipants": 10,
        }
        mock_db_service.get_project_subscription_count.return_value = 3

        # Mock subscription creation
        mock_db_service.create_subscription.return_value = {
            "id": "sub-456",
            "projectId": "project-456",
            "personId": "person-456",
            "status": "pending",
        }

        # Mock email service
        mock_email_service.generate_temporary_password.return_value = "NewPass456!"
        mock_email_service.send_welcome_email.return_value = MagicMock(success=True)

        # Act
        with (
            patch("src.handlers.versioned_api_handler.db_service", mock_db_service),
            patch(
                "src.handlers.versioned_api_handler.email_service", mock_email_service
            ),
        ):

            from src.handlers.versioned_api_handler import create_subscription_v2

            subscription_data = {
                "firstName": "Existing",
                "lastName": "User",
                "email": "existing@example.com",
                "phone": "1234567890",
                "notes": "Test existing user subscription",
            }

            result = await create_subscription_v2("project-456", subscription_data)

        # Assert
        assert result["person_created"] is False
        assert result["password_generated_for_existing_user"] is True
        assert result["temporary_password_generated"] is True

        # Verify existing person was updated with password
        mock_db_service.update_person.assert_called_once()
        person_update_call = mock_db_service.update_person.call_args[0][1]
        assert hasattr(person_update_call, "password_hash")
        assert person_update_call.password_hash is not None

        # Verify password was hashed
        assert person_update_call.password_hash != "NewPass456!"  # Should be hashed

        # Verify email was sent
        mock_email_service.send_welcome_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_existing_user_with_password_no_change(self):
        """Test that existing user with password doesn't get new password."""
        # Arrange
        mock_db_service = AsyncMock()
        mock_email_service = AsyncMock()

        # Mock existing person WITH password
        existing_person = Person(
            id="person-789",
            firstName="HasPassword",
            lastName="User",
            email="haspassword@example.com",
            phone="1234567890",
            dateOfBirth="1990-01-01",
            address={
                "street": "789 Password St",
                "city": "Password City",
                "state": "Password State",
                "postalCode": "11111",
                "country": "Password Country",
            },
            isAdmin=False,
            createdAt="2025-01-01T00:00:00",
            updatedAt="2025-01-01T00:00:00",
        )
        # Simulate existing password
        existing_person.password_hash = "existing_hashed_password"

        mock_db_service.get_person_by_email.return_value = existing_person
        mock_db_service.get_existing_subscription.return_value = None

        # Mock project
        mock_db_service.get_project.return_value = {
            "id": "project-789",
            "name": "Test Project",
            "maxParticipants": 10,
        }
        mock_db_service.get_project_subscription_count.return_value = 2

        # Mock subscription creation
        mock_db_service.create_subscription.return_value = {
            "id": "sub-789",
            "projectId": "project-789",
            "personId": "person-789",
            "status": "pending",
        }

        # Act
        with (
            patch("src.handlers.versioned_api_handler.db_service", mock_db_service),
            patch(
                "src.handlers.versioned_api_handler.email_service", mock_email_service
            ),
        ):

            from src.handlers.versioned_api_handler import create_subscription_v2

            subscription_data = {
                "firstName": "HasPassword",
                "lastName": "User",
                "email": "haspassword@example.com",
                "phone": "1234567890",
                "notes": "Test user with existing password",
            }

            result = await create_subscription_v2("project-789", subscription_data)

        # Assert
        assert result["person_created"] is False
        assert result.get("password_generated_for_existing_user", False) is False
        assert result["temporary_password_generated"] is False

        # Verify person was NOT updated (no password change needed)
        mock_db_service.update_person.assert_not_called()

        # Verify no welcome email was sent (user already has password)
        mock_email_service.send_welcome_email.assert_not_called()

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
        assert any(
            c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password
        )  # Has special chars


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
                "country": "Test Country",
            },
        }

        # Act & Assert - Should not raise exception
        person_create = PersonCreate(**person_data)
        assert person_create.password_hash is None

    def test_person_update_password_optional(self):
        """Test that password_hash is optional in PersonUpdate."""
        # Arrange
        update_data = {"firstName": "Updated Name"}

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
                "country": "Test Country",
            },
            "password_hash": "hashed_password",
            "password_salt": "random_salt_123",
        }

        # Act
        person_create = PersonCreate(**person_data)

        # Assert
        assert person_create.password_hash == "hashed_password"
        assert person_create.password_salt == "random_salt_123"


if __name__ == "__main__":
    pytest.main([__file__])
