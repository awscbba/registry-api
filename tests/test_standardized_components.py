"""
Tests for the new standardized components: error handling, logging, and response formats.
"""

import pytest
import json
from unittest.mock import MagicMock, patch
from fastapi import HTTPException, status
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from utils.error_handler import StandardErrorHandler, handle_database_error
from utils.logging_config import APILogger, get_handler_logger
from utils.response_models import (
    ResponseFactory,
    create_v1_response,
    create_v2_response,
)


class TestStandardErrorHandler:
    """Test the standardized error handler"""

    def test_internal_server_error_creation(self):
        """Test creating standardized internal server error"""
        error = Exception("Test error")
        http_exception = StandardErrorHandler.internal_server_error(
            operation="testing", error=error, person_id="test-123"
        )

        assert isinstance(http_exception, HTTPException)
        assert http_exception.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert http_exception.detail["error"] == "INTERNAL_SERVER_ERROR"
        assert "testing" in http_exception.detail["message"]
        assert http_exception.detail["operation"] == "testing"

    def test_bad_request_error_creation(self):
        """Test creating standardized bad request error"""
        http_exception = StandardErrorHandler.bad_request_error(
            message="Invalid input",
            error_code="VALIDATION_ERROR",
            details={"field": "email"},
        )

        assert http_exception.status_code == status.HTTP_400_BAD_REQUEST
        assert http_exception.detail["error"] == "VALIDATION_ERROR"
        assert http_exception.detail["message"] == "Invalid input"
        assert http_exception.detail["details"]["field"] == "email"

    def test_not_found_error_creation(self):
        """Test creating standardized not found error"""
        http_exception = StandardErrorHandler.not_found_error(
            resource="Person", resource_id="123"
        )

        assert http_exception.status_code == status.HTTP_404_NOT_FOUND
        assert http_exception.detail["error"] == "NOT_FOUND"
        assert "Person not found" in http_exception.detail["message"]
        assert http_exception.detail["resource_id"] == "123"

    def test_handle_database_error_convenience_function(self):
        """Test the convenience function for database errors"""
        error = Exception("Database connection failed")
        http_exception = handle_database_error("creating user", error, "user-123")

        assert isinstance(http_exception, HTTPException)
        assert http_exception.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestAPILogger:
    """Test the standardized API logger"""

    def test_logger_creation(self):
        """Test creating an API logger"""
        logger = APILogger("test_handler")
        assert logger.logger.name == "test_handler"

    def test_get_handler_logger(self):
        """Test getting a handler logger"""
        logger = get_handler_logger("versioned_api")
        assert isinstance(logger, APILogger)
        assert "handler.versioned_api" in logger.logger.name

    @patch("sys.stdout")
    def test_structured_logging(self, mock_stdout):
        """Test that structured logging produces JSON output"""
        logger = APILogger("test")
        logger.info("Test message", user_id="123", operation="test")

        # Verify that logging was called (stdout was written to)
        assert mock_stdout.write.called

    def test_api_request_logging(self):
        """Test API request logging with context"""
        logger = APILogger("test")

        # This should not raise an exception
        logger.log_api_request("GET", "/v1/subscriptions", user_id="123")
        logger.log_api_response("GET", "/v1/subscriptions", 200, duration_ms=150.5)

    def test_database_operation_logging(self):
        """Test database operation logging"""
        logger = APILogger("test")

        # This should not raise an exception
        logger.log_database_operation(
            "get_all_subscriptions",
            "subscriptions_table",
            success=True,
            duration_ms=50.2,
        )

    def test_security_event_logging(self):
        """Test security event logging"""
        logger = APILogger("test")

        # This should not raise an exception
        logger.log_security_event(
            "login_attempt", user_id="123", ip_address="192.168.1.1", success=True
        )


class TestResponseModels:
    """Test the standardized response models"""

    def test_create_v1_response_with_list(self):
        """Test creating v1-style response with list data"""
        data = [{"id": "1", "name": "Test"}, {"id": "2", "name": "Test2"}]
        response = create_v1_response(data)

        assert response["success"] is True
        assert response["data"] == data
        assert response["count"] == 2

    def test_create_v1_response_with_dict(self):
        """Test creating v1-style response with dict data"""
        data = {"id": "1", "name": "Test"}
        response = create_v1_response(data)

        assert response["success"] is True
        assert response["data"] == data
        assert "count" not in response

    def test_create_v2_response_with_metadata(self):
        """Test creating v2-style response with metadata"""
        data = [{"id": "1", "name": "Test"}]
        metadata = {"total_count": 1, "filtered": False}
        response = create_v2_response(data, metadata=metadata)

        assert response["success"] is True
        assert response["version"] == "v2"
        assert response["data"] == data
        assert response["count"] == 1
        assert response["metadata"] == metadata
        assert "timestamp" in response

    def test_response_factory_success_data(self):
        """Test ResponseFactory for creating success responses"""
        data = {"id": "1", "name": "Test"}
        response = ResponseFactory.success_data(data, version="v2")

        assert response.success is True
        assert response.version == "v2"
        assert response.data == data

    def test_response_factory_success_list(self):
        """Test ResponseFactory for creating list responses"""
        data = [{"id": "1", "name": "Test"}, {"id": "2", "name": "Test2"}]
        response = ResponseFactory.success_list(data, version="v2")

        assert response.success is True
        assert response.version == "v2"
        assert response.data == data
        assert response.count == 2

    def test_response_factory_error(self):
        """Test ResponseFactory for creating error responses"""
        response = ResponseFactory.error(
            error_code="VALIDATION_ERROR",
            message="Invalid input",
            details={"field": "email"},
            version="v2",
        )

        assert response.success is False
        assert response.version == "v2"
        assert response.error == "VALIDATION_ERROR"
        assert response.message == "Invalid input"
        assert response.details["field"] == "email"

    def test_response_factory_health(self):
        """Test ResponseFactory for creating health responses"""
        checks = {"database": "healthy", "cache": "healthy"}
        response = ResponseFactory.health("api-service", checks=checks)

        assert response.success is True
        assert response.status == "healthy"
        assert response.service == "api-service"
        assert response.checks == checks

    def test_response_factory_paginated(self):
        """Test ResponseFactory for creating paginated responses"""
        data = [{"id": str(i), "name": f"Test{i}"} for i in range(5)]
        response = ResponseFactory.paginated(
            data=data, page=1, limit=10, total=25, version="v2"
        )

        assert response.success is True
        assert response.version == "v2"
        assert response.data == data
        assert response.pagination["page"] == 1
        assert response.pagination["limit"] == 10
        assert response.pagination["total"] == 25
        assert response.pagination["count"] == 5
        assert response.pagination["pages"] == 3
        assert response.pagination["has_next"] is True
        assert response.pagination["has_prev"] is False


class TestIntegrationWithVersionedAPI:
    """Test integration of standardized components with versioned API"""

    def test_imports_work_correctly(self):
        """Test that all imports work correctly"""
        # Test that the utility modules can be imported
        from utils.error_handler import StandardErrorHandler
        from utils.logging_config import get_handler_logger
        from utils.response_models import ResponseFactory

        # Verify the handler uses the new components by checking source
        handler_source = open(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "src",
                "handlers",
                "versioned_api_handler.py",
            )
        ).read()

        assert "from ..utils.error_handler import" in handler_source
        assert "from ..utils.logging_config import" in handler_source
        assert "from ..utils.response_models import" in handler_source

    def test_response_format_consistency(self):
        """Test that response formats are consistent between v1 and v2"""
        # Test data
        test_data = [{"id": "1", "name": "Test"}]

        # V1 response
        v1_response = create_v1_response(test_data)

        # V2 response
        v2_response = create_v2_response(test_data)

        # Both should have success and data fields
        assert "success" in v1_response
        assert "data" in v1_response
        assert "success" in v2_response
        assert "data" in v2_response

        # V2 should have additional metadata
        assert "version" in v2_response
        assert "timestamp" in v2_response
        assert v2_response["version"] == "v2"

        # Data should be the same
        assert v1_response["data"] == v2_response["data"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
