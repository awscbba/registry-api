"""
Enterprise-grade audit logging and security monitoring.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from enum import Enum


class AuditEventType(Enum):
    """Types of audit events."""

    # Authentication events
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILED = "auth.login.failed"
    LOGOUT = "auth.logout"
    PASSWORD_CHANGED = "auth.password.changed"
    PASSWORD_RESET_REQUESTED = "auth.password.reset.requested"
    PASSWORD_RESET_COMPLETED = "auth.password.reset.completed"
    ACCOUNT_LOCKED = "auth.account.locked"

    # Data access events
    DATA_READ = "data.read"
    DATA_CREATE = "data.create"
    DATA_UPDATE = "data.update"
    DATA_DELETE = "data.delete"

    # Admin events
    ADMIN_ACTION = "admin.action"
    BULK_OPERATION = "admin.bulk.operation"
    PERMISSION_GRANTED = "admin.permission.granted"
    PERMISSION_REVOKED = "admin.permission.revoked"

    # Security events
    UNAUTHORIZED_ACCESS = "security.unauthorized.access"
    SUSPICIOUS_ACTIVITY = "security.suspicious.activity"
    RATE_LIMIT_EXCEEDED = "security.rate.limit.exceeded"
    INPUT_VALIDATION_FAILED = "security.input.validation.failed"

    # System events
    SYSTEM_ERROR = "system.error"
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"


class AuditLogger:
    """Enterprise audit logging service."""

    def __init__(self):
        # Configure audit logger
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)

        # Create formatter for structured logging
        formatter = logging.Formatter(
            "%(asctime)s - AUDIT - %(levelname)s - %(message)s"
        )

        # Add console handler (in production, this would be a secure log aggregator)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[str] = None,
        result: str = "success",
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Log an audit event."""

        audit_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type.value,
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action,
            "result": result,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "details": details or {},
        }

        # Remove None values
        audit_record = {k: v for k, v in audit_record.items() if v is not None}

        # Log as structured JSON
        self.logger.info(json.dumps(audit_record))

    def log_authentication_event(
        self,
        event_type: AuditEventType,
        user_id: str,
        result: str = "success",
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log authentication-related events."""
        self.log_event(
            event_type=event_type,
            user_id=user_id,
            result=result,
            ip_address=ip_address,
            details=details,
        )

    def log_data_access(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        user_id: str,
        result: str = "success",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log data access events."""
        event_type_map = {
            "read": AuditEventType.DATA_READ,
            "create": AuditEventType.DATA_CREATE,
            "update": AuditEventType.DATA_UPDATE,
            "delete": AuditEventType.DATA_DELETE,
        }

        event_type = event_type_map.get(action, AuditEventType.DATA_READ)

        self.log_event(
            event_type=event_type,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            result=result,
            details=details,
        )

    def log_security_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log security-related events."""
        self.log_event(
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            details=details,
            result="security_event",
        )

    def log_admin_action(
        self,
        action: str,
        admin_user_id: str,
        target_resource_type: Optional[str] = None,
        target_resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log administrative actions."""
        self.log_event(
            event_type=AuditEventType.ADMIN_ACTION,
            user_id=admin_user_id,
            resource_type=target_resource_type,
            resource_id=target_resource_id,
            action=action,
            details=details,
        )

    def log_system_error(
        self,
        error_type: str,
        error_message: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log system errors."""
        self.log_event(
            event_type=AuditEventType.SYSTEM_ERROR,
            user_id=user_id,
            result="error",
            details={
                "error_type": error_type,
                "error_message": error_message,
                **(details or {}),
            },
        )


class SecurityMonitor:
    """Security monitoring and alerting."""

    def __init__(self):
        self.audit_logger = AuditLogger()

    def detect_suspicious_activity(
        self,
        user_id: str,
        activity_type: str,
        details: Dict[str, Any],
    ) -> bool:
        """Detect and log suspicious activities."""

        # Simple heuristics for suspicious activity
        suspicious_indicators = [
            "rapid_requests",
            "unusual_access_pattern",
            "multiple_failed_logins",
            "access_from_new_location",
        ]

        if activity_type in suspicious_indicators:
            self.audit_logger.log_security_event(
                event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
                user_id=user_id,
                details={
                    "activity_type": activity_type,
                    **details,
                },
            )
            return True

        return False

    def check_rate_limit_violation(
        self,
        user_id: str,
        endpoint: str,
        request_count: int,
        time_window: int,
    ):
        """Check and log rate limit violations."""

        # Simple rate limiting check
        if request_count > 100:  # 100 requests per time window
            self.audit_logger.log_security_event(
                event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
                user_id=user_id,
                details={
                    "endpoint": endpoint,
                    "request_count": request_count,
                    "time_window": time_window,
                },
            )
            return True

        return False


# Global instances
audit_logger = AuditLogger()
security_monitor = SecurityMonitor()
