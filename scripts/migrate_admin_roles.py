#!/usr/bin/env python3
"""
Migration script to move hardcoded admin emails to database-driven roles.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Import with absolute paths
from src.models.roles import RoleType, RoleAssignmentRequest
from src.services.roles_service import RolesService

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def migrate_hardcoded_admins():
    """
    Migrate hardcoded admin emails to database roles.
    """
    logger.info("Starting admin roles migration...")

    # Initialize roles service
    roles_service = RolesService()

    # Hardcoded admin emails to migrate
    hardcoded_admins = [
        {
            "email": "admin@cbba.cloud.org.bo",
            "role": RoleType.SUPER_ADMIN,
            "notes": "Migrated from hardcoded admin list - Original system admin",
        },
        {
            "email": "admin@awsugcbba.org",
            "role": RoleType.SUPER_ADMIN,
            "notes": "Migrated from hardcoded admin list - AWS User Group Cochabamba admin",
        },
        {
            "email": "sergio.rodriguez.inclan@gmail.com",
            "role": RoleType.SUPER_ADMIN,
            "notes": "Migrated from hardcoded admin list - System administrator",
        },
    ]

    migration_results = []
    system_user_id = "system-migration"

    for admin in hardcoded_admins:
        try:
            logger.info(
                f"Migrating admin: {admin['email']} with role: {admin['role'].value}"
            )

            # Check if user already has roles
            existing_roles = await roles_service.get_user_roles_by_email(admin["email"])

            if existing_roles:
                logger.info(
                    f"User {admin['email']} already has roles: {[r.value for r in existing_roles]}"
                )
                migration_results.append(
                    {
                        "email": admin["email"],
                        "role": admin["role"].value,
                        "success": True,
                        "message": f"User already has roles: {[r.value for r in existing_roles]}",
                        "action": "skipped",
                    }
                )
                continue

            # Create role assignment request
            request = RoleAssignmentRequest(
                user_email=admin["email"], role_type=admin["role"], notes=admin["notes"]
            )

            # Assign the role
            response = await roles_service.assign_role(request, system_user_id)

            migration_results.append(
                {
                    "email": admin["email"],
                    "role": admin["role"].value,
                    "success": response.success,
                    "message": response.message,
                    "action": "assigned" if response.success else "failed",
                }
            )

            if response.success:
                logger.info(f"Successfully migrated {admin['email']}")
            else:
                logger.error(f"Failed to migrate {admin['email']}: {response.message}")

        except Exception as e:
            logger.error(f"Error migrating {admin['email']}: {str(e)}")
            migration_results.append(
                {
                    "email": admin["email"],
                    "role": admin["role"].value,
                    "success": False,
                    "message": f"Exception: {str(e)}",
                    "action": "error",
                }
            )

    # Print migration summary
    logger.info("\n" + "=" * 60)
    logger.info("MIGRATION SUMMARY")
    logger.info("=" * 60)

    successful_migrations = 0
    skipped_migrations = 0
    failed_migrations = 0

    for result in migration_results:
        status_icon = "✅" if result["success"] else "❌"
        action_text = result["action"].upper()

        logger.info(
            f"{status_icon} {result['email']} ({result['role']}) - {action_text}"
        )
        logger.info(f"   Message: {result['message']}")

        if result["action"] == "assigned":
            successful_migrations += 1
        elif result["action"] == "skipped":
            skipped_migrations += 1
        else:
            failed_migrations += 1

    logger.info("-" * 60)
    logger.info(f"Total admins processed: {len(migration_results)}")
    logger.info(f"Successfully migrated: {successful_migrations}")
    logger.info(f"Skipped (already exists): {skipped_migrations}")
    logger.info(f"Failed: {failed_migrations}")
    logger.info("=" * 60)

    if failed_migrations > 0:
        logger.warning("Some migrations failed. Please review the errors above.")
        return False
    else:
        logger.info("Migration completed successfully!")
        return True


async def verify_migration():
    """
    Verify that the migration was successful by checking admin roles.
    """
    logger.info("\nVerifying migration...")

    roles_service = RolesService()

    admin_emails = [
        "admin@cbba.cloud.org.bo",
        "admin@awsugcbba.org",
        "sergio.rodriguez.inclan@gmail.com",
    ]

    verification_results = []

    for email in admin_emails:
        try:
            roles = await roles_service.get_user_roles_by_email(email)
            has_super_admin = RoleType.SUPER_ADMIN in roles

            verification_results.append(
                {
                    "email": email,
                    "roles": [r.value for r in roles],
                    "has_super_admin": has_super_admin,
                    "success": has_super_admin,
                }
            )

        except Exception as e:
            logger.error(f"Error verifying {email}: {str(e)}")
            verification_results.append(
                {
                    "email": email,
                    "roles": [],
                    "has_super_admin": False,
                    "success": False,
                    "error": str(e),
                }
            )

    logger.info("\nVERIFICATION RESULTS:")
    logger.info("-" * 40)

    all_verified = True
    for result in verification_results:
        status_icon = "✅" if result["success"] else "❌"
        logger.info(f"{status_icon} {result['email']}")
        logger.info(f"   Roles: {result['roles']}")
        logger.info(f"   Has Super Admin: {result['has_super_admin']}")

        if not result["success"]:
            all_verified = False
            if "error" in result:
                logger.info(f"   Error: {result['error']}")

    if all_verified:
        logger.info("\n✅ All admin users verified successfully!")
    else:
        logger.warning("\n❌ Some admin users could not be verified.")

    return all_verified


async def main():
    """
    Main migration function.
    """
    try:
        logger.info("Starting admin roles migration process...")

        # Run migration
        migration_success = await migrate_hardcoded_admins()

        if migration_success:
            # Verify migration
            verification_success = await verify_migration()

            if verification_success:
                logger.info("\n🎉 Migration and verification completed successfully!")
                logger.info("\nNext steps:")
                logger.info(
                    "1. Update your application to use the new admin_middleware_v2.py"
                )
                logger.info(
                    "2. Remove the hardcoded admin emails from the old middleware"
                )
                logger.info("3. Test the new role-based access control system")
                return 0
            else:
                logger.error("\n❌ Migration completed but verification failed.")
                return 1
        else:
            logger.error("\n❌ Migration failed.")
            return 1

    except Exception as e:
        logger.error(f"Migration process failed: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
