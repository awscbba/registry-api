"""
Unified Configuration Management for Service Registry

This module provides centralized configuration management for all services,
ensuring consistent configuration access and environment variable handling.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class Environment(Enum):
    """Application environment types"""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


@dataclass
class DatabaseConfig:
    """Database configuration"""

    people_table: str = field(
        default_factory=lambda: os.environ.get("PEOPLE_TABLE_NAME", "PeopleTable")
    )
    projects_table: str = field(
        default_factory=lambda: os.environ.get("PROJECTS_TABLE_NAME", "ProjectsTable")
    )
    subscriptions_table: str = field(
        default_factory=lambda: os.environ.get(
            "SUBSCRIPTIONS_TABLE_NAME", "SubscriptionsTable"
        )
    )
    audit_logs_table: str = field(
        default_factory=lambda: os.environ.get(
            "AUDIT_LOGS_TABLE_NAME", "AuditLogsTable"
        )
    )
    password_reset_tokens_table: str = field(
        default_factory=lambda: os.environ.get(
            "PASSWORD_RESET_TOKENS_TABLE_NAME", "PasswordResetTokensTable"
        )
    )
    password_history_table: str = field(
        default_factory=lambda: os.environ.get(
            "PASSWORD_HISTORY_TABLE", "PasswordHistoryTable"
        )
    )
    sessions_table: str = field(
        default_factory=lambda: os.environ.get("SESSIONS_TABLE_NAME", "SessionsTable")
    )
    rate_limit_table: str = field(
        default_factory=lambda: os.environ.get(
            "RATE_LIMIT_TABLE_NAME", "RateLimitTable"
        )
    )
    email_tracking_table: str = field(
        default_factory=lambda: os.environ.get(
            "EMAIL_TRACKING_TABLE_NAME", "EmailTrackingTable"
        )
    )

    region: str = field(
        default_factory=lambda: os.environ.get("AWS_REGION", "us-east-1")
    )


@dataclass
class AuthConfig:
    """Authentication configuration"""

    jwt_secret: str = field(
        default_factory=lambda: os.environ.get(
            "JWT_SECRET", "your-jwt-secret-change-in-production-please"
        )
    )
    access_token_expiry_hours: int = field(
        default_factory=lambda: int(os.environ.get("ACCESS_TOKEN_EXPIRY_HOURS", "1"))
    )
    refresh_token_expiry_days: int = field(
        default_factory=lambda: int(os.environ.get("REFRESH_TOKEN_EXPIRY_DAYS", "30"))
    )
    max_failed_attempts: int = field(
        default_factory=lambda: int(os.environ.get("MAX_FAILED_ATTEMPTS", "5"))
    )
    account_lockout_minutes: int = field(
        default_factory=lambda: int(os.environ.get("ACCOUNT_LOCKOUT_MINUTES", "30"))
    )


@dataclass
class EmailConfig:
    """Email service configuration"""

    ses_region: str = field(
        default_factory=lambda: os.environ.get("SES_REGION", "us-east-1")
    )
    from_email: str = field(
        default_factory=lambda: os.environ.get("FROM_EMAIL", "noreply@example.com")
    )
    from_name: str = field(
        default_factory=lambda: os.environ.get("FROM_NAME", "People Register")
    )
    frontend_url: str = field(
        default_factory=lambda: os.environ.get("FRONTEND_URL", "https://example.com")
    )
    support_email: str = field(
        default_factory=lambda: os.environ.get("SUPPORT_EMAIL", "support@example.com")
    )


@dataclass
class SecurityConfig:
    """Security configuration"""

    csrf_secret: str = field(
        default_factory=lambda: os.environ.get(
            "CSRF_SECRET", "default-csrf-secret-change-in-production"
        )
    )
    rate_limit_requests_per_minute: int = field(
        default_factory=lambda: int(os.environ.get("RATE_LIMIT_RPM", "60"))
    )
    rate_limit_requests_per_hour: int = field(
        default_factory=lambda: int(os.environ.get("RATE_LIMIT_RPH", "1000"))
    )
    password_min_length: int = field(
        default_factory=lambda: int(os.environ.get("PASSWORD_MIN_LENGTH", "8"))
    )
    password_require_uppercase: bool = field(
        default_factory=lambda: os.environ.get(
            "PASSWORD_REQUIRE_UPPERCASE", "true"
        ).lower()
        == "true"
    )
    password_require_lowercase: bool = field(
        default_factory=lambda: os.environ.get(
            "PASSWORD_REQUIRE_LOWERCASE", "true"
        ).lower()
        == "true"
    )
    password_require_numbers: bool = field(
        default_factory=lambda: os.environ.get(
            "PASSWORD_REQUIRE_NUMBERS", "true"
        ).lower()
        == "true"
    )
    password_require_special: bool = field(
        default_factory=lambda: os.environ.get(
            "PASSWORD_REQUIRE_SPECIAL", "true"
        ).lower()
        == "true"
    )
    password_history_count: int = field(
        default_factory=lambda: int(os.environ.get("PASSWORD_HISTORY_COUNT", "5"))
    )


@dataclass
class ServiceConfig:
    """Main service configuration container"""

    environment: Environment = field(
        default_factory=lambda: Environment(
            os.environ.get("ENVIRONMENT", "development")
        )
    )
    debug: bool = field(
        default_factory=lambda: os.environ.get("DEBUG", "false").lower() == "true"
    )

    # Sub-configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)

    def __post_init__(self):
        """Validate configuration after initialization"""
        self._validate_config()

    def _validate_config(self):
        """Validate configuration values"""
        # Validate JWT secret in production
        if self.environment == Environment.PRODUCTION:
            if self.auth.jwt_secret == "your-jwt-secret-change-in-production-please":
                raise ValueError("JWT_SECRET must be changed in production environment")

            if self.security.csrf_secret == "default-csrf-secret-change-in-production":
                raise ValueError(
                    "CSRF_SECRET must be changed in production environment"
                )

        # Validate email configuration
        if not self.email.from_email or "@" not in self.email.from_email:
            raise ValueError("FROM_EMAIL must be a valid email address")

        # Validate password policy
        if self.security.password_min_length < 8:
            raise ValueError("PASSWORD_MIN_LENGTH must be at least 8")

    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment == Environment.PRODUCTION

    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment == Environment.DEVELOPMENT

    def get_table_name(self, table_type: str) -> str:
        """Get table name by type"""
        table_mapping = {
            "people": self.database.people_table,
            "projects": self.database.projects_table,
            "subscriptions": self.database.subscriptions_table,
            "audit_logs": self.database.audit_logs_table,
            "password_reset_tokens": self.database.password_reset_tokens_table,
            "password_history": self.database.password_history_table,
            "sessions": self.database.sessions_table,
            "rate_limit": self.database.rate_limit_table,
            "email_tracking": self.database.email_tracking_table,
        }

        if table_type not in table_mapping:
            raise ValueError(f"Unknown table type: {table_type}")

        return table_mapping[table_type]


# Global configuration instance
_config_instance: Optional[ServiceConfig] = None


def get_config() -> ServiceConfig:
    """Get the global configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = ServiceConfig()
    return _config_instance


def reset_config():
    """Reset the global configuration instance (mainly for testing)"""
    global _config_instance
    _config_instance = None
