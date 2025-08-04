"""
Test person update functionality to verify the fix for missing field handlers

This test checks if PersonUpdate fields are properly handled in the database service.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
import json

# Import the actual modules to test
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from src.handlers.versioned_api_handler import app, get_current_user
from src.models.person import PersonUpdate


class TestPersonUpdateFix:
    """Test person update functionality with all fields"""

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

    @patch("src.handlers.versioned_api_handler.db_service")
    def test_person_update_all_fields(self, mock_db_service, client):
        """Test that all PersonUpdate fields are properly handled"""
        from datetime import datetime
        from src.models.person import Address

        # Create a mock existing person
        mock_existing_person = Mock()
        mock_existing_person.id = "test-person-id"
        mock_existing_person.email = "test@example.com"
        mock_existing_person.first_name = "John"
        mock_existing_person.last_name = "Doe"
        mock_existing_person.phone = "123-456-7890"
        mock_existing_person.date_of_birth = datetime(1990, 1, 1).date()
        mock_existing_person.address = Address(
            street="123 Main St",
            city="Anytown",
            state="CA",
            postalCode="12345",
            country="USA"
        )
        mock_existing_person.is_admin = False
        mock_existing_person.is_active = True
        mock_existing_person.failed_login_attempts = 0
        mock_existing_person.require_password_change = False
        mock_existing_person.last_login_at = None
        mock_existing_person.created_at = datetime.now()
        mock_existing_person.updated_at = datetime.now()

        # Create a mock updated person with all fields changed
        mock_updated_person = Mock()
        mock_updated_person.id = "test-person-id"
        mock_updated_person.email = "updated@example.com"
        mock_updated_person.first_name = "Jane"
        mock_updated_person.last_name = "Smith"
        mock_updated_person.phone = "987-654-3210"
        mock_updated_person.date_of_birth = datetime(1985, 5, 15).date()
        mock_updated_person.address = Address(
            street="456 Oak Ave",
            city="Newtown",
            state="NY",
            postalCode="54321",
            country="USA"
        )
        mock_updated_person.is_admin = True
        mock_updated_person.is_active = False
        mock_updated_person.failed_login_attempts = 2
        mock_updated_person.require_password_change = True
        mock_updated_person.last_login_at = datetime.now()
        mock_updated_person.created_at = datetime.now()
        mock_updated_person.updated_at = datetime.now()

        # Mock the database service methods (async)
        mock_db_service.get_person = AsyncMock(return_value=mock_existing_person)
        mock_db_service.update_person = AsyncMock(return_value=mock_updated_person)

        # Test data for update with all possible fields
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
                "postalCode": "54321",
                "country": "USA"
            },
            "isAdmin": True,
            "isActive": False,
            "failedLoginAttempts": 2
        }

        # Make the request
        response = client.put("/v2/people/test-person-id", json=update_data)

        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")

        # Check if the response is valid JSON
        try:
            response_json = response.json()
            print(f"✅ Response is valid JSON")
            
            # Verify the PersonUpdate object was created correctly
            mock_db_service.update_person.assert_called_once()
            call_args = mock_db_service.update_person.call_args
            person_update_obj = call_args[0][1]  # Second argument is the PersonUpdate object
            
            # Verify all fields are present in the PersonUpdate object
            assert isinstance(person_update_obj, PersonUpdate), "Should be PersonUpdate object"
            assert person_update_obj.first_name == "Jane"
            assert person_update_obj.last_name == "Smith"
            assert person_update_obj.email == "updated@example.com"
            assert person_update_obj.phone == "987-654-3210"
            assert person_update_obj.date_of_birth == "1985-05-15"
            assert person_update_obj.is_admin == True
            assert person_update_obj.is_active == False
            assert person_update_obj.failed_login_attempts == 2
            assert person_update_obj.address is not None
            
            print("✅ All PersonUpdate fields properly handled")
                
        except json.JSONDecodeError as e:
            print(f"❌ Response is not valid JSON: {e}")
            print(f"Raw response: {response.text}")
            assert False, "Response should be valid JSON"

        # The request should succeed
        assert response.status_code == 200, f"Update failed: {response.text}"

    def test_person_update_model_validation(self):
        """Test PersonUpdate model validation with all fields"""
        from src.models.person import Address
        
        # Test with all valid fields
        update_data = {
            "firstName": "Jane",
            "lastName": "Smith", 
            "email": "test@example.com",
            "phone": "123-456-7890",
            "dateOfBirth": "1990-01-01",
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "state": "CA",
                "postalCode": "12345",
                "country": "USA"
            },
            "isAdmin": True,
            "isActive": False,
            "failedLoginAttempts": 3
        }
        
        try:
            person_update = PersonUpdate(**update_data)
            print("✅ PersonUpdate model validation successful")
            
            # Verify all fields are accessible
            assert person_update.first_name == "Jane"
            assert person_update.last_name == "Smith"
            assert person_update.email == "test@example.com"
            assert person_update.phone == "123-456-7890"
            assert person_update.date_of_birth == "1990-01-01"
            assert person_update.is_admin == True
            assert person_update.is_active == False
            assert person_update.failed_login_attempts == 3
            assert person_update.address is not None
            assert person_update.address.street == "123 Main St"
            
            print("✅ All PersonUpdate fields accessible")
            
        except Exception as e:
            print(f"❌ PersonUpdate model validation failed: {e}")
            assert False, f"PersonUpdate should validate successfully: {e}"

    def test_person_update_partial_fields(self):
        """Test PersonUpdate with only some fields (partial update)"""
        
        # Test with only some fields
        update_data = {
            "firstName": "UpdatedName",
            "isAdmin": True,
            "failedLoginAttempts": 1
        }
        
        try:
            person_update = PersonUpdate(**update_data)
            print("✅ Partial PersonUpdate validation successful")
            
            # Verify specified fields are set
            assert person_update.first_name == "UpdatedName"
            assert person_update.is_admin == True
            assert person_update.failed_login_attempts == 1
            
            # Verify unspecified fields are None
            assert person_update.last_name is None
            assert person_update.email is None
            assert person_update.phone is None
            assert person_update.address is None
            assert person_update.is_active is None
            
            print("✅ Partial PersonUpdate fields handled correctly")
            
        except Exception as e:
            print(f"❌ Partial PersonUpdate validation failed: {e}")
            assert False, f"Partial PersonUpdate should validate successfully: {e}"