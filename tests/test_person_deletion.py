"""
Test cases for person deletion functionality
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import uuid

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.services.person_deletion_service import PersonDeletionService
from src.models.person import PersonDeletionResponse, ReferentialIntegrityError
from src.models.security_event import SecurityEventType, SecurityEventSeverity


class TestPersonDeletionService:
    """Test cases for PersonDeletionService"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_db_service = Mock()
        self.deletion_service = PersonDeletionService(self.mock_db_service)

        # Mock person data
        self.mock_person = Mock()
        self.mock_person.id = "test-person-123"
        self.mock_person.email = "test@example.com"
        self.mock_person.first_name = "Test"
        self.mock_person.last_name = "User"

        self.test_person_id = "test-person-123"
        self.test_user_id = "test-user-456"

    @pytest.mark.asyncio
    async def test_initiate_deletion_person_not_found(self):
        """Test deletion initiation when person doesn't exist"""
        # Mock person not found
        self.mock_db_service.get_person = AsyncMock(return_value=None)

        success, response, error = await self.deletion_service.initiate_deletion(
            person_id=self.test_person_id,
            requesting_user_id=self.test_user_id,
            reason="Test deletion",
        )

        assert not success
        assert response.success is False
        assert "Person not found" in response.message
        assert error == "Person not found"

    @pytest.mark.asyncio
    async def test_initiate_deletion_with_active_subscriptions(self):
        """Test deletion initiation when person has active subscriptions"""
        # Mock person exists
        self.mock_db_service.get_person = AsyncMock(return_value=self.mock_person)

        # Mock active subscriptions
        mock_subscriptions = [
            {
                "id": "sub-1",
                "projectId": "proj-1",
                "status": "active",
                "createdAt": "2024-01-01T00:00:00Z",
            },
            {
                "id": "sub-2",
                "projectId": "proj-2",
                "status": "pending",
                "createdAt": "2024-01-02T00:00:00Z",
            },
        ]
        self.mock_db_service.get_subscriptions_by_person = Mock(
            return_value=mock_subscriptions
        )

        # Mock projects
        self.mock_db_service.get_project_by_id = Mock(
            return_value={"name": "Test Project"}
        )

        # Mock audit logging
        self.mock_db_service.log_security_event = AsyncMock()

        success, response, error = await self.deletion_service.initiate_deletion(
            person_id=self.test_person_id,
            requesting_user_id=self.test_user_id,
            reason="Test deletion",
        )

        assert not success
        assert response.success is False
        assert "active subscription" in response.message
        assert response.subscriptions_found == 2
        assert error is not None

        # Verify audit logging was called
        self.mock_db_service.log_security_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_initiate_deletion_success(self):
        """Test successful deletion initiation"""
        # Mock person exists
        self.mock_db_service.get_person = AsyncMock(return_value=self.mock_person)

        # Mock no active subscriptions
        mock_subscriptions = [
            {
                "id": "sub-1",
                "projectId": "proj-1",
                "status": "cancelled",
                "createdAt": "2024-01-01T00:00:00Z",
            }
        ]
        self.mock_db_service.get_subscriptions_by_person = Mock(
            return_value=mock_subscriptions
        )

        # Mock audit logging
        self.mock_db_service.log_security_event = AsyncMock()

        success, response, error = await self.deletion_service.initiate_deletion(
            person_id=self.test_person_id,
            requesting_user_id=self.test_user_id,
            reason="Test deletion",
        )

        assert success
        assert response.success is True
        assert response.confirmation_token is not None
        assert response.expires_at is not None
        assert response.subscriptions_found == 0
        assert error is None

        # Verify audit logging was called
        self.mock_db_service.log_security_event.assert_called_once()

        # Verify token was stored
        assert len(self.deletion_service._pending_deletions) == 1

    @pytest.mark.asyncio
    async def test_confirm_deletion_invalid_token(self):
        """Test deletion confirmation with invalid token"""
        success, response, error = await self.deletion_service.confirm_deletion(
            confirmation_token="invalid-token", requesting_user_id=self.test_user_id
        )

        assert not success
        assert response.success is False
        assert "Invalid or expired" in response.message
        assert "Invalid confirmation token" in error

    @pytest.mark.asyncio
    async def test_confirm_deletion_expired_token(self):
        """Test deletion confirmation with expired token"""
        # Create an expired token
        token = str(uuid.uuid4())
        expired_time = datetime.utcnow() - timedelta(minutes=1)

        self.deletion_service._pending_deletions[token] = {
            "person_id": self.test_person_id,
            "requesting_user_id": self.test_user_id,
            "reason": "Test",
            "expires_at": expired_time,
            "created_at": datetime.utcnow(),
        }

        success, response, error = await self.deletion_service.confirm_deletion(
            confirmation_token=token, requesting_user_id=self.test_user_id
        )

        assert not success
        assert response.success is False
        assert "expired" in response.message
        assert "Token expired" in error

        # Verify token was cleaned up
        assert token not in self.deletion_service._pending_deletions

    @pytest.mark.asyncio
    async def test_confirm_deletion_user_mismatch(self):
        """Test deletion confirmation with different user"""
        # Create a valid token
        token = str(uuid.uuid4())
        future_time = datetime.utcnow() + timedelta(minutes=10)

        self.deletion_service._pending_deletions[token] = {
            "person_id": self.test_person_id,
            "requesting_user_id": "different-user",
            "reason": "Test",
            "expires_at": future_time,
            "created_at": datetime.utcnow(),
        }

        success, response, error = await self.deletion_service.confirm_deletion(
            confirmation_token=token, requesting_user_id=self.test_user_id
        )

        assert not success
        assert response.success is False
        assert "Only the user who initiated" in response.message
        assert "User mismatch" in error

    @pytest.mark.asyncio
    async def test_confirm_deletion_success(self):
        """Test successful deletion confirmation"""
        # Create a valid token
        token = str(uuid.uuid4())
        future_time = datetime.utcnow() + timedelta(minutes=10)

        self.deletion_service._pending_deletions[token] = {
            "person_id": self.test_person_id,
            "requesting_user_id": self.test_user_id,
            "reason": "Test",
            "expires_at": future_time,
            "created_at": datetime.utcnow(),
        }

        # Mock person exists
        self.mock_db_service.get_person = AsyncMock(return_value=self.mock_person)

        # Mock no active subscriptions
        self.mock_db_service.get_subscriptions_by_person = Mock(return_value=[])

        # Mock successful deletion
        self.mock_db_service.delete_person = AsyncMock(return_value=True)

        # Mock audit logging
        self.mock_db_service.log_security_event = AsyncMock()

        success, response, error = await self.deletion_service.confirm_deletion(
            confirmation_token=token, requesting_user_id=self.test_user_id
        )

        assert success
        assert response.success is True
        assert "successfully deleted" in response.message
        assert error is None

        # Verify deletion was called
        self.mock_db_service.delete_person.assert_called_once_with(self.test_person_id)

        # Verify audit logging was called
        self.mock_db_service.log_security_event.assert_called_once()

        # Verify token was cleaned up
        assert token not in self.deletion_service._pending_deletions

    def test_cleanup_expired_tokens(self):
        """Test cleanup of expired tokens"""
        # Add some tokens - one expired, one valid
        expired_token = str(uuid.uuid4())
        valid_token = str(uuid.uuid4())

        expired_time = datetime.utcnow() - timedelta(minutes=1)
        future_time = datetime.utcnow() + timedelta(minutes=10)

        self.deletion_service._pending_deletions[expired_token] = {
            "person_id": "person-1",
            "requesting_user_id": "user-1",
            "expires_at": expired_time,
            "created_at": datetime.utcnow(),
        }

        self.deletion_service._pending_deletions[valid_token] = {
            "person_id": "person-2",
            "requesting_user_id": "user-2",
            "expires_at": future_time,
            "created_at": datetime.utcnow(),
        }

        # Run cleanup
        cleaned_count = self.deletion_service.cleanup_expired_tokens()

        assert cleaned_count == 1
        assert expired_token not in self.deletion_service._pending_deletions
        assert valid_token in self.deletion_service._pending_deletions

    def test_get_pending_deletions_count(self):
        """Test getting count of pending deletions"""
        assert self.deletion_service.get_pending_deletions_count() == 0

        # Add a pending deletion
        token = str(uuid.uuid4())
        self.deletion_service._pending_deletions[token] = {
            "person_id": "person-1",
            "requesting_user_id": "user-1",
            "expires_at": datetime.utcnow() + timedelta(minutes=10),
            "created_at": datetime.utcnow(),
        }

        assert self.deletion_service.get_pending_deletions_count() == 1


if __name__ == "__main__":
    pytest.main([__file__])
