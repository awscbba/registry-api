"""
Project Repository - Data access layer for project entities

Provides clean data access patterns for project management operations.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from .base_repository import (
    BaseRepository,
    RepositoryResult,
    QueryOptions,
    QueryFilter,
    QueryOperator,
)
from ..models.project import Project


class ProjectRepository(BaseRepository[Project]):
    """Repository for project data access operations"""

    def __init__(self, table_name: str = "people-registry-projects"):
        super().__init__(table_name)

    def _to_entity(self, item: Dict[str, Any]) -> Project:
        """Convert DynamoDB item to Project entity"""
        project_data = {
            "id": item.get("id"),
            "name": item.get("name"),
            "description": item.get("description"),
            "status": item.get("status", "active"),
            "created_by": item.get("created_by"),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
            "start_date": item.get("start_date"),
            "end_date": item.get("end_date"),
            "budget": item.get("budget"),
            "tags": item.get("tags", []),
        }

        return Project(**{k: v for k, v in project_data.items() if v is not None})

    def _to_item(self, entity: Project) -> Dict[str, Any]:
        """Convert Project entity to DynamoDB item"""
        item = {
            "id": entity.id,
            "name": entity.name,
            "description": entity.description,
            "status": getattr(entity, "status", "active"),
            "created_by": entity.created_by,
        }

        # Handle optional fields
        optional_fields = [
            "created_at",
            "updated_at",
            "start_date",
            "end_date",
            "budget",
            "tags",
        ]

        for field in optional_fields:
            value = getattr(entity, field, None)
            if value is not None:
                item[field] = value

        return item

    def _get_primary_key(self, entity: Project) -> Dict[str, Any]:
        """Get primary key from Project entity"""
        return {"id": entity.id}

    async def get_by_status(self, status: str) -> RepositoryResult[List[Project]]:
        """Get projects by status"""
        filters = [
            QueryFilter(field="status", operator=QueryOperator.EQUALS, value=status)
        ]
        options = QueryOptions(filters=filters)

        return await self.list_all(options)

    async def get_by_creator(self, creator_id: str) -> RepositoryResult[List[Project]]:
        """Get projects created by a specific user"""
        filters = [
            QueryFilter(
                field="created_by", operator=QueryOperator.EQUALS, value=creator_id
            )
        ]
        options = QueryOptions(filters=filters)

        return await self.list_all(options)
