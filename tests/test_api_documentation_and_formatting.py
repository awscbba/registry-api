"""
Tests for API documentation and response formatting (Task 15).
This test file verifies:
- Consistent HTTP status codes
- Proper camelCase field naming in responses
- Comprehensive API documentation
- Proper error response documentation with examples
"""

import pytest
from datetime import datetime
import json
import os

from src.utils.response_formatter import (
    ResponseFormatter,
    CamelCaseConverter,
    HTTPStatusCodes,
    ErrorCodes,
    create_person_response,
    create_validation_error,
)


class TestResponseFormatter:
    """Test the response formatting utilities."""

    def test_success_response(self):
        """Test successful response formatting."""
        data = {"id": "123", "name": "John"}
        response = ResponseFormatter.success_response(data, HTTPStatusCodes.OK)

        assert response.status_code == 200
        assert json.loads(response.body) == data

    def test_error_response(self):
        """Test error response formatting."""
        error = ResponseFormatter.error_response(
            error_code=ErrorCodes.VALIDATION_ERROR,
            message="Test error",
            status_code=HTTPStatusCodes.BAD_REQUEST,
        )

        assert error.status_code == 400
        assert error.detail["error"] == ErrorCodes.VALIDATION_ERROR
        assert error.detail["message"] == "Test error"
        assert "timestamp" in error.detail
        assert "requestId" in error.detail

    def test_validation_error_response(self):
        """Test validation error response formatting."""
        validation_errors = [
            create_validation_error(
                "email", "Invalid email format", ErrorCodes.EMAIL_FORMAT
            )
        ]

        error = ResponseFormatter.validation_error_response(validation_errors)

        assert error.status_code == 400
        assert error.detail["error"] == ErrorCodes.VALIDATION_ERROR
        assert error.detail["details"] == validation_errors

    def test_not_found_response(self):
        """Test 404 not found response formatting."""
        error = ResponseFormatter.not_found_response("Person")

        assert error.status_code == 404
        assert error.detail["error"] == "PERSON_NOT_FOUND"
        assert error.detail["message"] == "Person not found"

    def test_unauthorized_response(self):
        """Test 401 unauthorized response formatting."""
        error = ResponseFormatter.unauthorized_response()

        assert error.status_code == 401
        assert error.detail["error"] == ErrorCodes.AUTHENTICATION_REQUIRED

    def test_forbidden_response(self):
        """Test 403 forbidden response formatting."""
        error = ResponseFormatter.forbidden_response()

        assert error.status_code == 403
        assert error.detail["error"] == ErrorCodes.INSUFFICIENT_PERMISSIONS

    def test_conflict_response(self):
        """Test 409 conflict response formatting."""
        error = ResponseFormatter.conflict_response(
            "Email already exists", ErrorCodes.EMAIL_ALREADY_EXISTS
        )

        assert error.status_code == 409
        assert error.detail["error"] == ErrorCodes.EMAIL_ALREADY_EXISTS

    def test_rate_limit_response(self):
        """Test 429 rate limit response formatting."""
        error = ResponseFormatter.rate_limit_response()

        assert error.status_code == 429
        assert error.detail["error"] == ErrorCodes.RATE_LIMIT_EXCEEDED

    def test_internal_server_error_response(self):
        """Test 500 internal server error response formatting."""
        error = ResponseFormatter.internal_server_error_response()

        assert error.status_code == 500
        assert error.detail["error"] == ErrorCodes.INTERNAL_SERVER_ERROR


class TestCamelCaseConverter:
    """Test the camelCase conversion utilities."""

    def test_snake_to_camel(self):
        """Test snake_case to camelCase conversion."""
        assert CamelCaseConverter.snake_to_camel("first_name") == "firstName"
        assert CamelCaseConverter.snake_to_camel("last_name") == "lastName"
        assert CamelCaseConverter.snake_to_camel("date_of_birth") == "dateOfBirth"
        assert CamelCaseConverter.snake_to_camel("created_at") == "createdAt"
        assert CamelCaseConverter.snake_to_camel("updated_at") == "updatedAt"
        assert CamelCaseConverter.snake_to_camel("is_active") == "isActive"
        assert CamelCaseConverter.snake_to_camel("email_verified") == "emailVerified"

    def test_convert_dict_keys(self):
        """Test dictionary key conversion to camelCase."""
        snake_dict = {
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1990-01-15",
            "is_active": True,
            "email_verified": False,
        }

        camel_dict = CamelCaseConverter.convert_dict_keys(snake_dict)

        expected = {
            "firstName": "John",
            "lastName": "Doe",
            "dateOfBirth": "1990-01-15",
            "isActive": True,
            "emailVerified": False,
        }

        assert camel_dict == expected

    def test_convert_nested_dict_keys(self):
        """Test nested dictionary key conversion."""
        nested_dict = {
            "person_info": {"first_name": "John", "last_name": "Doe"},
            "address_info": {"street_address": "123 Main St", "zip_code": "12345"},
        }

        camel_dict = CamelCaseConverter.convert_dict_keys(nested_dict)

        expected = {
            "personInfo": {"firstName": "John", "lastName": "Doe"},
            "addressInfo": {"streetAddress": "123 Main St", "zipCode": "12345"},
        }

        assert camel_dict == expected

    def test_convert_response_data_list(self):
        """Test response data conversion for lists."""
        data_list = [
            {"first_name": "John", "last_name": "Doe"},
            {"first_name": "Jane", "last_name": "Smith"},
        ]

        converted = CamelCaseConverter.convert_response_data(data_list)

        expected = [
            {"firstName": "John", "lastName": "Doe"},
            {"firstName": "Jane", "lastName": "Smith"},
        ]

        assert converted == expected


class TestValidationErrorFormat:
    """Test validation error format matches documentation."""

    def test_validation_error_format(self):
        """Test validation error format matches documentation."""
        validation_errors = [
            create_validation_error(
                "email", "Invalid email format", ErrorCodes.EMAIL_FORMAT
            ),
            create_validation_error(
                "phone", "Invalid phone format", ErrorCodes.PHONE_FORMAT
            ),
        ]

        error = ResponseFormatter.validation_error_response(validation_errors)

        # Check error structure matches documentation
        detail = error.detail
        assert detail["error"] == "VALIDATION_ERROR"
        assert detail["message"] == "The request contains invalid data"
        assert "details" in detail
        assert len(detail["details"]) == 2
        assert "timestamp" in detail
        assert "requestId" in detail

        # Check detail structure
        for detail_item in detail["details"]:
            assert "field" in detail_item
            assert "message" in detail_item
            assert "code" in detail_item


class TestHTTPStatusCodes:
    """Test that HTTP status codes are used consistently."""

    def test_status_code_constants(self):
        """Test that status code constants are properly defined."""
        assert HTTPStatusCodes.OK == 200
        assert HTTPStatusCodes.CREATED == 201
        assert HTTPStatusCodes.NO_CONTENT == 204
        assert HTTPStatusCodes.BAD_REQUEST == 400
        assert HTTPStatusCodes.UNAUTHORIZED == 401
        assert HTTPStatusCodes.FORBIDDEN == 403
        assert HTTPStatusCodes.NOT_FOUND == 404
        assert HTTPStatusCodes.CONFLICT == 409
        assert HTTPStatusCodes.TOO_MANY_REQUESTS == 429
        assert HTTPStatusCodes.INTERNAL_SERVER_ERROR == 500

    def test_error_codes_constants(self):
        """Test that error code constants are properly defined."""
        # Authentication errors
        assert ErrorCodes.AUTHENTICATION_FAILED == "AUTHENTICATION_FAILED"
        assert ErrorCodes.AUTHENTICATION_REQUIRED == "AUTHENTICATION_REQUIRED"
        assert ErrorCodes.ACCOUNT_LOCKED == "ACCOUNT_LOCKED"

        # Validation errors
        assert ErrorCodes.VALIDATION_ERROR == "VALIDATION_ERROR"
        assert ErrorCodes.EMAIL_FORMAT == "EMAIL_FORMAT"
        assert ErrorCodes.PHONE_FORMAT == "PHONE_FORMAT"

        # Resource errors
        assert ErrorCodes.PERSON_NOT_FOUND == "PERSON_NOT_FOUND"
        assert ErrorCodes.EMAIL_ALREADY_EXISTS == "EMAIL_ALREADY_EXISTS"

        # System errors
        assert ErrorCodes.RATE_LIMIT_EXCEEDED == "RATE_LIMIT_EXCEEDED"
        assert ErrorCodes.INTERNAL_SERVER_ERROR == "INTERNAL_SERVER_ERROR"


class TestPersonResponseFormatting:
    """Test that person responses use proper camelCase formatting."""

    def test_person_response_camel_case(self):
        """Test that PersonResponse uses camelCase field names."""
        # This would typically test the actual PersonResponse model
        # but we'll test the conversion utility instead
        person_data = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone": "+1-555-0123",
            "date_of_birth": "1990-01-15",
            "created_at": "2025-01-20T10:30:00Z",
            "updated_at": "2025-01-22T10:30:00Z",
            "is_active": True,
            "email_verified": True,
        }

        camel_case_data = CamelCaseConverter.convert_response_data(person_data)

        # Check that all fields are in camelCase
        expected_fields = [
            "id",
            "firstName",
            "lastName",
            "email",
            "phone",
            "dateOfBirth",
            "createdAt",
            "updatedAt",
            "isActive",
            "emailVerified",
        ]

        for field in expected_fields:
            assert field in camel_case_data

        # Check that snake_case fields are not present
        snake_case_fields = [
            "first_name",
            "last_name",
            "date_of_birth",
            "created_at",
            "updated_at",
            "is_active",
            "email_verified",
        ]

        for field in snake_case_fields:
            assert field not in camel_case_data

    def test_address_response_camel_case(self):
        """Test that address fields use camelCase."""
        address_data = {
            "street": "123 Main St",
            "city": "Anytown",
            "state": "CA",
            "zip_code": "12345",
            "country": "USA",
        }

        camel_case_data = CamelCaseConverter.convert_response_data(address_data)

        assert "zipCode" in camel_case_data
        assert "zip_code" not in camel_case_data
        assert camel_case_data["zipCode"] == "12345"


class TestAPIDocumentationFile:
    """Test that the API documentation file is comprehensive."""

    @pytest.mark.skip(
        reason="API documentation moved to centralized registry-documentation repository"
    )
    def test_api_documentation_exists(self):
        """Test that API documentation file exists and has required sections."""
        # NOTE: API documentation has been moved to ../registry-documentation/api/API_DOCUMENTATION.md
        # This test is skipped as documentation is now centralized
        pass

    @pytest.mark.skip(
        reason="API documentation moved to centralized registry-documentation repository"
    )
    def test_api_documentation_examples(self):
        """Test that API documentation contains proper examples."""
        # NOTE: API documentation has been moved to ../registry-documentation/api/API_DOCUMENTATION.md
        # This test is skipped as documentation is now centralized
        pass


if __name__ == "__main__":
    pytest.main([__file__])
