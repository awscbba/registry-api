"""
Projects Service - Domain service for project-related operations.
Implements the Service Registry pattern for project management.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from ..core.base_service import BaseService
from ..models.project import ProjectCreate, ProjectUpdate
from ..services.defensive_dynamodb_service import DefensiveDynamoDBService
from ..utils.logging_config import get_handler_logger
from ..utils.error_handler import handle_database_error
from ..utils.response_models import create_v1_response, create_v2_response


class ProjectsService(BaseService):
    """Service for managing project-related operations."""

    def __init__(self):
        super().__init__("projects_service")
        self.db_service = DefensiveDynamoDBService()
        self.logger = get_handler_logger("projects_service")

    async def initialize(self):
        """Initialize the projects service."""
        try:
            # Test database connectivity
            await self.db_service.get_all_projects()
            self.logger.info("Projects service initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize projects service: {str(e)}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the projects service."""
        try:
            # Test database connectivity
            await self.db_service.get_all_projects()
            return {
                "service": "projects_service",
                "status": "healthy",
                "database": "connected",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Projects service health check failed: {str(e)}")
            return {
                "service": "projects_service",
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def get_all_projects_v1(self) -> Dict[str, Any]:
        """Get all projects (v1 format)."""
        try:
            self.logger.log_api_request("GET", "/v1/projects")
            projects = await self.db_service.get_all_projects()

            response = create_v1_response(projects)
            self.logger.log_api_response("GET", "/v1/projects", 200)
            return response
        except Exception as e:
            self.logger.error(
                "Failed to retrieve projects",
                operation="get_all_projects_v1",
                error_type=type(e).__name__,
            )
            raise handle_database_error("retrieving projects", e)

    async def get_all_projects_v2(self) -> Dict[str, Any]:
        """Get all projects (v2 format with enhanced metadata)."""
        try:
            self.logger.log_api_request("GET", "/v2/projects")
            projects = await self.db_service.get_all_projects()

            response = create_v2_response(
                projects,
                metadata={
                    "total_count": len(projects),
                    "service": "projects_service",
                    "version": "v2",
                },
            )
            self.logger.log_api_response(
                "GET", "/v2/projects", 200, additional_context={"count": len(projects)}
            )
            return response
        except Exception as e:
            self.logger.error(
                "Failed to retrieve projects",
                operation="get_all_projects_v2",
                error_type=type(e).__name__,
            )
            raise handle_database_error("retrieving projects", e)

    async def get_project_by_id_v1(self, project_id: str) -> Dict[str, Any]:
        """Get project by ID (v1 format)."""
        try:
            self.logger.log_api_request("GET", f"/v1/projects/{project_id}")
            project = await self.db_service.get_project_by_id(project_id)

            if not project:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
                )

            response = create_v1_response(project)
            self.logger.log_api_response("GET", f"/v1/projects/{project_id}", 200)
            return response
        except Exception as e:
            if hasattr(e, "status_code"):
                raise e
            self.logger.error(
                "Failed to retrieve project",
                operation="get_project_by_id_v1",
                project_id=project_id,
                error_type=type(e).__name__,
            )
            raise handle_database_error("retrieving project", e)

    async def get_project_by_id_v2(self, project_id: str) -> Dict[str, Any]:
        """Get project by ID (v2 format with enhanced metadata)."""
        try:
            self.logger.log_api_request("GET", f"/v2/projects/{project_id}")
            project = await self.db_service.get_project_by_id(project_id)

            if not project:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
                )

            response = create_v2_response(
                project,
                metadata={
                    "project_id": project_id,
                    "service": "projects_service",
                    "version": "v2",
                },
            )
            self.logger.log_api_response("GET", f"/v2/projects/{project_id}", 200)
            return response
        except Exception as e:
            if hasattr(e, "status_code"):
                raise e
            self.logger.error(
                "Failed to retrieve project",
                operation="get_project_by_id_v2",
                project_id=project_id,
                error_type=type(e).__name__,
            )
            raise handle_database_error("retrieving project", e)

    async def create_project_v1(self, project_data: ProjectCreate) -> Dict[str, Any]:
        """Create a new project (v1 format)."""
        try:
            self.logger.log_api_request("POST", "/v1/projects")

            # Generate ID if not provided
            project_id = str(uuid.uuid4())

            # Create project using database service
            created_project = await self.db_service.create_project(
                project_data, project_id
            )

            response = create_v1_response(created_project)
            self.logger.log_api_response("POST", "/v1/projects", 201)
            return response
        except Exception as e:
            self.logger.error(
                "Failed to create project",
                operation="create_project_v1",
                error_type=type(e).__name__,
            )
            raise handle_database_error("creating project", e)

    async def create_project_v2(self, project_data: ProjectCreate) -> Dict[str, Any]:
        """Create a new project (v2 format with enhanced features)."""
        try:
            self.logger.log_api_request("POST", "/v2/projects")

            # Generate ID if not provided
            project_id = str(uuid.uuid4())

            # Create project using database service
            created_project = await self.db_service.create_project(
                project_data, project_id
            )

            response = create_v2_response(
                created_project,
                metadata={
                    "project_id": project_id,
                    "service": "projects_service",
                    "version": "v2",
                    "created_at": datetime.now().isoformat(),
                },
            )
            self.logger.log_api_response("POST", "/v2/projects", 201)
            return response
        except Exception as e:
            self.logger.error(
                "Failed to create project",
                operation="create_project_v2",
                error_type=type(e).__name__,
            )
            raise handle_database_error("creating project", e)

    async def update_project_v1(
        self, project_id: str, project_data: ProjectUpdate
    ) -> Dict[str, Any]:
        """Update project (v1 format)."""
        try:
            self.logger.log_api_request("PUT", f"/v1/projects/{project_id}")

            # Check if project exists
            existing_project = await self.db_service.get_project_by_id(project_id)
            if not existing_project:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
                )

            # Update project
            updated_project = await self.db_service.update_project(
                project_id, project_data
            )

            response = create_v1_response(updated_project)
            self.logger.log_api_response("PUT", f"/v1/projects/{project_id}", 200)
            return response
        except Exception as e:
            if hasattr(e, "status_code"):
                raise e
            self.logger.error(
                "Failed to update project",
                operation="update_project_v1",
                project_id=project_id,
                error_type=type(e).__name__,
            )
            raise handle_database_error("updating project", e)

    async def update_project_v2(
        self, project_id: str, project_data: ProjectUpdate
    ) -> Dict[str, Any]:
        """Update project (v2 format with enhanced features)."""
        try:
            self.logger.log_api_request("PUT", f"/v2/projects/{project_id}")

            # Check if project exists
            existing_project = await self.db_service.get_project_by_id(project_id)
            if not existing_project:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
                )

            # Update project
            updated_project = await self.db_service.update_project(
                project_id, project_data
            )

            response = create_v2_response(
                updated_project,
                metadata={
                    "project_id": project_id,
                    "service": "projects_service",
                    "version": "v2",
                    "updated_at": datetime.now().isoformat(),
                },
            )
            self.logger.log_api_response("PUT", f"/v2/projects/{project_id}", 200)
            return response
        except Exception as e:
            if hasattr(e, "status_code"):
                raise e
            self.logger.error(
                "Failed to update project",
                operation="update_project_v2",
                project_id=project_id,
                error_type=type(e).__name__,
            )
            raise handle_database_error("updating project", e)

    async def delete_project_v1(self, project_id: str) -> Dict[str, Any]:
        """Delete project (v1 format)."""
        try:
            self.logger.log_api_request("DELETE", f"/v1/projects/{project_id}")

            # Check if project exists
            existing_project = await self.db_service.get_project_by_id(project_id)
            if not existing_project:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
                )

            # Delete project
            success = await self.db_service.delete_project(project_id)
            if not success:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete project",
                )

            response = create_v1_response(
                {"message": "Project deleted successfully", "projectId": project_id}
            )
            self.logger.log_api_response("DELETE", f"/v1/projects/{project_id}", 200)
            return response
        except Exception as e:
            if hasattr(e, "status_code"):
                raise e
            self.logger.error(
                "Failed to delete project",
                operation="delete_project_v1",
                project_id=project_id,
                error_type=type(e).__name__,
            )
            raise handle_database_error("deleting project", e)

    async def delete_project_v2(self, project_id: str) -> Dict[str, Any]:
        """Delete project (v2 format with enhanced features)."""
        try:
            self.logger.log_api_request("DELETE", f"/v2/projects/{project_id}")

            # Check if project exists
            existing_project = await self.db_service.get_project_by_id(project_id)
            if not existing_project:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
                )

            # Delete project
            success = await self.db_service.delete_project(project_id)
            if not success:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete project",
                )

            response = create_v2_response(
                {"message": "Project deleted successfully", "projectId": project_id},
                metadata={
                    "project_id": project_id,
                    "service": "projects_service",
                    "version": "v2",
                    "deleted_at": datetime.now().isoformat(),
                },
            )
            self.logger.log_api_response("DELETE", f"/v2/projects/{project_id}", 200)
            return response
        except Exception as e:
            if hasattr(e, "status_code"):
                raise e
            self.logger.error(
                "Failed to delete project",
                operation="delete_project_v2",
                project_id=project_id,
                error_type=type(e).__name__,
            )
            raise handle_database_error("deleting project", e)
