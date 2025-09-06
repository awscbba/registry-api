"""Tests for Subscriptions Repository - Subscription data operations"""

import pytest
from unittest.mock import Mock
from src.repositories.subscriptions_repository import SubscriptionsRepository
from src.models.subscription import SubscriptionCreate, Subscription


class TestSubscriptionsRepository:
    """Test Subscriptions Repository functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.subscriptions_repository = SubscriptionsRepository()
        self.subscriptions_repository.db = Mock()

    def test_create_subscription_success(self):
        """Test successful subscription creation"""
        # Arrange
        subscription_data = SubscriptionCreate(
            personId="person123", projectId="project456"
        )

        mock_response = {
            "id": "sub123",
            "personId": "person123",
            "projectId": "project456",
            "status": "active",
        }

        self.subscriptions_repository.db.put_item.return_value = mock_response

        # Act
        result = self.subscriptions_repository.create(subscription_data)

        # Assert
        assert isinstance(result, Subscription)
        assert result.id == "sub123"
        assert result.personId == "person123"
        self.subscriptions_repository.db.put_item.assert_called_once()

    def test_get_by_id_success(self):
        """Test getting subscription by ID"""
        # Arrange
        subscription_id = "sub123"
        mock_response = {
            "id": "sub123",
            "personId": "person123",
            "projectId": "project456",
            "status": "active",
        }

        self.subscriptions_repository.db.get_item.return_value = mock_response

        # Act
        result = self.subscriptions_repository.get_by_id(subscription_id)

        # Assert
        assert isinstance(result, Subscription)
        assert result.id == "sub123"

    def test_get_by_person_and_project_success(self):
        """Test getting subscription by person and project"""
        # Arrange
        person_id = "person123"
        project_id = "project456"
        mock_response = {
            "id": "sub123",
            "personId": person_id,
            "projectId": project_id,
            "status": "active",
        }

        self.subscriptions_repository.db.query_by_person_and_project.return_value = (
            mock_response
        )

        # Act
        result = self.subscriptions_repository.get_by_person_and_project(
            person_id, project_id
        )

        # Assert
        assert isinstance(result, Subscription)
        assert result.personId == person_id
        assert result.projectId == project_id

    def test_get_by_person_and_project_not_found(self):
        """Test getting subscription when not found"""
        # Arrange
        person_id = "person123"
        project_id = "project456"
        self.subscriptions_repository.db.query_by_person_and_project.return_value = None

        # Act
        result = self.subscriptions_repository.get_by_person_and_project(
            person_id, project_id
        )

        # Assert
        assert result is None

    def test_list_all_success(self):
        """Test listing all subscriptions"""
        # Arrange
        mock_response = [
            {
                "id": "sub1",
                "personId": "person1",
                "projectId": "project1",
                "status": "active",
            },
            {
                "id": "sub2",
                "personId": "person2",
                "projectId": "project2",
                "status": "active",
            },
        ]

        self.subscriptions_repository.db.scan.return_value = mock_response

        # Act
        result = self.subscriptions_repository.list_all()

        # Assert
        assert len(result) == 2
        assert all(isinstance(sub, Subscription) for sub in result)

    def test_update_subscription_success(self):
        """Test updating subscription"""
        # Arrange
        subscription_id = "sub123"
        update_data = {"status": "inactive"}

        mock_response = {
            "id": "sub123",
            "personId": "person123",
            "projectId": "project456",
            "status": "inactive",
        }

        self.subscriptions_repository.db.update_item.return_value = mock_response

        # Act
        result = self.subscriptions_repository.update(subscription_id, update_data)

        # Assert
        assert isinstance(result, Subscription)
        assert result.status == "inactive"

    def test_delete_subscription_success(self):
        """Test deleting subscription"""
        # Arrange
        subscription_id = "sub123"
        self.subscriptions_repository.db.delete_item.return_value = True

        # Act
        result = self.subscriptions_repository.delete(subscription_id)

        # Assert
        assert result is True
        self.subscriptions_repository.db.delete_item.assert_called_once_with(
            subscription_id
        )

    def test_subscriptions_repository_initialization(self):
        """Test subscriptions repository initializes correctly"""
        # Act
        repository = SubscriptionsRepository()

        # Assert
        assert hasattr(repository, "db")
