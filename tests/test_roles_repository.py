"""Tests for RolesRepository functionality."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.repositories.roles_repository import RolesRepository
from src.models.rbac import UserRole, RoleType


class TestRolesRepository:
    """Test cases for RolesRepository."""

    def setup_method(self):
        """Set up test fixtures."""
        self.repository = RolesRepository()

    @patch("src.repositories.roles_repository.boto3")
    def test_get_user_roles_success(self, mock_boto3):
        """Test successful retrieval of user roles."""
        # Mock DynamoDB client
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client

        mock_response = {
            "Items": [
                {
                    "user_id": {"S": "test-user-id"},
                    "role_type": {"S": "admin"},
                    "assigned_at": {"S": "2025-10-04T23:46:00.000Z"},
                    "assigned_by": {"S": "system"},
                    "is_active": {"BOOL": True},
                    "email": {"S": "test@example.com"},
                },
                {
                    "user_id": {"S": "test-user-id"},
                    "role_type": {"S": "super_admin"},
                    "assigned_at": {"S": "2025-10-04T23:46:00.000Z"},
                    "assigned_by": {"S": "system"},
                    "is_active": {"BOOL": True},
                    "email": {"S": "test@example.com"},
                    "expires_at": {"NULL": True},
                },
            ]
        }
        mock_client.query.return_value = mock_response

        # Create repository after mocking
        repository = RolesRepository()
        roles = repository.get_user_roles("test-user-id")

        # Assertions
        assert len(roles) == 2
        assert roles[0].role_type == RoleType.ADMIN
        assert roles[1].role_type == RoleType.SUPER_ADMIN
        assert all(role.is_active for role in roles)

    @patch("src.repositories.roles_repository.boto3")
    def test_get_user_roles_with_invalid_role_type(self, mock_boto3):
        """Test handling of invalid role types."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client

        mock_response = {
            "Items": [
                {
                    "user_id": {"S": "test-user-id"},
                    "role_type": {"S": "INVALID_ROLE"},  # Invalid enum value
                    "assigned_at": {"S": "2025-10-04T23:46:00.000Z"},
                    "assigned_by": {"S": "system"},
                    "is_active": {"BOOL": True},
                },
                {
                    "user_id": {"S": "test-user-id"},
                    "role_type": {"S": "admin"},  # Valid role
                    "assigned_at": {"S": "2025-10-04T23:46:00.000Z"},
                    "assigned_by": {"S": "system"},
                    "is_active": {"BOOL": True},
                },
            ]
        }
        mock_client.query.return_value = mock_response

        # Create repository after mocking
        repository = RolesRepository()
        roles = repository.get_user_roles("test-user-id")

        # Should only return the valid role
        assert len(roles) == 1
        assert roles[0].role_type == RoleType.ADMIN

    @patch("src.repositories.roles_repository.boto3")
    def test_get_user_roles_empty_result(self, mock_boto3):
        """Test handling of empty results."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        mock_client.query.return_value = {"Items": []}

        repository = RolesRepository()
        roles = repository.get_user_roles("nonexistent-user")

        assert len(roles) == 0
        assert roles == []
