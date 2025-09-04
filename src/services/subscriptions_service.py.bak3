"""
Subscriptions service implementation.
Handles business logic for subscription operations.
"""

from typing import List, Optional
from ..repositories.subscriptions_repository import SubscriptionsRepository
from ..models.subscription import (
    Subscription,
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
)


class SubscriptionsService:
    """Service for subscription business logic."""

    def __init__(self):
        self.subscriptions_repository = SubscriptionsRepository()

    async def create_subscription(
        self, subscription_data: SubscriptionCreate
    ) -> SubscriptionResponse:
        """Create a new subscription."""
        # Check if subscription already exists
        existing = await self.subscriptions_repository.subscription_exists(
            subscription_data.personId, subscription_data.projectId
        )
        if existing:
            raise ValueError("Subscription already exists for this person and project")

        # Create subscription
        subscription = await self.subscriptions_repository.create(subscription_data)

        # Convert to response format
        return SubscriptionResponse(**subscription.model_dump())

    async def get_subscription(
        self, subscription_id: str
    ) -> Optional[SubscriptionResponse]:
        """Get a subscription by ID."""
        subscription = await self.subscriptions_repository.get_by_id(subscription_id)
        if not subscription:
            return None

        return SubscriptionResponse(**subscription.model_dump())

    async def list_subscriptions(
        self, limit: Optional[int] = None
    ) -> List[SubscriptionResponse]:
        """List all subscriptions."""
        subscriptions = await self.subscriptions_repository.list_all(limit=limit)
        return [SubscriptionResponse(**sub.model_dump()) for sub in subscriptions]

    async def get_person_subscriptions(
        self, person_id: str
    ) -> List[SubscriptionResponse]:
        """Get all subscriptions for a person."""
        subscriptions = await self.subscriptions_repository.get_by_person(person_id)
        return [SubscriptionResponse(**sub.model_dump()) for sub in subscriptions]

    async def get_project_subscriptions(
        self, project_id: str
    ) -> List[SubscriptionResponse]:
        """Get all subscriptions for a project."""
        subscriptions = await self.subscriptions_repository.get_by_project(project_id)
        return [SubscriptionResponse(**sub.model_dump()) for sub in subscriptions]

    async def update_subscription(
        self, subscription_id: str, updates: SubscriptionUpdate
    ) -> Optional[SubscriptionResponse]:
        """Update a subscription."""
        subscription = await self.subscriptions_repository.update(
            subscription_id, updates
        )
        if not subscription:
            return None

        return SubscriptionResponse(**subscription.model_dump())

    async def delete_subscription(self, subscription_id: str) -> bool:
        """Delete a subscription."""
        return await self.subscriptions_repository.delete(subscription_id)

    async def check_subscription_exists(self, person_id: str, project_id: str) -> bool:
        """Check if a subscription exists for a person and project."""
        return await self.subscriptions_repository.subscription_exists(
            person_id, project_id
        )
