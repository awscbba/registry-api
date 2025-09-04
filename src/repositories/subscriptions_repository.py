"""
Subscriptions repository implementation.
Handles all data access operations for subscriptions.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from .base_repository import BaseRepository
from ..core.database import db
from ..models.subscription import Subscription, SubscriptionCreate, SubscriptionUpdate


class SubscriptionsRepository(BaseRepository[Subscription]):
    """Repository for subscriptions data access operations."""

    def __init__(self):
        from ..core.config import config

        self.table_name = config.database.subscriptions_table

    def create(self, subscription_data: SubscriptionCreate) -> Subscription:
        """Create a new subscription in the database."""
        # Generate ID and timestamps
        subscription_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # Convert to database format (already camelCase - no conversion needed!)
        db_item = subscription_data.model_dump()
        db_item.update(
            {
                "id": subscription_id,
                "subscriptionDate": now.isoformat(),
                "createdAt": now.isoformat(),
                "updatedAt": now.isoformat(),
                "isActive": True,
            }
        )

        # Save to database
        success = db.put_item(self.table_name, db_item)
        if not success:
            raise Exception("Failed to create subscription in database")

        return Subscription(**db_item)

    def get_by_id(self, subscription_id: str) -> Optional[Subscription]:
        """Get a subscription by its ID."""
        subscription_data = db.get_item(self.table_name, {"id": subscription_id})
        if not subscription_data:
            return None

        return Subscription(**subscription_data)

    def get_by_person_and_project(
        self, person_id: str, project_id: str
    ) -> Optional[Subscription]:
        """Get a subscription by person and project IDs."""
        # Scan for subscription with matching person and project
        all_subscriptions = db.scan_table(self.table_name)
        for subscription_data in all_subscriptions:
            if (
                subscription_data.get("personId") == person_id
                and subscription_data.get("projectId") == project_id
            ):
                return Subscription(**subscription_data)
        return None

    def get_by_person(self, person_id: str) -> List[Subscription]:
        """Get all subscriptions for a person."""
        all_subscriptions = db.scan_table(self.table_name)
        person_subscriptions = []
        for subscription_data in all_subscriptions:
            if subscription_data.get("personId") == person_id:
                person_subscriptions.append(Subscription(**subscription_data))
        return person_subscriptions

    def get_by_project(self, project_id: str) -> List[Subscription]:
        """Get all subscriptions for a project."""
        all_subscriptions = db.scan_table(self.table_name)
        project_subscriptions = []
        for subscription_data in all_subscriptions:
            if subscription_data.get("projectId") == project_id:
                project_subscriptions.append(Subscription(**subscription_data))
        return project_subscriptions

    def update(
        self, subscription_id: str, updates: SubscriptionUpdate
    ) -> Optional[Subscription]:
        """Update an existing subscription."""
        # Check if subscription exists
        existing_subscription = self.get_by_id(subscription_id)
        if not existing_subscription:
            return None

        # Prepare update data (exclude None values)
        update_data = updates.model_dump(exclude_none=True)
        if update_data:
            update_data["updatedAt"] = datetime.utcnow().isoformat()

            # Update in database (no field conversion needed!)
            success = db.update_item(
                self.table_name, {"id": subscription_id}, update_data
            )
            if not success:
                raise Exception("Failed to update subscription in database")

        # Return updated subscription
        return self.get_by_id(subscription_id)

    def delete(self, subscription_id: str) -> bool:
        """Delete a subscription by its ID."""
        return db.delete_item(self.table_name, {"id": subscription_id})

    def list_all(self, limit: Optional[int] = None) -> List[Subscription]:
        """List all subscriptions with optional limit."""
        subscriptions_data = db.scan_table(self.table_name, limit=limit)
        return [
            Subscription(**subscription_data)
            for subscription_data in subscriptions_data
        ]

    def exists(self, subscription_id: str) -> bool:
        """Check if a subscription exists."""
        subscription = self.get_by_id(subscription_id)
        return subscription is not None

    def subscription_exists(self, person_id: str, project_id: str) -> bool:
        """Check if a subscription exists for a person and project."""
        subscription = self.get_by_person_and_project(person_id, project_id)
        return subscription is not None
