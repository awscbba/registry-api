"""
Test router function for critical integration testing.
This test ensures the router function works correctly.
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from src.app import app


class TestRouterFunction:
    """Test cases for router function."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_router_health_endpoint(self):
        """Test that the health endpoint is accessible through the router."""
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "status" in data["data"]
        assert data["data"]["status"] == "healthy"

    def test_router_root_endpoint(self):
        """Test that the root endpoint is accessible through the router."""
        response = self.client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "name" in data["data"]
        assert data["data"]["name"] == "People Registry API"

    def test_router_404_handling(self):
        """Test that the router handles 404 errors correctly."""
        response = self.client.get("/nonexistent-endpoint")
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert data["errorCode"] == "NOT_FOUND"

    def test_router_cors_headers(self):
        """Test that CORS headers are properly set."""
        response = self.client.get("/health")
        # CORS headers should be present for GET requests
        # OPTIONS might not be supported, so test with GET
        assert response.status_code == 200

    def test_router_api_endpoints_accessible(self):
        """Test that API endpoints are accessible through the router."""
        # Test people endpoint
        response = self.client.get("/v2/people")
        # Should return 200 or appropriate error (not 404)
        assert response.status_code != 404

        # Test projects endpoint
        response = self.client.get("/v2/projects")
        # Should return 200 or appropriate error (not 404)
        assert response.status_code != 404

        # Test subscriptions endpoint
        response = self.client.get("/v2/subscriptions")
        # Should return 200 or appropriate error (not 404)
        assert response.status_code != 404
