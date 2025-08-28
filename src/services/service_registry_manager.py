"""
Service Registry Manager - Dependency injection container.
Manages service instances and their dependencies following clean architecture.
"""

from typing import Dict, Any, Optional
from functools import lru_cache

from ..repositories.people_repository import PeopleRepository
from ..repositories.projects_repository import ProjectsRepository
from ..repositories.subscriptions_repository import SubscriptionsRepository
from .people_service import PeopleService
from .projects_service import ProjectsService
from .subscriptions_service import SubscriptionsService
from .auth_service import AuthService
from .admin_service import AdminService


class ServiceRegistryManager:
    """Manages service instances and their dependencies."""

    def __init__(self):
        self._repositories: Dict[str, Any] = {}
        self._services: Dict[str, Any] = {}
        self._initialized = False

    def initialize(self):
        """Initialize all repositories and services."""
        if self._initialized:
            return

        # Initialize repositories
        self._repositories["people"] = PeopleRepository()
        self._repositories["projects"] = ProjectsRepository()
        self._repositories["subscriptions"] = SubscriptionsRepository()

        # Initialize services with dependency injection
        self._services["people"] = PeopleService(self._repositories["people"])
        self._services["projects"] = ProjectsService(self._repositories["projects"])
        self._services["subscriptions"] = SubscriptionsService()
        self._services["auth"] = AuthService()
        self._services["admin"] = AdminService()

        # Initialize email service
        from .email_service import EmailService

        self._services["email"] = EmailService()

        # Initialize enterprise services
        from .rbac_service import RBACService
        from .logging_service import EnterpriseLoggingService
        from .performance_service import PerformanceService

        self._services["rbac"] = RBACService()
        self._services["logging"] = EnterpriseLoggingService()
        self._services["performance"] = PerformanceService(self._services["logging"])

        self._initialized = True

    def get_people_repository(self) -> PeopleRepository:
        """Get the people repository instance."""
        self.initialize()
        return self._repositories["people"]

    def get_projects_repository(self) -> ProjectsRepository:
        """Get the projects repository instance."""
        self.initialize()
        return self._repositories["projects"]

    def get_subscriptions_repository(self) -> SubscriptionsRepository:
        """Get the subscriptions repository instance."""
        self.initialize()
        return self._repositories["subscriptions"]

    def get_people_service(self) -> PeopleService:
        """Get the people service instance."""
        self.initialize()
        return self._services["people"]

    def get_projects_service(self) -> ProjectsService:
        """Get the projects service instance."""
        self.initialize()
        return self._services["projects"]

    def get_subscriptions_service(self) -> SubscriptionsService:
        """Get the subscriptions service instance."""
        self.initialize()
        return self._services["subscriptions"]

    def get_auth_service(self) -> AuthService:
        """Get the auth service instance."""
        self.initialize()
        return self._services["auth"]

    def get_admin_service(self) -> AdminService:
        """Get the admin service instance."""
        self.initialize()
        return self._services["admin"]

    def get_email_service(self):
        """Get the email service instance."""
        self.initialize()
        return self._services["email"]

    def get_rbac_service(self):
        """Get the RBAC service instance."""
        self.initialize()
        return self._services["rbac"]

    def get_logging_service(self):
        """Get the logging service instance."""
        self.initialize()
        return self._services["logging"]

    def get_performance_service(self):
        """Get the performance service instance."""
        self.initialize()
        return self._services["performance"]

    def reset(self):
        """Reset all services and repositories (useful for testing)."""
        self._repositories.clear()
        self._services.clear()
        self._initialized = False


# Global service registry instance
service_registry = ServiceRegistryManager()


# FastAPI dependency functions
@lru_cache()
def get_service_registry() -> ServiceRegistryManager:
    """Get the global service registry instance."""
    return service_registry


def get_people_service() -> PeopleService:
    """FastAPI dependency for people service."""
    return service_registry.get_people_service()


def get_projects_service() -> ProjectsService:
    """FastAPI dependency for projects service."""
    return service_registry.get_projects_service()


def get_people_repository() -> PeopleRepository:
    """FastAPI dependency for people repository."""
    return service_registry.get_people_repository()


def get_projects_repository() -> ProjectsRepository:
    """FastAPI dependency for projects repository."""
    return service_registry.get_projects_repository()


def get_subscriptions_service() -> SubscriptionsService:
    """FastAPI dependency for subscriptions service."""
    return service_registry.get_subscriptions_service()


def get_subscriptions_repository() -> SubscriptionsRepository:
    """FastAPI dependency for subscriptions repository."""
    return service_registry.get_subscriptions_repository()


def get_auth_service() -> AuthService:
    """FastAPI dependency for auth service."""
    return service_registry.get_auth_service()


def get_admin_service() -> AdminService:
    """FastAPI dependency for admin service."""
    return service_registry.get_admin_service()


def get_email_service():
    """FastAPI dependency for email service."""
    return service_registry.get_email_service()


def get_rbac_service():
    """FastAPI dependency for RBAC service."""
    return service_registry.get_rbac_service()


def get_logging_service():
    """FastAPI dependency for logging service."""
    return service_registry.get_logging_service()


def get_performance_service():
    """FastAPI dependency for performance service."""
    return service_registry.get_performance_service()
