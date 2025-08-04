"""
Test project new fields integration

This test verifies that the new project fields (category, location, requirements)
are properly handled throughout the system.
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
from src.models.project import ProjectStatus, ProjectUpdate, ProjectCreate
from src.services.dynamodb_service import DynamoDBService


class TestProjectNewFieldsIntegration:
    """Test project new fields integration"""

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

    def test_project_model_with_new_fields(self):
        """Test that project models properly handle new fields"""

        # Test ProjectCreate with new fields
        create_data = {
            "name": "Test Project",
            "description": "Test Description",
            "startDate": "2025-01-01",
            "endDate": "2025-12-31",
            "maxParticipants": 100,
            "status": "active",
            "category": "workshop",
            "location": "Virtual",
            "requirements": "Basic programming knowledge",
        }

        project_create = ProjectCreate(**create_data)
        assert project_create.category == "workshop"
        assert project_create.location == "Virtual"
        assert project_create.requirements == "Basic programming knowledge"

        # Test ProjectUpdate with new fields
        update_data = {
            "name": "Updated Project",
            "category": "conference",
            "location": "In-person",
            "requirements": "Advanced programming skills",
        }

        project_update = ProjectUpdate(**update_data)
        assert project_update.category == "conference"
        assert project_update.location == "In-person"
        assert project_update.requirements == "Advanced programming skills"

        # Test serialization
        dumped = project_update.model_dump(exclude_unset=True)
        assert "category" in dumped
        assert "location" in dumped
        assert "requirements" in dumped
        assert dumped["category"] == "conference"

    @patch("src.handlers.versioned_api_handler.db_service")
    def test_project_update_api_with_new_fields(self, mock_db_service, client):
        """Test that project update API properly handles new fields"""

        # Create a mock existing project
        mock_existing_project = {
            "id": "test-project-id",
            "name": "Original Project",
            "description": "Original Description",
            "startDate": "2025-01-01",
            "endDate": "2025-12-31",
            "maxParticipants": 100,
            "status": ProjectStatus.ACTIVE,
            "category": "workshop",
            "location": "Virtual",
            "requirements": "Basic knowledge",
            "createdBy": "test-user-id",
            "createdAt": datetime.now().isoformat(),
            "updatedAt": datetime.now().isoformat(),
        }

        # Create updated project with new field values
        mock_updated_project = mock_existing_project.copy()
        mock_updated_project.update(
            {
                "name": "Updated Project Name",
                "category": "conference",
                "location": "In-person - Conference Center",
                "requirements": "Advanced programming skills required",
                "updatedAt": datetime.now().isoformat(),
            }
        )

        # Mock the database service methods
        mock_db_service.get_project_by_id.return_value = mock_existing_project
        mock_db_service.update_project.return_value = mock_updated_project

        # Test data for update with new fields
        update_data = {
            "name": "Updated Project Name",
            "category": "conference",
            "location": "In-person - Conference Center",
            "requirements": "Advanced programming skills required",
        }

        # Make the request
        response = client.put("/v2/projects/test-project-id", json=update_data)

        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")

        # Check if the response is valid JSON
        assert response.status_code == 200, f"Update failed: {response.text}"

        response_json = response.json()
        assert "data" in response_json

        project_data = response_json["data"]

        # Verify new fields are in the response
        assert "category" in project_data
        assert "location" in project_data
        assert "requirements" in project_data

        # Verify new field values
        assert project_data["category"] == "conference"
        assert project_data["location"] == "In-person - Conference Center"
        assert project_data["requirements"] == "Advanced programming skills required"

        # Verify the database service was called with correct data
        mock_db_service.update_project.assert_called_once()
        call_args = mock_db_service.update_project.call_args
        project_update_obj = call_args[0][
            1
        ]  # Second argument is the ProjectUpdate object

        assert project_update_obj.category == "conference"
        assert project_update_obj.location == "In-person - Conference Center"
        assert project_update_obj.requirements == "Advanced programming skills required"

    def test_dynamodb_service_update_with_new_fields(self):
        """Test that DynamoDB service properly handles new fields in update"""

        # Create a mock DynamoDB service
        db_service = DynamoDBService()

        # Mock the projects table
        mock_table = Mock()
        db_service.projects_table = mock_table

        # Mock successful update response
        mock_response = {
            "Attributes": {
                "id": "test-project-id",
                "name": "Updated Project",
                "category": "conference",
                "location": "In-person",
                "requirements": "Advanced skills",
                "updatedAt": "2025-08-04T16:00:00.000Z",
            }
        }
        mock_table.update_item.return_value = mock_response

        # Create ProjectUpdate with new fields
        project_update = ProjectUpdate(
            name="Updated Project",
            category="conference",
            location="In-person",
            requirements="Advanced skills",
        )

        # Call the update method
        result = db_service.update_project("test-project-id", project_update)

        # Verify the update_item was called
        mock_table.update_item.assert_called_once()
        call_kwargs = mock_table.update_item.call_args[1]

        # Check that the update expression includes new fields
        update_expression = call_kwargs["UpdateExpression"]
        assert "category = :category" in update_expression
        assert "#location = :location" in update_expression
        assert "requirements = :requirements" in update_expression

        # Check that expression values include new fields
        expression_values = call_kwargs["ExpressionAttributeValues"]
        assert ":category" in expression_values
        assert ":location" in expression_values
        assert ":requirements" in expression_values
        assert expression_values[":category"] == "conference"
        assert expression_values[":location"] == "In-person"
        assert expression_values[":requirements"] == "Advanced skills"

        # Check that expression names include location (reserved word)
        expression_names = call_kwargs["ExpressionAttributeNames"]
        assert "#location" in expression_names
        assert expression_names["#location"] == "location"

        # Verify result
        assert result is not None
        assert result["category"] == "conference"
        assert result["location"] == "In-person"
        assert result["requirements"] == "Advanced skills"

    def test_project_field_validation(self):
        """Test validation of new project fields"""

        # Test category field length validation
        with pytest.raises(ValueError):
            ProjectUpdate(category="x" * 101)  # Too long

        # Test location field length validation
        with pytest.raises(ValueError):
            ProjectUpdate(location="x" * 201)  # Too long

        # Test requirements field length validation
        with pytest.raises(ValueError):
            ProjectUpdate(requirements="x" * 501)  # Too long

        # Test valid lengths
        valid_update = ProjectUpdate(
            category="x" * 100,  # Max length
            location="x" * 200,  # Max length
            requirements="x" * 500,  # Max length
        )
        assert valid_update.category == "x" * 100
        assert valid_update.location == "x" * 200
        assert valid_update.requirements == "x" * 500

    def test_project_partial_update_with_new_fields(self):
        """Test partial updates that only include some new fields"""

        # Test updating only category
        update_category_only = ProjectUpdate(category="workshop")
        dumped = update_category_only.model_dump(exclude_unset=True)
        assert "category" in dumped
        assert "location" not in dumped
        assert "requirements" not in dumped

        # Test updating only location
        update_location_only = ProjectUpdate(location="Virtual")
        dumped = update_location_only.model_dump(exclude_unset=True)
        assert "location" in dumped
        assert "category" not in dumped
        assert "requirements" not in dumped

        # Test updating only requirements
        update_requirements_only = ProjectUpdate(requirements="No prerequisites")
        dumped = update_requirements_only.model_dump(exclude_unset=True)
        assert "requirements" in dumped
        assert "category" not in dumped
        assert "location" not in dumped
