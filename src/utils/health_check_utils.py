"""
HealthCheck Utilities - Standardized health check patterns for Service Registry

This module provides standardized utilities for handling HealthCheck objects
and converting them to consistent API response formats. This prevents the
common issue of treating HealthCheck objects as dictionaries.

Following Service Registry patterns for consistency and maintainability.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Union
from ..core.base_service import HealthCheck, ServiceStatus


class HealthCheckConverter:
    """
    Standardized converter for HealthCheck objects to API response format.

    This class ensures consistent handling of HealthCheck objects across
    all services and prevents the common error of using .get() on HealthCheck objects.
    """

    @staticmethod
    def to_dict(health_check: HealthCheck) -> Dict[str, Any]:
        """
        Convert HealthCheck object to dictionary format for API responses.

        Args:
            health_check: HealthCheck object from service

        Returns:
            Dict containing standardized health check information
        """
        return {
            "service_name": health_check.service_name,
            "status": health_check.status.value,
            "healthy": health_check.status == ServiceStatus.HEALTHY,
            "message": health_check.message,
            "details": health_check.details or {},
            "response_time_ms": health_check.response_time_ms,
            "last_check": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def to_dict_safe(
        health_check: Union[HealthCheck, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Safely convert HealthCheck object or dictionary to standardized format.

        This method handles both HealthCheck objects and dictionaries,
        making it safe to use in mixed environments.

        Args:
            health_check: HealthCheck object or dictionary

        Returns:
            Dict containing standardized health check information
        """
        if isinstance(health_check, dict):
            # Already a dictionary, ensure it has required fields
            return {
                "service_name": health_check.get("service_name", "unknown"),
                "status": health_check.get("status", "unknown"),
                "healthy": health_check.get(
                    "healthy", health_check.get("status") == "healthy"
                ),
                "message": health_check.get("message", ""),
                "details": health_check.get("details", {}),
                "response_time_ms": health_check.get("response_time_ms"),
                "last_check": health_check.get(
                    "last_check", datetime.now(timezone.utc).isoformat()
                ),
            }
        elif hasattr(health_check, "status"):
            # It's a HealthCheck object
            return HealthCheckConverter.to_dict(health_check)
        else:
            # Unknown format, return safe default
            return {
                "service_name": "unknown",
                "status": "unknown",
                "healthy": False,
                "message": f"Unknown health check format: {type(health_check)}",
                "details": {"raw_data": str(health_check)},
                "response_time_ms": None,
                "last_check": datetime.now(timezone.utc).isoformat(),
            }

    @staticmethod
    def aggregate_health(
        health_checks: List[Union[HealthCheck, Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """
        Aggregate multiple health checks into overall system health.

        Args:
            health_checks: List of HealthCheck objects or dictionaries

        Returns:
            Dict containing aggregated health information
        """
        converted_checks = [
            HealthCheckConverter.to_dict_safe(check) for check in health_checks
        ]

        total_services = len(converted_checks)
        healthy_services = sum(1 for check in converted_checks if check["healthy"])

        overall_healthy = healthy_services == total_services and total_services > 0

        return {
            "overall_status": "healthy" if overall_healthy else "degraded",
            "overall_healthy": overall_healthy,
            "total_services": total_services,
            "healthy_services": healthy_services,
            "unhealthy_services": total_services - healthy_services,
            "services": {check["service_name"]: check for check in converted_checks},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


class ServiceRegistryHealthChecker:
    """
    Standardized health checker for Service Registry pattern.

    This class provides consistent health checking across all services
    and ensures proper error handling and response formatting.
    """

    def __init__(self, service_registry):
        """
        Initialize health checker with service registry.

        Args:
            service_registry: Service registry instance
        """
        self.registry = service_registry

    async def check_all_services(self) -> Dict[str, Any]:
        """
        Check health of all registered services.

        Returns:
            Dict containing comprehensive health information
        """
        health_checks = []

        for service_name in self.registry.services.keys():
            try:
                service = self.registry.get_service(service_name)
                health_check = await service.health_check()
                health_checks.append(health_check)
            except Exception as e:
                # Create error health check
                error_check = {
                    "service_name": service_name,
                    "status": "unhealthy",
                    "healthy": False,
                    "message": f"Health check failed: {str(e)}",
                    "details": {"error": str(e), "error_type": type(e).__name__},
                    "response_time_ms": None,
                    "last_check": datetime.now(timezone.utc).isoformat(),
                }
                health_checks.append(error_check)

        return HealthCheckConverter.aggregate_health(health_checks)

    async def check_service(self, service_name: str) -> Dict[str, Any]:
        """
        Check health of a specific service.

        Args:
            service_name: Name of service to check

        Returns:
            Dict containing service health information
        """
        try:
            service = self.registry.get_service(service_name)
            health_check = await service.health_check()
            return HealthCheckConverter.to_dict_safe(health_check)
        except Exception as e:
            return {
                "service_name": service_name,
                "status": "unhealthy",
                "healthy": False,
                "message": f"Health check failed: {str(e)}",
                "details": {"error": str(e), "error_type": type(e).__name__},
                "response_time_ms": None,
                "last_check": datetime.now(timezone.utc).isoformat(),
            }


# Utility functions for backward compatibility and ease of use


def convert_health_check(
    health_check: Union[HealthCheck, Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Convert HealthCheck object to dictionary format.

    This is a convenience function that wraps HealthCheckConverter.to_dict_safe()
    for easier use in existing code.

    Args:
        health_check: HealthCheck object or dictionary

    Returns:
        Dict containing standardized health check information
    """
    return HealthCheckConverter.to_dict_safe(health_check)


def is_healthy(health_check: Union[HealthCheck, Dict[str, Any]]) -> bool:
    """
    Check if a health check indicates healthy status.

    This function safely determines health status regardless of whether
    the input is a HealthCheck object or dictionary.

    Args:
        health_check: HealthCheck object or dictionary

    Returns:
        bool indicating if the service is healthy
    """
    if isinstance(health_check, dict):
        return health_check.get("healthy", health_check.get("status") == "healthy")
    elif hasattr(health_check, "status"):
        return health_check.status == ServiceStatus.HEALTHY
    else:
        return False


def get_health_status(health_check: Union[HealthCheck, Dict[str, Any]]) -> str:
    """
    Get health status string from HealthCheck object or dictionary.

    Args:
        health_check: HealthCheck object or dictionary

    Returns:
        str indicating health status ("healthy", "unhealthy", "unknown")
    """
    if isinstance(health_check, dict):
        return health_check.get("status", "unknown")
    elif hasattr(health_check, "status"):
        return health_check.status.value
    else:
        return "unknown"


# Example usage patterns for Service Registry

"""
USAGE EXAMPLES:

1. Convert HealthCheck object to dictionary:
   health_dict = convert_health_check(service_health)

2. Check if service is healthy:
   if is_healthy(service_health):
       logger.info("Service is healthy")

3. Get health status string:
   status = get_health_status(service_health)
   logger.info(f"Service status: {status}")

4. Use in service registry manager:
   health_checker = ServiceRegistryHealthChecker(service_registry)
   all_health = await health_checker.check_all_services()

5. Safe health check in loops:
   for service_name in services:
       service = registry.get_service(service_name)
       health = await service.health_check()
       if is_healthy(health):
           logger.info(f"✅ {service_name}: {get_health_status(health)}")
       else:
           logger.warning(f"❌ {service_name}: {get_health_status(health)}")
"""
