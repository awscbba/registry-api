"""
Tests for the projects router.
Testing the clean, no-field-mapping architecture for projects.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from src.app import app
from .test_utils import TestAuthUtils

client = TestClient(app)


class TestProjectsRouter:
    """Test cases for projects router endpoints."""

    @patch("src.core.database.db.scan_table")
    def test_list_projects_empty(self, mock_scan):
        """Test listing projects when database is empty."""
        mock_scan.return_value = []

        response = client.get("/v2/projects/")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"] == []
        assert data["count"] == 0

    @patch("src.core.database.db.scan_table")
    def test_list_projects_with_data(self, mock_scan):
        """Test listing projects with sample data."""
        # Mock projects data
        sample_projects = [
            {
                "id": "proj-123",
                "name": "Community Garden",
                "description": "Building a community garden for local residents",
                "startDate": "2025-03-01",
                "endDate": "2025-06-30",
                "maxParticipants": 20,
                "status": "active",
                "category": "Environment",
                "location": "Central Park",
                "requirements": "Basic gardening knowledge helpful",
                "createdAt": "2025-01-27T00:00:00Z",
                "updatedAt": "2025-01-27T00:00:00Z",
                "createdBy": "admin-123",
            }
        ]

        # Mock subscriptions data (empty for this test)
        mock_scan.side_effect = [sample_projects, []]

        response = client.get("/v2/projects/")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "Community Garden"
        assert data["data"][0]["status"] == "active"
        assert data["data"][0]["currentParticipants"] == 0

    @patch("src.core.database.db.get_item")
    @patch("src.core.database.db.scan_table")
    def test_get_project_not_found(self, mock_scan, mock_get):
        """Test getting a project that doesn't exist."""
        mock_get.return_value = None

        response = client.get("/v2/projects/nonexistent")
        assert response.status_code == 404

    def test_create_project_validation(self):
        """Test project creation with validation."""
        # Override the dependency to bypass authentication
        from src.routers.auth_router import get_current_user
        from .test_utils import TestMockUtils

        async def mock_get_current_user():
            return TestMockUtils.mock_user()

        app.dependency_overrides[get_current_user] = mock_get_current_user

        try:
            # Test missing required fields
            response = client.post("/v2/projects/", json={})
            assert response.status_code == 422
        finally:
            # Clean up
            app.dependency_overrides.clear()

    @patch("src.core.database.db.put_item")
    def test_create_project_success(self, mock_put):
        """Test successful project creation."""
        # Override the dependency to bypass authentication
        from src.routers.auth_router import get_current_user
        from .test_utils import TestMockUtils

        async def mock_get_current_user():
            return TestMockUtils.mock_user(user_id="user-123")

        app.dependency_overrides[get_current_user] = mock_get_current_user
        mock_put.return_value = True

        try:
            valid_project = {
                "name": "Community Garden",
                "description": "Building a community garden for local residents",
                "startDate": "2025-03-01",
                "endDate": "2025-06-30",
                "maxParticipants": 20,
                "status": "pending",
                "category": "Environment",
                "location": "Central Park",
                "requirements": "Basic gardening knowledge helpful",
            }

            headers = TestAuthUtils.get_auth_headers()
            response = client.post("/v2/projects/", json=valid_project, headers=headers)
            assert response.status_code == 201

            data = response.json()
            assert data["success"] is True
            assert data["data"]["name"] == "Community Garden"
            assert data["data"]["status"] == "pending"
            assert "id" in data["data"]
            assert data["data"]["createdBy"] == "user-123"  # Verify creator is set
        finally:
            # Clean up
            app.dependency_overrides.clear()
        assert "createdAt" in data["data"]
        assert data["data"]["currentParticipants"] == 0
