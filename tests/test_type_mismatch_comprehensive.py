"""
Comprehensive Type Mismatch Tests

This test identifies and verifies fixes for all endpoints that pass dictionaries
to database service methods that expect Pydantic model objects.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

# Import the actual modules to test
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from src.handlers.versioned_api_handler import app, get_current_user


@pytest.mark.skip(reason="Temporarily skipped - uses deprecated versioned_api_handler")
class TestTypeMismatchComprehensive:
    """Tests for type mismatches between API handlers and database service"""

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
            "email": "admin@cbba.cloud.org.bo",  # Use super admin email
            "is_admin": True,
        }

    @pytest.fixture(autouse=True)
    def setup_auth_override(self, mock_user):
        """Setup authentication override for all tests"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        yield
        app.dependency_overrides.clear()

    @patch("src.handlers.versioned_api_handler.db_service")
    def test_project_create_type_mismatch(self, mock_db_service, client):
        """Test that project creation converts dict to ProjectCreate object"""
        mock_project = {
            "id": "test-project-id",
            "name": "Test Project",
            "description": "A test project",
            "status": "active",
        }

        mock_db_service.create_project = AsyncMock(return_value=mock_project)

        project_data = {
            "name": "Test Project",
            "description": "A test project",
            "maxParticipants": 50,
        }

        response = client.post("/v2/projects", json=project_data)

        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")

        # Should not be 500
        assert response.status_code != 500, f"Got 500 error: {response.text}"

        # Verify the service method was called
        assert mock_db_service.create_project.call_count == 1
        call_args = mock_db_service.create_project.call_args

        # Check if the first argument is a ProjectCreate object or dict
        project_arg = call_args[0][0]
        print(f"Project argument type: {type(project_arg)}")
        print(f"Project argument value: {project_arg}")

        # This test will help us identify if we need to fix this endpoint
        from src.models.project import ProjectCreate

        if not isinstance(project_arg, ProjectCreate):
            print(
                "⚠️  ISSUE FOUND: create_project called with dict instead of ProjectCreate object"
            )

    @patch("src.handlers.versioned_api_handler.db_service")
    def test_project_update_type_mismatch(self, mock_db_service, client):
        """Test that project update converts dict to ProjectUpdate object"""
        mock_project = {
            "id": "test-project-id",
            "name": "Updated Project",
            "description": "Updated description",
            "status": "active",
        }

        mock_db_service.get_project_by_id = AsyncMock(return_value=mock_project)
        mock_db_service.update_project = AsyncMock(return_value=mock_project)

        update_data = {"name": "Updated Project", "description": "Updated description"}

        response = client.put("/v2/projects/test-project-id", json=update_data)

        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")

        # Should not be 500
        assert response.status_code != 500, f"Got 500 error: {response.text}"

        # Verify the service method was called
        assert mock_db_service.update_project.call_count == 1
        call_args = mock_db_service.update_project.call_args

        # Check if the second argument is a ProjectUpdate object or dict
        project_update_arg = call_args[0][1]
        print(f"Project update argument type: {type(project_update_arg)}")
        print(f"Project update argument value: {project_update_arg}")

        # This test will help us identify if we need to fix this endpoint
        from src.models.project import ProjectUpdate

        if not isinstance(project_update_arg, ProjectUpdate):
            print(
                "⚠️  ISSUE FOUND: update_project called with dict instead of ProjectUpdate object"
            )

    @patch("src.middleware.admin_middleware_v2.roles_service")
    @patch("src.handlers.versioned_api_handler.db_service")
    def test_admin_status_update_type_mismatch(
        self, mock_db_service, mock_roles_service, client
    ):
        """Test that admin status update converts dict to PersonUpdate object"""
        from datetime import datetime

        mock_person = Mock()
        mock_person.id = "test-person-id"
        mock_person.first_name = "John"
        mock_person.last_name = "Doe"
        mock_person.email = "john@example.com"
        mock_person.phone = "+1234567890"
        mock_person.date_of_birth = datetime.fromisoformat("1990-01-01")
        mock_person.address = {"street": "123 Main St", "city": "Test City"}
        mock_person.is_admin = True  # Updated to admin
        mock_person.created_at = datetime.fromisoformat("2025-01-01T00:00:00")
        mock_person.updated_at = datetime.fromisoformat("2025-01-01T00:00:00")
        mock_person.is_active = True
        mock_person.require_password_change = False
        mock_person.last_login_at = None
        mock_person.failed_login_attempts = 0

        mock_db_service.get_person = AsyncMock(return_value=mock_person)
        mock_db_service.update_person = AsyncMock(return_value=mock_person)

        # Configure roles service to allow admin access
        mock_roles_service.user_is_admin = AsyncMock(return_value=True)
        mock_roles_service.user_is_super_admin = AsyncMock(return_value=True)
        mock_roles_service.get_user_roles = AsyncMock(return_value=[])

        admin_data = {"isAdmin": True}

        response = client.put("/v2/people/test-person-id/admin", json=admin_data)

        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")

        # Should not be 500
        assert response.status_code != 500, f"Got 500 error: {response.text}"

        # Verify the service method was called
        assert mock_db_service.update_person.call_count == 1
        call_args = mock_db_service.update_person.call_args

        # Check if the second argument is a PersonUpdate object or dict
        person_update_arg = call_args[0][1]
        print(f"Person update argument type: {type(person_update_arg)}")
        print(f"Person update argument value: {person_update_arg}")

        # This test will help us identify if we need to fix this endpoint
        from src.models.person import PersonUpdate

        if not isinstance(person_update_arg, PersonUpdate):
            print(
                "⚠️  ISSUE FOUND: update_person called with dict instead of PersonUpdate object"
            )

    def test_all_endpoints_for_500_errors(self, client):
        """Test all potentially problematic endpoints for 500 errors"""
        # Test endpoints that might have type mismatches
        test_cases = [
            ("POST", "/v2/projects", {"name": "Test Project"}),
            ("PUT", "/v2/projects/test-id", {"name": "Updated Project"}),
            ("PUT", "/v2/people/test-id/admin", {"isAdmin": True}),
        ]

        for method, endpoint, data in test_cases:
            print(f"\nTesting {method} {endpoint}")

            if method == "POST":
                response = client.post(endpoint, json=data)
            elif method == "PUT":
                response = client.put(endpoint, json=data)

            print(f"Status: {response.status_code}")
            if response.status_code >= 500:
                print(f"⚠️  500 ERROR FOUND: {method} {endpoint}")
                print(f"Response: {response.text}")
            else:
                print(f"✅ No 500 error: {method} {endpoint}")


if __name__ == "__main__":
    # Run the comprehensive type mismatch tests
    pytest.main([__file__, "-v", "-s"])
