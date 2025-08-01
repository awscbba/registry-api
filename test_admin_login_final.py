#!/usr/bin/env python3
"""
Test admin login functionality with the created admin user.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from fastapi.testclient import TestClient
from src.handlers.versioned_api_handler import app


def test_admin_login():
    """Test admin login flow with the created admin user."""
    print("🔐 Testing admin login flow...")

    client = TestClient(app)

    # Use the admin credentials from the creation script
    admin_email = "admin@awsugcbba.org"
    admin_password = "admin123"

    print(f"1. Testing login with admin credentials: {admin_email}")
    response = client.post(
        "/auth/login", json={"email": admin_email, "password": admin_password}
    )

    print(f"   Login response: {response.status_code}")

    if response.status_code == 200:
        login_data = response.json()
        print(f"   ✅ Login successful!")
        print(
            f"   User: {login_data['user']['firstName']} {login_data['user']['lastName']}"
        )
        print(f"   Email: {login_data['user']['email']}")
        print(f"   Token type: {login_data['token_type']}")
        print(f"   Expires in: {login_data['expires_in']} seconds")
        print(f"   Require password change: {login_data['require_password_change']}")

        # Test authenticated endpoint
        print("2. Testing authenticated endpoint (/auth/me)...")
        token = login_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/auth/me", headers=headers)
        print(f"   Me endpoint: {me_response.status_code}")

        if me_response.status_code == 200:
            me_data = me_response.json()
            print(f"   ✅ Authenticated request successful!")
            print(
                f"   User info: {me_data['user']['firstName']} {me_data['user']['lastName']}"
            )
            print(f"   Email: {me_data['user']['email']}")
            print(f"   Active: {me_data['user']['isActive']}")
        else:
            print(f"   ❌ Authenticated request failed: {me_response.json()}")

        # Test admin endpoint
        print("3. Testing admin endpoint (/v2/admin/test)...")
        admin_response = client.get("/v2/admin/test", headers=headers)
        print(f"   Admin test: {admin_response.status_code}")

        if admin_response.status_code == 200:
            print(f"   ✅ Admin endpoint accessible!")
            admin_data = admin_response.json()
            print(f"   Message: {admin_data.get('message', 'No message')}")
            if "admin_user" in admin_data:
                admin_user = admin_data["admin_user"]
                print(
                    f"   Admin user: {admin_user.get('firstName', 'Unknown')} {admin_user.get('lastName', '')}"
                )
                print(f"   Is admin: {admin_user.get('isAdmin', False)}")
        else:
            print(f"   ❌ Admin endpoint failed: {admin_response.json()}")

        # Test logout
        print("4. Testing logout...")
        logout_response = client.post("/auth/logout", headers=headers)
        print(f"   Logout: {logout_response.status_code}")

        if logout_response.status_code == 200:
            logout_data = logout_response.json()
            print(f"   ✅ Logout successful!")
            print(f"   Message: {logout_data['message']}")
        else:
            print(f"   ❌ Logout failed: {logout_response.json()}")

    else:
        print(f"   ❌ Login failed: {response.json()}")

    print("✅ Admin login test completed!")


if __name__ == "__main__":
    test_admin_login()
