#!/usr/bin/env python3
"""
Script to create the first admin user for the system.
"""

import asyncio
import sys
import os
from datetime import datetime, timezone

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from services.defensive_dynamodb_service import DefensiveDynamoDBService
from models.person import PersonCreate, Address
from utils.password_utils import PasswordHasher
import uuid


async def create_admin_user():
    """Create the first admin user."""

    print("🔧 Creating Admin User")
    print("=" * 50)

    # Initialize services
    db_service = DefensiveDynamoDBService()
    password_hasher = PasswordHasher()

    # Admin user details
    admin_email = "admin@cbba.cloud.org.bo"
    admin_password = "AdminPassword123!"  # Should be changed on first login

    print(f"Creating admin user: {admin_email}")

    try:
        # Check if admin user already exists
        existing_user = await db_service.get_person_by_email(admin_email)
        if existing_user:
            print(f"❌ Admin user {admin_email} already exists!")

            # Check if they're already an admin
            if getattr(existing_user, "is_admin", False):
                print("✅ User is already an admin")
                return existing_user
            else:
                print("🔧 Updating existing user to admin status...")
                from models.person import PersonUpdate

                update_data = PersonUpdate(isAdmin=True)
                updated_user = await db_service.update_person(
                    existing_user.id, update_data
                )
                print("✅ User updated to admin status")
                return updated_user

        # Create password hash
        password_hash, password_salt = password_hasher.hash_password(admin_password)

        # Create admin user
        admin_address = Address(
            street="Admin Street 123",
            city="Cochabamba",
            state="Cochabamba",
            postalCode="00000",
            country="Bolivia",
        )

        admin_person = PersonCreate(
            firstName="System",
            lastName="Administrator",
            email=admin_email,
            phone="+591-00000000",
            dateOfBirth="1990-01-01",
            address=admin_address,
            isAdmin=True,  # This is the key field!
            password_hash=password_hash,
            password_salt=password_salt,
        )

        # Create the admin user
        created_admin = await db_service.create_person(admin_person)

        print("✅ Admin user created successfully!")
        print(f"   ID: {created_admin.id}")
        print(f"   Email: {created_admin.email}")
        print(f"   Name: {created_admin.first_name} {created_admin.last_name}")
        print(f"   Is Admin: {created_admin.is_admin}")
        print(f"   Password: {admin_password}")
        print("")
        print("🚨 IMPORTANT SECURITY NOTES:")
        print("1. Change the admin password immediately after first login")
        print("2. Use a strong, unique password")
        print("3. Enable two-factor authentication if available")
        print("4. Regularly review admin access logs")

        return created_admin

    except Exception as e:
        print(f"❌ Error creating admin user: {str(e)}")
        raise


async def create_test_admin_user():
    """Create a test admin user for development."""

    print("\n🧪 Creating Test Admin User")
    print("=" * 50)

    # Initialize services
    db_service = DefensiveDynamoDBService()
    password_hasher = PasswordHasher()

    # Test admin user details
    test_admin_email = "sergio.rodriguez.inclan@gmail.com"
    test_admin_password = "TestAdmin123!"

    print(f"Creating test admin user: {test_admin_email}")

    try:
        # Check if test admin user already exists
        existing_user = await db_service.get_person_by_email(test_admin_email)
        if existing_user:
            print(f"❌ Test admin user {test_admin_email} already exists!")

            # Check if they're already an admin
            if getattr(existing_user, "is_admin", False):
                print("✅ User is already an admin")
                return existing_user
            else:
                print("🔧 Updating existing user to admin status...")
                from models.person import PersonUpdate

                update_data = PersonUpdate(isAdmin=True)
                updated_user = await db_service.update_person(
                    existing_user.id, update_data
                )
                print("✅ User updated to admin status")
                return updated_user

        # Create password hash
        password_hash, password_salt = password_hasher.hash_password(
            test_admin_password
        )

        # Create test admin user
        test_admin_address = Address(
            street="Test Street 456",
            city="Cochabamba",
            state="Cochabamba",
            postalCode="00001",
            country="Bolivia",
        )

        test_admin_person = PersonCreate(
            firstName="Sergio",
            lastName="Rodriguez",
            email=test_admin_email,
            phone="+591-11111111",
            dateOfBirth="1985-01-01",
            address=test_admin_address,
            isAdmin=True,  # This is the key field!
            password_hash=password_hash,
            password_salt=password_salt,
        )

        # Create the test admin user
        created_test_admin = await db_service.create_person(test_admin_person)

        print("✅ Test admin user created successfully!")
        print(f"   ID: {created_test_admin.id}")
        print(f"   Email: {created_test_admin.email}")
        print(
            f"   Name: {created_test_admin.first_name} {created_test_admin.last_name}"
        )
        print(f"   Is Admin: {created_test_admin.is_admin}")
        print(f"   Password: {test_admin_password}")

        return created_test_admin

    except Exception as e:
        print(f"❌ Error creating test admin user: {str(e)}")
        raise


async def verify_admin_users():
    """Verify that admin users were created correctly."""

    print("\n🔍 Verifying Admin Users")
    print("=" * 50)

    db_service = DefensiveDynamoDBService()

    admin_emails = ["admin@cbba.cloud.org.bo", "sergio.rodriguez.inclan@gmail.com"]

    for email in admin_emails:
        try:
            user = await db_service.get_person_by_email(email)
            if user:
                is_admin = getattr(user, "is_admin", False)
                print(f"✅ {email}: {'Admin' if is_admin else 'Regular User'}")
                if not is_admin:
                    print(f"   ⚠️  WARNING: User exists but is not an admin!")
            else:
                print(f"❌ {email}: Not found")
        except Exception as e:
            print(f"❌ {email}: Error checking user - {str(e)}")


async def main():
    """Main function to create admin users."""

    print("🚀 Admin User Creation Script")
    print("=" * 60)

    try:
        # Create main admin user
        await create_admin_user()

        # Create test admin user
        await create_test_admin_user()

        # Verify admin users
        await verify_admin_users()

        print("\n🎉 Admin user creation completed successfully!")
        print("\n📋 Next Steps:")
        print("1. Test admin login with the created credentials")
        print("2. Change default passwords immediately")
        print("3. Test admin panel access")
        print("4. Verify role-based access control is working")

    except Exception as e:
        print(f"\n❌ Script failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
