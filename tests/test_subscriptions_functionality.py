"""
Focused tests for subscription functionality.
Tests the actual deployed subscription endpoints and service behavior.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock

from src.app import app
from .test_utils import TestAuthUtils


class TestSubscriptionsFunctionality:
    """Test subscription functionality with deployed architecture."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    @patch("src.services.service_registry_manager.service_registry")
    def test_subscription_endpoints_available(self, mock_service_registry):
        """Test that subscription endpoints are available and responding."""
        # Mock service
        mock_service = Mock()
        mock_service.list_subscriptions.return_value = []
        mock_service_registry.get_subscriptions_service.return_value = mock_service

        # Test list endpoint
        response = self.client.get("/v2/subscriptions")
        assert response.status_code == 200

        data = response.json()
        assert "success" in data
        assert "data" in data

    @patch("src.services.service_registry_manager.service_registry")
    def test_subscription_creation_endpoint(self, mock_service_registry):
        """Test subscription creation endpoint."""
        # Mock service
        mock_service = Mock()
        mock_service.create_subscription.return_value = {
            "id": "sub-123",
            "personId": "person-456",
            "projectId": "project-789",
            "status": "active",
            "isActive": True,
            "createdAt": "2025-01-27T00:00:00Z",
            "updatedAt": "2025-01-27T00:00:00Z",
        }
        mock_service_registry.get_subscriptions_service.return_value = mock_service

        # Test creation
        subscription_data = {
            "personId": "person-456",
            "projectId": "project-789",
            "status": "active",
        }

        response = self.client.post("/v2/subscriptions", json=subscription_data)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["personId"] == "person-456"
        assert data["data"]["projectId"] == "project-789"

    @patch("src.services.service_registry_manager.service_registry")
    def test_subscription_retrieval_endpoint(self, mock_service_registry):
        """Test subscription retrieval endpoint."""
        # Mock service
        mock_service = Mock()
        mock_service.get_subscription.return_value = {
            "id": "sub-123",
            "personId": "person-456",
            "projectId": "project-789",
            "status": "active",
            "isActive": True,
        }
        mock_service_registry.get_subscriptions_service.return_value = mock_service

        # Test retrieval
        response = self.client.get("/v2/subscriptions/sub-123")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == "sub-123"

    @patch("src.services.service_registry_manager.service_registry")
    def test_subscription_not_found(self, mock_service_registry):
        """Test subscription not found scenario."""
        # Mock service
        mock_service = Mock()
        mock_service.get_subscription.return_value = None
        mock_service_registry.get_subscriptions_service.return_value = mock_service

        # Test not found
        response = self.client.get("/v2/subscriptions/nonexistent")
        assert response.status_code == 404

    def test_subscription_validation(self):
        """Test subscription data validation."""
        # Test invalid data
        invalid_data = {
            "personId": "",  # Empty personId should fail
            "projectId": "project-123",
        }

        response = self.client.post("/v2/subscriptions", json=invalid_data)
        assert response.status_code == 422  # Validation error

    @patch("src.services.service_registry_manager.service_registry")
    def test_subscription_update_endpoint(self, mock_service_registry):
        """Test subscription update endpoint."""
        # Mock service
        mock_service = Mock()
        mock_service.update_subscription.return_value = {
            "id": "sub-123",
            "personId": "person-456",
            "projectId": "project-789",
            "status": "inactive",
            "isActive": False,
            "updatedAt": "2025-01-27T01:00:00Z",
        }
        mock_service_registry.get_subscriptions_service.return_value = mock_service

        # Test update with admin authentication
        update_data = {"status": "inactive"}
        response = self.client.put(
            "/v2/subscriptions/sub-123",
            json=update_data,
            headers=TestAuthUtils.get_admin_headers(),  # Add admin auth
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "inactive"
        assert data["data"]["isActive"] is False

    @patch("src.services.service_registry_manager.service_registry")
    def test_subscription_deletion_endpoint(self, mock_service_registry):
        """Test subscription deletion endpoint."""
        # Mock service
        mock_service = Mock()
        mock_service.delete_subscription.return_value = True
        mock_service_registry.get_subscriptions_service.return_value = mock_service

        # Test deletion
        response = self.client.delete("/v2/subscriptions/sub-123")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True

    @patch("src.services.service_registry_manager.service_registry")
    def test_subscription_service_registry_integration(self, mock_service_registry):
        """Test that subscription service is properly registered and accessible."""
        # Mock service registry
        mock_service = Mock()
        mock_service.list_subscriptions.return_value = [
            {
                "id": "sub-1",
                "personId": "person-1",
                "projectId": "project-1",
                "status": "active",
            }
        ]
        mock_service_registry.get_subscriptions_service.return_value = mock_service

        # Test service registry integration
        response = self.client.get("/v2/subscriptions")
        assert response.status_code == 200

        # Verify service was called through registry
        mock_service_registry.get_subscriptions_service.assert_called_once()
        mock_service.list_subscriptions.assert_called_once()

    def test_subscription_error_handling(self):
        """Test subscription error handling."""
        # Test with malformed JSON
        response = self.client.post(
            "/v2/subscriptions",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    @patch("src.services.service_registry_manager.service_registry")
    def test_subscription_list_with_limit(self, mock_service_registry):
        """Test subscription listing with limit parameter."""
        # Mock service
        mock_service = Mock()
        mock_service.list_subscriptions.return_value = [
            {"id": "sub-1", "personId": "person-1", "projectId": "project-1"}
        ]
        mock_service_registry.get_subscriptions_service.return_value = mock_service

        # Test with limit
        response = self.client.get("/v2/subscriptions?limit=5")
        assert response.status_code == 200

        # Verify limit was passed to service
        mock_service.list_subscriptions.assert_called_once_with(limit=5)
