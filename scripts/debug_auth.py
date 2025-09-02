#!/usr/bin/env python3
"""
Debug authentication endpoint by simulating frontend request.
"""

import asyncio
import json
import sys
import os

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.auth_service import AuthService
from src.repositories.people_repository import PeopleRepository


async def debug_authentication():
    """Debug the authentication flow step by step."""
    print("🔍 Debugging Authentication Flow")
    print("=" * 50)

    # Test credentials
    email = "sergio.rodriguez@cbba.cloud.org.bo"
    password = "AdminCbba2025!"

    print(f"📧 Email: {email}")
    print(f"🔑 Password: {'*' * len(password)}")
    print()

    # Step 1: Check if user exists
    print("Step 1: Checking if user exists...")
    people_repo = PeopleRepository()

    try:
        # Check regular get_by_email (returns PersonResponse without passwordHash)
        person_response = await people_repo.get_by_email(email)
        if person_response:
            print(
                f"✅ User found via get_by_email: {person_response.firstName} {person_response.lastName}"
            )
            print(f"   - ID: {person_response.id}")
            print(f"   - Email: {person_response.email}")
            print(f"   - Is Admin: {person_response.isAdmin}")
            print(f"   - Is Active: {person_response.isActive}")
        else:
            print("❌ User NOT found via get_by_email")
            return
    except Exception as e:
        print(f"❌ Error in get_by_email: {e}")
        return

    print()

    # Step 2: Check auth-specific method
    print("Step 2: Checking auth-specific user data...")
    try:
        person_data = await people_repo.get_by_email_for_auth(email)
        if person_data:
            print(f"✅ User found via get_by_email_for_auth")
            print(f"   - ID: {person_data.get('id')}")
            print(f"   - Email: {person_data.get('email')}")
            print(f"   - Is Admin: {person_data.get('isAdmin')}")
            print(f"   - Is Active: {person_data.get('isActive')}")
            print(f"   - Has Password Hash: {'passwordHash' in person_data}")
            if "passwordHash" in person_data:
                hash_preview = (
                    person_data["passwordHash"][:20] + "..."
                    if len(person_data["passwordHash"]) > 20
                    else person_data["passwordHash"]
                )
                print(f"   - Password Hash Preview: {hash_preview}")
        else:
            print("❌ User NOT found via get_by_email_for_auth")
            return
    except Exception as e:
        print(f"❌ Error in get_by_email_for_auth: {e}")
        return

    print()

    # Step 3: Test password verification directly
    print("Step 3: Testing password verification directly...")
    try:
        from src.utils.password_utils import PasswordHasher

        if person_data and "passwordHash" in person_data:
            is_valid = PasswordHasher.verify_password(
                password, person_data["passwordHash"]
            )
            print(f"✅ Direct password verification: {is_valid}")
        else:
            print("❌ No password hash available for direct verification")
    except Exception as e:
        print(f"❌ Password verification error: {e}")

    print()

    # Step 4: Test authentication service
    print("Step 4: Testing AuthService.authenticate_user...")
    auth_service = AuthService()

    try:
        result = await auth_service.authenticate_user(email, password)
        if result:
            print("✅ Authentication SUCCESSFUL!")
            print(f"   - Access Token: {result.accessToken[:50]}...")
            print(f"   - Refresh Token: {result.refreshToken[:50]}...")
            print(f"   - Expires In: {result.expiresIn} seconds")
            print(f"   - User ID: {result.user['id']}")
            print(f"   - User Email: {result.user['email']}")
            print(f"   - Is Admin: {result.user['isAdmin']}")

            # Test the complete response format
            print("\n📋 Complete LoginResponse:")
            response_dict = result.model_dump()
            print(json.dumps(response_dict, indent=2))
        else:
            print("❌ Authentication FAILED - returned None")
    except Exception as e:
        print(f"❌ Authentication ERROR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_authentication())
