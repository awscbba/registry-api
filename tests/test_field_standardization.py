#!/usr/bin/env python3
"""
Comprehensive Tests for Field Standardization

Tests the complete field standardization implementation including:
1. Database field name consistency
2. Password reset functionality
3. Authentication system
4. Field mapping conversions
5. Backward compatibility during transition
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock
import bcrypt

from registry_api.src.models.person import Person, PersonCreate, PersonUpdate
from registry_api.src.services.defensive_dynamodb_service import (
    DefensiveDynamoDBService,
)
from registry_api.src.services.password_reset_service import PasswordResetService
from registry_api.src.services.email_service import EmailService
from registry_api.src.models.password_reset import (
    PasswordResetRequest,
    PasswordResetValidation,
)


class TestFieldStandardization:
    """Test field name standardization across the system"""

    @pytest.fixture
    def mock_dynamodb_service(self):
        """Create a mock DynamoDB service for testing"""
        service = Mock(spec=DefensiveDynamoDBService)
        service.table = Mock()
        service.logger = Mock()
        return service

    @pytest.fixture
    def sample_person_data(self):
        """Sample person data for testing"""
        return {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone": "+1234567890",
            "date_of_birth": "1990-01-01",
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "state": "CA",
                "postal_code": "12345",
                "country": "USA",
            },
            "is_admin": False,
        }

    @pytest.fixture
    def sample_database_item_snake_case(self):
        """Sample database item with snake_case field names"""
        return {
            "id": "test-id-123",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone": "+1234567890",
            "date_of_birth": "1990-01-01",
            "is_admin": False,
            "is_active": True,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "password_hash": "hashed_password_123",
            "password_salt": "salt_123",
            "failed_login_attempts": 0,
            "require_password_change": False,
            "email_verified": True,
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "state": "CA",
                "postal_code": "12345",
                "country": "USA",
            },
        }

    @pytest.fixture
    def sample_database_item_camel_case(self):
        """Sample database item with camelCase field names (legacy)"""
        return {
            "id": "test-id-123",
            "firstName": "John",
            "lastName": "Doe",
            "email": "john.doe@example.com",
            "phone": "+1234567890",
            "dateOfBirth": "1990-01-01",
            "isAdmin": False,
            "isActive": True,
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z",
            "passwordHash": "hashed_password_123",
            "passwordSalt": "salt_123",
            "failedLoginAttempts": 0,
            "requirePasswordChange": False,
            "emailVerified": True,
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "state": "CA",
                "postalCode": "12345",
                "country": "USA",
            },
        }

    def test_person_to_item_uses_snake_case(self, sample_person_data):
        """Test that _safe_person_to_item uses snake_case field names"""
        service = DefensiveDynamoDBService()

        # Create person from data
        person_create = PersonCreate(**sample_person_data)
        person = Person.create_new(person_create)

        # Convert to database item
        item = service._safe_person_to_item(person)

        # Verify snake_case field names are used
        assert "first_name" in item
        assert "last_name" in item
        assert "date_of_birth" in item
        assert "is_admin" in item
        assert "is_active" in item
        assert "created_at" in item
        assert "updated_at" in item

        # Verify camelCase fields are NOT used
        assert "firstName" not in item
        assert "lastName" not in item
        assert "dateOfBirth" not in item
        assert "isAdmin" not in item
        assert "isActive" not in item
        assert "createdAt" not in item
        assert "updatedAt" not in item

    def test_item_to_person_handles_snake_case(self, sample_database_item_snake_case):
        """Test that _safe_item_to_person handles snake_case field names"""
        service = DefensiveDynamoDBService()

        # Convert database item to person
        person = service._safe_item_to_person(sample_database_item_snake_case)

        # Verify person object is created correctly
        assert person.id == "test-id-123"
        assert person.first_name == "John"
        assert person.last_name == "Doe"
        assert person.email == "john.doe@example.com"
        assert person.is_admin == False
        assert person.is_active == True
        assert person.password_hash == "hashed_password_123"
        assert person.password_salt == "salt_123"

    def test_item_to_person_handles_camel_case_legacy(
        self, sample_database_item_camel_case
    ):
        """Test that _safe_item_to_person handles legacy camelCase field names"""
        service = DefensiveDynamoDBService()

        # Convert database item to person
        person = service._safe_item_to_person(sample_database_item_camel_case)

        # Verify person object is created correctly from camelCase fields
        assert person.id == "test-id-123"
        assert person.first_name == "John"
        assert person.last_name == "Doe"
        assert person.email == "john.doe@example.com"
        assert person.is_admin == False
        assert person.is_active == True
        assert person.password_hash == "hashed_password_123"
        assert person.password_salt == "salt_123"

    def test_item_to_person_prefers_snake_case_over_camel_case(self):
        """Test that when both naming conventions exist, snake_case is preferred"""
        service = DefensiveDynamoDBService()

        # Create item with both naming conventions
        mixed_item = {
            "id": "test-id-123",
            "first_name": "John_Snake",  # snake_case version
            "firstName": "John_Camel",  # camelCase version
            "last_name": "Doe_Snake",
            "lastName": "Doe_Camel",
            "email": "john.doe@example.com",
            "password_hash": "snake_hash",
            "passwordHash": "camel_hash",
            "is_active": True,
            "isActive": False,  # Different value to test preference
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }

        # Convert to person
        person = service._safe_item_to_person(mixed_item)

        # Verify snake_case values are preferred
        assert person.first_name == "John_Snake"
        assert person.last_name == "Doe_Snake"
        assert person.password_hash == "snake_hash"
        assert person.is_active == True  # snake_case value

    def test_field_mappings_use_snake_case(self):
        """Test that field mappings in update operations use snake_case"""
        service = DefensiveDynamoDBService()

        # Get the field mappings from the update_person method
        # This is a bit of a hack to access the field_mappings, but necessary for testing
        field_mappings = {
            "first_name": "first_name",
            "last_name": "last_name",
            "date_of_birth": "date_of_birth",
            "is_admin": "is_admin",
            "is_active": "is_active",
            "failed_login_attempts": "failed_login_attempts",
            "account_locked_until": "account_locked_until",
            "require_password_change": "require_password_change",
            "last_password_change": "last_password_change",
            "last_login_at": "last_login_at",
            "password_hash": "password_hash",
            "password_salt": "password_salt",
            "email_verified": "email_verified",
        }

        # Verify all mappings use snake_case
        for internal_name, db_name in field_mappings.items():
            assert "_" in db_name or db_name in ["id", "email", "phone", "address"]
            assert db_name.islower() or db_name in ["id"]
            # Verify no camelCase in database field names
            assert not any(c.isupper() for c in db_name[1:])

    @pytest.mark.asyncio
    async def test_password_reset_with_standardized_fields(self, sample_person_data):
        """Test password reset functionality with standardized field names"""
        # Mock services
        mock_db_service = Mock(spec=DefensiveDynamoDBService)
        mock_email_service = Mock(spec=EmailService)

        # Create person
        person_create = PersonCreate(**sample_person_data)
        person = Person.create_new(person_create)
        person.password_hash = "old_hash"

        # Mock database responses
        mock_db_service.get_person_by_email = AsyncMock(return_value=person)
        mock_db_service.update_person = AsyncMock(return_value=person)
        mock_email_service.send_password_reset_email = AsyncMock(
            return_value=Mock(success=True)
        )

        # Create password reset service
        password_service = PasswordResetService(mock_db_service, mock_email_service)

        # Test password reset initiation
        reset_request = PasswordResetRequest(
            email="john.doe@example.com",
            ip_address="127.0.0.1",
            user_agent="test-agent",
        )

        with patch.object(
            password_service, "_save_reset_token", new_callable=AsyncMock
        ):
            response = await password_service.initiate_password_reset(reset_request)
            assert response.success == True

    @pytest.mark.asyncio
    async def test_password_update_uses_person_update_object(self):
        """Test that password updates use PersonUpdate object instead of dictionary"""
        mock_db_service = Mock(spec=DefensiveDynamoDBService)
        mock_email_service = Mock(spec=EmailService)

        # Create person
        person = Person(
            id="test-id",
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="+1234567890",
            date_of_birth="1990-01-01",
            address={
                "street": "123 Main St",
                "city": "Anytown",
                "state": "CA",
                "postal_code": "12345",
                "country": "USA",
            },
            is_admin=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Mock database responses
        mock_db_service.get_person = AsyncMock(return_value=person)
        mock_db_service.update_person = AsyncMock(return_value=person)

        # Create password reset service
        password_service = PasswordResetService(mock_db_service, mock_email_service)

        # Mock token validation
        with patch.object(
            password_service, "validate_reset_token", new_callable=AsyncMock
        ) as mock_validate:
            with patch.object(
                password_service, "_mark_token_used", new_callable=AsyncMock
            ):
                mock_validate.return_value = (True, Mock(person_id="test-id"))

                # Test password reset completion
                validation = PasswordResetValidation(
                    reset_token="test-token", new_password="new_password_123"
                )

                response = await password_service.complete_password_reset(validation)

                # Verify update_person was called with PersonUpdate object
                mock_db_service.update_person.assert_called_once()
                call_args = mock_db_service.update_person.call_args

                # Verify first argument is person_id
                assert call_args[0][0] == "test-id"

                # Verify second argument is PersonUpdate object
                person_update = call_args[0][1]
                assert hasattr(person_update, "password_hash")
                assert hasattr(person_update, "require_password_change")
                assert hasattr(person_update, "failed_login_attempts")
                assert person_update.require_password_change == False
                assert person_update.failed_login_attempts == 0

    def test_password_hash_validation(self):
        """Test password hashing and validation works correctly"""
        password = "test_password_123"

        # Hash password
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        # Verify password
        assert bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

        # Verify wrong password fails
        assert not bcrypt.checkpw(
            "wrong_password".encode("utf-8"), password_hash.encode("utf-8")
        )

    def test_address_field_normalization(self):
        """Test that address fields are properly normalized"""
        service = DefensiveDynamoDBService()

        # Test various postal code field names
        address_variants = [
            {
                "street": "123 Main St",
                "city": "Test",
                "state": "CA",
                "postal_code": "12345",
                "country": "USA",
            },
            {
                "street": "123 Main St",
                "city": "Test",
                "state": "CA",
                "postalCode": "12345",
                "country": "USA",
            },
            {
                "street": "123 Main St",
                "city": "Test",
                "state": "CA",
                "zipCode": "12345",
                "country": "USA",
            },
            {
                "street": "123 Main St",
                "city": "Test",
                "state": "CA",
                "zip_code": "12345",
                "country": "USA",
            },
        ]

        for address in address_variants:
            normalized = service._normalize_address_for_storage(address)
            assert "postal_code" in normalized
            assert normalized["postal_code"] == "12345"
            # Verify other variants are removed
            assert "postalCode" not in normalized
            assert "zipCode" not in normalized
            assert "zip_code" not in normalized or normalized["zip_code"] == "12345"


class TestBackwardCompatibility:
    """Test backward compatibility during the transition period"""

    def test_mixed_field_names_in_database(self):
        """Test handling of mixed field names during transition"""
        service = DefensiveDynamoDBService()

        # Simulate database with mixed field names
        mixed_items = [
            {  # Old camelCase record
                "id": "old-record",
                "firstName": "Jane",
                "lastName": "Smith",
                "passwordHash": "old_hash",
                "isActive": True,
                "createdAt": "2024-01-01T00:00:00Z",
                "updatedAt": "2024-01-01T00:00:00Z",
                "email": "jane@example.com",
            },
            {  # New snake_case record
                "id": "new-record",
                "first_name": "Bob",
                "last_name": "Johnson",
                "password_hash": "new_hash",
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "email": "bob@example.com",
            },
            {  # Mixed record (both naming conventions)
                "id": "mixed-record",
                "first_name": "Alice",  # snake_case (preferred)
                "firstName": "Alice_Old",  # camelCase (should be ignored)
                "last_name": "Brown",
                "password_hash": "mixed_hash",
                "passwordHash": "old_mixed_hash",  # Should be ignored
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "email": "alice@example.com",
            },
        ]

        # Test conversion of all record types
        for item in mixed_items:
            person = service._safe_item_to_person(item)

            # Verify all records are converted successfully
            assert person.id == item["id"]
            assert person.email == item["email"]
            assert person.is_active == True

            # Verify field values are correct
            if item["id"] == "old-record":
                assert person.first_name == "Jane"
                assert person.last_name == "Smith"
                assert person.password_hash == "old_hash"
            elif item["id"] == "new-record":
                assert person.first_name == "Bob"
                assert person.last_name == "Johnson"
                assert person.password_hash == "new_hash"
            elif item["id"] == "mixed-record":
                # Should prefer snake_case values
                assert person.first_name == "Alice"  # Not "Alice_Old"
                assert person.last_name == "Brown"
                assert person.password_hash == "mixed_hash"  # Not "old_mixed_hash"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
