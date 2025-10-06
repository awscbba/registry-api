"""
Test cases for Image Upload API endpoints
Tests the REST API layer for S3 image upload functionality
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.app import create_app


class TestImageUploadAPI:
    """Test cases for image upload API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        app = create_app()
        return TestClient(app)

    def test_get_presigned_upload_url_endpoint(self, client):
        """Test GET /v2/images/upload-url endpoint"""
        # Arrange
        request_data = {
            "filename": "test-image.jpg",
            "content_type": "image/jpeg",
            "file_size": 1024000,
        }

        # Act
        response = client.post("/v2/images/upload-url", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "uploadUrl" in data["data"]
        assert "imageId" in data["data"]
        assert "cloudFrontUrl" in data["data"]

    def test_invalid_file_type_returns_400(self, client):
        """Test that invalid file types return 422 validation error"""
        # Arrange
        request_data = {
            "filename": "test-file.txt",
            "content_type": "text/plain",
            "file_size": 1024,
        }

        # Act
        response = client.post("/v2/images/upload-url", json=request_data)

        # Assert
        assert response.status_code == 422  # Pydantic validation error
        data = response.json()
        assert "detail" in data

    def test_file_too_large_returns_400(self, client):
        """Test that files too large return 422 validation error"""
        # Arrange
        request_data = {
            "filename": "large-image.jpg",
            "content_type": "image/jpeg",
            "file_size": 10 * 1024 * 1024 + 1,  # 10MB + 1 byte
        }

        # Act
        response = client.post("/v2/images/upload-url", json=request_data)

        # Assert
        assert response.status_code == 422  # Pydantic validation error
        data = response.json()
        assert "detail" in data

    def test_successful_upload_returns_cloudfront_url(self, client):
        """Test successful upload returns CloudFront URL"""
        # Arrange
        request_data = {
            "filename": "valid-image.png",
            "content_type": "image/png",
            "file_size": 2048000,  # 2MB
        }

        # Act
        response = client.post("/v2/images/upload-url", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify CloudFront URL format
        cloudfront_url = data["data"]["cloudFrontUrl"]
        assert cloudfront_url.startswith("https://")
        assert "cloudfront.net" in cloudfront_url or "amazonaws.com" in cloudfront_url

    def test_image_upload_api_endpoints_exist(self, client):
        """Test that image upload API endpoints exist and don't return 404"""
        # Test POST /v2/images/upload-url
        response = client.post("/v2/images/upload-url", json={})
        assert (
            response.status_code != 404
        )  # Endpoint exists (may return validation error)
