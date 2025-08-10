"""
Role-based access control models.
"""

from enum import Enum
from typing import List, Optional, Set
from pydantic import BaseModel, Field
from datetime import datetime


class RoleType(str, Enum):
    """Available role types in the system."""

    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"
    MODERATOR = "moderator"


class Permission(str, Enum):
    """Available permissions in the system."""

    # User permissions
    READ_OWN_PROFILE = "read_own_profile"
    UPDATE_OWN_PROFILE = "update_own_profile"

    # Project permissions
    READ_PROJECTS = "read_projects"
    CREATE_PROJECT = "create_project"
    UPDATE_OWN_PROJECT = "update_own_project"
    DELETE_OWN_PROJECT = "delete_own_project"

    # Admin permissions
    READ_ALL_USERS = "read_all_users"
    UPDATE_ANY_USER = "update_any_user"
    DELETE_ANY_USER = "delete_any_user"
    READ_ALL_PROJECTS = "read_all_projects"
    UPDATE_ANY_PROJECT = "update_any_project"
    DELETE_ANY_PROJECT = "delete_any_project"

    # Super admin permissions
    MANAGE_ROLES = "manage_roles"
    MANAGE_ADMINS = "manage_admins"
    SYSTEM_CONFIG = "system_config"
    VIEW_AUDIT_LOGS = "view_audit_logs"


class Role(BaseModel):
    """Role model with associated permissions."""

    role_type: RoleType
    permissions: Set[Permission]
    description: str
    is_active: bool = True


class UserRole(BaseModel):
    """User role assignment model."""

    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email for reference")
    role_type: RoleType = Field(..., description="Assigned role")
    assigned_by: str = Field(..., description="ID of user who assigned this role")
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(None, description="Role expiration date")
    is_active: bool = Field(True, description="Whether the role assignment is active")
    notes: Optional[str] = Field(
        None, description="Additional notes about the role assignment"
    )


class RoleAssignmentRequest(BaseModel):
    """Request model for role assignment."""

    user_email: str = Field(..., description="Email of user to assign role to")
    role_type: RoleType = Field(..., description="Role to assign")
    expires_at: Optional[datetime] = Field(None, description="Optional expiration date")
    notes: Optional[str] = Field(None, description="Optional notes")


class RoleAssignmentResponse(BaseModel):
    """Response model for role assignment operations."""

    success: bool
    message: str
    user_role: Optional[UserRole] = None


# Default role configurations
DEFAULT_ROLES: dict[RoleType, Role] = {
    RoleType.USER: Role(
        role_type=RoleType.USER,
        permissions={
            Permission.READ_OWN_PROFILE,
            Permission.UPDATE_OWN_PROFILE,
            Permission.READ_PROJECTS,
            Permission.CREATE_PROJECT,
            Permission.UPDATE_OWN_PROJECT,
            Permission.DELETE_OWN_PROJECT,
        },
        description="Standard user with basic permissions",
    ),
    RoleType.MODERATOR: Role(
        role_type=RoleType.MODERATOR,
        permissions={
            Permission.READ_OWN_PROFILE,
            Permission.UPDATE_OWN_PROFILE,
            Permission.READ_PROJECTS,
            Permission.CREATE_PROJECT,
            Permission.UPDATE_OWN_PROJECT,
            Permission.DELETE_OWN_PROJECT,
            Permission.READ_ALL_PROJECTS,
            Permission.UPDATE_ANY_PROJECT,
        },
        description="Moderator with project management permissions",
    ),
    RoleType.ADMIN: Role(
        role_type=RoleType.ADMIN,
        permissions={
            Permission.READ_OWN_PROFILE,
            Permission.UPDATE_OWN_PROFILE,
            Permission.READ_PROJECTS,
            Permission.CREATE_PROJECT,
            Permission.UPDATE_OWN_PROJECT,
            Permission.DELETE_OWN_PROJECT,
            Permission.READ_ALL_USERS,
            Permission.UPDATE_ANY_USER,
            Permission.READ_ALL_PROJECTS,
            Permission.UPDATE_ANY_PROJECT,
            Permission.DELETE_ANY_PROJECT,
        },
        description="Administrator with user and project management permissions",
    ),
    RoleType.SUPER_ADMIN: Role(
        role_type=RoleType.SUPER_ADMIN,
        permissions=set(Permission),  # All permissions
        description="Super administrator with full system access",
    ),
}


def get_role_permissions(role_type: RoleType) -> Set[Permission]:
    """Get permissions for a specific role type."""
    return DEFAULT_ROLES.get(role_type, DEFAULT_ROLES[RoleType.USER]).permissions


def has_permission(user_roles: List[RoleType], required_permission: Permission) -> bool:
    """Check if user has a specific permission based on their roles."""
    for role_type in user_roles:
        if required_permission in get_role_permissions(role_type):
            return True
    return False


def is_admin_role(role_type: RoleType) -> bool:
    """Check if a role type is considered an admin role."""
    return role_type in [RoleType.ADMIN, RoleType.SUPER_ADMIN]


def is_super_admin_role(role_type: RoleType) -> bool:
    """Check if a role type is super admin."""
    return role_type == RoleType.SUPER_ADMIN
