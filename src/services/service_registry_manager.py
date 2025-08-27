"""
Service Registry Manager - Dependency injection container.
Manages service instances and their dependencies following clean architecture.
"""

from typing import Dict, Any, Optional
from functools import lru_cache

from ..repositories.people_repository import PeopleRepository
from ..repositories.projects_repository import ProjectsRepository
from .people_service import PeopleService
from .projects_service import ProjectsService


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

        # Initialize services with dependency injection
        self._services["people"] = PeopleService(self._repositories["people"])
        self._services["projects"] = ProjectsService(self._repositories["projects"])

        self._initialized = True

    def get_people_repository(self) -> PeopleRepository:
        """Get the people repository instance."""
        self.initialize()
        return self._repositories["people"]

    def get_projects_repository(self) -> ProjectsRepository:
        """Get the projects repository instance."""
        self.initialize()
        return self._repositories["projects"]

    def get_people_service(self) -> PeopleService:
        """Get the people service instance."""
        self.initialize()
        return self._services["people"]

    def get_projects_service(self) -> ProjectsService:
        """Get the projects service instance."""
        self.initialize()
        return self._services["projects"]

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
