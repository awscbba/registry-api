"""
Tests for the people router.
Testing the clean, no-field-mapping architecture.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from src.app import app

client = TestClient(app)


class TestPeopleRouter:
    """Test cases for people router endpoints."""

    def test_root_endpoint(self):
        """Test the root endpoint returns API information."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "People Registry API"
        assert data["data"]["version"] == "2.0.0"

    def test_health_endpoint(self):
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "healthy"
        assert data["data"]["version"] == "2.0.0"

    @patch("src.core.database.db.scan_table")
    def test_list_people_empty(self, mock_scan, client, auth_headers):
        """Test listing people when database is empty."""
        mock_scan.return_value = []

        response = client.get("/v2/people/", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"] == []
        assert data["count"] == 0

    @patch("src.core.database.db.scan_table")
    def test_list_people_with_data(self, mock_scan, client, auth_headers):
        """Test listing people with sample data."""
        sample_people = [
            {
                "id": "123",
                "firstName": "John",
                "lastName": "Doe",
                "email": "john@example.com",
                "phone": "555-0123",
                "dateOfBirth": "1990-01-01",
                "address": {
                    "street": "123 Main St",
                    "city": "Anytown",
                    "state": "CA",
                    "postalCode": "12345",
                    "country": "USA",
                },
                "isAdmin": False,
                "isActive": True,
                "requirePasswordChange": False,
                "emailVerified": True,
                "createdAt": "2025-01-27T00:00:00Z",
                "updatedAt": "2025-01-27T00:00:00Z",
            }
        ]
        mock_scan.return_value = sample_people

        response = client.get("/v2/people/", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["firstName"] == "John"
        assert data["data"][0]["email"] == "john@example.com"

    @patch("src.core.database.db.get_item")
    def test_get_person_not_found(self, mock_get, client, auth_headers):
        """Test getting a person that doesn't exist."""
        mock_get.return_value = None

        response = client.get("/v2/people/nonexistent", headers=auth_headers)
        assert response.status_code == 404

    def test_create_person_validation(self, client, auth_headers):
        """Test person creation with validation."""
        # Test missing required fields
        response = client.post("/v2/people/", json={}, headers=auth_headers)
        assert response.status_code == 422  # Validation error

        # Test invalid email
        invalid_person = {
            "firstName": "John",
            "lastName": "Doe",
            "email": "invalid-email",
            "dateOfBirth": "1990-01-01",
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "state": "CA",
                "postalCode": "12345",
                "country": "USA",
            },
        }
        response = client.post("/v2/people/", json=invalid_person, headers=auth_headers)
        assert response.status_code == 422  # Validation error

    @patch("src.core.database.db.put_item")
    def test_create_person_success(self, mock_put, client, auth_headers):
        """Test successful person creation."""
        mock_put.return_value = True

        valid_person = {
            "firstName": "John",
            "lastName": "Doe",
            "email": "john@example.com",
            "phone": "555-0123",
            "dateOfBirth": "1990-01-01",
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "state": "CA",
                "postalCode": "12345",
                "country": "USA",
            },
            "isAdmin": False,
        }

        response = client.post("/v2/people/", json=valid_person, headers=auth_headers)
        assert response.status_code == 201

        data = response.json()
        assert data["success"] is True
        assert data["data"]["firstName"] == "John"
        assert data["data"]["email"] == "john@example.com"
        assert "id" in data["data"]
        assert "createdAt" in data["data"]
