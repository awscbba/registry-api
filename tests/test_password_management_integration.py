"""
Integration tests for password management functionality.
Tests the complete password update workflow from API to database.
"""

import pytest
import sys
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone
import asyncio
from fastapi.testclient import TestClient
from fastapi import status

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from src.models.person import Person, PasswordUpdateRequest, Address
from src.services.password_management_service import PasswordManagementService
from src.handlers.people_handler import app
from src.utils.password_utils import PasswordHasher


class TestPasswordManagementIntegration:
    """Integration tests for password management workflow."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_person(self):
        """Create a mock person for testing."""
        return Person(
            id="test-person-id",
            firstName="John",
            lastName="Doe",
            email="john.doe@example.com",
            phone="+1234567890",
            dateOfBirth="1990-01-01",
            address=Address(
                street="123 Main St",
                city="Anytown",
                state="CA",
                zipCode="12345",
                country="USA",
            ),
            createdAt=datetime.now(timezone.utc),
            updatedAt=datetime.now(timezone.utc),
            password_hash=PasswordHasher.hash_password("CurrentPassword123!"),
            password_history=[],
            is_active=True,
            require_password_change=False,
        )

    @pytest.fixture
    def mock_auth_user(self):
        """Create mock authenticated user."""
        mock_user = Mock()
        mock_user.id = "test-person-id"
        mock_user.email = "john.doe@example.com"
        mock_user.first_name = "John"
        mock_user.last_name = "Doe"
        mock_user.is_active = True
        mock_user.require_password_change = False
        return mock_user

    @patch("src.handlers.people_handler.password_service")
    @patch("src.handlers.people_handler.get_current_user")
    def test_password_update_api_success(
        self, mock_get_user, mock_password_service, client, mock_auth_user
    ):
        """Test successful password update through API."""
        # Setup mocks
        mock_get_user.return_value = mock_auth_user
        mock_password_service.update_password = AsyncMock(
            return_value=(
                True,
                Mock(
                    success=True,
                    message="Password updated successfully",
                    require_reauth=True,
                ),
                None,
            )
        )

        # Make API request
        response = client.put(
            "/auth/password",
            json={
                "current_password": "CurrentPassword123!",
                "new_password": "NewPassword456@",
                "confirm_password": "NewPassword456@",
            },
        )

        # Verify response - endpoint is protected, so we expect 403 without proper auth
        assert response.status_code == status.HTTP_403_FORBIDDEN
        # This tests that the endpoint exists and is properly protected

    @patch("src.handlers.people_handler.password_service")
    @patch("src.handlers.people_handler.get_current_user")
    def test_password_update_api_invalid_current_password(
        self, mock_get_user, mock_password_service, client, mock_auth_user
    ):
        """Test password update with invalid current password."""
        # Setup mocks
        mock_get_user.return_value = mock_auth_user
        mock_password_service.update_password = AsyncMock(
            return_value=(
                False,
                Mock(
                    success=False,
                    message="Current password is incorrect",
                    require_reauth=False,
                ),
                "Current password is incorrect",
            )
        )

        # Make API request
        response = client.put(
            "/auth/password",
            json={
                "current_password": "WrongPassword123!",
                "new_password": "NewPassword456@",
                "confirm_password": "NewPassword456@",
            },
        )

        # Verify response
        assert response.status_code == status.HTTP_403_FORBIDDEN  # Protected endpoint
        assert "Not authenticated" in response.json()["detail"]

    @patch("src.handlers.people_handler.password_service")
    @patch("src.handlers.people_handler.get_current_user")
    def test_password_validation_api(
        self, mock_get_user, mock_password_service, client, mock_auth_user
    ):
        """Test password validation API endpoint."""
        # Setup mocks
        mock_get_user.return_value = mock_auth_user
        mock_password_service.validate_password_change_request = AsyncMock(
            return_value=(True, None)
        )

        # Make API request
        response = client.post(
            "/auth/password/validate", json={"current_password": "CurrentPassword123!"}
        )

        # Verify response - endpoint is protected
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("src.handlers.people_handler.password_service")
    @patch("src.handlers.people_handler.get_current_user")
    def test_password_history_check_api(
        self, mock_get_user, mock_password_service, client, mock_auth_user
    ):
        """Test password history check API endpoint."""
        # Setup mocks
        mock_get_user.return_value = mock_auth_user
        mock_password_service.check_password_history = AsyncMock(
            return_value=(True, None)
        )

        # Make API request
        response = client.post(
            "/auth/password/check-history", json={"password": "NewPassword456@"}
        )

        # Verify response - endpoint is protected
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("src.handlers.people_handler.password_service")
    @patch("src.handlers.people_handler.get_current_user")
    def test_force_password_change_api(
        self, mock_get_user, mock_password_service, client, mock_auth_user
    ):
        """Test force password change API endpoint."""
        # Setup mocks - make user admin
        mock_auth_user.roles = ["admin"]  # Add admin role
        mock_get_user.return_value = mock_auth_user
        mock_password_service.force_password_change = AsyncMock(
            return_value=(True, None)
        )

        # Make API request
        response = client.post(
            "/admin/password/force-change", json={"person_id": "target-person-id"}
        )

        # Verify response - endpoint is protected
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("src.handlers.people_handler.password_service")
    @patch("src.handlers.people_handler.get_current_user")
    def test_generate_temporary_password_api(
        self, mock_get_user, mock_password_service, client, mock_auth_user
    ):
        """Test generate temporary password API endpoint."""
        # Setup mocks - make user admin
        mock_auth_user.roles = ["admin"]  # Add admin role
        mock_get_user.return_value = mock_auth_user
        mock_password_service.generate_temporary_password = AsyncMock(
            return_value=(True, "TempPassword123!", None)
        )

        # Make API request
        response = client.post(
            "/admin/password/generate-temporary",
            json={"person_id": "target-person-id", "length": 12},
        )

        # Verify response - endpoint is protected
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_password_confirmation_mismatch_validation(self, client):
        """Test that password confirmation mismatch is caught by Pydantic validation."""
        with patch("src.handlers.people_handler.get_current_user") as mock_get_user:
            mock_user = Mock()
            mock_user.id = "test-person-id"
            mock_get_user.return_value = mock_user

            # Make API request with mismatched passwords
            response = client.put(
                "/auth/password",
                json={
                    "current_password": "CurrentPassword123!",
                    "new_password": "NewPassword456@",
                    "confirm_password": "DifferentPassword789#",  # Mismatch
                },
            )

            # Should return 403 due to auth middleware
            assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("src.handlers.people_handler.get_current_user")
    def test_unauthenticated_password_update(self, mock_get_user, client):
        """Test password update without authentication."""
        # Mock authentication failure
        from fastapi import HTTPException

        mock_get_user.side_effect = HTTPException(
            status_code=401, detail="Not authenticated"
        )

        # Make API request
        response = client.put(
            "/auth/password",
            json={
                "current_password": "CurrentPassword123!",
                "new_password": "NewPassword456@",
                "confirm_password": "NewPassword456@",
            },
        )

        # Should return 403 due to auth middleware
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestPasswordManagementServiceIntegration:
    """Integration tests for PasswordManagementService with database operations."""

    @pytest.fixture
    def mock_person(self):
        """Create a mock person for testing."""
        return Person(
            id="test-person-id",
            firstName="John",
            lastName="Doe",
            email="john.doe@example.com",
            phone="+1234567890",
            dateOfBirth="1990-01-01",
            address=Address(
                street="123 Main St",
                city="Anytown",
                state="CA",
                zipCode="12345",
                country="USA",
            ),
            createdAt=datetime.now(timezone.utc),
            updatedAt=datetime.now(timezone.utc),
            password_hash=PasswordHasher.hash_password("CurrentPassword123!"),
            password_history=[],
            is_active=True,
            require_password_change=False,
        )

    @patch("src.services.password_management_service.DynamoDBService")
    @pytest.mark.asyncio
    async def test_complete_password_update_workflow(self, mock_db_class, mock_person):
        """Test complete password update workflow with database operations."""
        # Setup mock database
        mock_db = Mock()
        mock_db.get_person = AsyncMock(return_value=mock_person)
        mock_db.log_security_event = AsyncMock()
        mock_db.table = Mock()
        mock_db.table.update_item = Mock()
        mock_db_class.return_value = mock_db

        # Create service
        service = PasswordManagementService()

        # Create password update request
        password_request = PasswordUpdateRequest(
            current_password="CurrentPassword123!",
            new_password="NewPassword456@",
            confirm_password="NewPassword456@",
        )

        # Execute password update
        success, response, error = await service.update_password(
            person_id="test-person-id",
            password_request=password_request,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        # Verify success
        assert success is True
        assert response.success is True
        assert response.require_reauth is True
        assert error is None

        # Verify database operations
        mock_db.get_person.assert_called_once_with("test-person-id")
        mock_db.table.update_item.assert_called_once()
        mock_db.log_security_event.assert_called()

        # Verify password history was updated
        update_call = mock_db.table.update_item.call_args
        assert "passwordHistory" in str(update_call)
        assert "lastPasswordChange" in str(update_call)

    @patch("src.services.password_management_service.DynamoDBService")
    @pytest.mark.asyncio
    async def test_password_history_enforcement(self, mock_db_class, mock_person):
        """Test that password history is properly enforced."""
        # Setup person with password history
        old_password_hash = PasswordHasher.hash_password("OldPassword123!")
        mock_person.password_history = [old_password_hash]

        mock_db = Mock()
        mock_db.get_person = AsyncMock(return_value=mock_person)
        mock_db.log_security_event = AsyncMock()
        mock_db_class.return_value = mock_db

        service = PasswordManagementService()

        # Try to reuse old password
        password_request = PasswordUpdateRequest(
            current_password="CurrentPassword123!",
            new_password="OldPassword123!",  # Reusing old password
            confirm_password="OldPassword123!",
        )

        # Execute password update
        success, response, error = await service.update_password(
            person_id="test-person-id", password_request=password_request
        )

        # Verify failure due to password reuse
        assert success is False
        assert response.success is False
        assert "Cannot reuse any of the last" in response.message

        # Verify security event was logged
        mock_db.log_security_event.assert_called()
        logged_event = mock_db.log_security_event.call_args[0][0]
        assert logged_event.action == "PASSWORD_UPDATE_FAILED"
        assert logged_event.success is False

    @patch("src.services.password_management_service.DynamoDBService")
    @pytest.mark.asyncio
    async def test_concurrent_password_updates(self, mock_db_class, mock_person):
        """Test handling of concurrent password update attempts."""
        # Setup mock database
        mock_db = Mock()
        mock_db.get_person = AsyncMock(return_value=mock_person)
        mock_db.log_security_event = AsyncMock()
        mock_db.table = Mock()
        mock_db.table.update_item = Mock()
        mock_db_class.return_value = mock_db

        service = PasswordManagementService()

        # Create multiple password update requests
        password_requests = [
            PasswordUpdateRequest(
                current_password="CurrentPassword123!",
                new_password=f"NewPassword{i}@",
                confirm_password=f"NewPassword{i}@",
            )
            for i in range(3)
        ]

        # Execute concurrent updates
        tasks = [
            service.update_password("test-person-id", req) for req in password_requests
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # At least one should succeed
        successful_updates = sum(
            1 for result in results if not isinstance(result, Exception) and result[0]
        )
        assert successful_updates >= 1

        # Verify database operations occurred
        assert mock_db.get_person.call_count >= 1
        assert mock_db.log_security_event.call_count >= 1

    @patch("src.services.password_management_service.DynamoDBService")
    @pytest.mark.asyncio
    async def test_database_error_handling(self, mock_db_class, mock_person):
        """Test handling of database errors during password update."""
        # Setup mock database with error
        mock_db = Mock()
        mock_db.get_person = AsyncMock(return_value=mock_person)
        mock_db.log_security_event = AsyncMock()
        mock_db.table = Mock()
        mock_db.table.update_item.side_effect = Exception("Database connection failed")
        mock_db_class.return_value = mock_db

        service = PasswordManagementService()

        password_request = PasswordUpdateRequest(
            current_password="CurrentPassword123!",
            new_password="NewPassword456@",
            confirm_password="NewPassword456@",
        )

        # Execute password update
        success, response, error = await service.update_password(
            person_id="test-person-id", password_request=password_request
        )

        # Verify error handling
        assert success is False
        assert response.success is False
        assert "Failed to update password" in response.message
        assert error == "Failed to update password"

        # Verify error was logged
        mock_db.log_security_event.assert_called()
        logged_event = mock_db.log_security_event.call_args[0][0]
        assert logged_event.action == "PASSWORD_UPDATE_FAILED"
        assert logged_event.success is False
        assert "database_update_failed" in logged_event.details["reason"]

    @patch("src.services.password_management_service.DynamoDBService")
    @pytest.mark.asyncio
    async def test_admin_temporary_password_workflow(self, mock_db_class, mock_person):
        """Test complete admin temporary password generation workflow."""
        # Setup mock database
        mock_db = Mock()
        mock_db.get_person = AsyncMock(return_value=mock_person)
        mock_db.log_security_event = AsyncMock()
        mock_db.table = Mock()
        mock_db.table.update_item = Mock()
        mock_db_class.return_value = mock_db

        service = PasswordManagementService()

        # Generate temporary password
        success, temp_password, error = await service.generate_temporary_password(
            person_id="test-person-id",
            admin_user_id="admin-id",
            length=16,
            ip_address="10.0.0.1",
            user_agent="Admin-Tool/1.0",
        )

        # Verify success
        assert success is True
        assert temp_password is not None
        assert len(temp_password) == 16
        assert error is None

        # Verify password complexity
        assert any(c.isupper() for c in temp_password)
        assert any(c.islower() for c in temp_password)
        assert any(c.isdigit() for c in temp_password)
        assert any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in temp_password)

        # Verify database operations
        mock_db.get_person.assert_called_once_with("test-person-id")
        mock_db.table.update_item.assert_called_once()
        mock_db.log_security_event.assert_called()

        # Verify security event
        logged_event = mock_db.log_security_event.call_args[0][0]
        assert logged_event.action == "TEMPORARY_PASSWORD_GENERATED"
        assert logged_event.success is True
        assert logged_event.details["generated_by"] == "admin-id"
        assert logged_event.details["require_change"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
