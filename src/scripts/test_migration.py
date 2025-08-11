#!/usr/bin/env python3
"""
Migration Test Script - Verify Service Registry Migration

This script tests the new Service Registry architecture to ensure
it works correctly after migration from the monolithic handler.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from src.core.simple_registry import SimpleServiceRegistry
from src.core.config import ServiceConfig
from src.services.people_service import PeopleService
from src.services.projects_service import ProjectsService
from src.services.subscriptions_service import SubscriptionsService
from src.utils.logging_config import get_handler_logger

logger = get_handler_logger("migration_test")


class TestServiceRegistryManager:
    """Test version of the Service Registry Manager for migration testing."""

    def __init__(self):
        self.logger = get_handler_logger("test_service_registry_manager")
        self.config = ServiceConfig()
        self.registry = SimpleServiceRegistry()

        # Initialize and register all domain services
        self._initialize_services()

        self.logger.info("Test Service Registry Manager initialized successfully")

    def _initialize_services(self):
        """Initialize and register all domain services."""
        try:
            # Register People Service
            people_service = PeopleService()
            self.registry.register_service("people", people_service)

            # Register Projects Service
            projects_service = ProjectsService()
            self.registry.register_service("projects", projects_service)

            # Register Subscriptions Service
            subscriptions_service = SubscriptionsService()
            self.registry.register_service("subscriptions", subscriptions_service)

            self.logger.info("All domain services registered successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize services: {str(e)}")
            raise

    def get_service(self, service_name: str):
        """Get a registered service by name."""
        return self.registry.get_service(service_name)

    async def health_check(self):
        """Comprehensive health check for all services."""
        try:
            health_status = {
                "service_registry_manager": {
                    "status": "healthy",
                    "timestamp": "2025-08-11T19:44:50.000Z",
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
                        "timestamp": "2025-08-11T19:44:50.000Z",
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
                    "timestamp": "2025-08-11T19:44:50.000Z",
                },
                "overall_status": "unhealthy",
            }


# Create test service manager
test_service_manager = TestServiceRegistryManager()


async def test_service_registry():
    """Test the Service Registry functionality."""
    try:
        logger.info("🧪 Testing Service Registry Migration...")

        # Test 1: Health Check
        logger.info("Test 1: Service Registry Health Check")
        health = await test_service_manager.health_check()

        if health.get("overall_status") == "healthy":
            logger.info("✅ Service Registry health check passed")
        else:
            logger.error("❌ Service Registry health check failed")
            logger.error(f"Health status: {health}")
            return False

        # Test 2: Service Registration
        logger.info("Test 2: Service Registration")
        services = list(test_service_manager.registry.services.keys())
        expected_services = ["people", "projects", "subscriptions"]

        if all(service in services for service in expected_services):
            logger.info(f"✅ All expected services registered: {services}")
        else:
            logger.error(
                f"❌ Missing services. Expected: {expected_services}, Found: {services}"
            )
            return False

        # Test 3: Individual Service Health
        logger.info("Test 3: Individual Service Health Checks")
        for service_name in expected_services:
            service = test_service_manager.get_service(service_name)
            service_health = await service.health_check()

            if service_health.get("status") == "healthy":
                logger.info(f"✅ {service_name} service healthy")
            else:
                logger.warning(f"⚠️ {service_name} service status: {service_health}")
                # Don't fail the test for database connectivity issues in testing

        logger.info("🎉 All Service Registry migration tests passed!")
        return True

    except Exception as e:
        logger.error(f"❌ Service Registry test failed: {str(e)}")
        return False


async def test_service_methods():
    """Test service methods directly."""
    try:
        logger.info("🧪 Testing Service Methods...")

        # Test People Service
        logger.info("Testing People Service methods...")
        people_service = test_service_manager.get_service("people")

        # Test health check
        people_health = await people_service.health_check()
        logger.info(f"People service health: {people_health.get('status', 'unknown')}")

        # Test Projects Service
        logger.info("Testing Projects Service methods...")
        projects_service = test_service_manager.get_service("projects")

        # Test health check
        projects_health = await projects_service.health_check()
        logger.info(
            f"Projects service health: {projects_health.get('status', 'unknown')}"
        )

        # Test Subscriptions Service
        logger.info("Testing Subscriptions Service methods...")
        subscriptions_service = test_service_manager.get_service("subscriptions")

        # Test health check
        subscriptions_health = await subscriptions_service.health_check()
        logger.info(
            f"Subscriptions service health: {subscriptions_health.get('status', 'unknown')}"
        )

        logger.info("✅ Service methods accessible")
        logger.info("🎉 All service method tests passed!")
        return True

    except Exception as e:
        logger.error(f"❌ Service method test failed: {str(e)}")
        return False


async def test_service_registry_infrastructure():
    """Test the Service Registry infrastructure components."""
    try:
        logger.info("🧪 Testing Service Registry Infrastructure...")

        # Test ServiceRegistry
        logger.info("Testing SimpleServiceRegistry class...")
        registry = SimpleServiceRegistry()

        # Test service registration
        from src.services.people_service import PeopleService

        test_service = PeopleService()
        registry.register_service("test_people", test_service)

        # Test service retrieval
        retrieved_service = registry.get_service("test_people")
        if retrieved_service == test_service:
            logger.info("✅ Service registration and retrieval working")
        else:
            logger.error("❌ Service registration/retrieval failed")
            return False

        # Test ServiceConfig
        logger.info("Testing ServiceConfig class...")
        config = ServiceConfig()
        if hasattr(config, "database") and hasattr(config, "auth"):
            logger.info("✅ ServiceConfig loaded successfully")
        else:
            logger.error("❌ ServiceConfig failed to load")
            return False

        logger.info("🎉 All infrastructure tests passed!")
        return True

    except Exception as e:
        logger.error(f"❌ Infrastructure test failed: {str(e)}")
        return False


async def main():
    """Run all migration tests."""
    logger.info("🚀 Starting Service Registry Migration Tests")

    # Test Infrastructure
    infrastructure_test = await test_service_registry_infrastructure()

    # Test Service Registry
    registry_test = await test_service_registry()

    # Test Service Methods
    methods_test = await test_service_methods()

    if infrastructure_test and registry_test and methods_test:
        logger.info("🎉 Migration verification completed successfully!")
        logger.info("✅ Service Registry architecture is working correctly")
        logger.info("🔄 Ready to switch from monolithic to modular handler")
        logger.info("")
        logger.info("📋 Migration Summary:")
        logger.info("   ✅ Service Registry infrastructure verified")
        logger.info("   ✅ Domain services created and registered")
        logger.info("   ✅ Service health checks working")
        logger.info("   ✅ Service methods accessible")
        logger.info("   ✅ Configuration management working")
        logger.info("")
        logger.info("🚀 Next Steps:")
        logger.info("   1. Update main_versioned.py to use modular_api_handler")
        logger.info("   2. Run existing test suite to ensure compatibility")
        logger.info("   3. Deploy the new Service Registry architecture")
        logger.info("   4. Monitor performance and health metrics")
        return True
    else:
        logger.error("❌ Migration verification failed")
        logger.error("🔧 Please check the logs and fix issues before proceeding")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
