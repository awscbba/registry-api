"""
Debug test for person update 500 error

This test reproduces the exact scenario that's failing in production.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

# Import the actual modules to test
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from src.handlers.versioned_api_handler import app, get_current_user


class TestPersonUpdateDebug:
    """Debug tests for person update 500 error"""

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
    def test_person_update_500_error_reproduction(self, mock_db_service, client):
        """Test to reproduce the exact 500 error scenario"""
        from datetime import datetime

        # Create a mock person object that matches the production data
        mock_person = Mock()
        mock_person.id = "02724257-4c6a-4aac-9c19-89c87c499bc8"
        mock_person.first_name = "John"
        mock_person.last_name = "Doe"
        mock_person.email = "john@example.com"
        mock_person.phone = "+1234567890"
        mock_person.date_of_birth = datetime.fromisoformat("1990-01-01")
        mock_person.address = {
            "street": "123 Main St",
            "city": "Test City",
            "state": "Test State",
            "country": "Test Country",
            "postalCode": "12345",
        }
        mock_person.is_admin = False
        mock_person.created_at = datetime.fromisoformat("2025-01-01T00:00:00")
        mock_person.updated_at = datetime.fromisoformat("2025-01-01T00:00:00")
        mock_person.is_active = True
        mock_person.require_password_change = False
        mock_person.last_login_at = None
        mock_person.failed_login_attempts = 0

        # Mock the database service methods
        mock_db_service.get_person = AsyncMock(return_value=mock_person)
        mock_db_service.update_person = AsyncMock(return_value=mock_person)

        # Test data that might be causing the issue
        update_data = {"firstName": "Jane", "lastName": "Smith"}

        # Make the request that's failing in production
        response = client.put(
            "/v2/people/02724257-4c6a-4aac-9c19-89c87c499bc8", json=update_data
        )

        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")

        # This should not be 500
        assert response.status_code != 500, f"Got 500 error: {response.text}"

        # Verify the service methods were called
        mock_db_service.get_person.assert_called_once_with(
            "02724257-4c6a-4aac-9c19-89c87c499bc8"
        )

        # Verify update_person was called with a PersonUpdate object
        assert mock_db_service.update_person.call_count == 1
        call_args = mock_db_service.update_person.call_args
        assert call_args[0][0] == "02724257-4c6a-4aac-9c19-89c87c499bc8"

        # Check that the second argument is a PersonUpdate object with correct data
        person_update_obj = call_args[0][1]
        from src.models.person import PersonUpdate

        assert isinstance(person_update_obj, PersonUpdate)
        assert person_update_obj.first_name == "Jane"
        assert person_update_obj.last_name == "Smith"

    @patch("src.handlers.versioned_api_handler.db_service")
    def test_person_update_with_database_error(self, mock_db_service, client):
        """Test person update when database service throws an error"""
        from datetime import datetime

        # Mock person exists
        mock_person = Mock()
        mock_person.id = "test-person-id"
        mock_person.first_name = "John"
        mock_person.last_name = "Doe"
        mock_person.email = "john@example.com"
        mock_person.phone = "+1234567890"
        mock_person.date_of_birth = datetime.fromisoformat("1990-01-01")
        mock_person.address = {
            "street": "123 Main St",
            "city": "Test City",
            "state": "Test State",
            "country": "Test Country",
            "postalCode": "12345",
        }
        mock_person.is_admin = False
        mock_person.created_at = datetime.fromisoformat("2025-01-01T00:00:00")
        mock_person.updated_at = datetime.fromisoformat("2025-01-01T00:00:00")
        mock_person.is_active = True
        mock_person.require_password_change = False
        mock_person.last_login_at = None
        mock_person.failed_login_attempts = 0

        mock_db_service.get_person = AsyncMock(return_value=mock_person)

        # Mock update_person to throw an exception
        mock_db_service.update_person = AsyncMock(
            side_effect=Exception("Database connection error")
        )

        update_data = {"firstName": "Jane"}

        response = client.put("/v2/people/test-person-id", json=update_data)

        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")

        # Should be 500 due to database error
        assert response.status_code == 500

    @patch("src.handlers.versioned_api_handler.db_service")
    def test_person_update_with_none_fields(self, mock_db_service, client):
        """Test person update when some fields are None"""
        from datetime import datetime

        # Create a mock person with some None fields
        mock_person = Mock()
        mock_person.id = "test-person-id"
        mock_person.first_name = "John"
        mock_person.last_name = "Doe"
        mock_person.email = "john@example.com"
        mock_person.phone = None  # This could cause issues
        mock_person.date_of_birth = None  # This could cause issues
        mock_person.address = None  # This could cause issues
        mock_person.is_admin = False
        mock_person.created_at = datetime.fromisoformat("2025-01-01T00:00:00")
        mock_person.updated_at = datetime.fromisoformat("2025-01-01T00:00:00")
        mock_person.is_active = True
        mock_person.require_password_change = False
        mock_person.last_login_at = None
        mock_person.failed_login_attempts = None  # This could cause issues

        mock_db_service.get_person = AsyncMock(return_value=mock_person)
        mock_db_service.update_person = AsyncMock(return_value=mock_person)

        update_data = {"firstName": "Jane"}

        response = client.put("/v2/people/test-person-id", json=update_data)

        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")

        # This should work even with None fields
        assert response.status_code == 200


if __name__ == "__main__":
    # Run the debug tests
    pytest.main([__file__, "-v", "-s"])
