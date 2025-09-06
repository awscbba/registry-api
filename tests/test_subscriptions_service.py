"""Tests for Subscriptions Service - Current issue area"""

import pytest
from unittest.mock import Mock
from src.services.subscriptions_service import SubscriptionsService
from src.models.subscription import SubscriptionCreate, SubscriptionResponse


class TestSubscriptionsService:
    """Test Subscriptions Service functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.subscriptions_service = SubscriptionsService()
        self.subscriptions_service.subscriptions_repository = Mock()

    def test_create_subscription_success(self):
        """Test successful subscription creation"""
        # Arrange
        subscription_data = SubscriptionCreate(
            personId="person123", projectId="project456"
        )

        mock_subscription = Mock()
        mock_subscription.model_dump.return_value = {
            "id": "sub123",
            "personId": "person123",
            "projectId": "project456",
            "status": "active",
        }

        self.subscriptions_service.subscriptions_repository.get_by_person_and_project.return_value = (
            None
        )
        self.subscriptions_service.subscriptions_repository.create.return_value = (
            mock_subscription
        )

        # Act
        result = self.subscriptions_service.create_subscription(subscription_data)

        # Assert
        assert isinstance(result, SubscriptionResponse)
        self.subscriptions_service.subscriptions_repository.create.assert_called_once()

    def test_create_subscription_already_exists(self):
        """Test subscription creation when already exists"""
        # Arrange
        subscription_data = SubscriptionCreate(
            personId="person123", projectId="project456"
        )

        existing_subscription = Mock()
        self.subscriptions_service.subscriptions_repository.get_by_person_and_project.return_value = (
            existing_subscription
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Subscription already exists"):
            self.subscriptions_service.create_subscription(subscription_data)

    def test_list_subscriptions_success(self):
        """Test listing subscriptions successfully"""
        # Arrange
        mock_subscriptions = [Mock(), Mock()]
        self.subscriptions_service.subscriptions_repository.list_all.return_value = (
            mock_subscriptions
        )

        # Act
        result = self.subscriptions_service.list_subscriptions()

        # Assert
        assert result == mock_subscriptions
        self.subscriptions_service.subscriptions_repository.list_all.assert_called_once()

    def test_get_subscription_by_id_success(self):
        """Test getting subscription by ID"""
        # Arrange
        subscription_id = "sub123"
        mock_subscription = Mock()
        self.subscriptions_service.subscriptions_repository.get_by_id.return_value = (
            mock_subscription
        )

        # Act
        result = self.subscriptions_service.get_subscription_by_id(subscription_id)

        # Assert
        assert result == mock_subscription
        self.subscriptions_service.subscriptions_repository.get_by_id.assert_called_once_with(
            subscription_id
        )

    def test_subscriptions_service_initialization(self):
        """Test subscriptions service initializes correctly"""
        # Act
        service = SubscriptionsService()

        # Assert
        assert hasattr(service, "subscriptions_repository")
