"""
Admin authorization middleware for role-based access control (Database-driven version).
"""

import logging
from typing import Optional
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..models.auth import AuthenticatedUser
from ..models.roles import Permission, RoleType
from ..middleware.auth_middleware import get_current_user
from ..services.roles_service import RolesService

logger = logging.getLogger(__name__)
security = HTTPBearer()


class AdminAuthorizationError(HTTPException):
    """Custom exception for admin authorization failures."""

    def __init__(self, detail: str = "Insufficient privileges. Admin access required."):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


# Initialize roles service
roles_service = RolesService()


async def require_admin_access(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """
    Dependency that ensures the current user has admin privileges.

    Args:
        current_user: The authenticated user from auth middleware

    Returns:
        AuthenticatedUser: The admin user

    Raises:
        AdminAuthorizationError: If user is not authenticated or not an admin
    """
    if not current_user:
        logger.warning("Admin access attempted without authentication")
        raise AdminAuthorizationError("Authentication required for admin access")

    # Extract user information
    user_id = None
    user_email = None

    if isinstance(current_user, dict):
        user_id = current_user.get("id", "unknown")
        user_email = current_user.get("email", "unknown")
    else:
        user_id = getattr(current_user, "id", "unknown")
        user_email = getattr(current_user, "email", "unknown")

    # Check if user has admin privileges using roles service
    is_admin = await roles_service.user_is_admin(user_id)

    if not is_admin:
        logger.warning(
            f"Non-admin user {user_email} attempted admin access",
            extra={
                "user_id": user_id,
                "user_email": user_email,
                "attempted_admin_access": True,
            },
        )
        raise AdminAuthorizationError("Insufficient privileges. Admin access required.")

    logger.info(
        f"Admin access granted to {user_email}",
        extra={
            "user_id": user_id,
            "user_email": user_email,
            "admin_access_granted": True,
        },
    )

    return current_user


async def require_super_admin_access(
    current_user: AuthenticatedUser = Depends(require_admin_access),
) -> AuthenticatedUser:
    """
    Dependency that ensures the current user has super admin privileges.

    This is for highly sensitive operations like:
    - Creating/deleting admin users
    - System configuration changes
    - Security settings modifications

    Args:
        current_user: The authenticated admin user

    Returns:
        AuthenticatedUser: The super admin user

    Raises:
        AdminAuthorizationError: If user is not a super admin
    """
    # Extract user information
    user_id = None
    user_email = None

    if isinstance(current_user, dict):
        user_id = current_user.get("id", "unknown")
        user_email = current_user.get("email", "unknown")
    else:
        user_id = getattr(current_user, "id", "unknown")
        user_email = getattr(current_user, "email", "unknown")

    # Check if user has super admin privileges using roles service
    is_super_admin = await roles_service.user_is_super_admin(user_id)

    if not is_super_admin:
        logger.warning(
            f"Admin user {user_email} attempted super admin access",
            extra={
                "user_id": user_id,
                "user_email": user_email,
                "attempted_super_admin_access": True,
            },
        )
        raise AdminAuthorizationError(
            "Insufficient privileges. Super admin access required."
        )

    logger.info(
        f"Super admin access granted to {user_email}",
        extra={
            "user_id": user_id,
            "user_email": user_email,
            "super_admin_access_granted": True,
        },
    )

    return current_user


async def require_permission(permission: Permission):
    """
    Dependency factory that creates a dependency to check for specific permissions.

    Args:
        permission: The required permission

    Returns:
        Dependency function that checks for the permission
    """

    async def permission_checker(
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        if not current_user:
            raise AdminAuthorizationError("Authentication required")

        # Extract user information
        user_id = None
        user_email = None

        if isinstance(current_user, dict):
            user_id = current_user.get("id", "unknown")
            user_email = current_user.get("email", "unknown")
        else:
            user_id = getattr(current_user, "id", "unknown")
            user_email = getattr(current_user, "email", "unknown")

        # Check if user has the required permission
        has_permission = roles_service.user_has_permission(user_id, permission)

        if not has_permission:
            logger.warning(
                f"User {user_email} attempted access without permission {permission.value}",
                extra={
                    "user_id": user_id,
                    "user_email": user_email,
                    "required_permission": permission.value,
                    "permission_denied": True,
                },
            )
            raise AdminAuthorizationError(
                f"Insufficient privileges. Permission '{permission.value}' required."
            )

        logger.debug(
            f"Permission {permission.value} granted to {user_email}",
            extra={
                "user_id": user_id,
                "user_email": user_email,
                "granted_permission": permission.value,
            },
        )

        return current_user

    return permission_checker


async def get_admin_user_info(
    current_user: AuthenticatedUser = Depends(require_admin_access),
) -> dict:
    """
    Get detailed admin user information for audit logging.

    Args:
        current_user: The authenticated admin user

    Returns:
        dict: Admin user information for logging
    """
    # Extract user information
    if isinstance(current_user, dict):
        user_email = current_user.get("email", "unknown")
        user_id = current_user.get("id", "unknown")
        first_name = current_user.get("first_name", "")
        last_name = current_user.get("last_name", "")
    else:
        user_email = getattr(current_user, "email", "unknown")
        user_id = getattr(current_user, "id", "unknown")
        first_name = getattr(current_user, "first_name", "")
        last_name = getattr(current_user, "last_name", "")

    # Get user roles from database
    user_roles = await roles_service.get_user_roles(user_id)
    is_super_admin = await roles_service.user_is_super_admin(user_id)

    return {
        "admin_user_id": user_id,
        "admin_user_email": user_email,
        "admin_user_name": f"{first_name} {last_name}".strip(),
        "is_super_admin": is_super_admin,
        "roles": [role.value for role in user_roles],
    }


class AdminActionLogger:
    """Utility class for logging admin actions."""

    @staticmethod
    async def log_admin_action(
        action: str,
        admin_user: AuthenticatedUser,
        target_resource: Optional[str] = None,
        target_id: Optional[str] = None,
        details: Optional[dict] = None,
        success: bool = True,
    ):
        """
        Log an admin action for audit purposes.

        Args:
            action: The action performed (e.g., "CREATE_USER", "DELETE_PROJECT")
            admin_user: The admin user who performed the action
            target_resource: The type of resource affected (e.g., "user", "project")
            target_id: The ID of the affected resource
            details: Additional details about the action
            success: Whether the action was successful
        """
        # Extract user information
        if isinstance(admin_user, dict):
            admin_user_id = admin_user.get("id", "unknown")
            admin_user_email = admin_user.get("email", "unknown")
        else:
            admin_user_id = getattr(admin_user, "id", "unknown")
            admin_user_email = getattr(admin_user, "email", "unknown")

        # Get user roles for audit trail
        user_roles = roles_service.get_user_roles(admin_user_id)

        log_data = {
            "action": action,
            "admin_user_id": admin_user_id,
            "admin_user_email": admin_user_email,
            "admin_user_roles": [role.value for role in user_roles],
            "target_resource": target_resource,
            "target_id": target_id,
            "success": success,
            "timestamp": (
                logger._get_timestamp() if hasattr(logger, "_get_timestamp") else None
            ),
        }

        if details:
            log_data.update(details)

        if success:
            logger.info(f"Admin action: {action}", extra=log_data)
        else:
            logger.error(f"Failed admin action: {action}", extra=log_data)

        # TODO: Store in database for audit trail
        # This could be implemented as a separate audit log table


# Convenience functions for common admin checks
async def verify_admin_or_self_access(
    target_user_id: str, current_user: AuthenticatedUser = Depends(get_current_user)
) -> AuthenticatedUser:
    """
    Verify that the current user is either an admin or accessing their own data.

    Args:
        target_user_id: The ID of the user being accessed
        current_user: The authenticated user

    Returns:
        AuthenticatedUser: The authenticated user

    Raises:
        AdminAuthorizationError: If user cannot access the target user's data
    """
    if not current_user:
        raise AdminAuthorizationError("Authentication required")

    # Extract user information
    if isinstance(current_user, dict):
        user_id = current_user.get("id", "unknown")
        user_email = current_user.get("email", "unknown")
    else:
        user_id = getattr(current_user, "id", "unknown")
        user_email = getattr(current_user, "email", "unknown")

    # Check if user is admin or accessing their own data
    is_admin = await roles_service.user_is_admin(user_id)

    if is_admin or user_id == target_user_id:
        return current_user

    logger.warning(
        f"User {user_email} attempted unauthorized access to user {target_user_id}",
        extra={
            "user_id": user_id,
            "target_user_id": target_user_id,
            "unauthorized_access_attempt": True,
        },
    )

    raise AdminAuthorizationError(
        "Insufficient privileges. You can only access your own data or admin access is required."
    )


# Backward compatibility functions
async def is_user_admin(user_id: str) -> bool:
    """Check if a user is an admin (backward compatibility)."""
    return await roles_service.user_is_admin(user_id)


async def is_user_super_admin(user_id: str) -> bool:
    """Check if a user is a super admin (backward compatibility)."""
    return await roles_service.user_is_super_admin(user_id)
