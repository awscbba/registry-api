#!/usr/bin/env python3
"""
Diagnostic script to check and fix admin login issues.
"""

import asyncio
import sys
import os
from datetime import datetime, timezone

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from services.defensive_dynamodb_service import DefensiveDynamoDBService
from services.auth_service import AuthService
from models.person import PersonCreate, PersonUpdate, Address
from models.auth import LoginRequest
from utils.password_utils import PasswordHasher
import uuid


async def diagnose_admin_login():
    """Diagnose and fix admin login issues."""

    print("🔍 Diagnosing Admin Login Issues")
    print("=" * 50)

    # Initialize services
    db_service = DefensiveDynamoDBService()
    auth_service = AuthService()
    password_hasher = PasswordHasher()

    # Test both possible admin emails
    admin_emails = [
        "admin@awsugcbba.org",  # From test
        "admin@cbba.cloud.org.bo",  # From create script
    ]

    admin_passwords = [
        "admin123",  # From test
        "AdminPassword123!",  # From create script
    ]

    print("1. Checking existing admin users...")

    existing_admin = None
    for email in admin_emails:
        try:
            person = await db_service.get_person_by_email(email)
            if person:
                print(f"   ✅ Found user: {email}")
                print(f"      ID: {person.id}")
                print(f"      Name: {person.firstName} {person.lastName}")
                print(f"      Is Admin: {getattr(person, 'isAdmin', False)}")
                print(
                    f"      Has Password: {hasattr(person, 'password_hash') and person.password_hash is not None}"
                )
                print(f"      Is Active: {getattr(person, 'is_active', True)}")

                if getattr(person, "isAdmin", False):
                    existing_admin = person
                    break
            else:
                print(f"   ❌ User not found: {email}")
        except Exception as e:
            print(f"   ❌ Error checking {email}: {str(e)}")

    if not existing_admin:
        print("\n2. No admin user found. Creating admin user...")
        await create_admin_user(db_service, password_hasher)
        return

    print(f"\n2. Testing login with admin user: {existing_admin.email}")

    # Test login with different password combinations
    login_success = False
    working_password = None

    for password in admin_passwords:
        try:
            login_request = LoginRequest(email=existing_admin.email, password=password)
            success, response, error = await auth_service.authenticate_user(
                login_request
            )

            if success:
                print(f"   ✅ Login successful with password: {password}")
                print(f"      Token type: {response.token_type}")
                print(f"      Expires in: {response.expires_in}")
                login_success = True
                working_password = password
                break
            else:
                print(f"   ❌ Login failed with password '{password}': {error}")
        except Exception as e:
            print(f"   ❌ Login error with password '{password}': {str(e)}")

    if not login_success:
        print("\n3. Login failed with all passwords. Resetting admin password...")
        await reset_admin_password(db_service, existing_admin, password_hasher)
    else:
        print(f"\n✅ Admin login is working!")
        print(f"   Email: {existing_admin.email}")
        print(f"   Password: {working_password}")


async def create_admin_user(db_service, password_hasher):
    """Create a new admin user."""

    admin_email = "admin@awsugcbba.org"  # Use the email from the test
    admin_password = "admin123"  # Use the password from the test

    print(f"   Creating admin user: {admin_email}")

    try:
        # Hash the password
        password_hash = password_hasher.hash_password(admin_password)

        # Create admin user
        admin_data = PersonCreate(
            firstName="Admin",
            lastName="User",
            email=admin_email,
            phone="000-000-0000",
            dateOfBirth="1990-01-01",
            address=Address(
                street="Admin Street",
                city="Admin City",
                state="Admin State",
                postalCode="00000",
                country="Bolivia",
            ),
            isAdmin=True,
            password_hash=password_hash,
            password_salt="",  # Modern hashing doesn't need separate salt
            is_active=True,
        )

        person = await db_service.create_person(admin_data)
        print(f"   ✅ Admin user created successfully!")
        print(f"      ID: {person.id}")
        print(f"      Email: {admin_email}")
        print(f"      Password: {admin_password}")

    except Exception as e:
        print(f"   ❌ Error creating admin user: {str(e)}")


async def reset_admin_password(db_service, admin_user, password_hasher):
    """Reset admin user password."""

    new_password = "admin123"  # Use the test password

    print(f"   Resetting password for: {admin_user.email}")

    try:
        # Hash the new password
        password_hash = password_hasher.hash_password(new_password)

        # Update the user
        update_data = PersonUpdate(
            password_hash=password_hash,
            password_salt="",  # Modern hashing doesn't need separate salt
            isAdmin=True,  # Ensure admin status
            is_active=True,  # Ensure account is active
        )

        await db_service.update_person(admin_user.id, update_data)

        print(f"   ✅ Password reset successfully!")
        print(f"      Email: {admin_user.email}")
        print(f"      New Password: {new_password}")

        # Test the login again
        auth_service = AuthService()
        login_request = LoginRequest(email=admin_user.email, password=new_password)
        success, response, error = await auth_service.authenticate_user(login_request)

        if success:
            print(f"   ✅ Login test successful after password reset!")
        else:
            print(f"   ❌ Login test failed after password reset: {error}")

    except Exception as e:
        print(f"   ❌ Error resetting password: {str(e)}")


if __name__ == "__main__":
    asyncio.run(diagnose_admin_login())
