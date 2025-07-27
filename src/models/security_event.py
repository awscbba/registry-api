"""
Task 19: Security Event Model
Data models for security events and monitoring
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime

class SecurityEventType(Enum):
    """Types of security events for monitoring"""

    # Authentication events
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "FAILED_LOGIN"
    LOGOUT = "LOGOUT"

    # Password events
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    PASSWORD_RESET_REQUESTED = "PASSWORD_RESET_REQUESTED"
    PASSWORD_RESET_COMPLETED = "PASSWORD_RESET_COMPLETED"

    # Account events
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    ACCOUNT_UNLOCKED = "ACCOUNT_UNLOCKED"
    ACCOUNT_CREATED = "ACCOUNT_CREATED"
    ACCOUNT_DEACTIVATED = "ACCOUNT_DEACTIVATED"
    PROFILE_UPDATE = "PROFILE_UPDATE"

    # Admin events
    ADMIN_PASSWORD_RESET = "ADMIN_PASSWORD_RESET"
    ADMIN_ACCOUNT_UNLOCK = "ADMIN_ACCOUNT_UNLOCK"
    ADMIN_LOGIN = "ADMIN_LOGIN"

    # Security events
    SUSPICIOUS_ACTIVITY = "SUSPICIOUS_ACTIVITY"
    BRUTE_FORCE_ATTEMPT = "BRUTE_FORCE_ATTEMPT"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INVALID_TOKEN = "INVALID_TOKEN"

    # Data access events
    DATA_ACCESS = "DATA_ACCESS"
    PERSON_ACCESS = "PERSON_ACCESS"
    PERSON_LIST_ACCESS = "PERSON_LIST_ACCESS"
    PERSON_SEARCH = "PERSON_SEARCH"

    # Session events
    SESSION_CREATED = "SESSION_CREATED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    SESSION_INVALIDATED = "SESSION_INVALIDATED"
    MULTIPLE_SESSIONS_DETECTED = "MULTIPLE_SESSIONS_DETECTED"

class SecurityEventSeverity(Enum):
    """Severity levels for security events"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class SecurityEvent:
    """Security event data model"""

    id: str
    event_type: SecurityEventType
    timestamp: datetime
    severity: SecurityEventSeverity
    user_email: Optional[str] = None
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    processed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB storage"""
        return {
            'id': self.id,
            'eventType': self.event_type.value,
            'timestamp': self.timestamp.isoformat(),
            'severity': self.severity.value,
            'userEmail': self.user_email,
            'userId': self.user_id,
            'ipAddress': self.ip_address,
            'userAgent': self.user_agent,
            'details': self.details or {},
            'processed': self.processed
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SecurityEvent':
        """Create from dictionary (DynamoDB item)"""
        return cls(
            id=data['id'],
            event_type=SecurityEventType(data['eventType']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            severity=SecurityEventSeverity(data['severity']),
            user_email=data.get('userEmail'),
            user_id=data.get('userId'),
            ip_address=data.get('ipAddress'),
            user_agent=data.get('userAgent'),
            details=data.get('details', {}),
            processed=data.get('processed', False)
        )

@dataclass
class SecurityAlert:
    """Security alert for dashboard notifications"""

    id: str
    title: str
    message: str
    severity: SecurityEventSeverity
    event_type: SecurityEventType
    timestamp: datetime
    user_email: Optional[str] = None
    ip_address: Optional[str] = None
    action_required: bool = False
    acknowledged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'severity': self.severity.value,
            'eventType': self.event_type.value,
            'timestamp': self.timestamp.isoformat(),
            'userEmail': self.user_email,
            'ipAddress': self.ip_address,
            'actionRequired': self.action_required,
            'acknowledged': self.acknowledged
        }

@dataclass
class DashboardMetrics:
    """Dashboard metrics summary"""

    period_start: datetime
    period_end: datetime
    total_events: int
    failed_logins: int
    password_resets: int
    account_lockouts: int
    active_sessions: int
    high_severity_events: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'periodStart': self.period_start.isoformat(),
            'periodEnd': self.period_end.isoformat(),
            'totalEvents': self.total_events,
            'failedLogins': self.failed_logins,
            'passwordResets': self.password_resets,
            'accountLockouts': self.account_lockouts,
            'activeSessions': self.active_sessions,
            'highSeverityEvents': self.high_severity_events
        }

@dataclass
class UserSecurityProfile:
    """User security profile for monitoring"""

    user_id: str
    email: str
    failed_login_attempts: int
    last_login: Optional[datetime]
    last_password_change: Optional[datetime]
    active_sessions: int
    is_locked: bool
    locked_until: Optional[datetime]
    security_events_count: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'userId': self.user_id,
            'email': self.email,
            'failedLoginAttempts': self.failed_login_attempts,
            'lastLogin': self.last_login.isoformat() if self.last_login else None,
            'lastPasswordChange': self.last_password_change.isoformat() if self.last_password_change else None,
            'activeSessions': self.active_sessions,
            'isLocked': self.is_locked,
            'lockedUntil': self.locked_until.isoformat() if self.locked_until else None,
            'securityEventsCount': self.security_events_count
        }

# Security event severity mapping
EVENT_SEVERITY_MAPPING = {
    SecurityEventType.LOGIN_SUCCESS: SecurityEventSeverity.LOW,
    SecurityEventType.LOGIN_FAILED: SecurityEventSeverity.MEDIUM,
    SecurityEventType.LOGOUT: SecurityEventSeverity.LOW,

    SecurityEventType.PASSWORD_CHANGED: SecurityEventSeverity.LOW,
    SecurityEventType.PASSWORD_RESET_REQUESTED: SecurityEventSeverity.MEDIUM,
    SecurityEventType.PASSWORD_RESET_COMPLETED: SecurityEventSeverity.MEDIUM,

    SecurityEventType.ACCOUNT_LOCKED: SecurityEventSeverity.HIGH,
    SecurityEventType.ACCOUNT_UNLOCKED: SecurityEventSeverity.MEDIUM,
    SecurityEventType.ACCOUNT_CREATED: SecurityEventSeverity.LOW,
    SecurityEventType.ACCOUNT_DEACTIVATED: SecurityEventSeverity.MEDIUM,
    SecurityEventType.PROFILE_UPDATE: SecurityEventSeverity.LOW,

    SecurityEventType.ADMIN_PASSWORD_RESET: SecurityEventSeverity.MEDIUM,
    SecurityEventType.ADMIN_ACCOUNT_UNLOCK: SecurityEventSeverity.MEDIUM,
    SecurityEventType.ADMIN_LOGIN: SecurityEventSeverity.MEDIUM,

    SecurityEventType.SUSPICIOUS_ACTIVITY: SecurityEventSeverity.HIGH,
    SecurityEventType.BRUTE_FORCE_ATTEMPT: SecurityEventSeverity.CRITICAL,
    SecurityEventType.RATE_LIMIT_EXCEEDED: SecurityEventSeverity.HIGH,
    SecurityEventType.INVALID_TOKEN: SecurityEventSeverity.MEDIUM,

    SecurityEventType.SESSION_CREATED: SecurityEventSeverity.LOW,
    SecurityEventType.SESSION_EXPIRED: SecurityEventSeverity.LOW,
    SecurityEventType.SESSION_INVALIDATED: SecurityEventSeverity.LOW,
    SecurityEventType.MULTIPLE_SESSIONS_DETECTED: SecurityEventSeverity.MEDIUM,

    SecurityEventType.DATA_ACCESS: SecurityEventSeverity.LOW,
    SecurityEventType.PERSON_ACCESS: SecurityEventSeverity.LOW,
    SecurityEventType.PERSON_LIST_ACCESS: SecurityEventSeverity.LOW,
    SecurityEventType.PERSON_SEARCH: SecurityEventSeverity.LOW,
}

def get_default_severity(event_type: SecurityEventType) -> SecurityEventSeverity:
    """Get default severity for an event type"""
    return EVENT_SEVERITY_MAPPING.get(event_type, SecurityEventSeverity.MEDIUM)
