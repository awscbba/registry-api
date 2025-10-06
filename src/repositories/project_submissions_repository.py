"""
Project Submissions Repository
Handles database operations for project form submissions
"""

from typing import Dict, Any, Optional, List
import boto3
import uuid
from datetime import datetime
from botocore.exceptions import ClientError


class ProjectSubmissionsRepository:
    """Repository for project submissions"""

    def __init__(self):
        # This will fail initially because the table doesn't exist
        self.table_name = "ProjectSubmissions"
        self.dynamodb = boto3.resource("dynamodb")
        try:
            self.table = self.dynamodb.Table(self.table_name)
        except Exception:
            # Table doesn't exist yet - this is expected in TDD
            self.table = None

    def create(self, submission_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new project submission"""
        if not self.table:
            raise Exception(f"Table {self.table_name} does not exist")

        # Generate ID and timestamps
        submission_id = str(uuid.uuid4())
        now = datetime.utcnow()

        db_item = submission_data.copy()
        db_item.update(
            {
                "id": submission_id,
                "createdAt": now.isoformat(),
                "updatedAt": now.isoformat(),
            }
        )

        try:
            self.table.put_item(Item=db_item)
            return db_item
        except ClientError as e:
            raise Exception(f"Failed to create submission: {e}")

    def get_by_project_id(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all submissions for a project"""
        if not self.table:
            return []

        try:
            response = self.table.scan(
                FilterExpression="projectId = :project_id",
                ExpressionAttributeValues={":project_id": project_id},
            )
            return response.get("Items", [])
        except ClientError:
            return []

    def get_by_id(self, submission_id: str) -> Optional[Dict[str, Any]]:
        """Get submission by ID"""
        if not self.table:
            return None

        try:
            response = self.table.get_item(Key={"id": submission_id})
            return response.get("Item")
        except ClientError:
            return None

    def update(
        self, submission_id: str, updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update submission"""
        if not self.table:
            return None

        updates["updatedAt"] = datetime.utcnow().isoformat()

        try:
            response = self.table.update_item(
                Key={"id": submission_id},
                UpdateExpression="SET "
                + ", ".join([f"{k} = :{k}" for k in updates.keys()]),
                ExpressionAttributeValues={f":{k}": v for k, v in updates.items()},
                ReturnValues="ALL_NEW",
            )
            return response.get("Attributes")
        except ClientError:
            return None

    def delete(self, submission_id: str) -> bool:
        """Delete submission"""
        if not self.table:
            return False

        try:
            self.table.delete_item(Key={"id": submission_id})
            return True
        except ClientError:
            return False

    def list_all(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """List all submissions"""
        if not self.table:
            return []

        try:
            if limit:
                response = self.table.scan(Limit=limit)
            else:
                response = self.table.scan()
            return response.get("Items", [])
        except ClientError:
            return []

    def exists(self, submission_id: str) -> bool:
        """Check if submission exists"""
        return self.get_by_id(submission_id) is not None
