"""
Projects Service - Domain service for project-related operations.
Implements the Service Registry pattern with Repository pattern integration.
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from ..core.base_service import BaseService
from ..models.project import ProjectCreate, ProjectUpdate, Project
from ..repositories.project_repository import ProjectRepository
from ..services.defensive_dynamodb_service import DefensiveDynamoDBService
from ..utils.logging_config import get_handler_logger
from ..utils.error_handler import handle_database_error
from ..utils.response_models import create_v1_response, create_v2_response


class ProjectsService(BaseService):
    """Service for managing project-related operations with repository pattern."""

    def __init__(self):
        super().__init__("projects_service")
        # Use environment variable for table name
        table_name = os.getenv("PROJECTS_TABLE_NAME", "ProjectsTable")
        # Initialize repository for clean data access
        self.project_repository = ProjectRepository(table_name=table_name)
        # Keep legacy db_service for backward compatibility during transition
        self.db_service = DefensiveDynamoDBService()
        self.logger = get_handler_logger("projects_service")

    async def initialize(self):
        """Initialize the projects service with repository pattern."""
        try:
            # Test repository connectivity with a simple count operation
            count_result = await self.project_repository.count()
            if count_result.success:
                self.logger.info(
                    f"Projects service initialized successfully. Found {count_result.data} projects."
                )
                return True
            else:
                self.logger.error(
                    f"Repository health check failed: {count_result.error}"
                )
                return False
        except Exception as e:
            self.logger.error(f"Failed to initialize projects service: {str(e)}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the projects service using repository pattern."""
        try:
            import asyncio

            # Test repository connectivity with timeout
            try:
                count_result = await asyncio.wait_for(
                    self.project_repository.count(), timeout=1.0
                )
                performance_stats = self.project_repository.get_performance_stats()

                if count_result.success:
                    return {
                        "service": "projects_service",
                        "status": "healthy",
                        "repository": "connected",
                        "project_count": count_result.data,
                        "performance": performance_stats,
                        "timestamp": datetime.now().isoformat(),
                    }
                else:
                    return {
                        "service": "projects_service",
                        "status": "unhealthy",
                        "repository": "disconnected",
                        "error": count_result.error,
                        "timestamp": datetime.now().isoformat(),
                    }
            except asyncio.TimeoutError:
                return {
                    "service": "projects_service",
                    "status": "degraded",
                    "repository": "timeout",
                    "message": "Repository check timed out",
                    "timestamp": datetime.now().isoformat(),
                }
        except Exception as e:
            self.logger.error(f"Projects service health check failed: {str(e)}")
            return {
                "service": "projects_service",
                "status": "unhealthy",
                "repository": "disconnected",
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

            # Use repository for more efficient data access
            result = await self.project_repository.get_all()

            if result.success:
                # Add robust error handling for project serialization
                projects = []
                for i, project in enumerate(result.data):
                    try:
                        if hasattr(project, "model_dump"):
                            projects.append(project.model_dump())
                        elif hasattr(project, "dict"):
                            # Fallback for older Pydantic versions
                            projects.append(project.dict())
                        elif isinstance(project, dict):
                            # Already a dictionary
                            projects.append(project)
                        else:
                            self.logger.error(
                                f"Project {i} has unexpected type: {type(project)}"
                            )
                            # Skip invalid projects
                            continue
                    except Exception as e:
                        self.logger.error(
                            f"Error processing project {i}: {str(e)}, type: {type(project)}"
                        )
                        # Skip problematic projects
                        continue

                response = create_v2_response(
                    projects,
                    metadata={
                        "total_count": len(projects),
                        "service": "projects_service",
                        "version": "v2",
                        "repository_pattern": True,
                    },
                )
                self.logger.log_api_response(
                    "GET",
                    "/v2/projects",
                    200,
                    additional_context={"count": len(projects)},
                )
                return response
            else:
                # Repository failed - return limited data to prevent timeout
                self.logger.warning(
                    f"Repository failed: {result.error}, returning limited data"
                )

                # Return a basic response with count only to prevent timeout
                try:
                    # Try to get just a count using the defensive service
                    count_result = await self.project_repository.count()
                    total_count = count_result.data if count_result.success else 0
                except Exception:
                    total_count = 0

                response = create_v2_response(
                    [],  # Empty list to prevent timeout
                    metadata={
                        "total_count": total_count,
                        "service": "projects_service",
                        "version": "v2",
                        "limited_response": True,
                        "reason": "Repository failed, returning count only",
                    },
                )
                self.logger.log_api_response(
                    "GET",
                    "/v2/projects",
                    200,
                    additional_context={"count": 0, "total_available": total_count},
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

    # New Repository-Based Methods for Enhanced Functionality

    async def get_all_projects_repository(
        self, limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get all projects using repository pattern with enhanced features."""
        try:
            self.logger.log_api_request("GET", "/repository/projects")

            from ..repositories.base_repository import QueryOptions

            options = QueryOptions(limit=limit) if limit else None

            result = await self.project_repository.list_all(options)

            if result.success:
                # Convert Project objects to dict for response
                projects_data = (
                    [project.dict() for project in result.data] if result.data else []
                )

                response = create_v2_response(
                    projects_data,
                    metadata={
                        "total_count": len(projects_data),
                        "service": "projects_service",
                        "version": "repository",
                        "performance": self.project_repository.get_performance_stats(),
                    },
                )

                # Add result metadata if available
                if result.metadata:
                    response["metadata"].update(result.metadata)
                self.logger.log_api_response(
                    "GET",
                    "/repository/projects",
                    200,
                    additional_context={"count": len(projects_data)},
                )
                return response
            else:
                raise Exception(f"Repository error: {result.error}")

        except Exception as e:
            self.logger.error(
                "Failed to retrieve projects via repository",
                operation="get_all_projects_repository",
                error_type=type(e).__name__,
            )
            raise handle_database_error("retrieving projects", e)

    async def get_projects_by_status(self, status: str) -> Dict[str, Any]:
        """Get projects by status using repository pattern."""
        try:
            self.logger.log_api_request("GET", f"/repository/projects/status/{status}")

            result = await self.project_repository.get_by_status(status)

            if result.success:
                projects_data = (
                    [project.dict() for project in result.data] if result.data else []
                )

                response = create_v2_response(
                    projects_data,
                    metadata={
                        "status_filter": status,
                        "count": len(projects_data),
                        "service": "projects_service",
                        "version": "repository",
                    },
                )
                self.logger.log_api_response(
                    "GET",
                    f"/repository/projects/status/{status}",
                    200,
                    additional_context={"status": status, "count": len(projects_data)},
                )
                return response
            else:
                raise Exception(f"Repository error: {result.error}")

        except Exception as e:
            self.logger.error(
                "Failed to retrieve projects by status",
                operation="get_projects_by_status",
                status=status,
                error_type=type(e).__name__,
            )
            raise handle_database_error("retrieving projects by status", e)

    async def get_projects_by_creator(self, creator_id: str) -> Dict[str, Any]:
        """Get projects by creator using repository pattern."""
        try:
            self.logger.log_api_request(
                "GET", f"/repository/projects/creator/{creator_id}"
            )

            result = await self.project_repository.get_by_creator(creator_id)

            if result.success:
                projects_data = (
                    [project.dict() for project in result.data] if result.data else []
                )

                response = create_v2_response(
                    projects_data,
                    metadata={
                        "creator_id": creator_id,
                        "count": len(projects_data),
                        "service": "projects_service",
                        "version": "repository",
                    },
                )
                self.logger.log_api_response(
                    "GET",
                    f"/repository/projects/creator/{creator_id}",
                    200,
                    additional_context={
                        "creator_id": creator_id,
                        "count": len(projects_data),
                    },
                )
                return response
            else:
                raise Exception(f"Repository error: {result.error}")

        except Exception as e:
            self.logger.error(
                "Failed to retrieve projects by creator",
                operation="get_projects_by_creator",
                creator_id=creator_id,
                error_type=type(e).__name__,
            )
            raise handle_database_error("retrieving projects by creator", e)

    async def get_projects_performance_stats(self) -> Dict[str, Any]:
        """Get repository performance statistics."""
        try:
            stats = self.project_repository.get_performance_stats()
            return create_v2_response(
                stats,
                metadata={
                    "service": "projects_service",
                    "version": "repository",
                    "stats_type": "performance",
                    "timestamp": datetime.now().isoformat(),
                },
            )
        except Exception as e:
            self.logger.error(
                "Failed to get performance stats",
                operation="get_projects_performance_stats",
                error_type=type(e).__name__,
            )
            raise handle_database_error("getting performance stats", e)
