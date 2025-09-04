"""
Enterprise Role-Based Access Control (RBAC) service.
Implements comprehensive permission management with audit trails.
"""

from typing import List, Optional, Dict, Any, Set
from datetime import datetime, timedelta, timezone
import uuid

from ..models.rbac import (
    RoleType,
    Permission,
    UserRole,
    RoleAssignmentRequest,
    RoleAssignmentResponse,
    PermissionCheck,
    PermissionResult,
    DEFAULT_ROLES,
    get_role_permissions,
    has_permission,
    is_admin_role,
    is_super_admin_role,
    can_assign_role,
)
from ..exceptions.base_exceptions import (
    AuthorizationException,
    ResourceNotFoundException,
    ValidationException,
    BusinessLogicException,
    ErrorCode,
)
from ..repositories.people_repository import PeopleRepository
from .logging_service import logging_service, LogCategory, LogLevel, RequestContext


class RBACService:
    """Enterprise RBAC service with comprehensive permission management."""

    def __init__(self):
        self.people_repository = PeopleRepository()
        # In a real implementation, this would be a dedicated RBAC repository
        self._user_roles: Dict[str, List[UserRole]] = {}
        self._initialize_default_roles()

    def _initialize_default_roles(self):
        """Initialize default system roles."""
        # This would typically be done during system setup
        # For now, we'll simulate it in memory
        pass

    async def get_user_roles(self, user_id: str) -> List[RoleType]:
        """Get all active roles for a user."""
        try:
            # Get user roles from storage
            user_roles = self._user_roles.get(user_id, [])

            # Filter active and non-expired roles
            active_roles = []
            now = datetime.now(timezone.utc)

            for user_role in user_roles:
                if user_role.is_active and (
                    user_role.expires_at is None or user_role.expires_at > now
                ):
                    active_roles.append(user_role.role_type)

            # If no roles found, assign default USER role
            if not active_roles:
                # Check if user exists
                user = await self.people_repository.get_by_id(user_id)
                if user:
                    # Check legacy admin field
                    if getattr(user, "isAdmin", False):
                        active_roles = [RoleType.ADMIN]
                    else:
                        active_roles = [RoleType.USER]
                else:
                    active_roles = [RoleType.GUEST]

            return active_roles

        except Exception as e:
            logging_service.log_structured(
                level=LogLevel.ERROR,
                category=LogCategory.AUTHORIZATION,
                message=f"Failed to get user roles for {user_id}",
                additional_data={
                    "user_id": user_id,
                    "error": str(e),
                },
            )
            # Return guest role on error
            return [RoleType.GUEST]

    async def user_has_permission(
        self,
        user_id: str,
        permission: Permission,
        resource_id: Optional[str] = None,
        context: Optional[RequestContext] = None,
    ) -> PermissionResult:
        """Check if user has a specific permission."""

        try:
            # Get user roles
            user_roles = await self.get_user_roles(user_id)

            # Check permission
            has_perm = has_permission(user_roles, permission)

            # Additional context-based checks
            if has_perm and resource_id:
                has_perm = await self._check_resource_access(
                    user_id, user_roles, permission, resource_id
                )

            reason = "Permission granted" if has_perm else "Permission denied"
            if not has_perm:
                reason += f" - User roles: {[role.value for role in user_roles]}"

            # Log authorization check
            logging_service.log_authorization_event(
                action="permission_check",
                resource_type="permission",
                resource_id=permission.value,
                user_id=user_id,
                success=has_perm,
                context=context,
                details={
                    "permission": permission.value,
                    "user_roles": [role.value for role in user_roles],
                    "resource_id": resource_id,
                },
            )

            return PermissionResult(
                has_permission=has_perm,
                reason=reason,
            )

        except Exception as e:
            logging_service.log_structured(
                level=LogLevel.ERROR,
                category=LogCategory.AUTHORIZATION,
                message=f"Permission check failed for user {user_id}",
                context=context,
                additional_data={
                    "user_id": user_id,
                    "permission": permission.value,
                    "error": str(e),
                },
            )

            return PermissionResult(
                has_permission=False,
                reason=f"Permission check failed: {str(e)}",
            )

    async def _check_resource_access(
        self,
        user_id: str,
        user_roles: List[RoleType],
        permission: Permission,
        resource_id: str,
    ) -> bool:
        """Check resource-specific access rules."""

        # Admin and super admin can access everything
        if any(is_admin_role(role) for role in user_roles):
            return True

        # Check ownership for "own" permissions
        if "own" in permission.value:
            return await self._check_resource_ownership(
                user_id, permission, resource_id
            )

        return True

    async def _check_resource_ownership(
        self,
        user_id: str,
        permission: Permission,
        resource_id: str,
    ) -> bool:
        """Check if user owns the resource."""

        try:
            # Extract resource type from permission
            if "user:" in permission.value:
                # For user resources, check if resource_id matches user_id
                return resource_id == user_id

            elif "project:" in permission.value:
                # For project resources, check if user created the project
                # This would require checking the project's creator field
                # For now, return True (implement proper ownership check)
                return True

            elif "subscription:" in permission.value:
                # For subscription resources, check if user owns the subscription
                # This would require checking the subscription's user_id field
                # For now, return True (implement proper ownership check)
                return True

            return False

        except Exception:
            return False

    async def assign_role(
        self,
        request: RoleAssignmentRequest,
        assigned_by: str,
        context: Optional[RequestContext] = None,
    ) -> RoleAssignmentResponse:
        """Assign a role to a user."""

        try:
            # Get assigner's roles
            assigner_roles = await self.get_user_roles(assigned_by)

            # Check if assigner can assign this role
            if not can_assign_role(assigner_roles, request.role_type):
                raise AuthorizationException(
                    message=f"Cannot assign role {request.role_type.value}",
                    error_code=ErrorCode.INSUFFICIENT_PERMISSIONS,
                )

            # Get target user
            target_user = await self.people_repository.get_by_email(request.user_email)
            if not target_user:
                raise ResourceNotFoundException(
                    resource_type="User", details={"email": request.user_email}
                )

            # Check if role already assigned
            existing_roles = await self.get_user_roles(target_user.id)
            if request.role_type in existing_roles:
                raise BusinessLogicException(
                    message=f"User already has role {request.role_type.value}",
                    error_code=ErrorCode.DUPLICATE_VALUE,
                )

            # Create role assignment
            user_role = UserRole(
                user_id=target_user.id,
                user_email=target_user.email,
                role_type=request.role_type,
                assigned_by=assigned_by,
                expires_at=request.expires_at,
                notes=request.notes,
            )

            # Store role assignment
            if target_user.id not in self._user_roles:
                self._user_roles[target_user.id] = []
            self._user_roles[target_user.id].append(user_role)

            # Log role assignment
            logging_service.log_structured(
                level=LogLevel.INFO,
                category=LogCategory.AUTHORIZATION,
                message=f"Role {request.role_type.value} assigned to user {target_user.email}",
                context=context,
                additional_data={
                    "target_user_id": target_user.id,
                    "target_user_email": target_user.email,
                    "role_type": request.role_type.value,
                    "assigned_by": assigned_by,
                    "expires_at": (
                        request.expires_at.isoformat() if request.expires_at else None
                    ),
                },
            )

            return RoleAssignmentResponse(
                success=True,
                message=f"Role {request.role_type.value} assigned successfully",
                user_role=user_role,
            )

        except (
            AuthorizationException,
            ResourceNotFoundException,
            BusinessLogicException,
        ):
            raise
        except Exception as e:
            logging_service.log_structured(
                level=LogLevel.ERROR,
                category=LogCategory.AUTHORIZATION,
                message=f"Role assignment failed",
                context=context,
                additional_data={
                    "target_email": request.user_email,
                    "role_type": request.role_type.value,
                    "assigned_by": assigned_by,
                    "error": str(e),
                },
            )

            raise BusinessLogicException(
                message="Role assignment failed",
                error_code=ErrorCode.INTERNAL_ERROR,
                cause=e,
            )

    async def revoke_role(
        self,
        user_id: str,
        role_type: RoleType,
        revoked_by: str,
        context: Optional[RequestContext] = None,
    ) -> bool:
        """Revoke a role from a user."""

        try:
            # Get revoker's roles
            revoker_roles = await self.get_user_roles(revoked_by)

            # Check if revoker can revoke this role
            if not can_assign_role(revoker_roles, role_type):
                raise AuthorizationException(
                    message=f"Cannot revoke role {role_type.value}",
                    error_code=ErrorCode.INSUFFICIENT_PERMISSIONS,
                )

            # Find and deactivate role assignment
            user_roles = self._user_roles.get(user_id, [])
            role_found = False

            for user_role in user_roles:
                if user_role.role_type == role_type and user_role.is_active:
                    user_role.is_active = False
                    user_role.updated_at = datetime.now(timezone.utc)
                    role_found = True
                    break

            if not role_found:
                raise ResourceNotFoundException(
                    resource_type="Role assignment",
                    details={
                        "user_id": user_id,
                        "role_type": role_type.value,
                    },
                )

            # Log role revocation
            logging_service.log_structured(
                level=LogLevel.INFO,
                category=LogCategory.AUTHORIZATION,
                message=f"Role {role_type.value} revoked from user {user_id}",
                context=context,
                additional_data={
                    "user_id": user_id,
                    "role_type": role_type.value,
                    "revoked_by": revoked_by,
                },
            )

            return True

        except (AuthorizationException, ResourceNotFoundException):
            raise
        except Exception as e:
            logging_service.log_structured(
                level=LogLevel.ERROR,
                category=LogCategory.AUTHORIZATION,
                message=f"Role revocation failed",
                context=context,
                additional_data={
                    "user_id": user_id,
                    "role_type": role_type.value,
                    "revoked_by": revoked_by,
                    "error": str(e),
                },
            )

            raise BusinessLogicException(
                message="Role revocation failed",
                error_code=ErrorCode.INTERNAL_ERROR,
                cause=e,
            )

    async def user_is_admin(self, user_id: str) -> bool:
        """Check if user has admin privileges."""
        user_roles = await self.get_user_roles(user_id)
        return any(is_admin_role(role) for role in user_roles)

    async def user_is_super_admin(self, user_id: str) -> bool:
        """Check if user has super admin privileges."""
        user_roles = await self.get_user_roles(user_id)
        return any(is_super_admin_role(role) for role in user_roles)

    async def get_all_roles(self) -> Dict[str, Any]:
        """Get information about all available roles."""
        roles_info = {}

        for role_type, role in DEFAULT_ROLES.items():
            roles_info[role_type.value] = {
                "name": role.name,
                "description": role.description,
                "permissions": [perm.value for perm in role.permissions],
                "is_admin_role": is_admin_role(role_type),
                "is_super_admin_role": is_super_admin_role(role_type),
            }

        return {
            "roles": roles_info,
            "available_permissions": [perm.value for perm in Permission],
        }

    async def get_user_role_assignments(self, user_id: str) -> List[UserRole]:
        """Get all role assignments for a user."""
        return self._user_roles.get(user_id, [])


# Global RBAC service instance
rbac_service = RBACService()
