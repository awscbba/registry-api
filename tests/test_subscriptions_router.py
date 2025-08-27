"""
Tests for subscriptions router.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from src.app import app
from src.models.subscription import SubscriptionResponse


class TestSubscriptionsRouter:
    """Test cases for subscriptions router."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    @patch("src.routers.subscriptions_router.SubscriptionsService")
    def test_list_subscriptions_empty(self, mock_service_class):
        """Test listing subscriptions when none exist."""
        # Mock service
        mock_service = AsyncMock()
        mock_service.list_subscriptions.return_value = []
        mock_service_class.return_value = mock_service

        # Make request
        response = self.client.get("/v2/subscriptions")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] == []

    @patch("src.routers.subscriptions_router.SubscriptionsService")
    def test_list_subscriptions_with_data(self, mock_service_class):
        """Test listing subscriptions with data."""
        # Mock service
        mock_service = AsyncMock()
        mock_service.list_subscriptions.return_value = [
            {
                "id": "123",
                "personId": "person-1",
                "projectId": "project-1",
                "status": "active",
                "subscriptionDate": "2025-01-27T00:00:00Z",
                "isActive": True,
                "createdAt": "2025-01-27T00:00:00Z",
                "updatedAt": "2025-01-27T00:00:00Z",
            }
        ]
        mock_service_class.return_value = mock_service

        # Make request
        response = self.client.get("/v2/subscriptions")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["personId"] == "person-1"
        assert data["data"][0]["projectId"] == "project-1"

    @patch("src.routers.subscriptions_router.SubscriptionsService")
    def test_get_subscription_not_found(self, mock_service_class):
        """Test getting a subscription that doesn't exist."""
        # Mock service
        mock_service = AsyncMock()
        mock_service.get_subscription.return_value = None
        mock_service_class.return_value = mock_service

        # Make request
        response = self.client.get("/v2/subscriptions/nonexistent")

        # Assertions
        assert response.status_code == 404

    @patch("src.routers.subscriptions_router.SubscriptionsService")
    def test_create_subscription_validation(self, mock_service_class):
        """Test creating a subscription with invalid data."""
        # Mock service
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service

        # Test invalid data
        invalid_subscription = {
            "personId": "",  # Empty personId
            "projectId": "project-1",
        }

        response = self.client.post("/v2/subscriptions", json=invalid_subscription)

        # Should fail validation
        assert response.status_code == 422

    @patch("src.routers.subscriptions_router.SubscriptionsService")
    def test_create_subscription_success(self, mock_service_class):
        """Test creating a subscription successfully."""
        # Mock service
        mock_service = AsyncMock()
        mock_service.create_subscription.return_value = {
            "id": "123",
            "personId": "person-1",
            "projectId": "project-1",
            "status": "active",
            "subscriptionDate": "2025-01-27T00:00:00Z",
            "isActive": True,
            "createdAt": "2025-01-27T00:00:00Z",
            "updatedAt": "2025-01-27T00:00:00Z",
        }
        mock_service_class.return_value = mock_service

        # Valid subscription data
        valid_subscription = {
            "personId": "person-1",
            "projectId": "project-1",
            "status": "active",
        }

        response = self.client.post("/v2/subscriptions", json=valid_subscription)

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["personId"] == "person-1"
        assert data["data"]["projectId"] == "project-1"
        assert "id" in data["data"]
