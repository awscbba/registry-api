"""
Role management service for database operations.
"""

import logging
import time
from typing import List, Optional, Set, Dict, Any
from datetime import datetime
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from ..core.base_service import BaseService, ServiceStatus, HealthCheck, ServiceResponse
from ..models.roles import (
    RoleType,
    Permission,
    UserRole,
    RoleAssignmentRequest,
    RoleAssignmentResponse,
    get_role_permissions,
    has_permission,
    is_admin_role,
    is_super_admin_role,
)
from ..services.defensive_dynamodb_service import DefensiveDynamoDBService

logger = logging.getLogger(__name__)


class RolesService(BaseService):
    """Service for managing user roles and permissions."""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        table_name: str = "people-registry-roles",
    ):
        super().__init__("roles_service", config)
        self.table_name = table_name
        self.dynamodb = None
        self.table = None

    async def initialize(self) -> bool:
        """Initialize the roles service."""
        try:
            self.logger.info("Initializing RolesService...")

            # Initialize DynamoDB resources
            self.dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            self.table = self.dynamodb.Table(self.table_name)

            # Test table connectivity
            await self._test_table_connection()

            self._initialized = True
            self.logger.info("RolesService initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize RolesService: {str(e)}")
            return False

    async def health_check(self) -> HealthCheck:
        """Perform health check for the roles service."""
        start_time = time.time()

        try:
            if not self._initialized:
                return HealthCheck(
                    service_name=self.service_name,
                    status=ServiceStatus.UNHEALTHY,
                    message="Service not initialized",
                    response_time_ms=(time.time() - start_time) * 1000,
                )

            # Test table connectivity
            await self._test_table_connection()

            response_time = (time.time() - start_time) * 1000

            return HealthCheck(
                service_name=self.service_name,
                status=ServiceStatus.HEALTHY,
                message="Roles service is healthy",
                details={
                    "table_name": self.table_name,
                    "table_connected": True,
                    "region": "us-east-1",
                },
                response_time_ms=response_time,
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.logger.error(f"Health check failed: {str(e)}")

            return HealthCheck(
                service_name=self.service_name,
                status=ServiceStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                response_time_ms=response_time,
            )

    async def _test_table_connection(self):
        """Test DynamoDB table connectivity."""
        if not self.table:
            raise Exception("DynamoDB table not initialized")

        try:
            # Test table by describing it (lightweight operation)
            self.table.table_status
        except Exception as e:
            raise Exception(f"DynamoDB table connection test failed: {str(e)}")

    async def get_user_roles(self, user_id: str) -> List[RoleType]:
        """
        Get all active roles for a user.

        Args:
            user_id: The user ID to get roles for

        Returns:
            List of active role types for the user
        """
        try:
            # Query for user roles
            response = self.table.query(
                KeyConditionExpression=Key("user_id").eq(user_id)
            )

            roles = []
            current_time = datetime.utcnow()

            for item in response.get("Items", []):
                # Check if role is active and not expired
                if item.get("is_active", True) and (
                    not item.get("expires_at")
                    or datetime.fromisoformat(item["expires_at"]) > current_time
                ):
                    # Handle case-insensitive role matching
                    role_type_str = item["role_type"]
                    normalized_role = self._normalize_role_type(role_type_str)
                    if normalized_role:
                        roles.append(normalized_role)

            # If no roles found, assign default USER role
            if not roles:
                await self.assign_default_user_role(user_id)
                roles = [RoleType.USER]

            return roles

        except Exception as e:
            logger.error(f"Error getting user roles for {user_id}: {str(e)}")
            # Return default role on error
            return [RoleType.USER]

    def get_user_roles_by_email(self, email: str) -> List[RoleType]:
        """
        Get all active roles for a user by email.

        Args:
            email: The user email to get roles for

        Returns:
            List of active role types for the user
        """
        try:
            # Query by email using GSI
            response = self.table.query(
                IndexName="email-index", KeyConditionExpression=Key("email").eq(email)
            )

            roles = []
            current_time = datetime.utcnow()

            for item in response.get("Items", []):
                # Check if role is active and not expired
                if item.get("is_active", True) and (
                    not item.get("expires_at")
                    or datetime.fromisoformat(item["expires_at"]) > current_time
                ):
                    # Handle case-insensitive role matching
                    role_type_str = item["role_type"]
                    normalized_role = self._normalize_role_type(role_type_str)
                    if normalized_role:
                        roles.append(normalized_role)

            return roles

        except Exception as e:
            logger.error(f"Error getting user roles for email {email}: {str(e)}")
            return [RoleType.USER]

    async def user_has_permission(self, user_id: str, permission: Permission) -> bool:
        """
        Check if a user has a specific permission.

        Args:
            user_id: The user ID to check
            permission: The permission to check for

        Returns:
            True if user has the permission, False otherwise
        """
        user_roles = await self.get_user_roles(user_id)
        return has_permission(user_roles, permission)

    async def user_is_admin(self, user_id: str) -> bool:
        """
        Check if a user has admin privileges.

        Args:
            user_id: The user ID to check

        Returns:
            True if user is an admin, False otherwise
        """
        user_roles = await self.get_user_roles(user_id)
        return any(is_admin_role(role) for role in user_roles)

    async def user_is_super_admin(self, user_id: str) -> bool:
        """
        Check if a user has super admin privileges.

        Args:
            user_id: The user ID to check

        Returns:
            True if user is a super admin, False otherwise
        """
        user_roles = await self.get_user_roles(user_id)
        return any(is_super_admin_role(role) for role in user_roles)

    async def assign_role(
        self, request: RoleAssignmentRequest, assigned_by_user_id: str
    ) -> RoleAssignmentResponse:
        """
        Assign a role to a user.

        Args:
            request: Role assignment request
            assigned_by_user_id: ID of user making the assignment

        Returns:
            Role assignment response
        """
        try:
            # First, get the user ID from email (you'll need to implement this)
            user_id = await self._get_user_id_by_email(request.user_email)
            if not user_id:
                return RoleAssignmentResponse(
                    success=False,
                    message=f"User with email {request.user_email} not found",
                )

            # Create user role record
            user_role = UserRole(
                user_id=user_id,
                email=request.user_email,
                role_type=request.role_type,
                assigned_by=assigned_by_user_id,
                expires_at=request.expires_at,
                notes=request.notes,
            )

            # Store in database
            self.table.put_item(
                Item={
                    "user_id": user_role.user_id,
                    "role_type": user_role.role_type.value,
                    "email": user_role.email,
                    "assigned_by": user_role.assigned_by,
                    "assigned_at": user_role.assigned_at.isoformat(),
                    "expires_at": (
                        user_role.expires_at.isoformat()
                        if user_role.expires_at
                        else None
                    ),
                    "is_active": user_role.is_active,
                    "notes": user_role.notes,
                }
            )

            logger.info(
                f"Role {request.role_type.value} assigned to user {request.user_email} by {assigned_by_user_id}"
            )

            return RoleAssignmentResponse(
                success=True,
                message=f"Role {request.role_type.value} successfully assigned to {request.user_email}",
                user_role=user_role,
            )

        except Exception as e:
            logger.error(f"Error assigning role: {str(e)}")
            return RoleAssignmentResponse(
                success=False, message=f"Failed to assign role: {str(e)}"
            )

    def revoke_role(
        self, user_email: str, role_type: RoleType, revoked_by_user_id: str
    ) -> RoleAssignmentResponse:
        """
        Revoke a role from a user.

        Args:
            user_email: Email of user to revoke role from
            role_type: Role type to revoke
            revoked_by_user_id: ID of user making the revocation

        Returns:
            Role assignment response
        """
        try:
            user_id = self._get_user_id_by_email(user_email)
            if not user_id:
                return RoleAssignmentResponse(
                    success=False, message=f"User with email {user_email} not found"
                )

            # Update the role to inactive
            self.table.update_item(
                Key={"user_id": user_id, "role_type": role_type.value},
                UpdateExpression="SET is_active = :inactive, revoked_by = :revoked_by, revoked_at = :revoked_at",
                ExpressionAttributeValues={
                    ":inactive": False,
                    ":revoked_by": revoked_by_user_id,
                    ":revoked_at": datetime.utcnow().isoformat(),
                },
            )

            logger.info(
                f"Role {role_type.value} revoked from user {user_email} by {revoked_by_user_id}"
            )

            return RoleAssignmentResponse(
                success=True,
                message=f"Role {role_type.value} successfully revoked from {user_email}",
            )

        except Exception as e:
            logger.error(f"Error revoking role: {str(e)}")
            return RoleAssignmentResponse(
                success=False, message=f"Failed to revoke role: {str(e)}"
            )

    async def assign_default_user_role(
        self, user_id: str, user_email: str = None
    ) -> None:
        """
        Assign default USER role to a new user.

        Args:
            user_id: The user ID
            user_email: The user email (optional)
        """
        try:
            if not user_email:
                user_email = await self._get_user_email_by_id(user_id)

            user_role = UserRole(
                user_id=user_id,
                email=user_email or "unknown",
                role_type=RoleType.USER,
                assigned_by="system",
                notes="Default role assignment",
            )

            await self.dynamodb_service.put_item(
                table_name=self.table_name,
                item={
                    "user_id": user_role.user_id,
                    "role_type": user_role.role_type.value,
                    "email": user_role.email,
                    "assigned_by": user_role.assigned_by,
                    "assigned_at": user_role.assigned_at.isoformat(),
                    "expires_at": None,
                    "is_active": True,
                    "notes": user_role.notes,
                },
            )

            logger.info(f"Default USER role assigned to user {user_id}")

        except Exception as e:
            logger.error(f"Error assigning default role to user {user_id}: {str(e)}")

    async def list_user_roles(self, user_id: str) -> List[UserRole]:
        """
        Get detailed role information for a user.

        Args:
            user_id: The user ID

        Returns:
            List of UserRole objects
        """
        try:
            response = await self.dynamodb_service.query_items(
                table_name=self.table_name,
                key_condition_expression="user_id = :user_id",
                expression_attribute_values={":user_id": user_id},
            )

            user_roles = []
            for item in response.get("Items", []):
                user_role = UserRole(
                    user_id=item["user_id"],
                    email=item["email"],
                    role_type=RoleType(item["role_type"]),
                    assigned_by=item["assigned_by"],
                    assigned_at=datetime.fromisoformat(item["assigned_at"]),
                    expires_at=(
                        datetime.fromisoformat(item["expires_at"])
                        if item.get("expires_at")
                        else None
                    ),
                    is_active=item.get("is_active", True),
                    notes=item.get("notes"),
                )
                user_roles.append(user_role)

            return user_roles

        except Exception as e:
            logger.error(f"Error listing user roles for {user_id}: {str(e)}")
            return []

    def _normalize_role_type(self, role_type_str: str) -> Optional[RoleType]:
        """
        Normalize role type string to match RoleType enum values.
        Handles case-insensitive matching and format variations.

        Args:
            role_type_str: Role type string from database

        Returns:
            Normalized RoleType or None if not recognized
        """
        if not role_type_str:
            return None

        # Convert to lowercase and handle common variations
        normalized = role_type_str.lower().strip()

        # Handle different formats
        role_mapping = {
            # Standard formats
            "user": RoleType.USER,
            "admin": RoleType.ADMIN,
            "super_admin": RoleType.SUPER_ADMIN,
            "moderator": RoleType.MODERATOR,
            # Uppercase variations (from database)
            "USER": RoleType.USER,
            "ADMIN": RoleType.ADMIN,
            "SUPER_ADMIN": RoleType.SUPER_ADMIN,
            "MODERATOR": RoleType.MODERATOR,
            # Alternative formats
            "superadmin": RoleType.SUPER_ADMIN,
            "super-admin": RoleType.SUPER_ADMIN,
        }

        # Try direct mapping first
        if role_type_str in role_mapping:
            return role_mapping[role_type_str]

        # Try normalized (lowercase) mapping
        if normalized in role_mapping:
            return role_mapping[normalized]

        # Log unrecognized role types for debugging
        logger.warning(f"Unrecognized role type: '{role_type_str}', treating as USER")
        return RoleType.USER

    async def _get_user_id_by_email(self, email: str) -> Optional[str]:
        """
        Get user ID by email address.
        This should query your users table.
        """
        try:
            # This is a placeholder - you'll need to implement based on your user table structure
            # For now, using a simple table query (adjust table name and structure as needed)
            users_table = self.dynamodb.Table("people-registry-users")
            response = users_table.query(
                IndexName="email-index", KeyConditionExpression=Key("email").eq(email)
            )

            items = response.get("Items", [])
            if items:
                return items[0].get("id")
            return None

        except Exception as e:
            logger.error(f"Error getting user ID for email {email}: {str(e)}")
            return None

    async def _get_user_email_by_id(self, user_id: str) -> Optional[str]:
        """
        Get user email by user ID.
        This should query your users table.
        """
        try:
            # This is a placeholder - you'll need to implement based on your user table structure
            response = await self.dynamodb_service.get_item(
                table_name="people-registry-users",  # Adjust table name
                key={"id": user_id},
            )

            item = response.get("Item")
            if item:
                return item.get("email")
            return None

        except Exception as e:
            logger.error(f"Error getting user email for ID {user_id}: {str(e)}")
            return None
