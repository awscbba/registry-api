"""
Project Repository - Data access layer for project entities

Provides clean data access patterns for project management operations.
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from src.repositories.base_repository import (
    BaseRepository,
    RepositoryResult,
    QueryOptions,
    QueryFilter,
    QueryOperator,
)
from src.models.project import Project


class ProjectRepository(BaseRepository[Project]):
    """Repository for project data access operations"""

    def __init__(self, table_name: str = None):
        if table_name is None:
            table_name = os.getenv("PROJECTS_TABLE_NAME", "ProjectsTable")
        super().__init__(table_name)

    def _to_entity(self, item: Dict[str, Any]) -> Project:
        """Convert DynamoDB item to Project entity"""
        from datetime import datetime

        def safe_datetime_parse(date_str):
            """Safely parse datetime string to datetime object"""
            if not date_str:
                return None
            if isinstance(date_str, datetime):
                return date_str
            try:
                # Handle ISO format strings
                if isinstance(date_str, str):
                    if date_str.endswith("Z"):
                        date_str = date_str[:-1] + "+00:00"
                    return datetime.fromisoformat(date_str)
                return date_str
            except (ValueError, TypeError):
                return None

        # Use camelCase field names to match DefensiveDynamoDBService storage pattern
        project_data = {
            "id": item.get("id"),
            "name": item.get("name"),
            "description": item.get("description"),
            "startDate": item.get("startDate"),  # ✅ Fixed: was start_date
            "endDate": item.get("endDate"),  # ✅ Fixed: was end_date
            "maxParticipants": item.get("maxParticipants"),  # ✅ Added: was missing!
            "status": item.get("status", "active"),
            "category": item.get("category"),
            "location": item.get("location"),
            "requirements": item.get("requirements"),
            "createdBy": item.get("createdBy"),  # ✅ Fixed: was created_by
            "createdAt": safe_datetime_parse(
                item.get("createdAt")
            ),  # ✅ Fixed: was created_at + datetime conversion
            "updatedAt": safe_datetime_parse(
                item.get("updatedAt")
            ),  # ✅ Fixed: was updated_at + datetime conversion
        }

        return Project(**{k: v for k, v in project_data.items() if v is not None})

    def _to_item(self, entity: Project) -> Dict[str, Any]:
        """Convert Project entity to DynamoDB item"""

        def safe_datetime_format(dt):
            """Safely format datetime to ISO string"""
            if dt is None:
                return None
            if isinstance(dt, str):
                return dt
            try:
                return dt.isoformat()
            except (AttributeError, TypeError):
                return str(dt)

        # Use camelCase field names to match DefensiveDynamoDBService storage pattern
        item = {
            "id": entity.id,
            "name": entity.name,
            "description": entity.description,
            "startDate": entity.startDate,  # ✅ Fixed: was start_date
            "endDate": entity.endDate,  # ✅ Fixed: was end_date
            "maxParticipants": entity.maxParticipants,  # ✅ Added: was missing!
            "status": getattr(entity, "status", "active"),
            "category": getattr(entity, "category", ""),
            "location": getattr(entity, "location", ""),
            "requirements": getattr(entity, "requirements", ""),
            "createdBy": entity.createdBy,  # ✅ Fixed: was created_by
            "createdAt": safe_datetime_format(
                entity.createdAt
            ),  # ✅ Fixed: was created_at + datetime conversion
            "updatedAt": safe_datetime_format(
                entity.updatedAt
            ),  # ✅ Fixed: was updated_at + datetime conversion
        }

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
