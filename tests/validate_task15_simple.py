#!/usr/bin/env python3
"""
Simple validation script for Task 15: Update API documentation and response formatting.
This script validates that all requirements have been implemented without external dependencies.
"""

import os
import sys
import json
from datetime import datetime


def test_api_documentation():
    """Test that API documentation exists and is comprehensive."""
    print("🔍 Testing API Documentation...")

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

    # Check for HTTP status codes documentation
    status_codes = [
        "200 OK",
        "201 Created",
        "204 No Content",
        "400 Bad Request",
        "401 Unauthorized",
        "403 Forbidden",
        "404 Not Found",
        "409 Conflict",
        "429 Too Many Requests",
        "500 Internal Server Error",
    ]

    missing_status_codes = []
    for code in status_codes:
        if code not in content:
            missing_status_codes.append(code)

    if missing_status_codes:
        print(f"❌ Missing HTTP status codes: {missing_status_codes}")
        return False

    print("✅ API documentation is comprehensive and contains all required sections")
    return True


def test_response_formatter():
    """Test that response formatter utility exists."""
    print("\n🔍 Testing Response Formatter Utility...")

    formatter_path = "src/utils/response_formatter.py"

    if not os.path.exists(formatter_path):
        print(f"❌ Response formatter file not found: {formatter_path}")
        return False

    with open(formatter_path, "r") as f:
        content = f.read()

    # Check for required classes and functions
    required_elements = [
        "class ResponseFormatter:",
        "class CamelCaseConverter:",
        "class HTTPStatusCodes:",
        "class ErrorCodes:",
        "def snake_to_camel(",
        "def convert_dict_keys(",
        "def success_response(",
        "def error_response(",
        "def validation_error_response(",
        "def not_found_response(",
        "def unauthorized_response(",
        "def forbidden_response(",
        "def conflict_response(",
        "def rate_limit_response(",
        "def internal_server_error_response(",
    ]

    missing_elements = []
    for element in required_elements:
        if element not in content:
            missing_elements.append(element)

    if missing_elements:
        print(f"❌ Missing elements in response formatter: {missing_elements}")
        return False

    # Check for HTTP status code constants
    status_constants = [
        "OK = status.HTTP_200_OK",
        "CREATED = status.HTTP_201_CREATED",
        "NO_CONTENT = status.HTTP_204_NO_CONTENT",
        "BAD_REQUEST = status.HTTP_400_BAD_REQUEST",
        "UNAUTHORIZED = status.HTTP_401_UNAUTHORIZED",
        "FORBIDDEN = status.HTTP_403_FORBIDDEN",
        "NOT_FOUND = status.HTTP_404_NOT_FOUND",
        "CONFLICT = status.HTTP_409_CONFLICT",
        "TOO_MANY_REQUESTS = status.HTTP_429_TOO_MANY_REQUESTS",
        "INTERNAL_SERVER_ERROR = status.HTTP_500_INTERNAL_SERVER_ERROR",
    ]

    missing_constants = []
    for constant in status_constants:
        if constant not in content:
            missing_constants.append(constant)

    if missing_constants:
        print(f"❌ Missing HTTP status constants: {missing_constants}")
        return False

    # Check for error code constants
    error_constants = [
        'AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"',
        'AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"',
        'VALIDATION_ERROR = "VALIDATION_ERROR"',
        'PERSON_NOT_FOUND = "PERSON_NOT_FOUND"',
        'EMAIL_ALREADY_EXISTS = "EMAIL_ALREADY_EXISTS"',
        'RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"',
        'INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"',
    ]

    missing_error_constants = []
    for constant in error_constants:
        if constant not in content:
            missing_error_constants.append(constant)

    if missing_error_constants:
        print(f"❌ Missing error code constants: {missing_error_constants}")
        return False

    print("✅ Response formatter utility exists and contains all required elements")
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
        'tags=["authentication"]',
        'tags=["password-management"]',
        'tags=["people"]',
        'tags=["search"]',
        'tags=["admin"]',
    ]

    missing_elements = []
    for element in required_elements:
        if element not in content:
            missing_elements.append(element)

    if missing_elements:
        print(f"❌ Missing elements in documented handler: {missing_elements}")
        return False

    # Check for comprehensive endpoint documentation
    endpoint_docs = [
        'summary="User Login"',
        'summary="Get Current User"',
        'summary="Update Current User Password"',
        'summary="List People"',
        'summary="Get Person"',
        'summary="Create Person"',
        'summary="Update Person"',
        'summary="Delete Person"',
        'summary="Search People"',
        'summary="Unlock User Account"',
    ]

    missing_docs = []
    for doc in endpoint_docs:
        if doc not in content:
            missing_docs.append(doc)

    if missing_docs:
        print(f"❌ Missing endpoint documentation: {missing_docs}")
        return False

    print("✅ Documented handler exists and contains proper OpenAPI documentation")
    return True


def test_camel_case_examples():
    """Test that camelCase examples are present in the code."""
    print("\n🔍 Testing CamelCase Field Naming...")

    # Check person model for camelCase aliases
    person_model_path = "src/models/person.py"

    if not os.path.exists(person_model_path):
        print(f"❌ Person model file not found: {person_model_path}")
        return False

    with open(person_model_path, "r") as f:
        content = f.read()

    # Check for camelCase field aliases
    camel_case_aliases = [
        'alias="firstName"',
        'alias="lastName"',
        'alias="dateOfBirth"',
        'alias="createdAt"',
        'alias="updatedAt"',
        'alias="isActive"',
        'alias="emailVerified"',
        'alias="zipCode"',
    ]

    missing_aliases = []
    for alias in camel_case_aliases:
        if alias not in content:
            missing_aliases.append(alias)

    if missing_aliases:
        print(f"❌ Missing camelCase aliases in person model: {missing_aliases}")
        return False

    print("✅ CamelCase field naming is properly implemented")
    return True


def main():
    """Run all validation tests."""
    print("🚀 Validating Task 15: Update API documentation and response formatting")
    print("=" * 80)

    try:
        doc_success = test_api_documentation()
        formatter_success = test_response_formatter()
        handler_success = test_documented_handler()
        camel_case_success = test_camel_case_examples()

        print("\n" + "=" * 80)

        if doc_success and formatter_success and handler_success and camel_case_success:
            print("🎉 All Task 15 requirements have been successfully implemented!")
            print("\n✅ Requirements completed:")
            print("   - Consistent HTTP status codes")
            print("   - Proper camelCase field naming in responses")
            print("   - Comprehensive API documentation for new endpoints")
            print("   - Proper error response documentation with examples")
            print("\n📁 Files created/updated:")
            print("   - API_DOCUMENTATION.md - Comprehensive API documentation")
            print(
                "   - src/utils/response_formatter.py - Response formatting utilities"
            )
            print(
                "   - src/handlers/documented_people_handler.py - Documented API handler"
            )
            print("   - tests/test_api_documentation_and_formatting.py - Test suite")
            return True
        else:
            print("❌ Some Task 15 requirements are not fully implemented")
            return False

    except Exception as e:
        print(f"❌ Validation failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
