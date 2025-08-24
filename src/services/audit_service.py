"""
Audit Service - Domain service for audit trail operations.
Implements the Service Registry pattern with Repository pattern integration.
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import uuid

from ..core.base_service import BaseService
from ..repositories.audit_repository import AuditRepository
from ..utils.logging_config import get_handler_logger
from ..utils.error_handler import handle_database_error
from ..utils.response_models import create_v2_response


class AuditService(BaseService):
    """Service for managing audit trail operations with repository pattern."""

    def __init__(self):
        super().__init__("audit_service")
        # Use environment variable for table name
        table_name = os.getenv("AUDIT_LOGS_TABLE_NAME", "AuditLogsTable")
        # Initialize repository for clean data access
        self.audit_repository = AuditRepository(table_name=table_name)
        self.logger = get_handler_logger("audit_service")

    async def initialize(self):
        """Initialize the audit service with repository pattern."""
        try:
            # Test repository connectivity with a simple count operation
            count_result = await self.audit_repository.count()
            if count_result.success:
                self.logger.info(
                    f"Audit service initialized successfully. Found {count_result.data} audit logs."
                )
                return True
            else:
                self.logger.error(
                    f"Repository health check failed: {count_result.error}"
                )
                return False
        except Exception as e:
            self.logger.error(f"Failed to initialize audit service: {str(e)}")
            return False

    async def health_check(self):
        """Check the health of the audit service using repository pattern."""
        from ..core.base_service import HealthCheck, ServiceStatus
        import time

        start_time = time.time()

        try:
            import asyncio

            # Test repository connectivity with timeout
            try:
                count_result = await asyncio.wait_for(
                    self.audit_repository.count(), timeout=1.0
                )
                performance_stats = self.audit_repository.get_performance_stats()
                response_time = (time.time() - start_time) * 1000

                if count_result.success:
                    return HealthCheck(
                        service_name=self.service_name,
                        status=ServiceStatus.HEALTHY,
                        message="Audit service is healthy",
                        details={
                            "repository": "connected",
                            "audit_log_count": count_result.data,
                            "performance": performance_stats,
                            "timestamp": datetime.now().isoformat(),
                        },
                        response_time_ms=response_time,
                    )
                else:
                    return HealthCheck(
                        service_name=self.service_name,
                        status=ServiceStatus.UNHEALTHY,
                        message="Repository connectivity failed",
                        details={
                            "repository": "disconnected",
                            "error": count_result.error,
                            "timestamp": datetime.now().isoformat(),
                        },
                        response_time_ms=response_time,
                    )
            except asyncio.TimeoutError:
                response_time = (time.time() - start_time) * 1000
                return HealthCheck(
                    service_name=self.service_name,
                    status=ServiceStatus.DEGRADED,
                    message="Repository check timed out",
                    details={
                        "repository": "timeout",
                        "timestamp": datetime.now().isoformat(),
                    },
                    response_time_ms=response_time,
                )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.logger.error(f"Audit service health check failed: {str(e)}")
            return HealthCheck(
                service_name=self.service_name,
                status=ServiceStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                details={
                    "repository": "disconnected",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                },
                response_time_ms=response_time,
            )

    async def create_audit_log(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new audit log entry."""
        try:
            self.logger.log_api_request("POST", "/audit/logs")

            result = await self.audit_repository.create_audit_log(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            if result.success:
                audit_data = (
                    result.data.dict() if hasattr(result.data, "dict") else result.data
                )
                response = create_v2_response(
                    audit_data,
                    metadata={
                        "service": "audit_service",
                        "version": "repository",
                        "created_at": datetime.now().isoformat(),
                    },
                )
                self.logger.log_api_response("POST", "/audit/logs", 201)
                return response
            else:
                raise Exception(f"Repository error: {result.error}")

        except Exception as e:
            self.logger.error(
                "Failed to create audit log",
                operation="create_audit_log",
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                error_type=type(e).__name__,
            )
            raise handle_database_error("creating audit log", e)

    async def get_user_audit_trail(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Get audit trail for a specific user."""
        try:
            self.logger.log_api_request("GET", f"/audit/users/{user_id}")

            result = await self.audit_repository.get_user_audit_trail(
                user_id=user_id, start_date=start_date, end_date=end_date, limit=limit
            )

            if result.success:
                audit_data = (
                    [log.dict() if hasattr(log, "dict") else log for log in result.data]
                    if result.data
                    else []
                )

                response = create_v2_response(
                    audit_data,
                    metadata={
                        "user_id": user_id,
                        "count": len(audit_data),
                        "start_date": start_date.isoformat() if start_date else None,
                        "end_date": end_date.isoformat() if end_date else None,
                        "service": "audit_service",
                        "version": "repository",
                    },
                )
                self.logger.log_api_response(
                    "GET",
                    f"/audit/users/{user_id}",
                    200,
                    additional_context={"count": len(audit_data)},
                )
                return response
            else:
                raise Exception(f"Repository error: {result.error}")

        except Exception as e:
            self.logger.error(
                "Failed to retrieve user audit trail",
                operation="get_user_audit_trail",
                user_id=user_id,
                error_type=type(e).__name__,
            )
            raise handle_database_error("retrieving user audit trail", e)

    async def get_resource_audit_trail(
        self, resource_type: str, resource_id: str, limit: int = 100
    ) -> Dict[str, Any]:
        """Get audit trail for a specific resource."""
        try:
            self.logger.log_api_request(
                "GET", f"/audit/resources/{resource_type}/{resource_id}"
            )

            result = await self.audit_repository.get_resource_audit_trail(
                resource_type=resource_type, resource_id=resource_id, limit=limit
            )

            if result.success:
                audit_data = (
                    [log.dict() if hasattr(log, "dict") else log for log in result.data]
                    if result.data
                    else []
                )

                response = create_v2_response(
                    audit_data,
                    metadata={
                        "resource_type": resource_type,
                        "resource_id": resource_id,
                        "count": len(audit_data),
                        "service": "audit_service",
                        "version": "repository",
                    },
                )
                self.logger.log_api_response(
                    "GET",
                    f"/audit/resources/{resource_type}/{resource_id}",
                    200,
                    additional_context={"count": len(audit_data)},
                )
                return response
            else:
                raise Exception(f"Repository error: {result.error}")

        except Exception as e:
            self.logger.error(
                "Failed to retrieve resource audit trail",
                operation="get_resource_audit_trail",
                resource_type=resource_type,
                resource_id=resource_id,
                error_type=type(e).__name__,
            )
            raise handle_database_error("retrieving resource audit trail", e)

    async def get_audit_logs_by_action(
        self,
        action: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Get audit logs filtered by action type."""
        try:
            self.logger.log_api_request("GET", f"/audit/actions/{action}")

            result = await self.audit_repository.get_audit_logs_by_action(
                action=action, start_date=start_date, end_date=end_date, limit=limit
            )

            if result.success:
                audit_data = (
                    [log.dict() if hasattr(log, "dict") else log for log in result.data]
                    if result.data
                    else []
                )

                response = create_v2_response(
                    audit_data,
                    metadata={
                        "action": action,
                        "count": len(audit_data),
                        "start_date": start_date.isoformat() if start_date else None,
                        "end_date": end_date.isoformat() if end_date else None,
                        "service": "audit_service",
                        "version": "repository",
                    },
                )
                self.logger.log_api_response(
                    "GET",
                    f"/audit/actions/{action}",
                    200,
                    additional_context={"count": len(audit_data)},
                )
                return response
            else:
                raise Exception(f"Repository error: {result.error}")

        except Exception as e:
            self.logger.error(
                "Failed to retrieve audit logs by action",
                operation="get_audit_logs_by_action",
                action=action,
                error_type=type(e).__name__,
            )
            raise handle_database_error("retrieving audit logs by action", e)

    async def get_recent_audit_logs(
        self, hours: int = 24, limit: int = 100
    ) -> Dict[str, Any]:
        """Get recent audit logs within specified hours."""
        try:
            self.logger.log_api_request("GET", f"/audit/recent/{hours}h")

            result = await self.audit_repository.get_recent_audit_logs(
                hours=hours, limit=limit
            )

            if result.success:
                audit_data = (
                    [log.dict() if hasattr(log, "dict") else log for log in result.data]
                    if result.data
                    else []
                )

                response = create_v2_response(
                    audit_data,
                    metadata={
                        "hours": hours,
                        "count": len(audit_data),
                        "service": "audit_service",
                        "version": "repository",
                    },
                )
                self.logger.log_api_response(
                    "GET",
                    f"/audit/recent/{hours}h",
                    200,
                    additional_context={"count": len(audit_data)},
                )
                return response
            else:
                raise Exception(f"Repository error: {result.error}")

        except Exception as e:
            self.logger.error(
                "Failed to retrieve recent audit logs",
                operation="get_recent_audit_logs",
                hours=hours,
                error_type=type(e).__name__,
            )
            raise handle_database_error("retrieving recent audit logs", e)

    async def get_audit_summary(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Get audit summary statistics for a date range."""
        try:
            self.logger.log_api_request("GET", "/audit/summary")

            result = await self.audit_repository.get_audit_summary(
                start_date=start_date, end_date=end_date
            )

            if result.success:
                response = create_v2_response(
                    result.data,
                    metadata={
                        "service": "audit_service",
                        "version": "repository",
                        "report_type": "summary",
                        "generated_at": datetime.now().isoformat(),
                    },
                )
                self.logger.log_api_response("GET", "/audit/summary", 200)
                return response
            else:
                raise Exception(f"Repository error: {result.error}")

        except Exception as e:
            self.logger.error(
                "Failed to generate audit summary",
                operation="get_audit_summary",
                error_type=type(e).__name__,
            )
            raise handle_database_error("generating audit summary", e)

    async def get_compliance_report(
        self, start_date: datetime, end_date: datetime, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate compliance report for audit logs."""
        try:
            self.logger.log_api_request("GET", "/audit/compliance")

            result = await self.audit_repository.get_compliance_report(
                start_date=start_date, end_date=end_date, user_id=user_id
            )

            if result.success:
                response = create_v2_response(
                    result.data,
                    metadata={
                        "service": "audit_service",
                        "version": "repository",
                        "report_type": "compliance",
                        "generated_at": datetime.now().isoformat(),
                    },
                )
                self.logger.log_api_response("GET", "/audit/compliance", 200)
                return response
            else:
                raise Exception(f"Repository error: {result.error}")

        except Exception as e:
            self.logger.error(
                "Failed to generate compliance report",
                operation="get_compliance_report",
                error_type=type(e).__name__,
            )
            raise handle_database_error("generating compliance report", e)

    async def search_audit_logs(
        self,
        search_term: str,
        search_fields: Optional[List[str]] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Search audit logs by term in specified fields."""
        try:
            self.logger.log_api_request("GET", f"/audit/search/{search_term}")

            result = await self.audit_repository.search_audit_logs(
                search_term=search_term, search_fields=search_fields, limit=limit
            )

            if result.success:
                audit_data = (
                    [log.dict() if hasattr(log, "dict") else log for log in result.data]
                    if result.data
                    else []
                )

                response = create_v2_response(
                    audit_data,
                    metadata={
                        "search_term": search_term,
                        "search_fields": search_fields,
                        "count": len(audit_data),
                        "service": "audit_service",
                        "version": "repository",
                    },
                )
                self.logger.log_api_response(
                    "GET",
                    f"/audit/search/{search_term}",
                    200,
                    additional_context={"count": len(audit_data)},
                )
                return response
            else:
                raise Exception(f"Repository error: {result.error}")

        except Exception as e:
            self.logger.error(
                "Failed to search audit logs",
                operation="search_audit_logs",
                search_term=search_term,
                error_type=type(e).__name__,
            )
            raise handle_database_error("searching audit logs", e)

    async def delete_old_audit_logs(self, older_than_days: int) -> Dict[str, Any]:
        """Delete audit logs older than specified days (for compliance/cleanup)."""
        try:
            self.logger.log_api_request("DELETE", f"/audit/cleanup/{older_than_days}d")

            result = await self.audit_repository.delete_old_audit_logs(
                older_than_days=older_than_days
            )

            if result.success:
                response = create_v2_response(
                    {"deleted_count": result.data, "older_than_days": older_than_days},
                    metadata={
                        "service": "audit_service",
                        "version": "repository",
                        "operation": "cleanup",
                        "deleted_at": datetime.now().isoformat(),
                    },
                )
                self.logger.log_api_response(
                    "DELETE",
                    f"/audit/cleanup/{older_than_days}d",
                    200,
                    additional_context={"deleted_count": result.data},
                )
                return response
            else:
                raise Exception(f"Repository error: {result.error}")

        except Exception as e:
            self.logger.error(
                "Failed to delete old audit logs",
                operation="delete_old_audit_logs",
                older_than_days=older_than_days,
                error_type=type(e).__name__,
            )
            raise handle_database_error("deleting old audit logs", e)

    async def get_audit_performance_stats(self) -> Dict[str, Any]:
        """Get repository performance statistics."""
        try:
            stats = self.audit_repository.get_performance_stats()
            return create_v2_response(
                stats,
                metadata={
                    "service": "audit_service",
                    "version": "repository",
                    "stats_type": "performance",
                    "timestamp": datetime.now().isoformat(),
                },
            )
        except Exception as e:
            self.logger.error(
                "Failed to get performance stats",
                operation="get_audit_performance_stats",
                error_type=type(e).__name__,
            )
            raise handle_database_error("getting performance stats", e)
