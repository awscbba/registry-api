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

    def __init__(self, subscriptions_repository: SubscriptionsRepository = None):
        self.subscriptions_repository = (
            subscriptions_repository or SubscriptionsRepository()
        )

    def create_subscription(
        self, subscription_data: SubscriptionCreate
    ) -> SubscriptionResponse:
        """Create a new subscription."""
        # Check if subscription already exists
        existing = self.subscriptions_repository.subscription_exists(
            subscription_data.personId, subscription_data.projectId
        )
        if existing:
            raise ValueError("Subscription already exists for this person and project")

        # Create subscription
        subscription = self.subscriptions_repository.create(subscription_data)

        # Convert to response format
        return SubscriptionResponse(**subscription.model_dump())

    def get_subscription(self, subscription_id: str) -> Optional[SubscriptionResponse]:
        """Get a subscription by ID."""
        subscription = self.subscriptions_repository.get_by_id(subscription_id)
        if not subscription:
            return None

        return SubscriptionResponse(**subscription.model_dump())

    def list_subscriptions(
        self, limit: Optional[int] = None
    ) -> List[SubscriptionResponse]:
        """List all subscriptions."""
        subscriptions = self.subscriptions_repository.list_all(limit=limit)
        return [SubscriptionResponse(**sub.model_dump()) for sub in subscriptions]

    def get_person_subscriptions(self, person_id: str) -> List[SubscriptionResponse]:
        """Get all subscriptions for a person."""
        subscriptions = self.subscriptions_repository.get_by_person(person_id)
        return [SubscriptionResponse(**sub.model_dump()) for sub in subscriptions]

    def get_project_subscriptions(self, project_id: str) -> List[SubscriptionResponse]:
        """Get all subscriptions for a project."""
        subscriptions = self.subscriptions_repository.get_by_project(project_id)
        return [SubscriptionResponse(**sub.model_dump()) for sub in subscriptions]

    def update_subscription(
        self, subscription_id: str, updates: SubscriptionUpdate
    ) -> Optional[SubscriptionResponse]:
        """Update a subscription and send welcome email if approved."""
        # Get current subscription to check status change
        current_subscription = self.subscriptions_repository.get_by_id(subscription_id)
        if not current_subscription:
            return None

        # Update the subscription
        subscription = self.subscriptions_repository.update(subscription_id, updates)
        if not subscription:
            return None

        # Check if status changed from pending to active (approval)
        if current_subscription.status == "pending" and updates.status == "active":

            # Send welcome email asynchronously
            import asyncio
            from ..services.service_registry_manager import (
                get_email_service,
                get_people_service,
                get_projects_service,
            )

            async def send_welcome_email():
                try:
                    email_service = get_email_service()
                    people_service = get_people_service()
                    projects_service = get_projects_service()

                    # Get person and project details
                    person = people_service.get_person(
                        subscription.personId
                    )  # Not async
                    project = await projects_service.get_project(subscription.projectId)

                    if person and project:
                        await email_service.send_project_welcome_email(
                            person.email, person.firstName, project.name
                        )
                except Exception as e:
                    # Log error but don't fail the subscription update
                    from ..services.logging_service import (
                        logging_service,
                        LogCategory,
                        LogLevel,
                    )

                    logging_service.log(
                        LogLevel.ERROR,
                        LogCategory.BUSINESS_LOGIC,
                        "Failed to send welcome email on subscription approval",
                        event_type="welcome_email_failed",
                        details={"subscription_id": subscription_id, "error": str(e)},
                    )

            # Run email sending in background
            try:
                asyncio.create_task(send_welcome_email())
            except Exception:
                # If we can't create task, try to run it directly
                try:
                    asyncio.run(send_welcome_email())
                except Exception:
                    pass  # Fail silently to not break subscription update

        return SubscriptionResponse(**subscription.model_dump())

    def delete_subscription(self, subscription_id: str) -> bool:
        """Delete a subscription."""
        return self.subscriptions_repository.delete(subscription_id)

    def check_subscription_exists(self, person_id: str, project_id: str) -> bool:
        """Check if a subscription exists for a person and project."""
        return self.subscriptions_repository.subscription_exists(person_id, project_id)
