"""
Role management API endpoints.
"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from ..models.auth import AuthenticatedUser
from ..models.roles import (
    RoleType,
    Permission,
    UserRole,
    RoleAssignmentRequest,
    RoleAssignmentResponse,
    DEFAULT_ROLES,
)
from ..middleware.admin_middleware_v2 import (
    require_super_admin_access,
    require_admin_access,
    require_permission,
    get_admin_user_info,
    AdminActionLogger,
)
from ..services.roles_service import RolesService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/roles", tags=["roles"])

# Initialize services
roles_service = RolesService()
action_logger = AdminActionLogger()


@router.get("/", summary="List all available roles and permissions")
async def list_roles_and_permissions(
    current_user: AuthenticatedUser = Depends(require_admin_access),
):
    """
    Get information about all available roles and their permissions.
    Requires admin access.
    """
    try:
        roles_info = {}
        for role_type, role in DEFAULT_ROLES.items():
            roles_info[role_type.value] = {
                "description": role.description,
                "permissions": [perm.value for perm in role.permissions],
                "is_admin_role": role_type in [RoleType.ADMIN, RoleType.SUPER_ADMIN],
            }

        return {
            "success": True,
            "roles": roles_info,
            "available_permissions": [perm.value for perm in Permission],
        }

    except Exception as e:
        logger.error(f"Error listing roles: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve roles information",
        )


@router.get("/user/{user_id}", summary="Get user roles")
async def get_user_roles(
    user_id: str, current_user: AuthenticatedUser = Depends(require_admin_access)
) -> List[UserRole]:
    """
    Get detailed role information for a specific user.
    Requires admin access.
    """
    try:
        user_roles = await roles_service.list_user_roles(user_id)

        # Log the admin action
        await action_logger.log_admin_action(
            action="VIEW_USER_ROLES",
            admin_user=current_user,
            target_resource="user",
            target_id=user_id,
            success=True,
        )

        return user_roles

    except Exception as e:
        logger.error(f"Error getting user roles for {user_id}: {str(e)}")

        await action_logger.log_admin_action(
            action="VIEW_USER_ROLES",
            admin_user=current_user,
            target_resource="user",
            target_id=user_id,
            details={"error": str(e)},
            success=False,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user roles",
        )


@router.post("/assign", summary="Assign role to user")
async def assign_role(
    request: RoleAssignmentRequest,
    current_user: AuthenticatedUser = Depends(require_super_admin_access),
) -> RoleAssignmentResponse:
    """
    Assign a role to a user.
    Requires super admin access.
    """
    try:
        # Extract admin user ID
        admin_user_id = None
        if isinstance(current_user, dict):
            admin_user_id = current_user.get("id", "unknown")
        else:
            admin_user_id = getattr(current_user, "id", "unknown")

        # Assign the role
        response = await roles_service.assign_role(request, admin_user_id)

        # Log the admin action
        await action_logger.log_admin_action(
            action="ASSIGN_ROLE",
            admin_user=current_user,
            target_resource="user",
            target_id=request.user_email,
            details={
                "assigned_role": request.role_type.value,
                "expires_at": (
                    request.expires_at.isoformat() if request.expires_at else None
                ),
                "notes": request.notes,
            },
            success=response.success,
        )

        return response

    except Exception as e:
        logger.error(f"Error assigning role: {str(e)}")

        await action_logger.log_admin_action(
            action="ASSIGN_ROLE",
            admin_user=current_user,
            target_resource="user",
            target_id=request.user_email,
            details={"error": str(e), "attempted_role": request.role_type.value},
            success=False,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign role: {str(e)}",
        )


@router.post("/revoke", summary="Revoke role from user")
async def revoke_role(
    user_email: str,
    role_type: RoleType,
    current_user: AuthenticatedUser = Depends(require_super_admin_access),
) -> RoleAssignmentResponse:
    """
    Revoke a role from a user.
    Requires super admin access.
    """
    try:
        # Extract admin user ID
        admin_user_id = None
        if isinstance(current_user, dict):
            admin_user_id = current_user.get("id", "unknown")
        else:
            admin_user_id = getattr(current_user, "id", "unknown")

        # Revoke the role
        response = await roles_service.revoke_role(user_email, role_type, admin_user_id)

        # Log the admin action
        await action_logger.log_admin_action(
            action="REVOKE_ROLE",
            admin_user=current_user,
            target_resource="user",
            target_id=user_email,
            details={"revoked_role": role_type.value},
            success=response.success,
        )

        return response

    except Exception as e:
        logger.error(f"Error revoking role: {str(e)}")

        await action_logger.log_admin_action(
            action="REVOKE_ROLE",
            admin_user=current_user,
            target_resource="user",
            target_id=user_email,
            details={"error": str(e), "attempted_revoke_role": role_type.value},
            success=False,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke role: {str(e)}",
        )


@router.get("/my-roles", summary="Get current user's roles")
async def get_my_roles(
    current_user: AuthenticatedUser = Depends(require_admin_access),
) -> List[UserRole]:
    """
    Get the current user's role information.
    Requires authentication.
    """
    try:
        # Extract user ID
        user_id = None
        if isinstance(current_user, dict):
            user_id = current_user.get("id", "unknown")
        else:
            user_id = getattr(current_user, "id", "unknown")

        user_roles = await roles_service.list_user_roles(user_id)
        return user_roles

    except Exception as e:
        logger.error(f"Error getting current user roles: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve your roles",
        )


@router.get(
    "/check-permission/{permission}", summary="Check if current user has permission"
)
async def check_permission(
    permission: Permission,
    current_user: AuthenticatedUser = Depends(require_admin_access),
) -> dict:
    """
    Check if the current user has a specific permission.
    Requires authentication.
    """
    try:
        # Extract user ID
        user_id = None
        if isinstance(current_user, dict):
            user_id = current_user.get("id", "unknown")
        else:
            user_id = getattr(current_user, "id", "unknown")

        has_permission = await roles_service.user_has_permission(user_id, permission)

        return {"permission": permission.value, "has_permission": has_permission}

    except Exception as e:
        logger.error(f"Error checking permission: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check permission",
        )


@router.post("/migrate-existing-admins", summary="Migrate hardcoded admins to database")
async def migrate_existing_admins(
    current_user: AuthenticatedUser = Depends(require_super_admin_access),
) -> dict:
    """
    One-time migration endpoint to move hardcoded admin emails to database roles.
    Requires super admin access.
    """
    try:
        # Extract admin user ID
        admin_user_id = None
        if isinstance(current_user, dict):
            admin_user_id = current_user.get("id", "unknown")
        else:
            admin_user_id = getattr(current_user, "id", "unknown")

        # Hardcoded admin emails to migrate
        hardcoded_admins = [
            {"email": "admin@cbba.cloud.org.bo", "role": RoleType.SUPER_ADMIN},
            {"email": "admin@awsugcbba.org", "role": RoleType.SUPER_ADMIN},
            {
                "email": "sergio.rodriguez.inclan@gmail.com",
                "role": RoleType.SUPER_ADMIN,
            },
        ]

        migration_results = []

        for admin in hardcoded_admins:
            request = RoleAssignmentRequest(
                user_email=admin["email"],
                role_type=admin["role"],
                notes="Migrated from hardcoded admin list",
            )

            response = await roles_service.assign_role(request, admin_user_id)
            migration_results.append(
                {
                    "email": admin["email"],
                    "role": admin["role"].value,
                    "success": response.success,
                    "message": response.message,
                }
            )

        # Log the migration action
        await action_logger.log_admin_action(
            action="MIGRATE_HARDCODED_ADMINS",
            admin_user=current_user,
            target_resource="system",
            details={"migration_results": migration_results},
            success=True,
        )

        return {
            "success": True,
            "message": "Admin migration completed",
            "results": migration_results,
        }

    except Exception as e:
        logger.error(f"Error migrating admins: {str(e)}")

        await action_logger.log_admin_action(
            action="MIGRATE_HARDCODED_ADMINS",
            admin_user=current_user,
            target_resource="system",
            details={"error": str(e)},
            success=False,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to migrate admins: {str(e)}",
        )
