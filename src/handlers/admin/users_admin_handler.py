"""
Admin Users Handler - Domain-specific user management for administrators.

This module provides comprehensive user management functionality for admin users:
- User listing with pagination and filtering
- User creation, editing, and deletion
- Bulk user operations (activate, deactivate, etc.)
- User lifecycle management
- Admin audit logging for all user operations

Part of the domain-driven admin handler architecture.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field

from ...models.person import PersonUpdate, PersonResponse
from ...models.auth import AuthenticatedUser
from ...services.service_registry_manager import service_manager
from ...middleware.admin_middleware_v2 import (
    require_admin_access,
    require_super_admin_access,
    AdminActionLogger,
)
from ...utils.response_models import create_v2_response
from ...utils.logging_config import get_handler_logger

logger = get_handler_logger(__name__)

# Create router for admin user management
users_admin_router = APIRouter(prefix="/v2/admin", tags=["Admin - User Management"])


class UserEditRequest(BaseModel):
    """Request model for editing user information."""

    firstName: Optional[str] = Field(None, description="User's first name")
    lastName: Optional[str] = Field(None, description="User's last name")
    email: Optional[str] = Field(None, description="User's email address")
    phone: Optional[str] = Field(None, description="User's phone number")
    dateOfBirth: Optional[str] = Field(None, description="User's date of birth")
    isActive: Optional[bool] = Field(None, description="User active status")
    isAdmin: Optional[bool] = Field(None, description="User admin status")
    requirePasswordChange: Optional[bool] = Field(
        None, description="Require password change on next login"
    )
    address: Optional[Dict[str, Any]] = Field(None, description="User's address")


class BulkActionRequest(BaseModel):
    """Request model for bulk operations."""

    userIds: List[str] = Field(..., description="List of user IDs to perform action on")
    action: str = Field(
        ...,
        description="Action to perform (activate, deactivate, require_password_change)",
    )
    reason: Optional[str] = Field(None, description="Reason for the bulk action")


@users_admin_router.get("/users")
async def list_users(
    admin_user: AuthenticatedUser = Depends(require_admin_access),
    page: int = 1,
    limit: int = 25,
    status: Optional[str] = None,
    search: Optional[str] = None,
):
    """List all users with pagination and filtering (admin only)."""
    try:
        logger.log_api_request("GET", "/v2/admin/users")

        # Log admin action
        await AdminActionLogger.log_admin_action(
            action="LIST_USERS",
            admin_user=admin_user,
            target_resource="users",
            details={"page": page, "limit": limit, "status": status, "search": search},
        )

        people_service = service_manager.get_service("people")
        if not people_service:
            raise HTTPException(status_code=503, detail="People service not available")

        # Build filters for the people service
        filters = {}
        if status:
            if status == "active":
                filters["isActive"] = True
            elif status == "inactive":
                filters["isActive"] = False

        # Get users with pagination
        if search:
            # Use search functionality
            users_result = await people_service.advanced_search_users(
                query=search,
                filters=filters if filters else None,
                sort_by="created_at",
                sort_order="desc",
                page=page,
                limit=limit,
            )
        else:
            # Get all users with filters
            all_users = await people_service.get_all_people()
            users_list = (
                all_users.get("data", []) if isinstance(all_users, dict) else all_users
            )

            # Apply filters
            if filters:
                if "isActive" in filters:
                    users_list = [
                        u
                        for u in users_list
                        if u.get("isActive") == filters["isActive"]
                    ]

            # Apply pagination
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            paginated_users = users_list[start_idx:end_idx]

            users_result = {
                "users": paginated_users,
                "total": len(users_list),
                "page": page,
                "limit": limit,
                "total_pages": (len(users_list) + limit - 1) // limit,
            }

        # Format response data
        response_data = {
            "users": users_result.get("users", []),
            "pagination": {
                "page": users_result.get("page", page),
                "limit": users_result.get("limit", limit),
                "total": users_result.get("total", 0),
                "total_pages": users_result.get("total_pages", 0),
            },
            "filters": {"status": status, "search": search},
        }

        response = create_v2_response(response_data)
        logger.log_api_response("GET", "/v2/admin/users", 200)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list users: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve users")


@users_admin_router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    admin_user: AuthenticatedUser = Depends(require_admin_access),
):
    """Get specific user details (admin only)."""
    try:
        logger.log_api_request("GET", f"/v2/admin/users/{user_id}")

        # Log admin action
        await AdminActionLogger.log_admin_action(
            action="VIEW_USER",
            admin_user=admin_user,
            target_resource="user",
            target_id=user_id,
        )

        people_service = service_manager.get_service("people")
        if not people_service:
            raise HTTPException(status_code=503, detail="People service not available")

        user = await people_service.get_person_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Format user data for admin view
        formatted_user = {
            "id": user.get("id"),
            "firstName": user.get("firstName"),
            "lastName": user.get("lastName"),
            "email": user.get("email"),
            "phone": user.get("phone"),
            "dateOfBirth": user.get("dateOfBirth"),
            "address": user.get("address", {}),
            "isActive": user.get("isActive", True),
            "isAdmin": user.get("isAdmin", False),
            "requirePasswordChange": user.get("requirePasswordChange", False),
            "createdAt": user.get("createdAt"),
            "updatedAt": user.get("updatedAt"),
        }

        response = create_v2_response(formatted_user)
        logger.log_api_response("GET", f"/v2/admin/users/{user_id}", 200)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user")


@users_admin_router.post("/users")
async def create_user(
    user_data: dict,
    admin_user: AuthenticatedUser = Depends(require_admin_access),
):
    """Create new user (admin only)."""
    try:
        logger.log_api_request("POST", "/v2/admin/users")

        # Log admin action
        await AdminActionLogger.log_admin_action(
            action="CREATE_USER",
            admin_user=admin_user,
            target_resource="user",
            details={"email": user_data.get("email")},
        )

        people_service = service_manager.get_service("people")
        if not people_service:
            raise HTTPException(status_code=503, detail="People service not available")

        # Validate required fields
        required_fields = ["firstName", "lastName", "email"]
        for field in required_fields:
            if not user_data.get(field):
                raise HTTPException(
                    status_code=400, detail=f"Missing required field: {field}"
                )

        # Check if user already exists
        existing_user = await people_service.get_person_by_email(user_data["email"])
        if existing_user:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )

        # Create the user
        result = await people_service.create_person(user_data)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create user")

        response_data = {
            "message": "User created successfully",
            "user": result,
            "created_by": admin_user.id,
            "created_at": datetime.utcnow().isoformat(),
        }

        response = create_v2_response(response_data)
        logger.log_api_response("POST", "/v2/admin/users", 201)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create user: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create user")


@users_admin_router.put("/users/{user_id}")
async def edit_user(
    user_id: str,
    user_data: UserEditRequest,
    admin_user: AuthenticatedUser = Depends(require_admin_access),
):
    """Edit user information (admin only)."""
    try:
        logger.log_api_request("PUT", f"/v2/admin/users/{user_id}")

        # Log admin action
        await AdminActionLogger.log_admin_action(
            action="EDIT_USER",
            admin_user=admin_user,
            target_resource="user",
            target_id=user_id,
            details=user_data.dict(exclude_unset=True),
        )

        people_service = service_manager.get_service("people")
        if not people_service:
            raise HTTPException(status_code=503, detail="People service not available")

        # Check if user exists
        existing_user = await people_service.get_person_by_id(user_id)
        if not existing_user:
            raise HTTPException(status_code=404, detail="User not found")

        # Prepare update data
        update_data = user_data.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No update data provided")

        # Prevent non-super-admins from modifying admin users
        if existing_user.get("isAdmin") and not admin_user.is_super_admin:
            # Remove admin-only fields
            admin_only_fields = ["isAdmin", "isActive"]
            for field in admin_only_fields:
                if field in update_data:
                    del update_data[field]

        # Update the user
        result = await people_service.update_person(user_id, update_data)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to update user")

        response_data = {
            "message": "User updated successfully",
            "user": result,
            "updated_by": admin_user.id,
            "updated_at": datetime.utcnow().isoformat(),
            "changes": update_data,
        }

        response = create_v2_response(response_data)
        logger.log_api_response("PUT", f"/v2/admin/users/{user_id}", 200)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update user")


@users_admin_router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin_user: AuthenticatedUser = Depends(require_super_admin_access),
):
    """Delete user (super admin only)."""
    try:
        logger.log_api_request("DELETE", f"/v2/admin/users/{user_id}")

        # Log admin action
        await AdminActionLogger.log_admin_action(
            action="DELETE_USER",
            admin_user=admin_user,
            target_resource="user",
            target_id=user_id,
        )

        people_service = service_manager.get_service("people")
        if not people_service:
            raise HTTPException(status_code=503, detail="People service not available")

        # Check if user exists
        existing_user = await people_service.get_person_by_id(user_id)
        if not existing_user:
            raise HTTPException(status_code=404, detail="User not found")

        # Prevent deletion of admin users by non-super-admins
        if existing_user.get("isAdmin") and not admin_user.is_super_admin:
            raise HTTPException(status_code=403, detail="Cannot delete admin users")

        # Delete the user
        result = await people_service.delete_person(user_id)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to delete user")

        response_data = {
            "message": "User deleted successfully",
            "user_id": user_id,
            "deleted_by": admin_user.id,
            "deleted_at": datetime.utcnow().isoformat(),
        }

        response = create_v2_response(response_data)
        logger.log_api_response("DELETE", f"/v2/admin/users/{user_id}", 200)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete user")


@users_admin_router.post("/users/bulk-action")
async def bulk_user_action(
    bulk_request: BulkActionRequest,
    admin_user: AuthenticatedUser = Depends(require_super_admin_access),
):
    """Perform bulk actions on multiple users (super admin only)."""
    try:
        logger.log_api_request("POST", "/v2/admin/users/bulk-action")

        # Log admin action
        await AdminActionLogger.log_admin_action(
            action="BULK_USER_ACTION",
            admin_user=admin_user,
            target_resource="users",
            details={
                "action": bulk_request.action,
                "user_count": len(bulk_request.userIds),
                "reason": bulk_request.reason,
            },
        )

        people_service = service_manager.get_service("people")
        if not people_service:
            raise HTTPException(status_code=503, detail="People service not available")

        # Validate action
        valid_actions = ["activate", "deactivate", "require_password_change"]
        if bulk_request.action not in valid_actions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action. Must be one of: {valid_actions}",
            )

        # Process each user
        results = []
        for user_id in bulk_request.userIds:
            try:
                # Check if user exists
                user = await people_service.get_person_by_id(user_id)
                if not user:
                    results.append(
                        {
                            "user_id": user_id,
                            "status": "error",
                            "message": "User not found",
                        }
                    )
                    continue

                # Prepare update based on action
                update_data = {}
                if bulk_request.action == "activate":
                    update_data = {"isActive": True}
                elif bulk_request.action == "deactivate":
                    update_data = {"isActive": False}
                elif bulk_request.action == "require_password_change":
                    update_data = {"requirePasswordChange": True}

                # Update the user
                result = await people_service.update_person(user_id, update_data)
                if result:
                    results.append(
                        {
                            "user_id": user_id,
                            "status": "success",
                            "message": f"Action '{bulk_request.action}' applied",
                        }
                    )
                else:
                    results.append(
                        {
                            "user_id": user_id,
                            "status": "error",
                            "message": "Update failed",
                        }
                    )

            except Exception as e:
                results.append(
                    {"user_id": user_id, "status": "error", "message": str(e)}
                )

        # Summary
        success_count = len([r for r in results if r["status"] == "success"])
        error_count = len([r for r in results if r["status"] == "error"])

        response_data = {
            "message": f"Bulk action '{bulk_request.action}' completed",
            "summary": {
                "total": len(bulk_request.userIds),
                "success": success_count,
                "errors": error_count,
            },
            "results": results,
            "action": bulk_request.action,
            "reason": bulk_request.reason,
            "performed_by": admin_user.id,
            "performed_at": datetime.utcnow().isoformat(),
        }

        response = create_v2_response(response_data)
        logger.log_api_response("POST", "/v2/admin/users/bulk-action", 200)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to perform bulk action: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to perform bulk action")
