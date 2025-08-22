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

    @pytest.fixture
    def sample_project(self):
        """Sample project data for testing"""
        return {
            "id": "test-project-id",
            "name": "Test Project",
            "description": "A test project for integration testing",
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

    @patch("src.handlers.modular_api_handler.service_registry.get_service")
    def test_create_project_workflow(
        self, mock_get_service, client, mock_user, sample_project
    ):
        """Test complete project creation workflow"""
        # Setup mocks
        mock_projects_service = Mock()
        mock_projects_service.create_project = AsyncMock(return_value=sample_project)
        mock_get_service.return_value = mock_projects_service

        # Test data
        create_data = {
            "name": "Test Project",
            "description": "A test project for integration testing",
            "maxParticipants": 50,
        }

        # Make request
        response = client.post("/v2/projects", json=create_data)

        # Verify response
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["version"] == "v2"
        assert data["data"]["name"] == "Test Project"

        # Verify service was called correctly
        assert mock_projects_service.create_project.call_count == 1
        call_args = mock_projects_service.create_project.call_args
        assert call_args[0][1] == "test-user-id"  # Second argument should be user ID

        # Check that the first argument is a ProjectCreate object with correct data
        project_create_obj = call_args[0][0]
        from src.models.project import ProjectCreate

        assert isinstance(project_create_obj, ProjectCreate)
        assert project_create_obj.name == "Test Project"
        assert (
            project_create_obj.description == "A test project for integration testing"
        )
        assert project_create_obj.maxParticipants == 50

    @patch("src.handlers.versioned_api_handler.db_service")
    def test_get_project_by_id_workflow(self, mock_db_service, client, sample_project):
        """Test retrieving a specific project by ID"""
        # Setup mock
        mock_db_service.get_project_by_id = AsyncMock(return_value=sample_project)

        # Make request
        response = client.get("/v2/projects/test-project-id")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["version"] == "v2"
        assert data["data"]["id"] == "test-project-id"
        assert data["data"]["name"] == "Test Project"

        # Verify service was called correctly
        mock_db_service.get_project_by_id.assert_called_once_with("test-project-id")

    @patch("src.handlers.versioned_api_handler.db_service")
    def test_get_project_not_found(self, mock_db_service, client):
        """Test handling of non-existent project"""
        # Setup mock to return None
        mock_db_service.get_project_by_id = AsyncMock(return_value=None)

        # Make request
        response = client.get("/v2/projects/non-existent-id")

        # Verify 404 response
        assert response.status_code == 404
        data = response.json()
        assert "Project not found" in data["detail"]

    @patch("src.handlers.versioned_api_handler.db_service")
    def test_update_project_workflow(
        self, mock_db_service, client, mock_user, sample_project
    ):
        """Test complete project update workflow"""
        # Setup mocks
        mock_db_service.get_project_by_id = AsyncMock(return_value=sample_project)

        updated_project = {**sample_project, "name": "Updated Project Name"}
        mock_db_service.update_project = AsyncMock(return_value=updated_project)

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

        # Verify service calls
        mock_db_service.get_project_by_id.assert_called_once_with("test-project-id")

        # Verify update_project was called with a ProjectUpdate object
        assert mock_db_service.update_project.call_count == 1
        call_args = mock_db_service.update_project.call_args
        assert call_args[0][0] == "test-project-id"

        # Check that the second argument is a ProjectUpdate object with correct data
        project_update_obj = call_args[0][1]
        from src.models.project import ProjectUpdate

        assert isinstance(project_update_obj, ProjectUpdate)
        assert project_update_obj.name == "Updated Project Name"

    @patch("src.handlers.versioned_api_handler.db_service")
    def test_update_project_not_found(self, mock_db_service, client, mock_user):
        """Test updating non-existent project"""
        # Setup mocks
        mock_db_service.get_project_by_id = AsyncMock(return_value=None)

        # Make request
        response = client.put("/v2/projects/non-existent-id", json={"name": "Updated"})

        # Verify 404 response
        assert response.status_code == 404
        data = response.json()
        assert "Project not found" in data["detail"]

    @patch("src.handlers.versioned_api_handler.db_service")
    def test_delete_project_workflow(
        self, mock_db_service, client, mock_user, sample_project
    ):
        """Test complete project deletion workflow"""
        # Setup mocks
        mock_db_service.get_project_by_id = AsyncMock(return_value=sample_project)
        mock_db_service.delete_project = AsyncMock(return_value=True)

        # Make request
        response = client.delete("/v2/projects/test-project-id")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["version"] == "v2"
        assert data["data"]["deleted"] is True
        assert data["data"]["project_id"] == "test-project-id"

        # Verify service calls
        mock_db_service.get_project_by_id.assert_called_once_with("test-project-id")
        mock_db_service.delete_project.assert_called_once_with("test-project-id")

    @patch("src.handlers.versioned_api_handler.db_service")
    def test_delete_project_not_found(self, mock_db_service, client, mock_user):
        """Test deleting non-existent project"""
        # Setup mocks
        mock_db_service.get_project_by_id = AsyncMock(return_value=None)

        # Make request
        response = client.delete("/v2/projects/non-existent-id")

        # Verify 404 response
        assert response.status_code == 404
        data = response.json()
        assert "Project not found" in data["detail"]

    def test_create_project_missing_name(self, client, mock_user):
        """Test project creation with missing required name field"""
        # Test data without name
        create_data = {"description": "A project without a name"}

        # Make request
        response = client.post("/v2/projects", json=create_data)

        # Verify 400 response
        assert response.status_code == 400
        data = response.json()
        assert "Project name is required" in data["detail"]

    @patch("src.handlers.versioned_api_handler.db_service")
    def test_complete_project_crud_workflow(self, mock_db_service, client, mock_user):
        """Test complete CRUD workflow: Create -> Read -> Update -> Delete"""
        # Step 1: Create project
        create_data = {
            "name": "CRUD Test Project",
            "description": "Testing complete CRUD workflow",
            "maxParticipants": 25,
        }

        created_project = {
            "id": "crud-test-id",
            "name": "CRUD Test Project",
            "description": "Testing complete CRUD workflow",
            "maxParticipants": 25,
            "status": "active",
            "createdBy": "test-user-id",
        }
        mock_db_service.create_project = AsyncMock(return_value=created_project)

        create_response = client.post("/v2/projects", json=create_data)
        assert create_response.status_code == 201
        assert create_response.json()["data"]["name"] == "CRUD Test Project"

        # Step 2: Read project
        mock_db_service.get_project_by_id = AsyncMock(return_value=created_project)

        read_response = client.get("/v2/projects/crud-test-id")
        assert read_response.status_code == 200
        assert read_response.json()["data"]["id"] == "crud-test-id"

        # Step 3: Update project
        update_data = {"name": "Updated CRUD Test Project"}
        updated_project = {**created_project, "name": "Updated CRUD Test Project"}
        mock_db_service.update_project = AsyncMock(return_value=updated_project)

        update_response = client.put("/v2/projects/crud-test-id", json=update_data)
        assert update_response.status_code == 200
        assert update_response.json()["data"]["name"] == "Updated CRUD Test Project"

        # Step 4: Delete project
        mock_db_service.delete_project = AsyncMock(return_value=True)

        delete_response = client.delete("/v2/projects/crud-test-id")
        assert delete_response.status_code == 200
        assert delete_response.json()["data"]["deleted"] is True

        # Verify all service methods were called
        mock_db_service.create_project.assert_called_once()
        mock_db_service.get_project_by_id.assert_called()
        mock_db_service.update_project.assert_called_once()
        mock_db_service.delete_project.assert_called_once()

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

            # Should not be 404 (route not found), should be auth error or other business logic error
            assert (
                response.status_code != 404
            ), f"Endpoint {method} {endpoint} not found (route-level 404)"


if __name__ == "__main__":
    # Run the project CRUD tests
    pytest.main([__file__, "-v"])
