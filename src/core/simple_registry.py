"""
Simple Service Registry - Lightweight implementation for current usage

This is a simplified version of the Service Registry that matches our current
implementation needs without the complex dependency injection features.
"""

from typing import Dict, Any, Optional
import logging
from datetime import datetime

from .base_service import BaseService


class SimpleServiceRegistry:
    """
    Simple service registry for managing service instances.

    This is a lightweight implementation that provides basic service
    registration and retrieval without complex dependency injection.
    """

    def __init__(self):
        self.services: Dict[str, BaseService] = {}
        self.logger = logging.getLogger("SimpleServiceRegistry")
        self.logger.info("Simple Service Registry initialized")

    def register_service(self, service_name: str, service_instance: BaseService):
        """Register a service instance with the registry."""
        if service_name in self.services:
            self.logger.warning(
                f"Service '{service_name}' is already registered, replacing..."
            )

        self.services[service_name] = service_instance
        self.logger.info(f"Registered service: {service_name}")

    def get_service(self, service_name: str) -> BaseService:
        """Get a service instance by name."""
        if service_name not in self.services:
            raise ValueError(f"Service '{service_name}' is not registered")

        return self.services[service_name]

    def list_services(self) -> Dict[str, str]:
        """List all registered services."""
        return {name: type(service).__name__ for name, service in self.services.items()}

    async def health_check_all(self) -> Dict[str, Any]:
        """Perform health check on all registered services."""
        health_results = {}

        for service_name, service in self.services.items():
            try:
                health_result = await service.health_check()
                health_results[service_name] = health_result
            except Exception as e:
                health_results[service_name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }

        return health_results

    def shutdown(self):
        """Shutdown all services."""
        for service_name, service in self.services.items():
            try:
                if hasattr(service, "shutdown"):
                    service.shutdown()
                self.logger.info(f"Shutdown service: {service_name}")
            except Exception as e:
                self.logger.error(
                    f"Error shutting down service '{service_name}': {str(e)}"
                )

        self.services.clear()
        self.logger.info("All services shutdown")
