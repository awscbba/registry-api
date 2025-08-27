"""
Application configuration management.
"""

import os
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class Environment(str, Enum):
    """Application environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class DatabaseConfig(BaseModel):
    """Database configuration."""

    # Standardized V2 tables (Clean Architecture)
    people_table: str = Field(
        default_factory=lambda: os.getenv("PEOPLE_TABLE_V2_NAME", "PeopleTableV2")
    )
    projects_table: str = Field(
        default_factory=lambda: os.getenv("PROJECTS_TABLE_V2_NAME", "ProjectsTableV2")
    )
    subscriptions_table: str = Field(
        default_factory=lambda: os.getenv(
            "SUBSCRIPTIONS_TABLE_V2_NAME", "SubscriptionsTableV2"
        )
    )

    # Legacy tables (for migration compatibility)
    people_table_legacy: str = Field(
        default_factory=lambda: os.getenv("PEOPLE_TABLE_NAME", "PeopleTable")
    )
    projects_table_legacy: str = Field(
        default_factory=lambda: os.getenv("PROJECTS_TABLE_NAME", "ProjectsTable")
    )
    subscriptions_table_legacy: str = Field(
        default_factory=lambda: os.getenv(
            "SUBSCRIPTIONS_TABLE_NAME", "SubscriptionsTable"
        )
    )

    region: str = Field(default_factory=lambda: os.getenv("AWS_REGION", "us-east-1"))


class AuthConfig(BaseModel):
    """Authentication configuration."""

    jwt_secret: str = Field(
        default_factory=lambda: os.getenv(
            "JWT_SECRET", "your-jwt-secret-change-in-production"
        )
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_hours: int = 24
    refresh_token_expire_days: int = 30


class EmailConfig(BaseModel):
    """Email service configuration."""

    from_email: str = Field(
        default_factory=lambda: os.getenv("SES_FROM_EMAIL", "noreply@example.com")
    )
    region: str = Field(default_factory=lambda: os.getenv("AWS_REGION", "us-east-1"))


class AppConfig(BaseModel):
    """Main application configuration."""

    environment: Environment = Field(
        default_factory=lambda: Environment(os.getenv("ENVIRONMENT", "development"))
    )
    debug: bool = Field(
        default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true"
    )
    frontend_url: str = Field(
        default_factory=lambda: os.getenv("FRONTEND_URL", "http://localhost:3000")
    )

    # Sub-configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    email: EmailConfig = Field(default_factory=EmailConfig)


# Global configuration instance
config = AppConfig()
