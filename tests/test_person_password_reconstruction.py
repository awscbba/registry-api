"""
Test to verify that Person objects reconstructed from DynamoDB include password fields.
This addresses the bug where passwords were stored but not loaded back into Person objects.
"""

import pytest
from unittest.mock import AsyncMock, patch
from src.services.defensive_dynamodb_service import DefensiveDynamoDBService


class TestPersonPasswordReconstruction:
    """Test that Person objects include password fields when loaded from database."""

    @pytest.mark.asyncio
    async def test_person_object_includes_password_fields_from_dynamodb(self):
        """Test that Person objects reconstructed from DynamoDB include password_hash."""
        # Arrange
        mock_table = AsyncMock()
        mock_table.get_item = AsyncMock(
            return_value={
                "Item": {
                    "id": "test-person-id",
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
                    "createdAt": "2025-01-01T00:00:00",
                    "updatedAt": "2025-01-01T00:00:00",
                    # Password fields stored in DynamoDB
                    "password_hash": "hashed_password_123",
                    "password_salt": "salt_456",
                }
            }
        )

        with patch(
            "src.services.defensive_dynamodb_service.get_dynamodb_table",
            return_value=mock_table,
        ):
            db_service = DefensiveDynamoDBService()

            # Act
            person = await db_service.get_person("test-person-id")

            # Assert
            assert person is not None, "Person should be found"
            assert hasattr(
                person, "password_hash"
            ), "Person should have password_hash attribute"
            assert hasattr(
                person, "password_salt"
            ), "Person should have password_salt attribute"
            assert (
                person.password_hash == "hashed_password_123"
            ), "password_hash should match stored value"
            assert (
                person.password_salt == "salt_456"
            ), "password_salt should match stored value"

    @pytest.mark.asyncio
    async def test_person_object_handles_missing_password_fields(self):
        """Test that Person objects handle missing password fields gracefully."""
        # Arrange
        mock_table = AsyncMock()
        mock_table.get_item = AsyncMock(
            return_value={
                "Item": {
                    "id": "test-person-no-password",
                    "firstName": "Test",
                    "lastName": "NoPassword",
                    "email": "nopassword@example.com",
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
                    "createdAt": "2025-01-01T00:00:00",
                    "updatedAt": "2025-01-01T00:00:00",
                    # No password fields in DynamoDB
                }
            }
        )

        with patch(
            "src.services.defensive_dynamodb_service.get_dynamodb_table",
            return_value=mock_table,
        ):
            db_service = DefensiveDynamoDBService()

            # Act
            person = await db_service.get_person("test-person-no-password")

            # Assert
            assert person is not None, "Person should be found"
            assert hasattr(
                person, "password_hash"
            ), "Person should have password_hash attribute"
            assert hasattr(
                person, "password_salt"
            ), "Person should have password_salt attribute"
            assert (
                person.password_hash is None
            ), "password_hash should be None when not stored"
            assert (
                person.password_salt is None
            ), "password_salt should be None when not stored"

    @pytest.mark.asyncio
    async def test_get_person_by_email_includes_password_fields(self):
        """Test that get_person_by_email also includes password fields."""
        # Arrange
        mock_table = AsyncMock()
        mock_table.scan = AsyncMock(
            return_value={
                "Items": [
                    {
                        "id": "test-person-email",
                        "firstName": "Email",
                        "lastName": "Test",
                        "email": "email.test@example.com",
                        "phone": "1234567890",
                        "dateOfBirth": "1990-01-01",
                        "address": {
                            "street": "123 Email St",
                            "city": "Email City",
                            "state": "Email State",
                            "postalCode": "12345",
                            "country": "Email Country",
                        },
                        "isAdmin": False,
                        "createdAt": "2025-01-01T00:00:00",
                        "updatedAt": "2025-01-01T00:00:00",
                        # Password fields stored in DynamoDB
                        "password_hash": "email_hashed_password_789",
                        "password_salt": "email_salt_012",
                    }
                ]
            }
        )

        with patch(
            "src.services.defensive_dynamodb_service.get_dynamodb_table",
            return_value=mock_table,
        ):
            db_service = DefensiveDynamoDBService()

            # Act
            person = await db_service.get_person_by_email("email.test@example.com")

            # Assert
            assert person is not None, "Person should be found by email"
            assert hasattr(
                person, "password_hash"
            ), "Person should have password_hash attribute"
            assert hasattr(
                person, "password_salt"
            ), "Person should have password_salt attribute"
            assert (
                person.password_hash == "email_hashed_password_789"
            ), "password_hash should match stored value"
            assert (
                person.password_salt == "email_salt_012"
            ), "password_salt should match stored value"


if __name__ == "__main__":
    pytest.main([__file__])
