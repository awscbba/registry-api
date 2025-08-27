"""
Projects service - Business logic for projects operations.
Orchestrates repository operations and implements business rules.
"""

from typing import List, Optional

from ..repositories.projects_repository import ProjectsRepository
from ..models.project import (
    Project,
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectStatus,
)


class ProjectsService:
    """Service for projects business logic."""

    def __init__(self, projects_repository: ProjectsRepository):
        self.projects_repository = projects_repository

    async def create_project(self, project_data: ProjectCreate) -> ProjectResponse:
        """Create a new project with business validation."""
        # Business validation
        if project_data.endDate <= project_data.startDate:
            raise ValueError("End date must be after start date")

        if project_data.maxParticipants <= 0:
            raise ValueError("Maximum participants must be greater than 0")

        # Create project
        project = await self.projects_repository.create(project_data)

        # Convert to response model
        return ProjectResponse(**project.model_dump())

    async def get_project(self, project_id: str) -> Optional[ProjectResponse]:
        """Get a project by ID."""
        project = await self.projects_repository.get_by_id(project_id)
        if not project:
            return None

        return ProjectResponse(**project.model_dump())

    async def update_project(
        self, project_id: str, updates: ProjectUpdate
    ) -> Optional[ProjectResponse]:
        """Update a project with business validation."""
        # Business validation
        if (
            updates.endDate
            and updates.startDate
            and updates.endDate <= updates.startDate
        ):
            raise ValueError("End date must be after start date")

        if updates.maxParticipants is not None and updates.maxParticipants <= 0:
            raise ValueError("Maximum participants must be greater than 0")

        # Update project
        project = await self.projects_repository.update(project_id, updates)
        if not project:
            return None

        return ProjectResponse(**project.model_dump())

    async def delete_project(self, project_id: str) -> bool:
        """Delete a project."""
        # TODO: Add business rules (e.g., check for active subscriptions)
        return await self.projects_repository.delete(project_id)

    async def list_projects(
        self,
        limit: Optional[int] = None,
        status: Optional[ProjectStatus] = None,
        category: Optional[str] = None,
    ) -> List[ProjectResponse]:
        """List projects with optional filtering."""
        if status:
            projects = await self.projects_repository.list_by_status(status, limit)
        elif category:
            projects = await self.projects_repository.list_by_category(category, limit)
        else:
            projects = await self.projects_repository.list_all(limit)

        return [ProjectResponse(**project.model_dump()) for project in projects]

    async def list_public_projects(
        self, limit: Optional[int] = None
    ) -> List[ProjectResponse]:
        """List public/active projects."""
        projects = await self.projects_repository.list_public_projects(limit)
        return [ProjectResponse(**project.model_dump()) for project in projects]

    async def update_participant_count(
        self, project_id: str, count: int
    ) -> Optional[ProjectResponse]:
        """Update the current participant count for a project."""
        project = await self.projects_repository.update_participant_count(
            project_id, count
        )
        if not project:
            return None

        return ProjectResponse(**project.model_dump())

    async def can_accept_participants(self, project_id: str) -> bool:
        """Check if a project can accept more participants."""
        project = await self.projects_repository.get_by_id(project_id)
        if not project:
            return False

        return project.currentParticipants < project.maxParticipants

    async def is_project_active(self, project_id: str) -> bool:
        """Check if a project is active."""
        project = await self.projects_repository.get_by_id(project_id)
        if not project:
            return False

        return project.status == ProjectStatus.ACTIVE
