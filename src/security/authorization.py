"""
Enterprise-grade authorization and access control.
"""

from typing import Dict, List, Optional, Set
from enum import Enum
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class Permission(Enum):
    """System permissions."""

    # User permissions
    USER_READ = "user:read"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_ADMIN = "user:admin"

    # Project permissions
    PROJECT_READ = "project:read"
    PROJECT_CREATE = "project:create"
    PROJECT_UPDATE = "project:update"
    PROJECT_DELETE = "project:delete"
    PROJECT_ADMIN = "project:admin"

    # Subscription permissions
    SUBSCRIPTION_READ = "subscription:read"
    SUBSCRIPTION_CREATE = "subscription:create"
    SUBSCRIPTION_UPDATE = "subscription:update"
    SUBSCRIPTION_DELETE = "subscription:delete"
    SUBSCRIPTION_ADMIN = "subscription:admin"

    # System permissions
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_AUDIT = "system:audit"


class Role(Enum):
    """System roles."""

    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"
    AUDITOR = "auditor"


class AuthorizationService:
    """Enterprise authorization service."""

    # Role-Permission mapping
    ROLE_PERMISSIONS = {
        Role.USER: {
            Permission.USER_READ,
            Permission.PROJECT_READ,
            Permission.SUBSCRIPTION_READ,
            Permission.SUBSCRIPTION_CREATE,
            Permission.SUBSCRIPTION_UPDATE,
        },
        Role.ADMIN: {
            Permission.USER_READ,
            Permission.USER_CREATE,
            Permission.USER_UPDATE,
            Permission.USER_ADMIN,
            Permission.PROJECT_READ,
            Permission.PROJECT_CREATE,
            Permission.PROJECT_UPDATE,
            Permission.PROJECT_ADMIN,
            Permission.SUBSCRIPTION_READ,
            Permission.SUBSCRIPTION_CREATE,
            Permission.SUBSCRIPTION_UPDATE,
            Permission.SUBSCRIPTION_DELETE,
            Permission.SUBSCRIPTION_ADMIN,
        },
        Role.SUPER_ADMIN: {
            # Super admin has all permissions
            *[perm for perm in Permission],
        },
        Role.AUDITOR: {
            Permission.USER_READ,
            Permission.PROJECT_READ,
            Permission.SUBSCRIPTION_READ,
            Permission.SYSTEM_AUDIT,
        },
    }

    def __init__(self):
        self.failed_attempts: Dict[str, List[datetime]] = {}
        self.locked_accounts: Dict[str, datetime] = {}

    def get_user_permissions(self, user_id: str, roles: List[Role]) -> Set[Permission]:
        """Get all permissions for a user based on their roles."""
        permissions = set()

        for role in roles:
            if role in self.ROLE_PERMISSIONS:
                permissions.update(self.ROLE_PERMISSIONS[role])

        return permissions

    def has_permission(
        self, user_id: str, user_roles: List[Role], required_permission: Permission
    ) -> bool:
        """Check if user has required permission."""
        user_permissions = self.get_user_permissions(user_id, user_roles)
        return required_permission in user_permissions

    def can_access_resource(
        self,
        user_id: str,
        user_roles: List[Role],
        resource_type: str,
        resource_id: str,
        action: str,
    ) -> bool:
        """Check if user can access specific resource."""

        # Map action to permission
        permission_map = {
            "read": f"{resource_type}:read",
            "create": f"{resource_type}:create",
            "update": f"{resource_type}:update",
            "delete": f"{resource_type}:delete",
            "admin": f"{resource_type}:admin",
        }

        required_permission_str = permission_map.get(action)
        if not required_permission_str:
            return False

        try:
            required_permission = Permission(required_permission_str)
        except ValueError:
            return False

        # Check basic permission
        if not self.has_permission(user_id, user_roles, required_permission):
            return False

        # Additional resource-specific checks
        if resource_type == "user" and action in ["update", "delete"]:
            # Users can only modify their own data unless they're admin
            if resource_id != user_id and not self.has_permission(
                user_id, user_roles, Permission.USER_ADMIN
            ):
                return False

        return True

    def record_failed_login(self, user_id: str):
        """Record failed login attempt."""
        now = datetime.utcnow()

        if user_id not in self.failed_attempts:
            self.failed_attempts[user_id] = []

        # Clean old attempts (older than 1 hour)
        self.failed_attempts[user_id] = [
            attempt
            for attempt in self.failed_attempts[user_id]
            if now - attempt < timedelta(hours=1)
        ]

        # Add new attempt
        self.failed_attempts[user_id].append(now)

        # Lock account if too many attempts
        if len(self.failed_attempts[user_id]) >= 5:
            self.locked_accounts[user_id] = now + timedelta(minutes=30)
            logger.warning(f"Account {user_id} locked due to failed login attempts")

    def is_account_locked(self, user_id: str) -> bool:
        """Check if account is locked."""
        if user_id not in self.locked_accounts:
            return False

        lock_until = self.locked_accounts[user_id]
        if datetime.utcnow() > lock_until:
            # Lock expired, remove it
            del self.locked_accounts[user_id]
            return False

        return True

    def clear_failed_attempts(self, user_id: str):
        """Clear failed login attempts (on successful login)."""
        if user_id in self.failed_attempts:
            del self.failed_attempts[user_id]
        if user_id in self.locked_accounts:
            del self.locked_accounts[user_id]


class SecurityContext:
    """Security context for request processing."""

    def __init__(self, user_id: str, user_roles: List[Role], ip_address: str = None):
        self.user_id = user_id
        self.user_roles = user_roles
        self.ip_address = ip_address
        self.request_time = datetime.utcnow()

    def has_permission(self, permission: Permission) -> bool:
        """Check if current user has permission."""
        auth_service = AuthorizationService()
        return auth_service.has_permission(self.user_id, self.user_roles, permission)

    def can_access_resource(
        self, resource_type: str, resource_id: str, action: str
    ) -> bool:
        """Check if current user can access resource."""
        auth_service = AuthorizationService()
        return auth_service.can_access_resource(
            self.user_id, self.user_roles, resource_type, resource_id, action
        )


# Global authorization service instance
authorization_service = AuthorizationService()
