"""
Enhanced Admin Handler for comprehensive administration features.

This module provides enhanced admin functionality including:
- Project management with full CRUD operations
- Enhanced dashboard with comprehensive statistics
- Analytics and reporting capabilities

Note: User management has been moved to dedicated users_admin_handler.py
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field

from ..models.person import PersonUpdate, PersonResponse
from ..models.project import ProjectCreate, ProjectUpdate
from ..models.auth import AuthenticatedUser
from ..services.service_registry_manager import service_manager
from ..middleware.admin_middleware_v2 import (
    require_admin_access,
    require_super_admin_access,
    AdminActionLogger,
)
from ..utils.response_models import create_v2_response
from ..utils.logging_config import get_handler_logger

logger = get_handler_logger(__name__)

# Create router
enhanced_admin_router = APIRouter(prefix="/v2/admin", tags=["Enhanced Admin"])


class ProjectEditRequest(BaseModel):
    """Request model for editing project information."""

    name: Optional[str] = Field(None, description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    startDate: Optional[str] = Field(None, description="Project start date")
    endDate: Optional[str] = Field(None, description="Project end date")
    maxParticipants: Optional[int] = Field(
        None, description="Maximum number of participants"
    )
    status: Optional[str] = Field(
        None, description="Project status (active, completed, cancelled)"
    )


@enhanced_admin_router.get("/dashboard/enhanced")
async def get_enhanced_admin_dashboard(
    admin_user: AuthenticatedUser = Depends(require_admin_access),
):
    """Get enhanced admin dashboard with comprehensive statistics including user data."""
    try:
        logger.log_api_request("GET", "/v2/admin/dashboard/enhanced")

        # Log admin action
        await AdminActionLogger.log_admin_action(
            action="VIEW_ENHANCED_DASHBOARD",
            admin_user=admin_user,
            target_resource="dashboard",
        )

        # Get all data using service registry
        projects_service = service_manager.get_service("projects")
        subscriptions_service = service_manager.get_service("subscriptions")
        people_service = service_manager.get_service("people")

        projects = await projects_service.get_all_projects()
        subscriptions = await subscriptions_service.get_all_subscriptions()
        people_result = await people_service.get_all_people()
        people = (
            people_result.get("data", [])
            if isinstance(people_result, dict)
            else people_result
        )

        # Calculate project statistics
        active_projects = [p for p in projects if p.get("status") == "active"]
        completed_projects = [p for p in projects if p.get("status") == "completed"]

        # Calculate subscription statistics
        active_subscriptions = [s for s in subscriptions if s.get("status") == "active"]
        pending_subscriptions = [
            s for s in subscriptions if s.get("status") == "pending"
        ]
        current_subscriptions = active_subscriptions + pending_subscriptions

        # Calculate user statistics
        active_users = [p for p in people if p.get("isActive", True)]
        admin_users = [p for p in people if p.get("isAdmin", False)]
        users_requiring_password_change = [
            p for p in people if p.get("requirePasswordChange", False)
        ]

        # Calculate recent activity (last 30 days)
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
        recent_users = [p for p in people if p.get("createdAt", "") > thirty_days_ago]
        recent_projects = [
            p for p in projects if p.get("createdAt", "") > thirty_days_ago
        ]
        recent_subscriptions = [
            s for s in subscriptions if s.get("createdAt", "") > thirty_days_ago
        ]

        # Get recent activity for timeline
        recent_activity = sorted(
            subscriptions, key=lambda x: x.get("createdAt", ""), reverse=True
        )[:10]

        # Create enhanced dashboard data
        dashboard_data = {
            # Project statistics
            "totalProjects": len(projects),
            "activeProjects": len(active_projects),
            "completedProjects": len(completed_projects),
            # Subscription statistics
            "totalSubscriptions": len(current_subscriptions),
            "activeSubscriptions": len(active_subscriptions),
            "pendingSubscriptions": len(pending_subscriptions),
            "totalSubscriptionsEverCreated": len(subscriptions),
            # User statistics (this was missing!)
            "totalUsers": len(people),
            "activeUsers": len(active_users),
            "adminUsers": len(admin_users),
            "usersRequiringPasswordChange": len(users_requiring_password_change),
            # Recent activity
            "recentActivity": recent_activity,
            # Enhanced statistics
            "statistics": {
                "projectsCreatedThisMonth": len(
                    [
                        p
                        for p in projects
                        if p.get("createdAt", "").startswith("2025-08")
                    ]
                ),
                "subscriptionsThisMonth": len(
                    [
                        s
                        for s in current_subscriptions
                        if s.get("createdAt", "").startswith("2025-08")
                    ]
                ),
                "usersCreatedThisMonth": len(
                    [p for p in people if p.get("createdAt", "").startswith("2025-08")]
                ),
                "averageSubscriptionsPerProject": len(current_subscriptions)
                / max(len(projects), 1),
                "userEngagementRate": len(current_subscriptions) / max(len(people), 1),
                # Recent activity counts
                "recentActivity30Days": {
                    "newUsers": len(recent_users),
                    "newProjects": len(recent_projects),
                    "newSubscriptions": len(recent_subscriptions),
                },
            },
            # System health indicators
            "systemHealth": {
                "totalActiveEntities": len(active_users)
                + len(active_projects)
                + len(active_subscriptions),
                "pendingActions": len(pending_subscriptions)
                + len(users_requiring_password_change),
                "lastUpdated": datetime.utcnow().isoformat(),
            },
        }

        response = create_v2_response(dashboard_data)
        logger.log_api_response("GET", "/v2/admin/dashboard/enhanced", 200)
        return response

    except Exception as e:
        logger.error(f"Failed to get enhanced admin dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load enhanced dashboard: {str(e)}",
        )


@enhanced_admin_router.post("/projects")
async def create_project(
    project_data: ProjectEditRequest,
    admin_user: AuthenticatedUser = Depends(require_admin_access),
):
    """Create a new project (admin only)."""
    try:
        logger.log_api_request("POST", "/v2/admin/projects")

        # Log admin action
        await AdminActionLogger.log_admin_action(
            action="CREATE_PROJECT",
            admin_user=admin_user,
            target_resource="project",
            details=project_data.dict(exclude_none=True),
        )

        # Create project data
        project_create_data = {
            "name": project_data.name,
            "description": project_data.description,
            "startDate": project_data.startDate,
            "endDate": project_data.endDate,
            "maxParticipants": project_data.maxParticipants or 50,
            "status": project_data.status or "active",
            "createdBy": f"{admin_user.first_name} {admin_user.last_name}",
        }

        project_create = ProjectCreate(**project_create_data)
        projects_service = service_manager.get_service("projects")
        create_result = await projects_service.create_project(project_create)
        created_project = (
            create_result.get("data")
            if isinstance(create_result, dict)
            else create_result
        )

        response_data = {
            "message": "Project created successfully",
            "project": {
                "id": created_project.id,
                "name": created_project.name,
                "description": created_project.description,
                "startDate": created_project.start_date,
                "endDate": created_project.end_date,
                "maxParticipants": created_project.max_participants,
                "status": created_project.status,
                "createdBy": created_project.created_by,
                "createdAt": (
                    created_project.created_at.isoformat()
                    if created_project.created_at
                    else None
                ),
            },
            "createdBy": {
                "id": admin_user.id,
                "email": admin_user.email,
                "name": f"{admin_user.first_name} {admin_user.last_name}",
            },
        }

        response = create_v2_response(response_data)
        logger.log_api_response("POST", "/v2/admin/projects", 201)
        return response

    except Exception as e:
        logger.error(f"Failed to create project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}",
        )


@enhanced_admin_router.put("/projects/{project_id}")
async def edit_project(
    project_id: str,
    project_data: ProjectEditRequest,
    admin_user: AuthenticatedUser = Depends(require_admin_access),
):
    """Edit project information (admin only)."""
    try:
        logger.log_api_request("PUT", f"/v2/admin/projects/{project_id}")

        # Log admin action
        await AdminActionLogger.log_admin_action(
            action="EDIT_PROJECT",
            admin_user=admin_user,
            target_resource="project",
            target_id=project_id,
            details=project_data.dict(exclude_none=True),
        )

        # Get current project using service registry
        projects_service = service_manager.get_service("projects")
        project_result = await projects_service.get_project_by_id(project_id)
        current_project = (
            project_result.get("data")
            if isinstance(project_result, dict)
            else project_result
        )
        if not current_project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
            )

        # Convert request to ProjectUpdate format
        update_data = {}
        if project_data.name is not None:
            update_data["name"] = project_data.name
        if project_data.description is not None:
            update_data["description"] = project_data.description
        if project_data.startDate is not None:
            update_data["startDate"] = project_data.startDate
        if project_data.endDate is not None:
            update_data["endDate"] = project_data.endDate
        if project_data.maxParticipants is not None:
            update_data["maxParticipants"] = project_data.maxParticipants
        if project_data.status is not None:
            update_data["status"] = project_data.status

        # Create ProjectUpdate object
        project_update = ProjectUpdate(**update_data)

        # Update project using service registry
        update_result = await projects_service.update_project(
            project_id, project_update
        )
        updated_project = (
            update_result.get("data")
            if isinstance(update_result, dict)
            else update_result
        )

        response_data = {
            "message": "Project updated successfully",
            "project": {
                "id": updated_project.id,
                "name": updated_project.name,
                "description": updated_project.description,
                "startDate": updated_project.start_date,
                "endDate": updated_project.end_date,
                "maxParticipants": updated_project.max_participants,
                "status": updated_project.status,
                "updatedAt": (
                    updated_project.updated_at.isoformat()
                    if updated_project.updated_at
                    else None
                ),
            },
            "updatedBy": {
                "id": admin_user.id,
                "email": admin_user.email,
                "name": f"{admin_user.first_name} {admin_user.last_name}",
            },
        }

        response = create_v2_response(response_data)
        logger.log_api_response("PUT", f"/v2/admin/projects/{project_id}", 200)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to edit project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}",
        )


@enhanced_admin_router.get("/analytics")
async def get_admin_analytics(
    admin_user: AuthenticatedUser = Depends(require_admin_access),
):
    """Get detailed analytics for admin dashboard."""
    try:
        logger.log_api_request("GET", "/v2/admin/analytics")

        # Log admin action
        await AdminActionLogger.log_admin_action(
            action="VIEW_ANALYTICS",
            admin_user=admin_user,
            target_resource="analytics",
        )

        # Get all data using service registry
        projects_service = service_manager.get_service("projects")
        subscriptions_service = service_manager.get_service("subscriptions")
        people_service = service_manager.get_service("people")

        projects = await projects_service.get_all_projects()
        subscriptions = await subscriptions_service.get_all_subscriptions()
        people_result = await people_service.get_all_people()
        people = (
            people_result.get("data", [])
            if isinstance(people_result, dict)
            else people_result
        )

        # Calculate monthly trends (last 6 months)
        monthly_data = {}
        for i in range(6):
            month_date = datetime.utcnow() - timedelta(days=30 * i)
            month_key = month_date.strftime("%Y-%m")

            monthly_data[month_key] = {
                "users": len(
                    [p for p in people if p.get("createdAt", "").startswith(month_key)]
                ),
                "projects": len(
                    [
                        p
                        for p in projects
                        if p.get("createdAt", "").startswith(month_key)
                    ]
                ),
                "subscriptions": len(
                    [
                        s
                        for s in subscriptions
                        if s.get("createdAt", "").startswith(month_key)
                    ]
                ),
            }

        # Project status distribution
        project_status_dist = {}
        for project in projects:
            status = project.get("status", "unknown")
            project_status_dist[status] = project_status_dist.get(status, 0) + 1

        # Subscription status distribution
        subscription_status_dist = {}
        for subscription in subscriptions:
            status = subscription.get("status", "unknown")
            subscription_status_dist[status] = (
                subscription_status_dist.get(status, 0) + 1
            )

        analytics_data = {
            "monthlyTrends": monthly_data,
            "distributions": {
                "projectStatus": project_status_dist,
                "subscriptionStatus": subscription_status_dist,
            },
            "topProjects": sorted(
                [
                    {
                        "id": p.get("id"),
                        "name": p.get("name"),
                        "subscriptionCount": len(
                            [
                                s
                                for s in subscriptions
                                if s.get("projectId") == p.get("id")
                            ]
                        ),
                    }
                    for p in projects
                ],
                key=lambda x: x["subscriptionCount"],
                reverse=True,
            )[:5],
            "generatedAt": datetime.utcnow().isoformat(),
        }

        response = create_v2_response(analytics_data)
        logger.log_api_response("GET", "/v2/admin/analytics", 200)
        return response

    except Exception as e:
        logger.error(f"Failed to get admin analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load analytics: {str(e)}",
        )
