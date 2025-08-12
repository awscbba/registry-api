#!/usr/bin/env python3
"""
Test the API login endpoint directly.
"""

import requests
import json


def test_api_login():
    """Test the deployed API login endpoint."""

    print("🔐 Testing API Login Endpoint")
    print("=" * 50)

    # API endpoint
    api_url = "https://2t9blvt2c1.execute-api.us-east-1.amazonaws.com/prod/auth/login"

    # Admin credentials
    admin_email = "admin@awsugcbba.org"
    admin_password = "awsugcbba2025"

    print(f"1. Testing login at: {api_url}")
    print(f"   Email: {admin_email}")
    print(f"   Password: {admin_password}")

    try:
        # Make login request
        response = requests.post(
            api_url,
            json={"email": admin_email, "password": admin_password},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        print(f"\n2. Response Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Login successful!")
            print(
                f"   User: {data.get('user', {}).get('firstName', 'N/A')} {data.get('user', {}).get('lastName', 'N/A')}"
            )
            print(f"   Email: {data.get('user', {}).get('email', 'N/A')}")
            print(f"   Is Admin: {data.get('user', {}).get('isAdmin', False)}")
            print(f"   Token Type: {data.get('token_type', 'N/A')}")
            print(f"   Expires In: {data.get('expires_in', 'N/A')} seconds")

            # Test an admin endpoint
            token = data.get("access_token")
            if token:
                print(f"\n3. Testing admin endpoint...")
                admin_url = "https://2t9blvt2c1.execute-api.us-east-1.amazonaws.com/prod/v2/admin/dashboard"

                admin_response = requests.get(
                    admin_url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    timeout=30,
                )

                print(f"   Admin Dashboard Status: {admin_response.status_code}")
                if admin_response.status_code == 200:
                    print(f"   ✅ Admin access working!")
                else:
                    print(f"   ❌ Admin access failed: {admin_response.text}")

        else:
            print(f"   ❌ Login failed!")
            print(f"   Response: {response.text}")

    except Exception as e:
        print(f"   ❌ Error: {str(e)}")


if __name__ == "__main__":
    test_api_login()
