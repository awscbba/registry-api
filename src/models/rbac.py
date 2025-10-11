"""
Enterprise Role-Based Access Control (RBAC) models.
Implements comprehensive permission system with hierarchical roles.
"""

from enum import Enum
from typing import List, Optional, Set, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class Permission(str, Enum):
    """System permissions with granular access control."""

    # User Management Permissions
    USER_READ_OWN = "user:read:own"
    USER_UPDATE_OWN = "user:update:own"
    USER_DELETE_OWN = "user:delete:own"
    USER_READ_ALL = "user:read:all"
    USER_CREATE = "user:create"
    USER_UPDATE_ALL = "user:update:all"
    USER_DELETE_ALL = "user:delete:all"
    USER_ADMIN = "user:admin"

    # Project Management Permissions
    PROJECT_READ_PUBLIC = "project:read:public"
    PROJECT_READ_ALL = "project:read:all"
    PROJECT_CREATE = "project:create"
    PROJECT_UPDATE_OWN = "project:update:own"
    PROJECT_UPDATE_ALL = "project:update:all"
    PROJECT_DELETE_OWN = "project:delete:own"
    PROJECT_DELETE_ALL = "project:delete:all"
    PROJECT_ADMIN = "project:admin"

    # Subscription Management Permissions
    SUBSCRIPTION_READ_OWN = "subscription:read:own"
    SUBSCRIPTION_READ_ALL = "subscription:read:all"
    SUBSCRIPTION_CREATE = "subscription:create"
    SUBSCRIPTION_UPDATE_OWN = "subscription:update:own"
    SUBSCRIPTION_UPDATE_ALL = "subscription:update:all"
    SUBSCRIPTION_DELETE_OWN = "subscription:delete:own"
    SUBSCRIPTION_DELETE_ALL = "subscription:delete:all"
    SUBSCRIPTION_ADMIN = "subscription:admin"

    # System Administration Permissions
    SYSTEM_CONFIG = "system:config"
    SYSTEM_AUDIT = "system:audit"
    SYSTEM_MONITOR = "system:monitor"
    SYSTEM_BACKUP = "system:backup"

    # Role Management Permissions
    ROLE_READ = "role:read"
    ROLE_ASSIGN = "role:assign"
    ROLE_REVOKE = "role:revoke"
    ROLE_ADMIN = "role:admin"

    # Security Permissions
    SECURITY_AUDIT = "security:audit"
    SECURITY_ADMIN = "security:admin"


class RoleType(str, Enum):
    """System role types with clear hierarchy."""

    GUEST = "guest"
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"
    AUDITOR = "auditor"
    SYSTEM = "system"


class Role(BaseModel):
    """Role definition with permissions and metadata."""

    role_type: RoleType
    name: str
    description: str
    permissions: Set[Permission]
    is_active: bool = True
    is_system_role: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserRole(BaseModel):
    """User role assignment with audit trail."""

    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    user_id: str
    user_email: str
    role_type: RoleType
    assigned_by: str
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    is_active: bool = True
    notes: Optional[str] = None

    # Audit fields
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RoleAssignmentRequest(BaseModel):
    """Request to assign role to user."""

    user_email: str
    role_type: RoleType
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None


class RoleAssignmentResponse(BaseModel):
    """Response for role assignment operations."""

    success: bool
    message: str
    user_role: Optional[UserRole] = None
    errors: List[str] = Field(default_factory=list)


class PermissionCheck(BaseModel):
    """Permission check request."""

    user_id: str
    permission: Permission
    resource_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class PermissionResult(BaseModel):
    """Permission check result."""

    has_permission: bool
    reason: str
    checked_at: datetime = Field(default_factory=datetime.utcnow)


# Default role configurations with enterprise-grade permissions
DEFAULT_ROLES: Dict[RoleType, Role] = {
    RoleType.GUEST: Role(
        role_type=RoleType.GUEST,
        name="Guest User",
        description="Anonymous user with minimal read access",
        permissions={
            Permission.PROJECT_READ_PUBLIC,
        },
    ),
    RoleType.USER: Role(
        role_type=RoleType.USER,
        name="Standard User",
        description="Authenticated user with basic permissions",
        permissions={
            Permission.USER_READ_OWN,
            Permission.USER_UPDATE_OWN,
            Permission.PROJECT_READ_PUBLIC,
            Permission.PROJECT_READ_ALL,
            Permission.PROJECT_CREATE,
            Permission.PROJECT_UPDATE_OWN,
            Permission.PROJECT_DELETE_OWN,
            Permission.SUBSCRIPTION_READ_OWN,
            Permission.SUBSCRIPTION_CREATE,
            Permission.SUBSCRIPTION_UPDATE_OWN,
            Permission.SUBSCRIPTION_DELETE_OWN,
        },
    ),
    RoleType.MODERATOR: Role(
        role_type=RoleType.MODERATOR,
        name="Content Moderator",
        description="User with project moderation capabilities",
        permissions={
            Permission.USER_READ_OWN,
            Permission.USER_UPDATE_OWN,
            Permission.PROJECT_READ_ALL,
            Permission.PROJECT_CREATE,
            Permission.PROJECT_UPDATE_ALL,
            Permission.PROJECT_DELETE_OWN,
            Permission.SUBSCRIPTION_READ_ALL,
            Permission.SUBSCRIPTION_CREATE,
            Permission.SUBSCRIPTION_UPDATE_ALL,
            Permission.SUBSCRIPTION_DELETE_OWN,
            Permission.SYSTEM_CONFIG,  # Required for admin endpoint access
        },
    ),
    RoleType.ADMIN: Role(
        role_type=RoleType.ADMIN,
        name="Administrator",
        description="System administrator with user and content management",
        permissions={
            Permission.USER_READ_ALL,
            Permission.USER_CREATE,
            Permission.USER_UPDATE_ALL,
            Permission.USER_ADMIN,
            Permission.PROJECT_READ_ALL,
            Permission.PROJECT_CREATE,
            Permission.PROJECT_UPDATE_ALL,
            Permission.PROJECT_DELETE_ALL,
            Permission.PROJECT_ADMIN,
            Permission.SUBSCRIPTION_READ_ALL,
            Permission.SUBSCRIPTION_CREATE,
            Permission.SUBSCRIPTION_UPDATE_ALL,
            Permission.SUBSCRIPTION_DELETE_ALL,
            Permission.SUBSCRIPTION_ADMIN,
            Permission.ROLE_READ,
            Permission.ROLE_ASSIGN,
            Permission.SYSTEM_CONFIG,  # Required for admin endpoint access
            Permission.SYSTEM_MONITOR,
            Permission.SYSTEM_AUDIT,  # Required for admin dashboard access
            Permission.SECURITY_AUDIT,  # Required for admin security operations
        },
    ),
    RoleType.SUPER_ADMIN: Role(
        role_type=RoleType.SUPER_ADMIN,
        name="Super Administrator",
        description="Full system access with all permissions",
        permissions=set(Permission),  # All permissions
    ),
    RoleType.AUDITOR: Role(
        role_type=RoleType.AUDITOR,
        name="System Auditor",
        description="Read-only access for compliance and auditing",
        permissions={
            Permission.USER_READ_ALL,
            Permission.PROJECT_READ_ALL,
            Permission.SUBSCRIPTION_READ_ALL,
            Permission.SYSTEM_CONFIG,  # Required for admin endpoint access (read-only)
            Permission.SYSTEM_AUDIT,
            Permission.SECURITY_AUDIT,
            Permission.ROLE_READ,
        },
    ),
    RoleType.SYSTEM: Role(
        role_type=RoleType.SYSTEM,
        name="System Service",
        description="Internal system service account",
        permissions={
            Permission.SYSTEM_CONFIG,
            Permission.SYSTEM_BACKUP,
            Permission.SECURITY_ADMIN,
        },
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


def get_role_hierarchy_level(role_type: RoleType) -> int:
    """Get numeric hierarchy level for role comparison."""
    hierarchy = {
        RoleType.GUEST: 0,
        RoleType.USER: 1,
        RoleType.MODERATOR: 2,
        RoleType.AUDITOR: 3,
        RoleType.ADMIN: 4,
        RoleType.SUPER_ADMIN: 5,
        RoleType.SYSTEM: 6,
    }
    return hierarchy.get(role_type, 0)


def can_assign_role(assigner_roles: List[RoleType], target_role: RoleType) -> bool:
    """Check if user can assign a specific role based on hierarchy."""
    max_assigner_level = max(
        [get_role_hierarchy_level(role) for role in assigner_roles], default=0
    )
    target_level = get_role_hierarchy_level(target_role)

    # Can only assign roles at same level or below, except super admin can assign any role
    return max_assigner_level >= target_level or RoleType.SUPER_ADMIN in assigner_roles
