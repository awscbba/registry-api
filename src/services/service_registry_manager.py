"""
Service Registry Manager - Coordinates all domain services using the Service Registry pattern.
This replaces the monolithic handler with a clean, modular architecture.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from ..core.simple_registry import SimpleServiceRegistry
from ..core.config import ServiceConfig
from .people_service import PeopleService
from .projects_service import ProjectsService
from .subscriptions_service import SubscriptionsService
from .auth_service import AuthService
from .roles_service import RolesService
from .email_service import EmailService
from .audit_service import AuditService
from .logging_service import LoggingService
from .rate_limiting_service import RateLimitingService
from .metrics_service import MetricsService
from .project_administration_service import ProjectAdministrationService
from ..utils.logging_config import get_handler_logger


class ServiceRegistryManager:
    """
    Central manager for all domain services using the Service Registry pattern.
    Provides a clean interface to replace the monolithic versioned_api_handler.
    """

    def __init__(self):
        self.logger = get_handler_logger("service_registry_manager")
        self.config = ServiceConfig()
        self.registry = SimpleServiceRegistry()

        # Initialize and register all domain services
        self._initialize_services()

        self.logger.info("Service Registry Manager initialized successfully")

    def _initialize_services(self):
        """Initialize and register all domain services."""
        try:
            # Register Domain Services
            people_service = PeopleService()
            self.registry.register_service("people", people_service)

            projects_service = ProjectsService()
            self.registry.register_service("projects", projects_service)

            subscriptions_service = SubscriptionsService()
            self.registry.register_service("subscriptions", subscriptions_service)

            # Register Core Services
            auth_service = AuthService()
            self.registry.register_service("auth", auth_service)

            roles_service = RolesService()
            self.registry.register_service("roles", roles_service)

            email_service = EmailService()
            self.registry.register_service("email", email_service)

            audit_service = AuditService()
            self.registry.register_service("audit", audit_service)

            logging_service = LoggingService()
            self.registry.register_service("logging", logging_service)

            rate_limiting_service = RateLimitingService()
            self.registry.register_service("rate_limiting", rate_limiting_service)

            # Register Monitoring Services
            metrics_service = MetricsService()
            self.registry.register_service("metrics", metrics_service)

            # Register Administration Services
            project_admin_service = ProjectAdministrationService()
            self.registry.register_service(
                "project_administration", project_admin_service
            )

            self.logger.info(
                f"All services registered successfully: {list(self.registry.services.keys())}"
            )

        except Exception as e:
            self.logger.error(f"Failed to initialize services: {str(e)}")
            raise

    def get_service(self, service_name: str):
        """Get a registered service by name."""
        return self.registry.get_service(service_name)

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for all services."""
        try:
            health_status = {
                "service_registry_manager": {
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "services_registered": len(self.registry.services),
                    "config_loaded": self.config is not None,
                },
                "services": {},
            }

            # Check health of all registered services
            for service_name in self.registry.services.keys():
                try:
                    service = self.registry.get_service(service_name)
                    service_health = await service.health_check()
                    health_status["services"][service_name] = service_health
                except Exception as e:
                    health_status["services"][service_name] = {
                        "status": "unhealthy",
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                    }

            # Determine overall health
            all_healthy = all(
                service_health.get("status") == "healthy"
                for service_health in health_status["services"].values()
            )

            health_status["overall_status"] = "healthy" if all_healthy else "degraded"

            return health_status

        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return {
                "service_registry_manager": {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                },
                "overall_status": "unhealthy",
            }

    # ==================== PEOPLE SERVICE METHODS ====================

    async def get_all_people_v1(self) -> Dict[str, Any]:
        """Get all people (v1 format)."""
        people_service = self.get_service("people")
        return await people_service.get_all_people_v1()

    async def get_all_people_v2(self) -> Dict[str, Any]:
        """Get all people (v2 format)."""
        people_service = self.get_service("people")
        return await people_service.get_all_people_v2()

    async def get_person_by_id_v1(self, person_id: str) -> Dict[str, Any]:
        """Get person by ID (v1 format)."""
        people_service = self.get_service("people")
        return await people_service.get_person_by_id_v1(person_id)

    async def get_person_by_id_v2(self, person_id: str) -> Dict[str, Any]:
        """Get person by ID (v2 format)."""
        people_service = self.get_service("people")
        return await people_service.get_person_by_id_v2(person_id)

    async def create_person_v1(self, person_data) -> Dict[str, Any]:
        """Create person (v1 format)."""
        people_service = self.get_service("people")
        return await people_service.create_person_v1(person_data)

    async def create_person_v2(self, person_data) -> Dict[str, Any]:
        """Create person (v2 format)."""
        people_service = self.get_service("people")
        return await people_service.create_person_v2(person_data)

    async def update_person_v1(self, person_id: str, person_data) -> Dict[str, Any]:
        """Update person (v1 format)."""
        people_service = self.get_service("people")
        return await people_service.update_person_v1(person_id, person_data)

    async def update_person_v2(self, person_id: str, person_data) -> Dict[str, Any]:
        """Update person (v2 format)."""
        people_service = self.get_service("people")
        return await people_service.update_person_v2(person_id, person_data)

    async def delete_person_v1(self, person_id: str) -> Dict[str, Any]:
        """Delete person (v1 format)."""
        people_service = self.get_service("people")
        return await people_service.delete_person_v1(person_id)

    async def delete_person_v2(self, person_id: str) -> Dict[str, Any]:
        """Delete person (v2 format)."""
        people_service = self.get_service("people")
        return await people_service.delete_person_v2(person_id)

    # ==================== PROJECTS SERVICE METHODS ====================

    async def get_all_projects_v1(self) -> Dict[str, Any]:
        """Get all projects (v1 format)."""
        projects_service = self.get_service("projects")
        return await projects_service.get_all_projects_v1()

    async def get_all_projects_v2(self) -> Dict[str, Any]:
        """Get all projects (v2 format)."""
        projects_service = self.get_service("projects")
        return await projects_service.get_all_projects_v2()

    async def get_project_by_id_v1(self, project_id: str) -> Dict[str, Any]:
        """Get project by ID (v1 format)."""
        projects_service = self.get_service("projects")
        return await projects_service.get_project_by_id_v1(project_id)

    async def get_project_by_id_v2(self, project_id: str) -> Dict[str, Any]:
        """Get project by ID (v2 format)."""
        projects_service = self.get_service("projects")
        return await projects_service.get_project_by_id_v2(project_id)

    async def create_project_v1(self, project_data) -> Dict[str, Any]:
        """Create project (v1 format)."""
        projects_service = self.get_service("projects")
        return await projects_service.create_project_v1(project_data)

    async def create_project_v2(self, project_data) -> Dict[str, Any]:
        """Create project (v2 format)."""
        projects_service = self.get_service("projects")
        return await projects_service.create_project_v2(project_data)

    async def update_project_v1(self, project_id: str, project_data) -> Dict[str, Any]:
        """Update project (v1 format)."""
        projects_service = self.get_service("projects")
        return await projects_service.update_project_v1(project_id, project_data)

    async def update_project_v2(self, project_id: str, project_data) -> Dict[str, Any]:
        """Update project (v2 format)."""
        projects_service = self.get_service("projects")
        return await projects_service.update_project_v2(project_id, project_data)

    async def delete_project_v1(self, project_id: str) -> Dict[str, Any]:
        """Delete project (v1 format)."""
        projects_service = self.get_service("projects")
        return await projects_service.delete_project_v1(project_id)

    async def delete_project_v2(self, project_id: str) -> Dict[str, Any]:
        """Delete project (v2 format)."""
        projects_service = self.get_service("projects")
        return await projects_service.delete_project_v2(project_id)

    # ==================== SUBSCRIPTIONS SERVICE METHODS ====================

    async def get_all_subscriptions_v1(self) -> Dict[str, Any]:
        """Get all subscriptions (v1 format)."""
        subscriptions_service = self.get_service("subscriptions")
        return await subscriptions_service.get_all_subscriptions_v1()

    async def get_all_subscriptions_v2(self) -> Dict[str, Any]:
        """Get all subscriptions (v2 format)."""
        subscriptions_service = self.get_service("subscriptions")
        return await subscriptions_service.get_all_subscriptions_v2()

    async def get_subscription_by_id_v1(self, subscription_id: str) -> Dict[str, Any]:
        """Get subscription by ID (v1 format)."""
        subscriptions_service = self.get_service("subscriptions")
        return await subscriptions_service.get_subscription_by_id_v1(subscription_id)

    async def get_subscription_by_id_v2(self, subscription_id: str) -> Dict[str, Any]:
        """Get subscription by ID (v2 format)."""
        subscriptions_service = self.get_service("subscriptions")
        return await subscriptions_service.get_subscription_by_id_v2(subscription_id)

    async def create_subscription_v1(self, subscription_data: dict) -> Dict[str, Any]:
        """Create subscription (v1 format - redirects to v2)."""
        subscriptions_service = self.get_service("subscriptions")
        return await subscriptions_service.create_subscription_v1(subscription_data)

    async def create_subscription_v2(self, subscription_data: dict) -> Dict[str, Any]:
        """Create subscription (v2 format)."""
        subscriptions_service = self.get_service("subscriptions")
        return await subscriptions_service.create_subscription_v2(subscription_data)

    async def update_subscription_v1(
        self, subscription_id: str, subscription_data
    ) -> Dict[str, Any]:
        """Update subscription (v1 format)."""
        subscriptions_service = self.get_service("subscriptions")
        return await subscriptions_service.update_subscription_v1(
            subscription_id, subscription_data
        )

    async def update_subscription_v2(
        self, subscription_id: str, subscription_data
    ) -> Dict[str, Any]:
        """Update subscription (v2 format)."""
        subscriptions_service = self.get_service("subscriptions")
        return await subscriptions_service.update_subscription_v2(
            subscription_id, subscription_data
        )

    async def delete_subscription_v1(self, subscription_id: str) -> Dict[str, Any]:
        """Delete subscription (v1 format)."""
        subscriptions_service = self.get_service("subscriptions")
        return await subscriptions_service.delete_subscription_v1(subscription_id)

    async def delete_subscription_v2(self, subscription_id: str) -> Dict[str, Any]:
        """Delete subscription (v2 format)."""
        subscriptions_service = self.get_service("subscriptions")
        return await subscriptions_service.delete_subscription_v2(subscription_id)

    async def get_project_subscriptions_v1(self, project_id: str) -> Dict[str, Any]:
        """Get project subscriptions (v1 format)."""
        subscriptions_service = self.get_service("subscriptions")
        return await subscriptions_service.get_project_subscriptions_v1(project_id)

    async def get_project_subscriptions_v2(self, project_id: str) -> Dict[str, Any]:
        """Get project subscriptions (v2 format)."""
        subscriptions_service = self.get_service("subscriptions")
        return await subscriptions_service.get_project_subscriptions_v2(project_id)


# Global instance for use in FastAPI endpoints
service_manager = ServiceRegistryManager()
