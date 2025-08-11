"""
Service Registry - Dependency Injection Container

This module implements the Service Registry pattern, providing centralized
service management, dependency injection, and service lifecycle management.
"""

import asyncio
from typing import Dict, Any, Optional, Type, TypeVar, List
from dataclasses import dataclass
import logging
import time
from enum import Enum

from .base_service import BaseService, HealthCheck, ServiceStatus
from .config import ServiceConfig, get_config


T = TypeVar("T", bound=BaseService)


class RegistryStatus(Enum):
    """Service registry status"""

    INITIALIZING = "initializing"
    READY = "ready"
    DEGRADED = "degraded"
    SHUTTING_DOWN = "shutting_down"
    STOPPED = "stopped"


@dataclass
class ServiceRegistration:
    """Service registration information"""

    service_class: Type[BaseService]
    instance: Optional[BaseService] = None
    singleton: bool = True
    dependencies: List[str] = None
    initialized: bool = False
    last_health_check: Optional[HealthCheck] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class ServiceRegistry:
    """
    Central service registry implementing dependency injection pattern.

    Features:
    - Service registration and discovery
    - Dependency injection
    - Service lifecycle management
    - Health monitoring
    - Graceful shutdown
    """

    def __init__(self, config: Optional[ServiceConfig] = None):
        self.config = config or get_config()
        self.logger = logging.getLogger("ServiceRegistry")
        self._services: Dict[str, ServiceRegistration] = {}
        self._status = RegistryStatus.INITIALIZING
        self._initialization_order: List[str] = []

    def register_service(
        self,
        service_name: str,
        service_class: Type[T],
        singleton: bool = True,
        dependencies: Optional[List[str]] = None,
    ) -> "ServiceRegistry":
        """Register a service with the registry"""
        if service_name in self._services:
            raise ValueError(f"Service '{service_name}' is already registered")

        self._services[service_name] = ServiceRegistration(
            service_class=service_class,
            singleton=singleton,
            dependencies=dependencies or [],
        )

        self.logger.info(f"Registered service: {service_name}")
        return self

    async def get_service(self, service_name: str) -> BaseService:
        """Get a service instance by name"""
        if service_name not in self._services:
            raise ValueError(f"Service '{service_name}' is not registered")

        registration = self._services[service_name]

        # Return existing instance for singletons
        if registration.singleton and registration.instance is not None:
            return registration.instance

        # Create new instance
        instance = await self._create_service_instance(service_name, registration)

        if registration.singleton:
            registration.instance = instance
            registration.initialized = True

        return instance

    async def _create_service_instance(
        self, service_name: str, registration: ServiceRegistration
    ) -> BaseService:
        """Create and initialize a service instance"""
        try:
            # Resolve dependencies first
            dependencies = {}
            for dep_name in registration.dependencies:
                dependencies[dep_name] = await self.get_service(dep_name)

            # Create service instance with configuration
            service_config = self._get_service_config(service_name)
            instance = registration.service_class(
                service_name=service_name, config=service_config
            )

            # Inject dependencies if the service supports it
            if hasattr(instance, "set_dependencies"):
                instance.set_dependencies(dependencies)

            # Initialize the service
            if not await instance.initialize():
                raise RuntimeError(f"Failed to initialize service: {service_name}")

            self.logger.info(f"Created and initialized service: {service_name}")
            return instance

        except Exception as e:
            self.logger.error(f"Failed to create service '{service_name}': {str(e)}")
            raise RuntimeError(f"Service creation failed: {service_name}") from e

    def _get_service_config(self, service_name: str) -> Dict[str, Any]:
        """Get configuration for a specific service"""
        service_configs = {
            "auth_service": {
                "jwt_secret": self.config.auth.jwt_secret,
                "access_token_expiry_hours": self.config.auth.access_token_expiry_hours,
                "refresh_token_expiry_days": self.config.auth.refresh_token_expiry_days,
                "max_failed_attempts": self.config.auth.max_failed_attempts,
                "account_lockout_minutes": self.config.auth.account_lockout_minutes,
            },
            "email_service": {
                "ses_region": self.config.email.ses_region,
                "from_email": self.config.email.from_email,
                "from_name": self.config.email.from_name,
                "frontend_url": self.config.email.frontend_url,
                "support_email": self.config.email.support_email,
            },
            "security_service": {
                "csrf_secret": self.config.security.csrf_secret,
                "rate_limit_rpm": self.config.security.rate_limit_requests_per_minute,
                "rate_limit_rph": self.config.security.rate_limit_requests_per_hour,
                "password_policy": {
                    "min_length": self.config.security.password_min_length,
                    "require_uppercase": self.config.security.password_require_uppercase,
                    "require_lowercase": self.config.security.password_require_lowercase,
                    "require_numbers": self.config.security.password_require_numbers,
                    "require_special": self.config.security.password_require_special,
                    "history_count": self.config.security.password_history_count,
                },
            },
        }

        return service_configs.get(service_name, {})

    async def initialize_all(self) -> bool:
        """Initialize all registered services in dependency order"""
        self.logger.info("Initializing all services...")
        self._status = RegistryStatus.INITIALIZING

        try:
            # Calculate initialization order based on dependencies
            self._initialization_order = self._calculate_initialization_order()

            # Initialize services in order
            for service_name in self._initialization_order:
                self.logger.info(f"Initializing service: {service_name}")
                await self.get_service(service_name)

            self._status = RegistryStatus.READY
            self.logger.info("All services initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize services: {str(e)}")
            self._status = RegistryStatus.DEGRADED
            return False

    def _calculate_initialization_order(self) -> List[str]:
        """Calculate service initialization order based on dependencies"""
        order = []
        visited = set()
        temp_visited = set()

        def visit(service_name: str):
            if service_name in temp_visited:
                raise ValueError(
                    f"Circular dependency detected involving: {service_name}"
                )
            if service_name in visited:
                return

            temp_visited.add(service_name)

            registration = self._services[service_name]
            for dep in registration.dependencies:
                if dep not in self._services:
                    raise ValueError(
                        f"Dependency '{dep}' not registered for service '{service_name}'"
                    )
                visit(dep)

            temp_visited.remove(service_name)
            visited.add(service_name)
            order.append(service_name)

        for service_name in self._services:
            visit(service_name)

        return order

    async def health_check_all(self) -> Dict[str, HealthCheck]:
        """Perform health check on all initialized services"""
        results = {}

        for service_name, registration in self._services.items():
            if registration.instance and registration.initialized:
                try:
                    start_time = time.time()
                    health_check = await registration.instance.health_check()
                    health_check.response_time_ms = (time.time() - start_time) * 1000
                    results[service_name] = health_check
                    registration.last_health_check = health_check
                except Exception as e:
                    results[service_name] = HealthCheck(
                        service_name=service_name,
                        status=ServiceStatus.UNHEALTHY,
                        message=f"Health check failed: {str(e)}",
                    )

        return results

    def get_status(self) -> RegistryStatus:
        """Get current registry status"""
        return self._status


# Global registry instance
_registry_instance: Optional[ServiceRegistry] = None


def get_registry() -> ServiceRegistry:
    """Get the global service registry instance"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ServiceRegistry()
    return _registry_instance


def reset_registry():
    """Reset the global registry instance (mainly for testing)"""
    global _registry_instance
    _registry_instance = None
