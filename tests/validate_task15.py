#!/usr/bin/env python3
"""
Validation script for Task 15: Update API documentation and response formatting.
This script validates that all requirements have been implemented:
- Consistent HTTP status codes
- Proper camelCase field naming in responses
- Comprehensive API documentation
- Proper error response documentation with examples
"""

import os
import sys
import json
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    from utils.response_formatter import (
        ResponseFormatter,
        CamelCaseConverter,
        HTTPStatusCodes,
        ErrorCodes,
        create_person_response,
        create_validation_error,
    )

    print("✅ Response formatter utilities imported successfully")
except ImportError as e:
    print(f"❌ Failed to import response formatter utilities: {e}")
    sys.exit(1)


def test_http_status_codes():
    """Test that HTTP status codes are properly defined."""
    print("\n🔍 Testing HTTP Status Codes...")

    # Test status code constants
    assert HTTPStatusCodes.OK == 200, "OK status code should be 200"
    assert HTTPStatusCodes.CREATED == 201, "CREATED status code should be 201"
    assert HTTPStatusCodes.NO_CONTENT == 204, "NO_CONTENT status code should be 204"
    assert HTTPStatusCodes.BAD_REQUEST == 400, "BAD_REQUEST status code should be 400"
    assert HTTPStatusCodes.UNAUTHORIZED == 401, "UNAUTHORIZED status code should be 401"
    assert HTTPStatusCodes.FORBIDDEN == 403, "FORBIDDEN status code should be 403"
    assert HTTPStatusCodes.NOT_FOUND == 404, "NOT_FOUND status code should be 404"
    assert HTTPStatusCodes.CONFLICT == 409, "CONFLICT status code should be 409"
    assert (
        HTTPStatusCodes.TOO_MANY_REQUESTS == 429
    ), "TOO_MANY_REQUESTS status code should be 429"
    assert (
        HTTPStatusCodes.INTERNAL_SERVER_ERROR == 500
    ), "INTERNAL_SERVER_ERROR status code should be 500"

    print("✅ All HTTP status codes are properly defined")


def test_error_codes():
    """Test that error codes are properly defined."""
    print("\n🔍 Testing Error Codes...")

    # Test authentication error codes
    assert ErrorCodes.AUTHENTICATION_FAILED == "AUTHENTICATION_FAILED"
    assert ErrorCodes.AUTHENTICATION_REQUIRED == "AUTHENTICATION_REQUIRED"
    assert ErrorCodes.ACCOUNT_LOCKED == "ACCOUNT_LOCKED"

    # Test validation error codes
    assert ErrorCodes.VALIDATION_ERROR == "VALIDATION_ERROR"
    assert ErrorCodes.EMAIL_FORMAT == "EMAIL_FORMAT"
    assert ErrorCodes.PHONE_FORMAT == "PHONE_FORMAT"

    # Test resource error codes
    assert ErrorCodes.PERSON_NOT_FOUND == "PERSON_NOT_FOUND"
    assert ErrorCodes.EMAIL_ALREADY_EXISTS == "EMAIL_ALREADY_EXISTS"

    # Test system error codes
    assert ErrorCodes.RATE_LIMIT_EXCEEDED == "RATE_LIMIT_EXCEEDED"
    assert ErrorCodes.INTERNAL_SERVER_ERROR == "INTERNAL_SERVER_ERROR"

    print("✅ All error codes are properly defined")


def test_camel_case_conversion():
    """Test camelCase conversion functionality."""
    print("\n🔍 Testing CamelCase Conversion...")

    # Test snake_case to camelCase conversion
    assert CamelCaseConverter.snake_to_camel("first_name") == "firstName"
    assert CamelCaseConverter.snake_to_camel("last_name") == "lastName"
    assert CamelCaseConverter.snake_to_camel("date_of_birth") == "dateOfBirth"
    assert CamelCaseConverter.snake_to_camel("created_at") == "createdAt"
    assert CamelCaseConverter.snake_to_camel("updated_at") == "updatedAt"
    assert CamelCaseConverter.snake_to_camel("is_active") == "isActive"
    assert CamelCaseConverter.snake_to_camel("email_verified") == "emailVerified"

    # Test dictionary conversion
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

    assert camel_dict == expected, "Dictionary conversion should work correctly"

    print("✅ CamelCase conversion works correctly")


def test_response_formatting():
    """Test response formatting functionality."""
    print("\n🔍 Testing Response Formatting...")

    # Test error response formatting
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

    # Test validation error response
    validation_errors = [
        create_validation_error(
            "email", "Invalid email format", ErrorCodes.EMAIL_FORMAT
        )
    ]

    validation_error = ResponseFormatter.validation_error_response(validation_errors)

    assert validation_error.status_code == 400
    assert validation_error.detail["error"] == ErrorCodes.VALIDATION_ERROR
    assert validation_error.detail["details"] == validation_errors

    # Test not found response
    not_found_error = ResponseFormatter.not_found_response("Person")

    assert not_found_error.status_code == 404
    assert not_found_error.detail["error"] == "PERSON_NOT_FOUND"
    assert not_found_error.detail["message"] == "Person not found"

    print("✅ Response formatting works correctly")


def test_api_documentation():
    """Test that API documentation exists and is comprehensive."""
    print("\n🔍 Testing API Documentation...")

    doc_path = "API_DOCUMENTATION.md"

    if not os.path.exists(doc_path):
        print(f"❌ API documentation file not found: {doc_path}")
        return False

    with open(doc_path, "r") as f:
        content = f.read()

    # Check for required sections
    required_sections = [
        "# People Register API Documentation",
        "## Overview",
        "## Authentication",
        "## Response Format",
        "## HTTP Status Codes",
        "## Endpoints",
        "### Health Check",
        "### Authentication",
        "### Password Management",
        "### People Management",
        "### Search",
        "### Admin Functions",
        "## Error Codes",
        "## Rate Limiting",
        "## Security Features",
        "## Field Naming Convention",
    ]

    missing_sections = []
    for section in required_sections:
        if section not in content:
            missing_sections.append(section)

    if missing_sections:
        print(f"❌ Missing documentation sections: {missing_sections}")
        return False

    # Check for camelCase examples
    camel_case_examples = [
        '"firstName": "John"',
        '"lastName": "Doe"',
        '"dateOfBirth": "1990-01-15"',
        '"createdAt": "2025-01-22T10:30:00Z"',
        '"updatedAt": "2025-01-22T10:30:00Z"',
        '"isActive": true',
        '"emailVerified": true',
    ]

    missing_examples = []
    for example in camel_case_examples:
        if example not in content:
            missing_examples.append(example)

    if missing_examples:
        print(f"❌ Missing camelCase examples: {missing_examples}")
        return False

    # Check for error response examples
    error_examples = [
        '"error": "AUTHENTICATION_FAILED"',
        '"error": "VALIDATION_ERROR"',
        '"error": "PERSON_NOT_FOUND"',
        '"requestId": "req_123456789"',
    ]

    missing_error_examples = []
    for example in error_examples:
        if example not in content:
            missing_error_examples.append(example)

    if missing_error_examples:
        print(f"❌ Missing error response examples: {missing_error_examples}")
        return False

    print("✅ API documentation is comprehensive and contains all required sections")
    return True


def test_documented_handler():
    """Test that the documented handler exists."""
    print("\n🔍 Testing Documented Handler...")

    handler_path = "src/handlers/documented_people_handler.py"

    if not os.path.exists(handler_path):
        print(f"❌ Documented handler file not found: {handler_path}")
        return False

    with open(handler_path, "r") as f:
        content = f.read()

    # Check for FastAPI app with comprehensive documentation
    required_elements = [
        "app = FastAPI(",
        'title="People Register API"',
        "openapi_tags=[",
        "@app.get(",
        'tags=["health"]',
        'summary="Health Check"',
        "responses={",
        '"application/json"',
        '"example"',
    ]

    missing_elements = []
    for element in required_elements:
        if element not in content:
            missing_elements.append(element)

    if missing_elements:
        print(f"❌ Missing elements in documented handler: {missing_elements}")
        return False

    print("✅ Documented handler exists and contains proper OpenAPI documentation")
    return True


def main():
    """Run all validation tests."""
    print("🚀 Validating Task 15: Update API documentation and response formatting")
    print("=" * 80)

    try:
        test_http_status_codes()
        test_error_codes()
        test_camel_case_conversion()
        test_response_formatting()

        doc_success = test_api_documentation()
        handler_success = test_documented_handler()

        print("\n" + "=" * 80)

        if doc_success and handler_success:
            print("🎉 All Task 15 requirements have been successfully implemented!")
            print("\n✅ Requirements completed:")
            print("   - Consistent HTTP status codes")
            print("   - Proper camelCase field naming in responses")
            print("   - Comprehensive API documentation for new endpoints")
            print("   - Proper error response documentation with examples")
            return True
        else:
            print("❌ Some Task 15 requirements are not fully implemented")
            return False

    except Exception as e:
        print(f"❌ Validation failed with error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
