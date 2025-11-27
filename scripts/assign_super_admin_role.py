#!/usr/bin/env python3
"""
Assign super_admin role to a user.
This script properly assigns roles through the RBAC system.
"""

import sys
import os
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.rbac_service import RBACService
from src.models.rbac import RoleType, RoleAssignmentRequest


async def assign_super_admin(user_id: str, assigned_by: str = "system"):
    """Assign super_admin role to a user."""
    from src.repositories.people_repository import PeopleRepository
    from src.repositories.roles_repository import RolesRepository
    from src.models.rbac import UserRole

    people_repo = PeopleRepository()
    roles_repo = RolesRepository()
    rbac_service = RBACService()

    print(f"Assigning super_admin role to user: {user_id}")

    try:
        # Get user email
        person = people_repo.get_by_id(user_id)
        if not person:
            print(f"✗ User not found: {user_id}")
            return False

        print(f"  User: {person.firstName} {person.lastName} ({person.email})")

        # Create role assignment directly (bypassing permission checks for system setup)
        user_role = UserRole(
            user_id=user_id,
            user_email=person.email,
            role_type=RoleType.SUPER_ADMIN,
            assigned_by=assigned_by,
            notes="Initial super admin setup",
        )

        # Save directly to database
        roles_repo.create_role_assignment(user_role)

        print(f"✓ Successfully assigned super_admin role")
        print(f"  User ID: {user_role.user_id}")
        print(f"  Role: {user_role.role_type.value}")

        # Verify the assignment
        user_roles = await rbac_service.get_user_roles(user_id)
        print(f"\n✓ Verified user roles: {[role.value for role in user_roles]}")

        return True

    except Exception as e:
        print(f"✗ Error assigning role: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python assign_super_admin_role.py <user_id> [assigned_by]")
        print("\nExample:")
        print(
            "  python assign_super_admin_role.py 4a375abe-6d1a-47bc-98ff-ced6f8247c1b system"
        )
        sys.exit(1)

    user_id = sys.argv[1]
    assigned_by = sys.argv[2] if len(sys.argv) > 2 else "system"

    success = await assign_super_admin(user_id, assigned_by)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
