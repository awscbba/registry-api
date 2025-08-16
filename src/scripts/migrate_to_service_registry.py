#!/usr/bin/env python3
"""
Migration Script: Transition from Monolithic to Service Registry Architecture

This script helps migrate from the monolithic versioned_api_handler.py to the new
modular Service Registry architecture while maintaining backward compatibility.
"""

import os
import sys
import shutil
from datetime import datetime
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.logging_config import get_handler_logger
from core.base_service import ServiceStatus

logger = get_handler_logger("migration_script")


class ServiceRegistryMigration:
    """Handles the migration from monolithic to Service Registry architecture."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.src_dir = self.project_root / "src"
        self.handlers_dir = self.src_dir / "handlers"
        self.backup_dir = self.project_root / "migration_backup"

        logger.info(f"Initializing migration for project: {self.project_root}")

    def create_backup(self):
        """Create a backup of the current monolithic handler."""
        try:
            # Create backup directory
            self.backup_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Backup the monolithic handler
            monolithic_handler = self.handlers_dir / "versioned_api_handler.py"
            if monolithic_handler.exists():
                backup_file = (
                    self.backup_dir / f"versioned_api_handler_backup_{timestamp}.py"
                )
                shutil.copy2(monolithic_handler, backup_file)
                logger.info(f"Backed up monolithic handler to: {backup_file}")
            else:
                logger.warning("Monolithic handler not found - skipping backup")

            # Create migration log
            migration_log = self.backup_dir / f"migration_log_{timestamp}.txt"
            with open(migration_log, "w") as f:
                f.write(f"Service Registry Migration Log\n")
                f.write(f"Migration Date: {datetime.now().isoformat()}\n")
                f.write(f"Project Root: {self.project_root}\n")
                f.write(f"Monolithic Handler: {monolithic_handler}\n")
                f.write(
                    f"Backup Created: {backup_file if monolithic_handler.exists() else 'N/A'}\n"
                )
                f.write(f"\nMigration Steps:\n")
                f.write(f"1. Backup created\n")
                f.write(f"2. Service Registry infrastructure verified\n")
                f.write(f"3. Domain services created\n")
                f.write(f"4. Modular handler created\n")
                f.write(f"5. Ready for testing\n")

            logger.info(f"Migration log created: {migration_log}")
            return True

        except Exception as e:
            logger.error(f"Failed to create backup: {str(e)}")
            return False

    def verify_service_registry_infrastructure(self):
        """Verify that the Service Registry infrastructure is in place."""
        try:
            required_files = [
                self.src_dir / "core" / "__init__.py",
                self.src_dir / "core" / "base_service.py",
                self.src_dir / "core" / "registry.py",
                self.src_dir / "core" / "config.py",
            ]

            missing_files = []
            for file_path in required_files:
                if not file_path.exists():
                    missing_files.append(str(file_path))

            if missing_files:
                logger.error(
                    f"Missing Service Registry infrastructure files: {missing_files}"
                )
                return False

            logger.info("Service Registry infrastructure verified ✅")
            return True

        except Exception as e:
            logger.error(f"Failed to verify Service Registry infrastructure: {str(e)}")
            return False

    def verify_domain_services(self):
        """Verify that domain services are created."""
        try:
            required_services = [
                self.src_dir / "services" / "people_service.py",
                self.src_dir / "services" / "projects_service.py",
                self.src_dir / "services" / "subscriptions_service.py",
                self.src_dir / "services" / "service_registry_manager.py",
            ]

            missing_services = []
            for service_path in required_services:
                if not service_path.exists():
                    missing_services.append(str(service_path))

            if missing_services:
                logger.error(f"Missing domain services: {missing_services}")
                return False

            logger.info("Domain services verified ✅")
            return True

        except Exception as e:
            logger.error(f"Failed to verify domain services: {str(e)}")
            return False

    def verify_modular_handler(self):
        """Verify that the modular handler is created."""
        try:
            modular_handler = self.handlers_dir / "modular_api_handler.py"
            if not modular_handler.exists():
                logger.error(f"Modular handler not found: {modular_handler}")
                return False

            logger.info("Modular handler verified ✅")
            return True

        except Exception as e:
            logger.error(f"Failed to verify modular handler: {str(e)}")
            return False

    def create_migration_test_script(self):
        """Create a test script to verify the migration."""
        try:
            test_script_content = '''#!/usr/bin/env python3
"""
Migration Test Script - Verify Service Registry Migration

This script tests the new Service Registry architecture to ensure
it works correctly after migration from the monolithic handler.
"""

import asyncio
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.service_registry_manager import service_manager
from utils.logging_config import get_handler_logger

logger = get_handler_logger("migration_test")


async def test_service_registry():
    """Test the Service Registry functionality."""
    try:
        logger.info("🧪 Testing Service Registry Migration...")

        # Test 1: Health Check
        logger.info("Test 1: Service Registry Health Check")
        health = await service_manager.health_check()

        if health.status == ServiceStatus.HEALTHY:
            logger.info("✅ Service Registry health check passed")
        else:
            logger.error("❌ Service Registry health check failed")
            return False

        # Test 2: Service Registration
        logger.info("Test 2: Service Registration")
        services = list(service_manager.registry.services.keys())
        expected_services = ["people", "projects", "subscriptions"]

        if all(service in services for service in expected_services):
            logger.info(f"✅ All expected services registered: {services}")
        else:
            logger.error(f"❌ Missing services. Expected: {expected_services}, Found: {services}")
            return False

        # Test 3: Individual Service Health
        logger.info("Test 3: Individual Service Health Checks")
        for service_name in expected_services:
            service = service_manager.get_service(service_name)
            service_health = await service.health_check()

            if service_health.status == ServiceStatus.HEALTHY:
                logger.info(f"✅ {service_name} service healthy")
            else:
                logger.error(f"❌ {service_name} service unhealthy: {service_health}")
                return False

        logger.info("🎉 All Service Registry migration tests passed!")
        return True

    except Exception as e:
        logger.error(f"❌ Service Registry test failed: {str(e)}")
        return False


async def test_api_endpoints():
    """Test API endpoints using the Service Registry."""
    try:
        logger.info("🧪 Testing API Endpoints...")

        # Test v1 endpoints
        logger.info("Testing v1 endpoints...")
        try:
            # These would normally be HTTP requests, but we'll test the service methods directly
            people_v1 = await service_manager.get_all_people_v1()
            projects_v1 = await service_manager.get_all_projects_v1()
            subscriptions_v1 = await service_manager.get_all_subscriptions_v1()

            logger.info("✅ v1 endpoints accessible")
        except Exception as e:
            logger.error(f"❌ v1 endpoints failed: {str(e)}")
            return False

        # Test v2 endpoints
        logger.info("Testing v2 endpoints...")
        try:
            people_v2 = await service_manager.get_all_people_v2()
            projects_v2 = await service_manager.get_all_projects_v2()
            subscriptions_v2 = await service_manager.get_all_subscriptions_v2()

            logger.info("✅ v2 endpoints accessible")
        except Exception as e:
            logger.error(f"❌ v2 endpoints failed: {str(e)}")
            return False

        logger.info("🎉 All API endpoint tests passed!")
        return True

    except Exception as e:
        logger.error(f"❌ API endpoint test failed: {str(e)}")
        return False


async def main():
    """Run all migration tests."""
    logger.info("🚀 Starting Service Registry Migration Tests")

    # Test Service Registry
    registry_test = await test_service_registry()

    # Test API Endpoints
    api_test = await test_api_endpoints()

    if registry_test and api_test:
        logger.info("🎉 Migration verification completed successfully!")
        logger.info("✅ Service Registry architecture is working correctly")
        logger.info("🔄 Ready to switch from monolithic to modular handler")
        return True
    else:
        logger.error("❌ Migration verification failed")
        logger.error("🔧 Please check the logs and fix issues before proceeding")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
'''

            test_script_path = self.src_dir / "scripts" / "test_migration.py"
            test_script_path.parent.mkdir(exist_ok=True)

            with open(test_script_path, "w") as f:
                f.write(test_script_content)

            # Make it executable
            os.chmod(test_script_path, 0o755)

            logger.info(f"Migration test script created: {test_script_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to create migration test script: {str(e)}")
            return False

    def run_migration(self):
        """Run the complete migration process."""
        logger.info("🚀 Starting Service Registry Migration")

        steps = [
            ("Creating backup", self.create_backup),
            (
                "Verifying Service Registry infrastructure",
                self.verify_service_registry_infrastructure,
            ),
            ("Verifying domain services", self.verify_domain_services),
            ("Verifying modular handler", self.verify_modular_handler),
            ("Creating migration test script", self.create_migration_test_script),
        ]

        for step_name, step_function in steps:
            logger.info(f"📋 {step_name}...")
            if not step_function():
                logger.error(f"❌ Migration failed at step: {step_name}")
                return False
            logger.info(f"✅ {step_name} completed")

        logger.info("🎉 Service Registry Migration completed successfully!")
        logger.info("📝 Next steps:")
        logger.info(
            "   1. Run the migration test: python src/scripts/test_migration.py"
        )
        logger.info("   2. Update your main application to use modular_api_handler.py")
        logger.info("   3. Run your existing tests to ensure compatibility")
        logger.info("   4. Deploy and monitor the new architecture")

        return True


def main():
    """Main migration function."""
    if len(sys.argv) != 2:
        print("Usage: python migrate_to_service_registry.py <project_root>")
        print("Example: python migrate_to_service_registry.py /path/to/registry-api")
        sys.exit(1)

    project_root = sys.argv[1]

    if not os.path.exists(project_root):
        print(f"Error: Project root does not exist: {project_root}")
        sys.exit(1)

    migration = ServiceRegistryMigration(project_root)
    success = migration.run_migration()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
