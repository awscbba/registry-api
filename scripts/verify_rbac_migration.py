#!/usr/bin/env python3
"""
Script to verify the RBAC migration was successful and system is working correctly.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from models.roles import RoleType, Permission
from services.roles_service import RolesService

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def verify_admin_roles():
    """Verify that all expected admin roles are in the database."""
    logger.info("🔍 Verifying admin roles in database...")

    roles_service = RolesService()

    expected_admins = [
        "admin@cbba.cloud.org.bo",
        "admin@awsugcbba.org",
        "sergio.rodriguez.inclan@gmail.com",
    ]

    verification_results = []

    for email in expected_admins:
        try:
            roles = await roles_service.get_user_roles_by_email(email)
            is_admin = any(
                role in [RoleType.ADMIN, RoleType.SUPER_ADMIN] for role in roles
            )

            verification_results.append(
                {
                    "email": email,
                    "roles": [role.value for role in roles],
                    "is_admin": is_admin,
                    "success": is_admin,
                }
            )

            if is_admin:
                logger.info(
                    f"✅ {email} has admin roles: {[role.value for role in roles]}"
                )
            else:
                logger.warning(
                    f"⚠️  {email} does not have admin roles: {[role.value for role in roles]}"
                )

        except Exception as e:
            logger.error(f"❌ Error checking roles for {email}: {e}")
            verification_results.append(
                {
                    "email": email,
                    "roles": [],
                    "is_admin": False,
                    "success": False,
                    "error": str(e),
                }
            )

    return verification_results


async def test_permission_system():
    """Test the permission system with various scenarios."""
    logger.info("🧪 Testing permission system...")

    roles_service = RolesService()
    test_results = []

    # Test cases
    test_cases = [
        {
            "email": "admin@cbba.cloud.org.bo",
            "permission": Permission.MANAGE_USERS,
            "expected": True,
            "description": "Super admin should have MANAGE_USERS permission",
        },
        {
            "email": "admin@awsugcbba.org",
            "permission": Permission.VIEW_ADMIN_DASHBOARD,
            "expected": True,
            "description": "Super admin should have VIEW_ADMIN_DASHBOARD permission",
        },
        {
            "email": "nonexistent@example.com",
            "permission": Permission.MANAGE_USERS,
            "expected": False,
            "description": "Non-existent user should not have admin permissions",
        },
    ]

    for test_case in test_cases:
        try:
            has_permission = await roles_service.user_has_permission_by_email(
                test_case["email"], test_case["permission"]
            )

            success = has_permission == test_case["expected"]

            test_results.append(
                {
                    "email": test_case["email"],
                    "permission": test_case["permission"].value,
                    "expected": test_case["expected"],
                    "actual": has_permission,
                    "success": success,
                    "description": test_case["description"],
                }
            )

            if success:
                logger.info(f"✅ {test_case['description']}: PASS")
            else:
                logger.error(
                    f"❌ {test_case['description']}: FAIL (expected {test_case['expected']}, got {has_permission})"
                )

        except Exception as e:
            logger.error(f"❌ Error testing {test_case['description']}: {e}")
            test_results.append(
                {
                    "email": test_case["email"],
                    "permission": test_case["permission"].value,
                    "expected": test_case["expected"],
                    "actual": None,
                    "success": False,
                    "description": test_case["description"],
                    "error": str(e),
                }
            )

    return test_results


async def check_middleware_compatibility():
    """Check that both middleware versions are available."""
    logger.info("🔧 Checking middleware compatibility...")

    try:
        # Check if both middleware files exist
        middleware_v1_path = os.path.join(
            os.path.dirname(__file__), "..", "src", "middleware", "admin_middleware.py"
        )
        middleware_v2_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "middleware",
            "admin_middleware_v2.py",
        )

        v1_exists = os.path.exists(middleware_v1_path)
        v2_exists = os.path.exists(middleware_v2_path)

        logger.info(
            f"admin_middleware.py (legacy): {'✅ Found' if v1_exists else '❌ Missing'}"
        )
        logger.info(
            f"admin_middleware_v2.py (new): {'✅ Found' if v2_exists else '❌ Missing'}"
        )

        if not v2_exists:
            logger.error(
                "❌ admin_middleware_v2.py is missing! This is required for the new RBAC system."
            )
            return False

        # Try to import both
        try:
            from middleware.admin_middleware import (
                require_admin_access as require_admin_v1,
            )

            logger.info("✅ Successfully imported admin_middleware (v1)")
        except ImportError as e:
            logger.error(f"❌ Failed to import admin_middleware (v1): {e}")

        try:
            from middleware.admin_middleware_v2 import (
                require_admin_access as require_admin_v2,
            )

            logger.info("✅ Successfully imported admin_middleware_v2 (v2)")
        except ImportError as e:
            logger.error(f"❌ Failed to import admin_middleware_v2 (v2): {e}")
            return False

        return True

    except Exception as e:
        logger.error(f"❌ Error checking middleware compatibility: {e}")
        return False


def generate_migration_report(admin_results, permission_results, middleware_check):
    """Generate a comprehensive migration report."""
    logger.info("\n" + "=" * 60)
    logger.info("📊 RBAC MIGRATION VERIFICATION REPORT")
    logger.info("=" * 60)

    # Admin roles summary
    logger.info("\n🔐 ADMIN ROLES VERIFICATION:")
    admin_success_count = sum(1 for result in admin_results if result["success"])
    logger.info(f"  ✅ Successful: {admin_success_count}/{len(admin_results)}")

    for result in admin_results:
        status = "✅" if result["success"] else "❌"
        logger.info(f"  {status} {result['email']}: {result['roles']}")

    # Permission system summary
    logger.info("\n🧪 PERMISSION SYSTEM TESTS:")
    permission_success_count = sum(
        1 for result in permission_results if result["success"]
    )
    logger.info(
        f"  ✅ Successful: {permission_success_count}/{len(permission_results)}"
    )

    for result in permission_results:
        status = "✅" if result["success"] else "❌"
        logger.info(f"  {status} {result['description']}")

    # Middleware compatibility
    logger.info("\n🔧 MIDDLEWARE COMPATIBILITY:")
    middleware_status = "✅ PASS" if middleware_check else "❌ FAIL"
    logger.info(f"  {middleware_status}")

    # Overall status
    logger.info("\n🎯 OVERALL MIGRATION STATUS:")
    all_admin_success = admin_success_count == len(admin_results)
    all_permission_success = permission_success_count == len(permission_results)
    overall_success = all_admin_success and all_permission_success and middleware_check

    if overall_success:
        logger.info("  🎉 MIGRATION SUCCESSFUL! Ready to switch to admin_middleware_v2")
        logger.info("\n📋 NEXT STEPS:")
        logger.info("  1. Update handler imports to use admin_middleware_v2")
        logger.info("  2. Test endpoints with the new middleware")
        logger.info("  3. Remove hardcoded emails from admin_middleware.py")
        logger.info("  4. Eventually remove admin_middleware.py entirely")
    else:
        logger.error("  ❌ MIGRATION INCOMPLETE! Please fix issues before proceeding.")

    logger.info("=" * 60)

    return overall_success


async def main():
    """Main verification function."""
    logger.info("🚀 Starting RBAC migration verification...")

    try:
        # Verify admin roles
        admin_results = await verify_admin_roles()

        # Test permission system
        permission_results = await test_permission_system()

        # Check middleware compatibility
        middleware_check = await check_middleware_compatibility()

        # Generate report
        success = generate_migration_report(
            admin_results, permission_results, middleware_check
        )

        if success:
            logger.info("✅ Migration verification completed successfully!")
            sys.exit(0)
        else:
            logger.error("❌ Migration verification failed!")
            sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Verification failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
