"""Repository for managing user roles in DynamoDB."""

from typing import List, Optional, Any, Dict
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

from .base_repository import BaseRepository
from ..models.rbac import UserRole, RoleType


class RolesRepository(BaseRepository):
    """Repository for user roles stored in DynamoDB."""

    def __init__(self):
        super().__init__()
        self.table_name = "people-registry-roles"
        self.dynamodb = boto3.client("dynamodb", region_name="us-east-1")

    def get_user_roles(self, user_id: str) -> List[UserRole]:
        """Get all roles for a user."""
        try:
            response = self.dynamodb.scan(
                TableName=self.table_name,
                FilterExpression="user_id = :user_id",
                ExpressionAttributeValues={":user_id": {"S": user_id}},
            )

            roles = []
            for item in response.get("Items", []):
                role = UserRole(
                    user_id=item["user_id"]["S"],
                    role_type=RoleType(item["role_type"]["S"]),
                    assigned_at=datetime.fromisoformat(
                        item["assigned_at"]["S"].replace("Z", "+00:00")
                    ),
                    assigned_by=item["assigned_by"]["S"],
                    is_active=item.get("is_active", {"BOOL": True})["BOOL"],
                    expires_at=(
                        None
                        if item.get("expires_at", {}).get("NULL")
                        else datetime.fromisoformat(
                            item["expires_at"]["S"].replace("Z", "+00:00")
                        )
                    ),
                    notes=item.get("notes", {}).get("S"),
                )
                roles.append(role)

            return roles

        except ClientError as e:
            print(f"Error fetching user roles: {e}")
            return []

    # Required abstract method implementations
    def create(self, data: Dict[str, Any]) -> Any:
        """Create a role assignment."""
        pass

    def get_by_id(self, role_id: str) -> Optional[Any]:
        """Get role by ID."""
        pass

    def update(self, role_id: str, data: Dict[str, Any]) -> Optional[Any]:
        """Update role assignment."""
        pass

    def delete(self, role_id: str) -> bool:
        """Delete role assignment."""
        pass

    def list_all(self) -> List[Any]:
        """List all role assignments."""
        pass

    def exists(self, role_id: str) -> bool:
        """Check if role exists."""
        pass
