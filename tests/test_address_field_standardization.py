"""
Test suite for address field standardization functionality.

This test suite ensures that the address field naming inconsistencies
that were causing 500 errors in person update operations are properly handled.
"""

import pytest
from datetime import datetime
from src.models.person import Address, PersonCreate, PersonUpdate
from src.services.defensive_dynamodb_service import (
    DefensiveDynamoDBService as DynamoDBService,
)


class TestAddressFieldStandardization:
    """Test address field standardization across the entire system."""

    def test_address_model_with_postal_code_alias(self):
        """Test that Address model correctly uses postal_code with postalCode alias."""
        # Test creation with alias (frontend format)
        addr = Address(
            street="123 Main St",
            city="Test City",
            state="Test State",
            postalCode="12345",
            country="USA",
        )

        # Verify internal field name
        assert addr.postal_code == "12345"

        # Verify model_dump uses internal field names
        dump_internal = addr.model_dump()
        assert "postal_code" in dump_internal
        assert dump_internal["postal_code"] == "12345"

        # Verify model_dump with alias uses frontend field names
        dump_alias = addr.model_dump(by_alias=True)
        assert "postalCode" in dump_alias
        assert dump_alias["postalCode"] == "12345"
        assert "postal_code" not in dump_alias

    def test_person_create_with_address(self):
        """Test PersonCreate works with the new address field structure."""
        addr = Address(
            street="123 Main St",
            city="Test City",
            state="Test State",
            postalCode="12345",
            country="USA",
        )

        person = PersonCreate(
            firstName="Test",
            lastName="User",
            email="test@example.com",
            phone="123-456-7890",
            dateOfBirth="1990-01-01",
            address=addr,
        )

        assert person.address.postal_code == "12345"

    def test_person_update_with_address(self):
        """Test PersonUpdate works with the new address field structure."""
        addr = Address(
            street="456 Oak Ave",
            city="Update City",
            state="Update State",
            postalCode="67890",
            country="USA",
        )

        person_update = PersonUpdate(address=addr)
        assert person_update.address.postal_code == "67890"

    def test_dynamodb_address_normalization_for_storage(self):
        """Test DynamoDB service normalizes all address field variations for storage."""
        db_service = DynamoDBService()

        # Test cases with different field name variations
        test_cases = [
            # Frontend format (postalCode)
            {
                "input": {
                    "street": "123 Main St",
                    "city": "Test City",
                    "state": "CA",
                    "postalCode": "12345",
                    "country": "USA",
                },
                "expected_postal_code": "12345",
                "description": "postalCode field",
            },
            # Legacy postalCode format
            {
                "input": {
                    "street": "456 Oak Ave",
                    "city": "Test City",
                    "state": "NY",
                    "postalCode": "67890",
                    "country": "USA",
                },
                "expected_postal_code": "67890",
                "description": "legacy postalCode field",
            },
            # Legacy zip_code format
            {
                "input": {
                    "street": "789 Pine St",
                    "city": "Test City",
                    "state": "TX",
                    "zip_code": "54321",
                    "country": "USA",
                },
                "expected_postal_code": "54321",
                "description": "legacy zip_code field",
            },
        ]

        for test_case in test_cases:
            normalized = db_service._normalize_address_for_storage(
                test_case["input"].copy()
            )

            # Should always normalize to postal_code
            assert "postal_code" in normalized, f"Failed for {test_case['description']}"
            assert normalized["postal_code"] == test_case["expected_postal_code"]

            # Should remove the original field name
            original_field = None
            for field in ["postalCode", "postalCode", "zip_code"]:
                if field in test_case["input"]:
                    original_field = field
                    break

            if original_field != "postal_code":
                assert (
                    original_field not in normalized
                ), f"Original field {original_field} should be removed"

    def test_dynamodb_item_to_person_conversion(self):
        """Test DynamoDB service converts all legacy address field variations to Person model."""
        db_service = DynamoDBService()

        # Test cases with different stored field name variations
        test_items = [
            # Current format (postal_code)
            {
                "id": "123",
                "firstName": "John",
                "lastName": "Doe",
                "email": "john@example.com",
                "phone": "123-456-7890",
                "dateOfBirth": "1990-01-01",
                "address": {
                    "street": "123 Main St",
                    "city": "Test City",
                    "state": "CA",
                    "postal_code": "12345",
                    "country": "USA",
                },
                "createdAt": "2023-01-01T00:00:00",
                "updatedAt": "2023-01-01T00:00:00",
                "description": "postal_code field",
            },
            # Legacy zip_code format
            {
                "id": "124",
                "firstName": "Jane",
                "lastName": "Doe",
                "email": "jane@example.com",
                "phone": "123-456-7890",
                "dateOfBirth": "1990-01-01",
                "address": {
                    "street": "456 Oak Ave",
                    "city": "Test City",
                    "state": "NY",
                    "zip_code": "67890",
                    "country": "USA",
                },
                "createdAt": "2023-01-01T00:00:00",
                "updatedAt": "2023-01-01T00:00:00",
                "description": "legacy zip_code field",
            },
            # Legacy postalCode format
            {
                "id": "125",
                "firstName": "Bob",
                "lastName": "Smith",
                "email": "bob@example.com",
                "phone": "123-456-7890",
                "dateOfBirth": "1990-01-01",
                "address": {
                    "street": "789 Pine St",
                    "city": "Test City",
                    "state": "TX",
                    "postalCode": "54321",
                    "country": "USA",
                },
                "createdAt": "2023-01-01T00:00:00",
                "updatedAt": "2023-01-01T00:00:00",
                "description": "legacy postalCode field",
            },
        ]

        expected_postal_codes = ["12345", "67890", "54321"]

        for i, item in enumerate(test_items):
            person = db_service._item_to_person(item)

            # Should always convert to postal_code in the Person model
            assert (
                person.address.postal_code == expected_postal_codes[i]
            ), f"Failed for {item['description']}"

            # Verify other address fields are preserved
            assert person.address.street == item["address"]["street"]
            assert person.address.city == item["address"]["city"]
            assert person.address.state == item["address"]["state"]
            assert person.address.country == item["address"]["country"]

    def test_address_field_consistency_across_system(self):
        """Test that address fields are consistent across the entire system flow."""
        db_service = DynamoDBService()

        # 1. Create Address with frontend format (postalCode)
        addr = Address(
            street="123 Integration St",
            city="Test City",
            state="CA",
            postalCode="99999",
            country="USA",
        )

        # 2. Create Person with address
        person_create = PersonCreate(
            firstName="Integration",
            lastName="Test",
            email="integration@example.com",
            phone="555-123-4567",
            dateOfBirth="1990-01-01",
            address=addr,
        )

        # 3. Simulate storage normalization
        address_for_storage = db_service._normalize_address_for_storage(
            person_create.address.model_dump()
        )

        # Should be normalized to postal_code for storage
        assert "postal_code" in address_for_storage
        assert address_for_storage["postal_code"] == "99999"

        # 4. Simulate retrieval from database
        mock_db_item = {
            "id": "integration-test",
            "firstName": "Integration",
            "lastName": "Test",
            "email": "integration@example.com",
            "phone": "555-123-4567",
            "dateOfBirth": "1990-01-01",
            "address": address_for_storage,
            "createdAt": "2023-01-01T00:00:00",
            "updatedAt": "2023-01-01T00:00:00",
        }

        # 5. Convert back to Person model
        retrieved_person = db_service._item_to_person(mock_db_item)

        # Should have correct postal_code
        assert retrieved_person.address.postal_code == "99999"

        # 6. Verify API response format (should use postalCode alias)
        api_response_address = retrieved_person.address.model_dump(by_alias=True)
        assert "postalCode" in api_response_address
        assert api_response_address["postalCode"] == "99999"
        assert "postal_code" not in api_response_address

    def test_legacy_data_migration_compatibility(self):
        """Test that the system can handle legacy data with different field names."""
        db_service = DynamoDBService()

        # Simulate legacy data that might exist in the database
        legacy_data_variations = [
            # Old system used postalCode directly in database
            {
                "address": {
                    "street": "Legacy St",
                    "city": "Old City",
                    "state": "CA",
                    "postalCode": "11111",  # This shouldn't happen but test anyway
                    "country": "USA",
                },
                "expected": "11111",
            },
            # Even older system used postalCode
            {
                "address": {
                    "street": "Ancient Ave",
                    "city": "Historic City",
                    "state": "NY",
                    "postalCode": "22222",
                    "country": "USA",
                },
                "expected": "22222",
            },
            # Oldest system used zip_code
            {
                "address": {
                    "street": "Prehistoric Pl",
                    "city": "Fossil City",
                    "state": "TX",
                    "zip_code": "33333",
                    "country": "USA",
                },
                "expected": "33333",
            },
        ]

        for i, legacy_data in enumerate(legacy_data_variations):
            mock_item = {
                "id": f"legacy-{i}",
                "firstName": "Legacy",
                "lastName": "User",
                "email": f"legacy{i}@example.com",
                "phone": "555-000-0000",
                "dateOfBirth": "1980-01-01",
                "address": legacy_data["address"],
                "createdAt": "2020-01-01T00:00:00",
                "updatedAt": "2020-01-01T00:00:00",
            }

            # Should successfully convert legacy data
            person = db_service._item_to_person(mock_item)
            assert (
                person.address.postal_code == legacy_data["expected"]
            ), f"Failed to handle legacy data variation {i}"

    def test_address_update_field_handling(self):
        """Test that address updates properly handle field name conversions."""
        db_service = DynamoDBService()

        # Create an address update with frontend format
        addr_update = Address(
            street="Updated Street",
            city="Updated City",
            state="Updated State",
            postalCode="88888",
            country="Updated Country",
        )

        # Simulate the update process
        address_dict = addr_update.model_dump()
        normalized_address = db_service._normalize_address_for_storage(address_dict)

        # Should be properly normalized for storage
        assert "postal_code" in normalized_address
        assert normalized_address["postal_code"] == "88888"
        assert "postalCode" not in normalized_address

        # Verify all other fields are preserved
        assert normalized_address["street"] == "Updated Street"
        assert normalized_address["city"] == "Updated City"
        assert normalized_address["state"] == "Updated State"
        assert normalized_address["country"] == "Updated Country"


if __name__ == "__main__":
    pytest.main([__file__])
