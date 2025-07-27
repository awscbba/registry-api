"""
Tests for the new PUT /people/{person_id}/password endpoint.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime

from src.handlers.people_handler import app
from src.models.person import PasswordUpdateRequest, PasswordUpdateResponse
from src.models.auth import AuthenticatedUser
from src.middleware.auth_middleware import get_current_user


class TestPersonPasswordEndpoint:
    """Test the PUT /people/{person_id}/password endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_auth_user(self):
        """Create mock authenticated user."""
        return AuthenticatedUser(
            id="test-user-123",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            require_password_change=False,
            is_active=True,
            last_login_at=None
        )

    @pytest.fixture
    def mock_person(self):
        """Create mock person object."""
        person = Mock()
        person.id = "test-user-123"
        person.email = "test@example.com"
        person.first_name = "Test"
        person.last_name = "User"
        person.is_active = True
        person.password_hash = "hashed_password"
        return person

    @pytest.fixture
    def password_request_data(self):
        """Create valid password request data."""
        return {
            "current_password": "OldPassword123!",
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!"
        }

    @patch('src.handlers.people_handler.db_service')
    @patch('src.handlers.people_handler.password_service')
    def test_update_person_password_success(self, mock_password_service, mock_db_service, client, mock_auth_user, mock_person, password_request_data):
        """Test successful password update for a person."""
        # Override the dependency
        app.dependency_overrides[get_current_user] = lambda: mock_auth_user

        # Setup mocks
        mock_db_service.get_person = AsyncMock(return_value=mock_person)

        mock_response = PasswordUpdateResponse(
            success=True,
            message="Password updated successfully",
            require_reauth=True
        )
        mock_password_service.update_password = AsyncMock(return_value=(True, mock_response, None))

        try:
            # Make request
            response = client.put(
                f"/people/{mock_auth_user.id}/password",
                json=password_request_data,
                headers={"Authorization": "Bearer test-token"}
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["message"] == "Password updated successfully"
            assert data["requireReauth"] is True
            assert "timestamp" in data

            # Verify service was called correctly
            mock_password_service.update_password.assert_called_once()
            call_args = mock_password_service.update_password.call_args
            assert call_args[1]["person_id"] == mock_auth_user.id
            assert isinstance(call_args[1]["password_request"], PasswordUpdateRequest)
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    def test_update_person_password_unauthorized_different_user(self, client, mock_auth_user, password_request_data):
        """Test that users cannot update other users' passwords."""
        # Override the dependency
        app.dependency_overrides[get_current_user] = lambda: mock_auth_user

        try:
            # Try to update different user's password
            different_user_id = "different-user-456"
            response = client.put(
                f"/people/{different_user_id}/password",
                json=password_request_data,
                headers={"Authorization": "Bearer test-token"}
            )

            # Verify forbidden response
            assert response.status_code == 403
            data = response.json()
            assert "You can only update your own password" in data["detail"]
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    @patch('src.handlers.people_handler.db_service')
    def test_update_person_password_person_not_found(self, mock_db_service, client, mock_auth_user, password_request_data):
        """Test password update when person doesn't exist."""
        # Override the dependency
        app.dependency_overrides[get_current_user] = lambda: mock_auth_user

        # Setup mocks
        mock_db_service.get_person = AsyncMock(return_value=None)

        try:
            # Make request
            response = client.put(
                f"/people/{mock_auth_user.id}/password",
                json=password_request_data,
                headers={"Authorization": "Bearer test-token"}
            )

            # Verify not found response
            assert response.status_code == 404
            data = response.json()
            assert "Person not found" in data["detail"]
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    @patch('src.handlers.people_handler.db_service')
    def test_update_person_password_inactive_account(self, mock_db_service, client, mock_auth_user, mock_person, password_request_data):
        """Test password update for inactive account."""
        # Override the dependency
        app.dependency_overrides[get_current_user] = lambda: mock_auth_user

        # Setup mocks
        mock_person.is_active = False
        mock_db_service.get_person = AsyncMock(return_value=mock_person)

        try:
            # Make request
            response = client.put(
                f"/people/{mock_auth_user.id}/password",
                json=password_request_data,
                headers={"Authorization": "Bearer test-token"}
            )

            # Verify forbidden response
            assert response.status_code == 403
            data = response.json()
            assert "Cannot update password for inactive account" in data["detail"]
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    @patch('src.handlers.people_handler.db_service')
    @patch('src.handlers.people_handler.password_service')
    def test_update_person_password_invalid_current_password(self, mock_password_service, mock_db_service, client, mock_auth_user, mock_person, password_request_data):
        """Test password update with invalid current password."""
        # Override the dependency
        app.dependency_overrides[get_current_user] = lambda: mock_auth_user

        # Setup mocks
        mock_db_service.get_person = AsyncMock(return_value=mock_person)

        mock_response = PasswordUpdateResponse(
            success=False,
            message="Current password is incorrect"
        )
        mock_password_service.update_password = AsyncMock(return_value=(False, mock_response, "Current password is incorrect"))

        try:
            # Make request
            response = client.put(
                f"/people/{mock_auth_user.id}/password",
                json=password_request_data,
                headers={"Authorization": "Bearer test-token"}
            )

            # Verify bad request response
            assert response.status_code == 400
            data = response.json()
            assert data["detail"]["error"] == "INVALID_CURRENT_PASSWORD"
            assert data["detail"]["message"] == "Current password is incorrect"
            assert "timestamp" in data["detail"]
            assert "request_id" in data["detail"]
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    @patch('src.handlers.people_handler.db_service')
    @patch('src.handlers.people_handler.password_service')
    def test_update_person_password_policy_violation(self, mock_password_service, mock_db_service, client, mock_auth_user, mock_person, password_request_data):
        """Test password update with policy violation."""
        # Override the dependency
        app.dependency_overrides[get_current_user] = lambda: mock_auth_user

        # Setup mocks
        mock_db_service.get_person = AsyncMock(return_value=mock_person)

        mock_response = PasswordUpdateResponse(
            success=False,
            message="Password does not meet policy requirements"
        )
        mock_password_service.update_password = AsyncMock(return_value=(False, mock_response, "Password does not meet policy requirements"))

        try:
            # Make request
            response = client.put(
                f"/people/{mock_auth_user.id}/password",
                json=password_request_data,
                headers={"Authorization": "Bearer test-token"}
            )

            # Verify bad request response
            assert response.status_code == 400
            data = response.json()
            assert data["detail"]["error"] == "PASSWORD_POLICY_VIOLATION"
            assert data["detail"]["message"] == "Password does not meet policy requirements"
            assert "timestamp" in data["detail"]
            assert "request_id" in data["detail"]
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    @patch('src.handlers.people_handler.db_service')
    @patch('src.handlers.people_handler.password_service')
    def test_update_person_password_service_error(self, mock_password_service, mock_db_service, client, mock_auth_user, mock_person, password_request_data):
        """Test password update with service error."""
        # Override the dependency
        app.dependency_overrides[get_current_user] = lambda: mock_auth_user

        # Setup mocks
        mock_db_service.get_person = AsyncMock(return_value=mock_person)
        mock_password_service.update_password = AsyncMock(side_effect=Exception("Database error"))

        try:
            # Make request
            response = client.put(
                f"/people/{mock_auth_user.id}/password",
                json=password_request_data,
                headers={"Authorization": "Bearer test-token"}
            )

            # Verify internal server error response
            assert response.status_code == 500
            data = response.json()
            assert data["detail"]["error"] == "INTERNAL_SERVER_ERROR"
            assert data["detail"]["message"] == "An unexpected error occurred while updating the password"
            assert "timestamp" in data["detail"]
            assert "request_id" in data["detail"]
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    def test_update_person_password_invalid_request_data(self, client, mock_auth_user):
        """Test password update with invalid request data."""
        # Override the dependency
        app.dependency_overrides[get_current_user] = lambda: mock_auth_user

        invalid_data = {
            "current_password": "",  # Empty current password
            "new_password": "short",  # Too short
            "confirm_password": "different"  # Doesn't match
        }

        try:
            response = client.put(
                "/people/test-user-123/password",
                json=invalid_data,
                headers={"Authorization": "Bearer test-token"}
            )

            # Should get validation error from Pydantic
            assert response.status_code == 422
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    def test_update_person_password_missing_auth(self, client, password_request_data):
        """Test password update without authentication."""
        response = client.put(
            "/people/test-user-123/password",
            json=password_request_data
        )

        # Should get unauthorized
        assert response.status_code == 403  # FastAPI returns 403 for missing auth
