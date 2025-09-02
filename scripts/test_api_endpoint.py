#!/usr/bin/env python3
"""
Test the actual API endpoint to simulate frontend request.
"""

import asyncio
import json
import sys
import os
from fastapi.testclient import TestClient

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app


def test_login_endpoint():
    """Test the /auth/login endpoint directly."""
    print("🔍 Testing /auth/login API Endpoint")
    print("=" * 50)

    # Create test client
    client = TestClient(app)

    # Test credentials
    login_data = {
        "email": "sergio.rodriguez@cbba.cloud.org.bo",
        "password": "AdminCbba2025!",
    }

    print(f"📧 Email: {login_data['email']}")
    print(f"🔑 Password: {'*' * len(login_data['password'])}")
    print()

    # Test the endpoint
    print("🚀 Making POST request to /auth/login...")
    try:
        response = client.post("/auth/login", json=login_data)

        print(f"📊 Response Status: {response.status_code}")
        print(f"📋 Response Headers: {dict(response.headers)}")
        print()

        if response.status_code == 200:
            print("✅ SUCCESS! Login endpoint working correctly")
            response_data = response.json()
            print("📄 Response Data:")
            print(json.dumps(response_data, indent=2))

            # Validate response structure
            if "success" in response_data and response_data["success"]:
                data = response_data.get("data", {})
                if "accessToken" in data and "user" in data:
                    print("\n✅ Response structure is correct!")
                    print(f"   - Access Token: {data['accessToken'][:50]}...")
                    print(f"   - User ID: {data['user']['id']}")
                    print(f"   - User Email: {data['user']['email']}")
                    print(f"   - Is Admin: {data['user']['isAdmin']}")
                else:
                    print("\n⚠️  Response missing expected fields")
            else:
                print("\n❌ Response indicates failure")
        else:
            print(f"❌ FAILED! Status: {response.status_code}")
            print("📄 Error Response:")
            try:
                error_data = response.json()
                print(json.dumps(error_data, indent=2))
            except Exception:
                print(response.text)

    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        import traceback

        traceback.print_exc()

    print()

    # Test with invalid credentials
    print("🔍 Testing with invalid credentials...")
    invalid_data = {
        "email": "sergio.rodriguez@cbba.cloud.org.bo",
        "password": "WrongPassword123!",
    }

    try:
        response = client.post("/auth/login", json=invalid_data)
        print(f"📊 Invalid Credentials Response Status: {response.status_code}")

        if response.status_code == 401:
            print("✅ Correctly rejected invalid credentials")
        else:
            print("⚠️  Unexpected response for invalid credentials")

        response_data = response.json()
        print("📄 Invalid Credentials Response:")
        print(json.dumps(response_data, indent=2))

    except Exception as e:
        print(f"❌ Exception with invalid credentials: {e}")


if __name__ == "__main__":
    test_login_endpoint()
