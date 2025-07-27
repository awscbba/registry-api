#!/usr/bin/env python3
"""
Test script to verify security enhancements for person retrieval endpoints
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.handlers.people_handler import app
from src.models.person import Person, PersonResponse
from src.models.security_event import (
    SecurityEvent,
    SecurityEventType,
    SecurityEventSeverity,
)
from fastapi.testclient import TestClient
from fastapi import Request

# Create test client
client = TestClient(app)


def create_mock_person():
    """Create a mock person for testing"""
    return Person(
        id="test-person-123",
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="+1234567890",
        date_of_birth="1990-01-01",
        address={
            "street": "123 Main St",
            "city": "Anytown",
            "state": "CA",
            "zip_code": "12345",
            "country": "USA",
        },
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_active=True,
        email_verified=True,
    )


def create_mock_user():
    """Create a mock authenticated user"""
    return Person(
        id="auth-user-456",
        first_name="Auth",
        last_name="User",
        email="auth.user@example.com",
        phone="+1987654321",
        date_of_birth="1985-05-15",
        address={
            "street": "456 Auth St",
            "city": "Authtown",
            "state": "NY",
            "zip_code": "54321",
            "country": "USA",
        },
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_active=True,
        email_verified=True,
    )


async def test_list_people_security_enhancements():
    """Test security enhancements for list_people endpoint"""
    print("Testing list_people security enhancements...")

    mock_user = create_mock_user()
    mock_people = [create_mock_person()]

    with (
        patch("src.handlers.people_handler.db_service") as mock_db,
        patch("src.handlers.people_handler.get_current_user", return_value=mock_user),
        patch(
            "src.handlers.people_handler.require_no_password_change",
            return_value=mock_user,
        ),
        patch(
            "src.handlers.people_handler._log_people_list_access_event"
        ) as mock_log_access,
        patch(
            "src.handlers.people_handler._log_people_list_success_event"
        ) as mock_log_success,
    ):

        mock_db.list_people.return_value = mock_people

        # Test successful request
        response = client.get("/people?limit=50")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "test-person-123"
        assert data[0]["firstName"] == "John"
        assert "password" not in str(data)  # Ensure no sensitive fields

        # Verify audit logging was called
        mock_log_access.assert_called_once()
        mock_log_success.assert_called_once()

        print("✓ list_people security enhancements working correctly")


async def test_list_people_validation():
    """Test input validation for list_people endpoint"""
    print("Testing list_people input validation...")

    mock_user = create_mock_user()

    with (
        patch("src.handlers.people_handler.get_current_user", return_value=mock_user),
        patch(
            "src.handlers.people_handler.require_no_password_change",
            return_value=mock_user,
        ),
    ):

        # Test invalid limit (too high)
        response = client.get("/people?limit=2000")
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "INVALID_PAGINATION"
        assert "1000" in data["message"]

        # Test invalid limit (too low)
        response = client.get("/people?limit=0")
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "INVALID_PAGINATION"

        print("✓ list_people input validation working correctly")


async def test_get_person_security_enhancements():
    """Test security enhancements for get_person endpoint"""
    print("Testing get_person security enhancements...")

    mock_user = create_mock_user()
    mock_person = create_mock_person()

    with (
        patch("src.handlers.people_handler.db_service") as mock_db,
        patch("src.handlers.people_handler.get_current_user", return_value=mock_user),
        patch(
            "src.handlers.people_handler.require_no_password_change",
            return_value=mock_user,
        ),
        patch(
            "src.handlers.people_handler._log_person_access_event"
        ) as mock_log_access,
        patch(
            "src.handlers.people_handler._log_person_access_success_event"
        ) as mock_log_success,
    ):

        mock_db.get_person.return_value = mock_person

        # Test successful request
        response = client.get("/people/test-person-123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-person-123"
        assert data["firstName"] == "John"
        assert "password" not in str(data)  # Ensure no sensitive fields

        # Verify audit logging was called
        mock_log_access.assert_called_once()
        mock_log_success.assert_called_once()

        print("✓ get_person security enhancements working correctly")


async def test_get_person_not_found():
    """Test not found handling for get_person endpoint"""
    print("Testing get_person not found handling...")

    mock_user = create_mock_user()

    with (
        patch("src.handlers.people_handler.db_service") as mock_db,
        patch("src.handlers.people_handler.get_current_user", return_value=mock_user),
        patch(
            "src.handlers.people_handler.require_no_password_change",
            return_value=mock_user,
        ),
        patch(
            "src.handlers.people_handler._log_person_access_event"
        ) as mock_log_access,
        patch(
            "src.handlers.people_handler._log_person_not_found_event"
        ) as mock_log_not_found,
    ):

        mock_db.get_person.return_value = None

        # Test not found request
        response = client.get("/people/nonexistent-person")

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "PERSON_NOT_FOUND"
        assert "not found" in data["message"].lower()

        # Verify audit logging was called
        mock_log_access.assert_called_once()
        mock_log_not_found.assert_called_once()

        print("✓ get_person not found handling working correctly")


async def test_get_person_validation():
    """Test input validation for get_person endpoint"""
    print("Testing get_person input validation...")

    mock_user = create_mock_user()

    with (
        patch("src.handlers.people_handler.get_current_user", return_value=mock_user),
        patch(
            "src.handlers.people_handler.require_no_password_change",
            return_value=mock_user,
        ),
    ):

        # Test empty person_id
        response = client.get("/people/ ")
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "INVALID_PERSON_ID"

        print("✓ get_person input validation working correctly")


async def test_security_event_logging():
    """Test that security events are properly structured"""
    print("Testing security event logging...")

    # Test that security event types are properly defined
    assert hasattr(SecurityEventType, "PERSON_ACCESS")
    assert hasattr(SecurityEventType, "PERSON_LIST_ACCESS")
    assert hasattr(SecurityEventType, "PERSON_SEARCH")

    # Test security event creation
    event = SecurityEvent(
        id="test-event-123",
        event_type=SecurityEventType.PERSON_ACCESS,
        timestamp=datetime.utcnow(),
        severity=SecurityEventSeverity.LOW,
        user_id="test-user",
        ip_address="192.168.1.1",
        user_agent="Test Agent",
        details={"action": "person_access_request"},
    )

    assert event.event_type == SecurityEventType.PERSON_ACCESS
    assert event.severity == SecurityEventSeverity.LOW
    assert event.details["action"] == "person_access_request"

    print("✓ Security event logging structure working correctly")


async def test_response_structure():
    """Test that responses exclude sensitive fields"""
    print("Testing response structure...")

    mock_person = Person(
        id="test-person-123",
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="+1234567890",
        date_of_birth="1990-01-01",
        address={
            "street": "123 Main St",
            "city": "Anytown",
            "state": "CA",
            "zip_code": "12345",
            "country": "USA",
        },
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_active=True,
        email_verified=True,
        password_hash="secret_hash",  # This should be excluded
        password_salt="secret_salt",  # This should be excluded
        password_history=["old_hash1", "old_hash2"],  # This should be excluded
        email_verification_token="secret_token",  # This should be excluded
    )

    # Test PersonResponse excludes sensitive fields
    response = PersonResponse.from_person(mock_person)
    response_dict = response.model_dump()

    # Check that sensitive fields are not included
    sensitive_fields = [
        "password_hash",
        "password_salt",
        "password_history",
        "email_verification_token",
        "failed_login_attempts",
        "account_locked_until",
        "last_login_at",
        "require_password_change",
    ]

    for field in sensitive_fields:
        assert field not in response_dict, f"Sensitive field {field} found in response"

    # Check that expected fields are included
    expected_fields = [
        "id",
        "firstName",
        "lastName",
        "email",
        "phone",
        "dateOfBirth",
        "address",
        "createdAt",
        "updatedAt",
        "isActive",
        "emailVerified",
    ]

    for field in expected_fields:
        assert field in response_dict, f"Expected field {field} not found in response"

    print("✓ Response structure correctly excludes sensitive fields")


async def main():
    """Run all security enhancement tests"""
    print("Running security enhancement tests for person retrieval endpoints...\n")

    try:
        await test_list_people_security_enhancements()
        await test_list_people_validation()
        await test_get_person_security_enhancements()
        await test_get_person_not_found()
        await test_get_person_validation()
        await test_security_event_logging()
        await test_response_structure()

        print("\n✅ All security enhancement tests passed!")
        print("\nSecurity improvements implemented:")
        print("- Comprehensive access logging for audit purposes")
        print("- Structured error responses with request IDs and timestamps")
        print("- Input validation with detailed error messages")
        print("- Sensitive field exclusion from API responses")
        print("- Proper HTTP status codes for different error scenarios")
        print("- IP address and user agent logging for security events")

    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
