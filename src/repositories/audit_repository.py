"""
Audit Repository for managing audit trail data access.

This repository handles all audit-related database operations including
audit log creation, querying, and compliance reporting.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal

from .base_repository import BaseRepository, QueryFilter, QueryOptions, RepositoryResult
from ..models.audit import AuditLog


class AuditRepository(BaseRepository[AuditLog]):
    """Repository for audit trail data access and management."""

    def __init__(self, table_name: str = "audit_logs", region: str = "us-east-1"):
        """
        Initialize AuditRepository.

        Args:
            table_name: DynamoDB table name for audit logs
            region: AWS region for DynamoDB
        """
        super().__init__(table_name, region)

    def _get_primary_key(self, entity: AuditLog) -> Dict[str, Any]:
        """Get primary key from AuditLog entity."""
        return {"id": entity.id}

    def _to_entity(self, item: Dict[str, Any]) -> AuditLog:
        """Convert DynamoDB item to AuditLog entity."""
        return AuditLog(
            id=item["id"],
            user_id=item["user_id"],
            action=item["action"],
            resource_type=item["resource_type"],
            resource_id=item["resource_id"],
            timestamp=item["timestamp"],
            details=item.get("details", {}),
            ip_address=item.get("ip_address"),
            user_agent=item.get("user_agent"),
            success=item.get("success", True),
            error_message=item.get("error_message"),
        )

    def _to_item(self, entity: AuditLog) -> Dict[str, Any]:
        """Convert AuditLog entity to DynamoDB item."""
        item = {
            "id": entity.id,
            "user_id": entity.user_id,
            "action": entity.action,
            "resource_type": entity.resource_type,
            "resource_id": entity.resource_id,
            "timestamp": entity.timestamp,
            "success": entity.success,
        }

        if entity.details:
            item["details"] = entity.details
        if entity.ip_address:
            item["ip_address"] = entity.ip_address
        if entity.user_agent:
            item["user_agent"] = entity.user_agent
        if entity.error_message:
            item["error_message"] = entity.error_message

        return item

    async def create_audit_log(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> RepositoryResult[AuditLog]:
        """
        Create a new audit log entry.

        Args:
            user_id: ID of the user performing the action
            action: Action being performed (CREATE, UPDATE, DELETE, etc.)
            resource_type: Type of resource being acted upon
            resource_id: ID of the resource being acted upon
            details: Additional details about the action
            ip_address: IP address of the user
            user_agent: User agent string

        Returns:
            RepositoryResult containing the created audit log
        """
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            timestamp=datetime.utcnow(),
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return await self.create(audit_log)

    async def get_user_audit_trail(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> RepositoryResult[List[AuditLog]]:
        """
        Get audit trail for a specific user.

        Args:
            user_id: User ID to get audit trail for
            start_date: Start date for filtering (optional)
            end_date: End date for filtering (optional)
            limit: Maximum number of records to return

        Returns:
            RepositoryResult containing list of audit logs
        """
        filters = [QueryFilter("user_id", "=", user_id)]

        if start_date:
            filters.append(QueryFilter("timestamp", ">=", start_date))
        if end_date:
            filters.append(QueryFilter("timestamp", "<=", end_date))

        options = QueryOptions(limit=limit, sort_key="timestamp", sort_order="desc")

        return await self.query(filters, options)

    async def get_resource_audit_trail(
        self, resource_type: str, resource_id: str, limit: int = 100
    ) -> RepositoryResult[List[AuditLog]]:
        """
        Get audit trail for a specific resource.

        Args:
            resource_type: Type of resource
            resource_id: ID of the resource
            limit: Maximum number of records to return

        Returns:
            RepositoryResult containing list of audit logs
        """
        filters = [
            QueryFilter("resource_type", "=", resource_type),
            QueryFilter("resource_id", "=", resource_id),
        ]

        options = QueryOptions(limit=limit, sort_key="timestamp", sort_order="desc")

        return await self.query(filters, options)

    async def get_audit_logs_by_action(
        self,
        action: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> RepositoryResult[List[AuditLog]]:
        """
        Get audit logs filtered by action type.

        Args:
            action: Action type to filter by
            start_date: Start date for filtering (optional)
            end_date: End date for filtering (optional)
            limit: Maximum number of records to return

        Returns:
            RepositoryResult containing list of audit logs
        """
        filters = [QueryFilter("action", "=", action)]

        if start_date:
            filters.append(QueryFilter("timestamp", ">=", start_date))
        if end_date:
            filters.append(QueryFilter("timestamp", "<=", end_date))

        options = QueryOptions(limit=limit, sort_key="timestamp", sort_order="desc")

        return await self.query(filters, options)

    async def get_recent_audit_logs(
        self, hours: int = 24, limit: int = 100
    ) -> RepositoryResult[List[AuditLog]]:
        """
        Get recent audit logs within specified hours.

        Args:
            hours: Number of hours to look back
            limit: Maximum number of records to return

        Returns:
            RepositoryResult containing list of recent audit logs
        """
        from datetime import timedelta

        start_date = datetime.utcnow() - timedelta(hours=hours)
        filters = [QueryFilter("timestamp", ">=", start_date)]

        options = QueryOptions(limit=limit, sort_key="timestamp", sort_order="desc")

        return await self.query(filters, options)

    async def get_audit_summary(
        self, start_date: datetime, end_date: datetime
    ) -> RepositoryResult[Dict[str, Any]]:
        """
        Get audit summary statistics for a date range.

        Args:
            start_date: Start date for the summary
            end_date: End date for the summary

        Returns:
            RepositoryResult containing audit summary statistics
        """
        try:
            self._increment_operation_count("get_audit_summary")
            start_time = datetime.utcnow()

            # Get all audit logs in the date range
            filters = [
                QueryFilter("timestamp", ">=", start_date),
                QueryFilter("timestamp", "<=", end_date),
            ]

            result = await self.query(filters, QueryOptions(limit=10000))

            if not result.success or not result.data:
                return RepositoryResult(
                    success=True,
                    data={
                        "total_actions": 0,
                        "unique_users": 0,
                        "actions_by_type": {},
                        "resources_by_type": {},
                        "date_range": {
                            "start": start_date.isoformat(),
                            "end": end_date.isoformat(),
                        },
                    },
                )

            audit_logs = result.data

            # Calculate summary statistics
            actions_by_type = {}
            resources_by_type = {}
            unique_users = set()

            for log in audit_logs:
                # Count actions by type
                actions_by_type[log.action] = actions_by_type.get(log.action, 0) + 1

                # Count resources by type
                resources_by_type[log.resource_type] = (
                    resources_by_type.get(log.resource_type, 0) + 1
                )

                # Track unique users
                unique_users.add(log.user_id)

            summary = {
                "total_actions": len(audit_logs),
                "unique_users": len(unique_users),
                "actions_by_type": actions_by_type,
                "resources_by_type": resources_by_type,
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
            }

            # Record performance metrics
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            self._record_response_time("get_audit_summary", response_time)

            return RepositoryResult(success=True, data=summary)

        except Exception as e:
            return RepositoryResult(
                success=False, error=f"Failed to get audit summary: {str(e)}"
            )

    async def search_audit_logs(
        self,
        search_term: str,
        search_fields: Optional[List[str]] = None,
        limit: int = 100,
    ) -> RepositoryResult[List[AuditLog]]:
        """
        Search audit logs by term in specified fields.

        Args:
            search_term: Term to search for
            search_fields: Fields to search in (defaults to ['action', 'resource_type'])
            limit: Maximum number of records to return

        Returns:
            RepositoryResult containing matching audit logs
        """
        if search_fields is None:
            search_fields = ["action", "resource_type", "user_id"]

        # Create filters for each search field
        filters = []
        for field in search_fields:
            filters.append(QueryFilter(field, "contains", search_term))

        options = QueryOptions(limit=limit, sort_key="timestamp", sort_order="desc")

        # Note: This is a simplified search implementation
        # In a real scenario, you might want to use DynamoDB's scan operation
        # or implement a more sophisticated search mechanism
        return await self.query(filters, options)

    async def delete_old_audit_logs(
        self, older_than_days: int
    ) -> RepositoryResult[int]:
        """
        Delete audit logs older than specified days (for compliance/cleanup).

        Args:
            older_than_days: Delete logs older than this many days

        Returns:
            RepositoryResult containing count of deleted records
        """
        try:
            self._increment_operation_count("delete_old_audit_logs")
            start_time = datetime.utcnow()

            from datetime import timedelta

            cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)

            # Get old audit logs
            filters = [QueryFilter("timestamp", "<", cutoff_date)]
            old_logs_result = await self.query(filters, QueryOptions(limit=10000))

            if not old_logs_result.success or not old_logs_result.data:
                return RepositoryResult(success=True, data=0)

            # Delete old logs in batches
            deleted_count = 0
            batch_size = 25  # DynamoDB batch write limit

            old_logs = old_logs_result.data
            for i in range(0, len(old_logs), batch_size):
                batch = old_logs[i : i + batch_size]

                # Delete batch
                for log in batch:
                    delete_result = await self.delete(log.audit_id)
                    if delete_result.success:
                        deleted_count += 1

            # Record performance metrics
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            self._record_response_time("delete_old_audit_logs", response_time)

            return RepositoryResult(success=True, data=deleted_count)

        except Exception as e:
            return RepositoryResult(
                success=False, error=f"Failed to delete old audit logs: {str(e)}"
            )

    async def get_compliance_report(
        self, start_date: datetime, end_date: datetime, user_id: Optional[str] = None
    ) -> RepositoryResult[Dict[str, Any]]:
        """
        Generate compliance report for audit logs.

        Args:
            start_date: Start date for the report
            end_date: End date for the report
            user_id: Optional user ID to filter by

        Returns:
            RepositoryResult containing compliance report data
        """
        try:
            self._increment_operation_count("get_compliance_report")
            start_time = datetime.utcnow()

            filters = [
                QueryFilter("timestamp", ">=", start_date),
                QueryFilter("timestamp", "<=", end_date),
            ]

            if user_id:
                filters.append(QueryFilter("user_id", "=", user_id))

            result = await self.query(filters, QueryOptions(limit=10000))

            if not result.success:
                return RepositoryResult(
                    success=False,
                    error=f"Failed to get audit logs for compliance report: {result.error}",
                )

            audit_logs = result.data or []

            # Generate compliance metrics
            report = {
                "report_period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
                "total_events": len(audit_logs),
                "user_filter": user_id,
                "event_breakdown": {
                    "create_operations": len(
                        [log for log in audit_logs if log.action == "CREATE"]
                    ),
                    "update_operations": len(
                        [log for log in audit_logs if log.action == "UPDATE"]
                    ),
                    "delete_operations": len(
                        [log for log in audit_logs if log.action == "DELETE"]
                    ),
                    "read_operations": len(
                        [log for log in audit_logs if log.action == "READ"]
                    ),
                },
                "resource_access": {},
                "user_activity": {},
                "security_events": [],
            }

            # Analyze resource access patterns
            for log in audit_logs:
                resource_key = f"{log.resource_type}:{log.resource_id}"
                if resource_key not in report["resource_access"]:
                    report["resource_access"][resource_key] = {
                        "access_count": 0,
                        "unique_users": set(),
                        "actions": [],
                    }

                report["resource_access"][resource_key]["access_count"] += 1
                report["resource_access"][resource_key]["unique_users"].add(log.user_id)
                report["resource_access"][resource_key]["actions"].append(log.action)

            # Convert sets to counts for JSON serialization
            for resource_key in report["resource_access"]:
                report["resource_access"][resource_key]["unique_users"] = len(
                    report["resource_access"][resource_key]["unique_users"]
                )

            # Analyze user activity
            for log in audit_logs:
                if log.user_id not in report["user_activity"]:
                    report["user_activity"][log.user_id] = {
                        "total_actions": 0,
                        "actions_by_type": {},
                        "resources_accessed": set(),
                    }

                report["user_activity"][log.user_id]["total_actions"] += 1
                action_type = log.action
                report["user_activity"][log.user_id]["actions_by_type"][action_type] = (
                    report["user_activity"][log.user_id]["actions_by_type"].get(
                        action_type, 0
                    )
                    + 1
                )
                report["user_activity"][log.user_id]["resources_accessed"].add(
                    f"{log.resource_type}:{log.resource_id}"
                )

            # Convert sets to counts for JSON serialization
            for user_id in report["user_activity"]:
                report["user_activity"][user_id]["resources_accessed"] = len(
                    report["user_activity"][user_id]["resources_accessed"]
                )

            # Record performance metrics
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            self._record_response_time("get_compliance_report", response_time)

            return RepositoryResult(success=True, data=report)

        except Exception as e:
            return RepositoryResult(
                success=False, error=f"Failed to generate compliance report: {str(e)}"
            )
