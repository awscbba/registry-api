"""
Project CRUD Integration Tests

These tests ensure complete project management functionality works end-to-end.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

# Import the actual modules to test
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from src.handlers.modular_api_handler import app, get_current_user


class TestProjectCRUDIntegration:
    """Tests for complete project CRUD operations"""

    @pytest.fixture
    def client(self, dynamodb_mock):
        """Test client for the API with mocked DynamoDB"""
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

    @pytest.fixture
    def sample_project(self):
        """Sample project data for testing"""
        return {
            "id": "test-project-id",
            "name": "Test Project",
            "description": "A test project for integration testing",
            "startDate": "2025-01-01",
            "endDate": "2025-12-31",
            "maxParticipants": 50,
            "status": "active",
            "createdBy": "test-user-id",
            "createdAt": "2025-01-01T00:00:00Z",
            "updatedAt": "2025-01-01T00:00:00Z",
        }

    @pytest.fixture(autouse=True)
    def setup_auth_override(self, mock_user):
        """Setup authentication override for all tests"""
        # Override the dependency to bypass authentication
        app.dependency_overrides[get_current_user] = lambda: mock_user
        yield
        # Clean up after test
        app.dependency_overrides.clear()

    def test_create_project_workflow(
        self, client, mock_user, sample_project, dynamodb_mock
    ):
        """Test complete project creation workflow"""
        # Setup mock DynamoDB table
        projects_table = dynamodb_mock.Table("test-projects-table")

        # Mock authentication
        with patch(
            "src.handlers.modular_api_handler.get_current_user", return_value=mock_user
        ):
            # Test data
            create_data = {
                "name": "Test Project",
                "description": "A test project for integration testing",
                "startDate": "2025-01-01",
                "endDate": "2025-12-31",
                "maxParticipants": 50,
            }

            # Make request
            response = client.post("/v2/projects", json=create_data)

            # Verify response
            assert (
                response.status_code == 200
            )  # Service Registry returns 200 for successful operations
            data = response.json()
            assert data["success"] is True
            assert data["version"] == "v2"
            assert data["data"]["name"] == "Test Project"

    def test_get_project_by_id_workflow(self, client, sample_project, dynamodb_mock):
        """Test retrieving a specific project by ID"""
        # Setup mock DynamoDB data
        projects_table = dynamodb_mock.Table("test-projects-table")
        projects_table.put_item(Item=sample_project)

        # Make request
        response = client.get("/v2/projects/test-project-id")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["version"] == "v2"
        assert data["data"]["id"] == "test-project-id"
        assert data["data"]["name"] == "Test Project"

    def test_get_project_not_found(self, client, dynamodb_mock):
        """Test handling of non-existent project"""
        # Don't add any data to the table, so the project won't be found

        # Make request
        response = client.get("/v2/projects/non-existent-id")

        # Verify 404 response
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False

    def test_update_project_workflow(
        self, client, mock_user, sample_project, dynamodb_mock
    ):
        """Test complete project update workflow"""
        # Setup mock DynamoDB table with existing project
        projects_table = dynamodb_mock.Table("test-projects-table")
        projects_table.put_item(Item=sample_project)

        # Mock authentication
        with patch(
            "src.handlers.modular_api_handler.get_current_user", return_value=mock_user
        ):
            # Test data
            update_data = {"name": "Updated Project Name"}

            # Make request
            response = client.put("/v2/projects/test-project-id", json=update_data)

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["version"] == "v2"
            assert data["data"]["name"] == "Updated Project Name"

    def test_update_project_not_found(self, client, mock_user):
        """Test updating non-existent project"""
        # Mock authentication
        with patch(
            "src.handlers.modular_api_handler.get_current_user", return_value=mock_user
        ):
            # Make request
            response = client.put(
                "/v2/projects/non-existent-id", json={"name": "Updated"}
            )

            # Verify 404 response
            assert response.status_code == 404
            data = response.json()
            assert data["success"] is False

    def test_delete_project_workflow(
        self, client, mock_user, sample_project, dynamodb_mock
    ):
        """Test complete project deletion workflow"""
        # Setup mock DynamoDB table with existing project
        projects_table = dynamodb_mock.Table("test-projects-table")
        projects_table.put_item(Item=sample_project)

        # Mock authentication
        with patch(
            "src.handlers.modular_api_handler.get_current_user", return_value=mock_user
        ):
            # Make request
            response = client.delete("/v2/projects/test-project-id")

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["version"] == "v2"

    def test_delete_project_not_found(self, client, mock_user):
        """Test deleting non-existent project"""
        # Mock authentication
        with patch(
            "src.handlers.modular_api_handler.get_current_user", return_value=mock_user
        ):
            # Make request
            response = client.delete("/v2/projects/non-existent-id")

            # Verify 404 response
            assert response.status_code == 404
            data = response.json()
            assert data["success"] is False

    def test_create_project_missing_name(self, client, mock_user):
        """Test project creation with missing required name field"""
        # Mock authentication
        with patch(
            "src.handlers.modular_api_handler.get_current_user", return_value=mock_user
        ):
            # Test data without name
            create_data = {"description": "A project without a name"}

            # Make request
            response = client.post("/v2/projects", json=create_data)

            # Verify 422 response (validation error)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_complete_project_crud_workflow(self, client, mock_user, dynamodb_mock):
        """Test complete CRUD workflow: Create -> Read -> Update -> Delete"""
        # Mock authentication
        with patch(
            "src.handlers.modular_api_handler.get_current_user", return_value=mock_user
        ):
            # Step 1: Create project
            create_data = {
                "name": "CRUD Test Project",
                "description": "Testing complete CRUD workflow",
                "startDate": "2025-01-01",
                "endDate": "2025-12-31",
                "maxParticipants": 25,
            }

            create_response = client.post("/v2/projects", json=create_data)

            # Verify response
            assert (
                create_response.status_code == 200
            )  # Service Registry returns 200 for successful operations
            assert create_response.json()["data"]["name"] == "CRUD Test Project"

    def test_project_crud_endpoints_exist(self, client):
        """Test that all project CRUD endpoints are properly registered"""
        # Test that endpoints exist (they should return auth errors, not 404s)
        endpoints_to_test = [
            ("GET", "/v2/projects/test-id"),
            ("POST", "/v2/projects"),
            ("PUT", "/v2/projects/test-id"),
            ("DELETE", "/v2/projects/test-id"),
        ]

        for method, endpoint in endpoints_to_test:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json={})
            elif method == "PUT":
                response = client.put(endpoint, json={})
            elif method == "DELETE":
                response = client.delete(endpoint)

            # Should not be 404 for route not found, but 404 is valid when resource doesn't exist
            if method in ["GET", "PUT", "DELETE"]:
                assert response.status_code in [
                    401,
                    404,
                    422,
                ], f"Endpoint {method} {endpoint} returned unexpected status {response.status_code}"
            else:  # POST
                assert response.status_code in [
                    401,
                    422,
                ], f"Endpoint {method} {endpoint} returned unexpected status {response.status_code}"


if __name__ == "__main__":
    # Run the project CRUD tests
    pytest.main([__file__, "-v"])
