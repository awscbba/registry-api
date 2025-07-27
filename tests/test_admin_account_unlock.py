"""
Test cases for admin account unlock functionality.
"""

import pytest
from datetime import datetime, timedelta, timezone
import uuid
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.handlers.people_handler import app
from src.models.person import Person, PersonUpdate, AdminUnlockRequest, Address
from src.models.auth import AuthenticatedUser
from src.services.dynamodb_service import DynamoDBService


# Mock the DynamoDB service
class MockDynamoDBService:
    def __init__(self):
        self.people = {}
        self.security_events = []

    async def get_person(self, person_id):
        return self.people.get(person_id)

    async def update_person(self, person_id, person_update):
        if person_id not in self.people:
            return None

        person = self.people[person_id]
        # Only update fields that were explicitly set
        update_dict = person_update.model_dump(exclude_unset=True)

        for key, value in update_dict.items():
            setattr(person, key, value)

        person.updated_at = datetime.now(timezone.utc)
        self.people[person_id] = person

        return person

    async def log_security_event(self, security_event):
        self.security_events.append(security_event)
        return True


# Mock the authentication middleware
async def mock_get_current_user():
    return AuthenticatedUser(
        id="admin-user-id",
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        require_password_change=False,
        is_active=True,
    )


@pytest.fixture
def test_app():
    # Store original overrides
    original_overrides = app.dependency_overrides.copy()

    # Create a test instance of the app
    app.dependency_overrides = {}

    # Override the DynamoDB service
    mock_db = MockDynamoDBService()
    app.dependency_overrides[DynamoDBService] = lambda: mock_db

    # Override the authentication middleware
    from src.middleware.auth_middleware import get_current_user

    app.dependency_overrides[get_current_user] = mock_get_current_user

    # Create a test client
    client = TestClient(app)

    # Return both the client and the mock DB for assertions
    yield client, mock_db

    # Cleanup: restore original overrides
    app.dependency_overrides = original_overrides


def test_unlock_account_success(test_app):
    """Test successful account unlock by admin."""
    client, mock_db = test_app

    # Create a locked user
    locked_user_id = str(uuid.uuid4())
    locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)

    mock_db.people[locked_user_id] = Person(
        id=locked_user_id,
        first_name="Locked",
        last_name="User",
        email="locked@example.com",
        phone="123-456-7890",
        date_of_birth="1990-01-01",
        address=Address(
            street="123 Main St",
            city="Anytown",
            state="CA",
            zipCode="12345",
            country="USA",
        ),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        failed_login_attempts=5,
        account_locked_until=locked_until,
        is_active=True,
    )

    # Make the unlock request
    response = client.post(
        f"/people/{locked_user_id}/unlock",
        json={"reason": "Customer service request to unlock account"},
    )

    # Check response
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "Account unlocked successfully" in response.json()["message"]

    # Check that the account was unlocked
    updated_user = mock_db.people[locked_user_id]
    assert updated_user.failed_login_attempts == 0
    assert updated_user.account_locked_until is None

    # Check that a security event was logged
    assert len(mock_db.security_events) == 1
    event = mock_db.security_events[0]
    assert event.event_type.value == "ADMIN_ACCOUNT_UNLOCK"
    assert event.user_id == "admin-user-id"
    assert event.details["target_user_id"] == locked_user_id
    assert "reason" in event.details


def test_unlock_account_not_found(test_app):
    """Test unlock attempt for non-existent account."""
    client, mock_db = test_app

    # Make the unlock request for a non-existent user
    response = client.post(
        f"/people/non-existent-id/unlock",
        json={"reason": "Customer service request to unlock account"},
    )

    # Check response
    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "PERSON_NOT_FOUND"

    # Check that no security event was logged
    assert len(mock_db.security_events) == 0


def test_unlock_account_already_unlocked(test_app):
    """Test unlock attempt for an account that is not locked."""
    client, mock_db = test_app

    # Create an unlocked user
    unlocked_user_id = str(uuid.uuid4())

    mock_db.people[unlocked_user_id] = Person(
        id=unlocked_user_id,
        first_name="Unlocked",
        last_name="User",
        email="unlocked@example.com",
        phone="123-456-7890",
        date_of_birth="1990-01-01",
        address=Address(
            street="123 Main St",
            city="Anytown",
            state="CA",
            zipCode="12345",
            country="USA",
        ),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        failed_login_attempts=0,
        account_locked_until=None,
        is_active=True,
    )

    # Make the unlock request
    response = client.post(
        f"/people/{unlocked_user_id}/unlock",
        json={"reason": "Customer service request to unlock account"},
    )

    # Check response
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "Account is not locked" in response.json()["message"]

    # Check that no security event was logged (since no action was needed)
    assert len(mock_db.security_events) == 0


def test_unlock_account_invalid_request(test_app):
    """Test unlock attempt with invalid request data."""
    client, mock_db = test_app

    # Create a locked user
    locked_user_id = str(uuid.uuid4())
    locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)

    mock_db.people[locked_user_id] = Person(
        id=locked_user_id,
        first_name="Locked",
        last_name="User",
        email="locked@example.com",
        phone="123-456-7890",
        date_of_birth="1990-01-01",
        address=Address(
            street="123 Main St",
            city="Anytown",
            state="CA",
            zipCode="12345",
            country="USA",
        ),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        failed_login_attempts=5,
        account_locked_until=locked_until,
        is_active=True,
    )

    # Make the unlock request with invalid data (missing reason)
    response = client.post(f"/people/{locked_user_id}/unlock", json={})

    # Check response
    assert response.status_code == 422  # Validation error

    # Check that the account is still locked
    user = mock_db.people[locked_user_id]
    assert user.failed_login_attempts == 5
    assert user.account_locked_until == locked_until

    # Check that no security event was logged
    assert len(mock_db.security_events) == 0


def test_unlock_account_short_reason(test_app):
    """Test unlock attempt with too short reason."""
    client, mock_db = test_app

    # Create a locked user
    locked_user_id = str(uuid.uuid4())
    locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)

    mock_db.people[locked_user_id] = Person(
        id=locked_user_id,
        first_name="Locked",
        last_name="User",
        email="locked@example.com",
        phone="123-456-7890",
        date_of_birth="1990-01-01",
        address=Address(
            street="123 Main St",
            city="Anytown",
            state="CA",
            zipCode="12345",
            country="USA",
        ),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        failed_login_attempts=5,
        account_locked_until=locked_until,
        is_active=True,
    )

    # Make the unlock request with too short reason
    response = client.post(f"/people/{locked_user_id}/unlock", json={"reason": "Short"})

    # Check response
    assert response.status_code == 422  # Validation error

    # Check that the account is still locked
    user = mock_db.people[locked_user_id]
    assert user.failed_login_attempts == 5
    assert user.account_locked_until == locked_until

    # Check that no security event was logged
    assert len(mock_db.security_events) == 0
