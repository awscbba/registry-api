"""
Audit models for tracking system activities and compliance.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class AuditAction(str, Enum):
    """Enumeration of audit actions."""

    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    ADMIN_ACTION = "ADMIN_ACTION"
    SECURITY_EVENT = "SECURITY_EVENT"
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"


class AuditSeverity(str, Enum):
    """Enumeration of audit severity levels."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AuditLog(BaseModel):
    """Model for audit log entries."""

    id: str = Field(..., description="Unique identifier for the audit log entry")
    user_id: str = Field(..., description="ID of the user who performed the action")
    action: AuditAction = Field(..., description="Type of action performed")
    resource_type: str = Field(..., description="Type of resource affected")
    resource_id: Optional[str] = Field(None, description="ID of the affected resource")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When the action occurred"
    )
    severity: AuditSeverity = Field(
        default=AuditSeverity.LOW, description="Severity level of the action"
    )
    ip_address: Optional[str] = Field(None, description="IP address of the user")
    user_agent: Optional[str] = Field(None, description="User agent string")
    details: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional details about the action"
    )
    success: bool = Field(default=True, description="Whether the action was successful")
    error_message: Optional[str] = Field(
        None, description="Error message if action failed"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class AuditLogCreate(BaseModel):
    """Model for creating audit log entries."""

    user_id: str = Field(..., description="ID of the user who performed the action")
    action: AuditAction = Field(..., description="Type of action performed")
    resource_type: str = Field(..., description="Type of resource affected")
    resource_id: Optional[str] = Field(None, description="ID of the affected resource")
    severity: AuditSeverity = Field(
        default=AuditSeverity.LOW, description="Severity level of the action"
    )
    ip_address: Optional[str] = Field(None, description="IP address of the user")
    user_agent: Optional[str] = Field(None, description="User agent string")
    details: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional details about the action"
    )
    success: bool = Field(default=True, description="Whether the action was successful")
    error_message: Optional[str] = Field(
        None, description="Error message if action failed"
    )


class AuditLogQuery(BaseModel):
    """Model for querying audit logs."""

    user_id: Optional[str] = Field(None, description="Filter by user ID")
    action: Optional[AuditAction] = Field(None, description="Filter by action type")
    resource_type: Optional[str] = Field(None, description="Filter by resource type")
    resource_id: Optional[str] = Field(None, description="Filter by resource ID")
    severity: Optional[AuditSeverity] = Field(
        None, description="Filter by severity level"
    )
    start_date: Optional[datetime] = Field(None, description="Filter by start date")
    end_date: Optional[datetime] = Field(None, description="Filter by end date")
    success: Optional[bool] = Field(None, description="Filter by success status")
    limit: int = Field(default=100, description="Maximum number of results to return")
    offset: int = Field(default=0, description="Number of results to skip")


class AuditLogResponse(BaseModel):
    """Model for audit log API responses."""

    logs: list[AuditLog] = Field(..., description="List of audit log entries")
    total_count: int = Field(..., description="Total number of matching audit logs")
    has_more: bool = Field(..., description="Whether there are more results available")


class AuditSummary(BaseModel):
    """Model for audit summary statistics."""

    total_logs: int = Field(..., description="Total number of audit logs")
    logs_by_action: Dict[str, int] = Field(
        ..., description="Count of logs by action type"
    )
    logs_by_severity: Dict[str, int] = Field(
        ..., description="Count of logs by severity level"
    )
    logs_by_user: Dict[str, int] = Field(..., description="Count of logs by user")
    failed_actions: int = Field(..., description="Number of failed actions")
    success_rate: float = Field(..., description="Success rate as a percentage")
    date_range: Dict[str, datetime] = Field(
        ..., description="Date range of the audit logs"
    )
