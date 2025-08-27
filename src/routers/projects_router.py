"""
Projects router - handles all project-related endpoints.
Clean architecture implementation using service layer.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends

from ..models.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectStatus,
)
from ..services.projects_service import ProjectsService
from ..services.service_registry_manager import get_projects_service
from ..utils.responses import (
    create_success_response,
    create_error_response,
    create_list_response,
)

router = APIRouter(prefix="/v2/projects", tags=["Projects"])


@router.get("/", response_model=dict)
async def list_projects(
    limit: Optional[int] = Query(
        None, ge=1, le=1000, description="Limit number of results"
    ),
    status: Optional[ProjectStatus] = Query(
        None, description="Filter by project status"
    ),
    category: Optional[str] = Query(None, description="Filter by category"),
    projects_service: ProjectsService = Depends(get_projects_service),
) -> dict:
    """Get all projects with optional filtering."""
    try:
        projects = await projects_service.list_projects(
            limit=limit, status=status, category=category
        )
        return create_list_response(projects)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve projects: {str(e)}"
        )


@router.get("/{project_id}", response_model=dict)
async def get_project(
    project_id: str, projects_service: ProjectsService = Depends(get_projects_service)
) -> dict:
    """Get a specific project by ID."""
    try:
        project = await projects_service.get_project(project_id)

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        return create_success_response(project)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve project: {str(e)}"
        )


@router.post("/", response_model=dict, status_code=201)
async def create_project(
    project_data: ProjectCreate,
    projects_service: ProjectsService = Depends(get_projects_service),
) -> dict:
    """Create a new project."""
    try:
        project = await projects_service.create_project(project_data)
        return create_success_response(project, "Project created successfully")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create project: {str(e)}"
        )


@router.get("/public", response_model=dict)
async def get_public_projects(
    limit: Optional[int] = Query(
        None, ge=1, le=1000, description="Limit number of results"
    ),
    projects_service: ProjectsService = Depends(get_projects_service),
) -> dict:
    """Get all public/active projects (no authentication required)."""
    try:
        projects = await projects_service.list_public_projects(limit=limit)
        return create_list_response(projects)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve public projects: {str(e)}"
        )
