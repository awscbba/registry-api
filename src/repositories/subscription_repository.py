"""
Subscription Repository - Data access layer for subscription entities

Provides clean data access patterns for subscription management operations.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from src.repositories.base_repository import (
    BaseRepository,
    RepositoryResult,
    QueryOptions,
    QueryFilter,
    QueryOperator,
)
from src.models.subscription import Subscription


class SubscriptionRepository(BaseRepository[Subscription]):
    """Repository for subscription data access operations"""

    def __init__(self, table_name: str = "SubscriptionsTable"):
        super().__init__(table_name)

    def _to_entity(self, item: Dict[str, Any]) -> Subscription:
        """Convert DynamoDB item to Subscription entity"""
        try:
            # Handle subscription data conversion
            subscription_data = {
                "id": item.get("id"),
                "person_id": item.get("person_id"),
                "project_id": item.get("project_id"),
                "person_name": item.get("person_name"),
                "person_email": item.get("person_email"),
                "status": item.get("status", "active"),
                "notes": item.get("notes", ""),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "email_sent": item.get("email_sent", False),
            }

            return Subscription(
                **{k: v for k, v in subscription_data.items() if v is not None}
            )

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                f"Failed to convert DynamoDB item to Subscription entity: {str(e)}"
            )
            logger.error(f"Item data: {item}")
            raise e

    def _to_item(self, entity: Subscription) -> Dict[str, Any]:
        """Convert Subscription entity to DynamoDB item"""
        item = {
            "id": entity.id,
            "person_id": entity.person_id,
            "project_id": entity.project_id,
            "person_name": entity.person_name,
            "person_email": entity.person_email,
            "status": getattr(entity, "status", "active"),
            "notes": getattr(entity, "notes", ""),
            "email_sent": getattr(entity, "email_sent", False),
        }

        # Handle optional fields
        optional_fields = ["created_at", "updated_at"]
        for field in optional_fields:
            value = getattr(entity, field, None)
            if value is not None:
                item[field] = value

        return item

    def _get_primary_key(self, entity: Subscription) -> Dict[str, Any]:
        """Get primary key from Subscription entity"""
        return {"id": entity.id}

    async def get_by_person_id(
        self, person_id: str
    ) -> RepositoryResult[List[Subscription]]:
        """Get subscriptions by person ID"""
        filters = [
            QueryFilter(
                field="person_id", operator=QueryOperator.EQUALS, value=person_id
            )
        ]
        options = QueryOptions(filters=filters)
        return await self.list_all(options)

    async def get_by_project_id(
        self, project_id: str
    ) -> RepositoryResult[List[Subscription]]:
        """Get subscriptions by project ID"""
        filters = [
            QueryFilter(
                field="project_id", operator=QueryOperator.EQUALS, value=project_id
            )
        ]
        options = QueryOptions(filters=filters)
        return await self.list_all(options)

    async def get_by_person_and_project(
        self, person_id: str, project_id: str
    ) -> RepositoryResult[Subscription]:
        """Get subscription by person and project"""
        filters = [
            QueryFilter(
                field="person_id", operator=QueryOperator.EQUALS, value=person_id
            ),
            QueryFilter(
                field="project_id", operator=QueryOperator.EQUALS, value=project_id
            ),
        ]
        options = QueryOptions(filters=filters, limit=1)

        result = await self.list_all(options)
        if result.success and result.data:
            return RepositoryResult[Subscription](success=True, data=result.data[0])

        return RepositoryResult[Subscription](success=True, data=None)

    async def get_active_subscriptions(self) -> RepositoryResult[List[Subscription]]:
        """Get all active subscriptions"""
        filters = [
            QueryFilter(field="status", operator=QueryOperator.EQUALS, value="active")
        ]
        options = QueryOptions(filters=filters)
        return await self.list_all(options)

    async def get_by_email(self, email: str) -> RepositoryResult[List[Subscription]]:
        """Get subscriptions by person email"""
        filters = [
            QueryFilter(
                field="person_email", operator=QueryOperator.EQUALS, value=email
            )
        ]
        options = QueryOptions(filters=filters)
        return await self.list_all(options)
