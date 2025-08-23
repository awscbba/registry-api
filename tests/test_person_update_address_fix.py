"""
Test person update address field handling

This test specifically focuses on address field handling issues that might occur
in production when updating persons.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
import json
from datetime import datetime

# Import the actual modules to test
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from src.handlers.versioned_api_handler import app, get_current_user
from src.models.person import PersonUpdate, Address, Person


@pytest.mark.skip(reason="Temporarily skipped - uses deprecated versioned_api_handler")
class TestPersonUpdateAddressFix:
    """Test person update address field handling"""

    @pytest.fixture
    def client(self):
        """Test client for the API"""
        return TestClient(app)

    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user"""
        return {
            "id": "test-user-id",
            "sub": "test-user-sub",
            "email": "admin@example.com",
            "is_admin": True,
        }

    @pytest.fixture(autouse=True)
    def setup_auth_override(self, mock_user):
        """Setup authentication override for all tests"""
        # Override the dependency to bypass authentication
        app.dependency_overrides[get_current_user] = lambda: mock_user
        yield
        # Clean up after test
        app.dependency_overrides.clear()

    def test_address_field_access_patterns(self):
        """Test different ways of accessing address fields"""

        # Create an Address object using the API input format (camelCase)
        address_data = {
            "street": "123 Main St",
            "city": "Anytown",
            "state": "CA",
            "postalCode": "12345",  # camelCase as it comes from API
            "country": "USA",
        }

        address = Address(**address_data)
        print(f"Address created: {address}")

        # Test field access patterns
        print(f"address.street: {address.street}")
        print(f"address.city: {address.city}")
        print(f"address.state: {address.state}")
        print(f"address.country: {address.country}")

        # The critical test - how to access postal_code
        try:
            postal_code_snake = address.postal_code
            print(f"✅ address.postal_code: {postal_code_snake}")
        except AttributeError as e:
            print(f"❌ address.postal_code failed: {e}")

        # Test model_dump to see the actual field names
        dumped = address.model_dump()
        print(f"address.model_dump(): {dumped}")

        dumped_by_alias = address.model_dump(by_alias=True)
        print(f"address.model_dump(by_alias=True): {dumped_by_alias}")

    @patch("src.handlers.versioned_api_handler.db_service")
    def test_person_update_with_address_response_formatting(
        self, mock_db_service, client
    ):
        """Test that person update properly formats address in response"""

        # Create a mock existing person
        mock_existing_person = Mock()
        mock_existing_person.id = "test-person-id"
        mock_existing_person.email = "test@example.com"
        mock_existing_person.first_name = "John"
        mock_existing_person.last_name = "Doe"
        mock_existing_person.phone = "123-456-7890"
        mock_existing_person.date_of_birth = datetime(1990, 1, 1).date()

        # Create address with proper field access
        mock_address = Mock()
        mock_address.street = "123 Main St"
        mock_address.city = "Anytown"
        mock_address.state = "CA"
        mock_address.postal_code = "12345"  # This is the snake_case field name
        mock_address.country = "USA"

        mock_existing_person.address = mock_address
        mock_existing_person.is_admin = False
        mock_existing_person.is_active = True
        mock_existing_person.failed_login_attempts = 0
        mock_existing_person.require_password_change = False
        mock_existing_person.last_login_at = None
        mock_existing_person.created_at = datetime.now()
        mock_existing_person.updated_at = datetime.now()

        # Create updated person with same structure
        mock_updated_person = Mock()
        mock_updated_person.id = "test-person-id"
        mock_updated_person.email = "updated@example.com"
        mock_updated_person.first_name = "Jane"
        mock_updated_person.last_name = "Smith"
        mock_updated_person.phone = "987-654-3210"
        mock_updated_person.date_of_birth = datetime(1985, 5, 15).date()

        # Updated address
        mock_updated_address = Mock()
        mock_updated_address.street = "456 Oak Ave"
        mock_updated_address.city = "Newtown"
        mock_updated_address.state = "NY"
        mock_updated_address.postal_code = "54321"  # snake_case field name
        mock_updated_address.country = "USA"

        mock_updated_person.address = mock_updated_address
        mock_updated_person.is_admin = True
        mock_updated_person.is_active = False
        mock_updated_person.failed_login_attempts = 2
        mock_updated_person.require_password_change = True
        mock_updated_person.last_login_at = datetime.now()
        mock_updated_person.created_at = datetime.now()
        mock_updated_person.updated_at = datetime.now()

        # Mock the database service methods
        mock_db_service.get_person = AsyncMock(return_value=mock_existing_person)
        mock_db_service.update_person = AsyncMock(return_value=mock_updated_person)

        # Test data for update with address
        update_data = {
            "firstName": "Jane",
            "lastName": "Smith",
            "email": "updated@example.com",
            "phone": "987-654-3210",
            "dateOfBirth": "1985-05-15",
            "address": {
                "street": "456 Oak Ave",
                "city": "Newtown",
                "state": "NY",
                "postalCode": "54321",  # camelCase as it comes from API
                "country": "USA",
            },
            "isAdmin": True,
            "isActive": False,
            "failedLoginAttempts": 2,
        }

        # Make the request
        response = client.put("/v2/people/test-person-id", json=update_data)

        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")

        # The request should succeed
        assert response.status_code == 200, f"Update failed: {response.text}"

        # Check if the response is valid JSON
        try:
            response_json = response.json()
            print(f"✅ Response is valid JSON")

            # Check address formatting in response
            if "data" in response_json and "address" in response_json["data"]:
                address_data = response_json["data"]["address"]
                print(f"Address in response: {address_data}")

                # Verify all address fields are present
                assert "street" in address_data
                assert "city" in address_data
                assert "state" in address_data
                assert "postalCode" in address_data  # Should be camelCase in response
                assert "country" in address_data

                # Verify values
                assert address_data["street"] == "456 Oak Ave"
                assert address_data["city"] == "Newtown"
                assert address_data["state"] == "NY"
                assert address_data["postalCode"] == "54321"
                assert address_data["country"] == "USA"

                print("✅ Address fields properly formatted in response")
            else:
                print("❌ No address found in response")
                assert False, "Address should be present in response"

        except json.JSONDecodeError as e:
            print(f"❌ Response is not valid JSON: {e}")
            print(f"Raw response: {response.text}")
            assert False, "Response should be valid JSON"

    def test_address_model_field_access(self):
        """Test Address model field access patterns to understand the issue"""

        # Test creating Address with camelCase input (as from API)
        address_input = {
            "street": "123 Main St",
            "city": "Anytown",
            "state": "CA",
            "postalCode": "12345",  # camelCase
            "country": "USA",
        }

        address = Address(**address_input)

        # Test different access patterns
        print("=== Address Field Access Test ===")
        print(f"address.street: {address.street}")
        print(f"address.city: {address.city}")
        print(f"address.state: {address.state}")
        print(f"address.country: {address.country}")

        # Test postal_code access (this is the actual field name)
        try:
            print(f"address.postal_code: {address.postal_code}")
            postal_code_value = address.postal_code
            print("✅ postal_code access successful")
        except AttributeError as e:
            print(f"❌ postal_code access failed: {e}")
            postal_code_value = None

        # Test if we can access by alias
        try:
            # This should NOT work - aliases are for input/output, not field access
            postal_code_alias = address.postalCode
            print(f"address.postalCode: {postal_code_alias}")
            print("⚠️ postalCode alias access worked (unexpected)")
        except AttributeError as e:
            print(f"✅ postalCode alias access correctly failed: {e}")

        # Test model_dump to see actual structure
        dumped = address.model_dump()
        print(f"model_dump(): {dumped}")

        dumped_by_alias = address.model_dump(by_alias=True)
        print(f"model_dump(by_alias=True): {dumped_by_alias}")

        # The key insight: field access uses the actual field name (postal_code)
        # but input/output uses the alias (postalCode)
        assert (
            postal_code_value == "12345"
        ), "Should be able to access postal_code field"
        assert "postal_code" in dumped, "model_dump should use actual field names"
        assert (
            "postalCode" in dumped_by_alias
        ), "model_dump(by_alias=True) should use aliases"
