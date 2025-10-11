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
from ..models.dynamic_forms import EnhancedProjectCreate, FormSchema
from ..services.projects_service import ProjectsService
from ..services.subscriptions_service import SubscriptionsService
from ..services.service_registry_manager import (
    get_projects_service,
    get_subscriptions_service,
)
from ..utils.responses import (
    create_success_response,
    create_error_response,
    create_list_response,
)

router = APIRouter(prefix="/v2/projects", tags=["Projects"])


@router.get("", response_model=dict)
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


@router.post("", response_model=dict, status_code=201)
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


@router.put("/{project_id}", response_model=dict)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    projects_service: ProjectsService = Depends(get_projects_service),
) -> dict:
    """Update an existing project."""
    try:
        project = await projects_service.update_project(project_id, project_data)

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        return create_success_response(project, "Project updated successfully")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update project: {str(e)}"
        )


@router.delete("/{project_id}", response_model=dict)
async def delete_project(
    project_id: str, projects_service: ProjectsService = Depends(get_projects_service)
) -> dict:
    """Delete a project."""
    try:
        success = await projects_service.delete_project(project_id)

        if not success:
            raise HTTPException(status_code=404, detail="Project not found")

        return create_success_response(
            {"deleted": True}, "Project deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete project: {str(e)}"
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


# Project Subscription Management Endpoints
@router.get("/{project_id}/subscriptions", response_model=dict)
async def get_project_subscriptions(
    project_id: str,
    subscriptions_service: SubscriptionsService = Depends(get_subscriptions_service),
):
    """Get all subscriptions for a specific project."""
    try:
        subscriptions = subscriptions_service.get_project_subscriptions(
            project_id
        )  # Not async
        return create_success_response(subscriptions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/subscriptions", response_model=dict, status_code=201)
async def subscribe_to_project(
    project_id: str,
    subscription_data: dict,
    subscriptions_service: SubscriptionsService = Depends(get_subscriptions_service),
):
    """Subscribe a person to a project."""
    try:
        # Add project_id to subscription data
        subscription_data["projectId"] = project_id

        from ..models.subscription import SubscriptionCreate

        subscription_create = SubscriptionCreate(**subscription_data)

        subscription = subscriptions_service.create_subscription(
            subscription_create
        )  # Not async
        return create_success_response(subscription)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{project_id}/subscribers/{subscription_id}", response_model=dict)
async def update_project_subscription(
    project_id: str,
    subscription_id: str,
    subscription_data: dict,
    subscriptions_service: SubscriptionsService = Depends(get_subscriptions_service),
):
    """Update a project subscription."""
    try:
        from ..models.subscription import SubscriptionUpdate

        subscription_update = SubscriptionUpdate(**subscription_data)

        subscription = subscriptions_service.update_subscription(
            subscription_id, subscription_update
        )  # Not async
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        return create_success_response(subscription)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}/subscribers/{subscription_id}", response_model=dict)
async def unsubscribe_from_project(
    project_id: str,
    subscription_id: str,
    subscriptions_service: SubscriptionsService = Depends(get_subscriptions_service),
):
    """Remove a subscription from a project."""
    try:
        success = subscriptions_service.delete_subscription(
            subscription_id
        )  # Not async
        if not success:
            raise HTTPException(status_code=404, detail="Subscription not found")

        return create_success_response(
            {"deleted": True, "subscriptionId": subscription_id}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Enhanced Dynamic Forms Endpoints
@router.post("/enhanced", response_model=dict)
async def create_project_with_dynamic_fields(
    project_data: EnhancedProjectCreate,
    projects_service: ProjectsService = Depends(get_projects_service),
):
    """Create a project with dynamic form fields and rich text description."""
    try:
        project = projects_service.create_with_dynamic_fields(project_data)
        return create_success_response(project.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/enhanced", response_model=dict)
async def get_project_with_dynamic_fields(
    project_id: str,
    projects_service: ProjectsService = Depends(get_projects_service),
):
    """Get a project with its dynamic form schema and custom fields."""
    try:
        project = projects_service.get_with_dynamic_fields(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        return create_success_response(project.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{project_id}/form-schema", response_model=dict)
async def update_project_form_schema(
    project_id: str,
    form_schema: FormSchema,
    projects_service: ProjectsService = Depends(get_projects_service),
):
    """Update the form schema for a project."""
    try:
        # Validate schema first
        projects_service.validate_form_schema(form_schema)

        # Update the schema
        project = projects_service.update_form_schema(project_id, form_schema)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        return create_success_response(project.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
