"""
Form Submissions API Tests for Dynamic Form Builder
Test-Driven Development approach - testing API endpoint behavior
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)


class TestFormSubmissionsAPI:
    """Test form submissions API endpoints"""

    def test_submit_form_responses_endpoint(self):
        """Test POST /v2/form-submissions"""
        # Arrange
        submission_data = {
            "projectId": "project-123",
            "personId": "person-456",
            "responses": {
                "experience": "Intermediate",
                "skills": ["Python", "AWS"],
                "availability": "Full-time",
            },
        }

        # Act
        response = client.post("/v2/form-submissions", json=submission_data)

        # Assert - Endpoint exists and accepts the request
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_get_project_submissions_endpoint(self):
        """Test GET /v2/form-submissions/project/{project_id}"""
        # Arrange
        project_id = "project-123"

        # Act
        response = client.get(f"/v2/form-submissions/project/{project_id}")

        # Assert - Endpoint exists
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_invalid_submission_returns_error(self):
        """Test that invalid submission data returns validation error"""
        # Arrange - Missing required fields
        invalid_submission = {
            "projectId": "project-123",
            # Missing personId and responses
        }

        # Act
        response = client.post("/v2/form-submissions", json=invalid_submission)

        # Assert - Validation error
        assert response.status_code in [400, 422]  # Validation error

    def test_get_person_project_submission_endpoint(self):
        """Test GET /v2/form-submissions/person/{person_id}/project/{project_id}"""
        # Arrange
        person_id = "person-456"
        project_id = "project-123"

        # Act
        response = client.get(
            f"/v2/form-submissions/person/{person_id}/project/{project_id}"
        )

        # Assert - Endpoint exists
        assert response.status_code in [200, 404]  # May not exist, but endpoint should

    def test_form_submissions_api_endpoints_exist(self):
        """Test that all form submission API endpoints are properly registered"""
        # Test that endpoints exist by checking they don't return 404 for method not allowed

        # POST /v2/form-submissions
        response = client.post("/v2/form-submissions", json={})
        assert response.status_code != 404  # Endpoint exists

        # GET /v2/form-submissions/project/test
        response = client.get("/v2/form-submissions/project/test")
        assert response.status_code != 404  # Endpoint exists

        # GET /v2/form-submissions/person/test/project/test
        response = client.get("/v2/form-submissions/person/test/project/test")
        assert response.status_code != 404  # Endpoint exists
