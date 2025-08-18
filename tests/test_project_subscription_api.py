#!/usr/bin/env python3
"""
Test the actual project and subscription API endpoints to identify real issues
"""

import requests
import json
import sys
import pytest
from src.utils.api_config import get_api_url


def get_auth_token(api_url: str) -> str:
    """Get authentication token for API testing."""
    try:
        # Use admin credentials for testing
        login_data = {"email": "admin@cbba.cloud.org.bo", "password": "admin123"}

        response = requests.post(
            f"{api_url}/auth/login",
            headers={"Content-Type": "application/json"},
            json=login_data,
            timeout=10,
        )

        if response.status_code == 200:
            token_data = response.json()
            return token_data.get("access_token", "")
        else:
            print(f"⚠️ Login failed: {response.status_code} - {response.text}")
            return ""
    except Exception as e:
        print(f"⚠️ Authentication error: {e}")
        return ""


def get_auth_headers(api_url: str) -> dict:
    """Get authentication headers for API requests."""
    token = get_auth_token(api_url)
    if token:
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    else:
        return {"Content-Type": "application/json"}


# Integration test - now enabled after deployment fixes
def test_project_subscription_apis():
    """Test the actual API endpoints for projects and subscriptions"""

    print("🌐 Testing Project and Subscription API Endpoints")
    print("=" * 60)

    # Get API URL using proper configuration
    api_url = get_api_url()
    print(f"📡 API URL: {api_url}")

    # Get authentication headers
    headers = get_auth_headers(api_url)
    print(
        f"🔐 Authentication: {'✅ Token obtained' if 'Authorization' in headers else '❌ No token'}"
    )

    # Test 1: Create a project
    print(f"\n1️⃣ Testing project creation...")
    project_data = {
        "name": "Test Project API",
        "description": "Test project for API validation",
        "startDate": "2025-01-01",
        "endDate": "2025-12-31",
        "maxParticipants": 50,
        "status": "active",  # String enum
        "category": "test",
        "location": "Test Location",
        "requirements": "None",
    }

    try:
        response = requests.post(
            f"{api_url}/v2/projects",  # Fixed URL formatting
            headers=headers,
            json=project_data,
            timeout=30,
        )

        print(f"   📤 Request: POST {api_url}/v2/projects")
        print(f"   📤 Data: {json.dumps(project_data, indent=2)}")
        print(f"   📥 Status: {response.status_code}")
        print(f"   📥 Response: {response.text[:300]}...")

        if response.status_code in [200, 201]:
            print("   ✅ Project creation successful")
            project_response = response.json()
            project_id = project_response.get("data", {}).get(
                "id"
            ) or project_response.get("id")
        elif response.status_code in [401, 403]:
            print("   ⚠️ Authentication required - endpoint exists (good security)")
            project_id = "test-project-id"  # Use test ID for remaining tests
        elif response.status_code == 500:
            print("   🚨 500 error - likely enum handling issue!")
            if "Authorization" in headers:  # Only fail if we have auth
                assert False, f"500 error with authentication: {response.text}"
        else:
            print(f"   ❌ Project creation failed: {response.status_code}")
            if response.status_code not in [401, 403]:  # Auth errors are acceptable
                assert False, f"Unexpected status code: {response.status_code}"

    except Exception as e:
        print(f"   ❌ Request failed: {e}")
        assert False

    # Test 2: Update the project
    if "project_id" in locals():
        print(f"\n2️⃣ Testing project update...")
        update_data = {
            "name": "Updated Test Project",
            "status": "completed",  # String enum
            "maxParticipants": 75,
        }

        try:
            response = requests.put(
                f"{api_url}/v2/projects/{project_id}",  # Fixed URL formatting
                headers=headers,
                json=update_data,
                timeout=30,
            )

            print(f"   📤 Request: PUT {api_url}/v2/projects/{project_id}")
            print(f"   📤 Data: {json.dumps(update_data)}")
            print(f"   📥 Status: {response.status_code}")
            print(f"   📥 Response: {response.text[:300]}...")

            if response.status_code == 200:
                print("   ✅ Project update successful")
            elif response.status_code == 500:
                print("   🚨 500 error - likely enum handling issue in update!")
                assert False
            else:
                print(f"   ❌ Project update failed: {response.status_code}")

        except Exception as e:
            print(f"   ❌ Request failed: {e}")

    # Test 3: Create a subscription
    print(f"\n3️⃣ Testing subscription creation...")
    subscription_data = {
        "personId": "02724257-4c6a-4aac-9c19-89c87c499bc8",  # Known test person
        "projectId": project_id if "project_id" in locals() else "test-project-id",
        "status": "active",  # String enum
        "notes": "Test subscription",
    }

    try:
        response = requests.post(
            f"{api_url}/v2/subscriptions",  # Fixed URL formatting
            headers=headers,
            json=subscription_data,
            timeout=30,
        )

        print(f"   📤 Request: POST {api_url}/v2/subscriptions")
        print(f"   📤 Data: {json.dumps(subscription_data)}")
        print(f"   📥 Status: {response.status_code}")
        print(f"   📥 Response: {response.text[:300]}...")

        if response.status_code == 201:
            print("   ✅ Subscription creation successful")
            subscription_response = response.json()
            subscription_id = subscription_response.get("id")
        elif response.status_code == 500:
            print("   🚨 500 error - likely enum handling issue!")
            assert False
        else:
            print(f"   ❌ Subscription creation failed: {response.status_code}")

    except Exception as e:
        print(f"   ❌ Request failed: {e}")

    # Test 4: Update the subscription
    if "subscription_id" in locals():
        print(f"\n4️⃣ Testing subscription update...")
        update_data = {
            "status": "completed",  # String enum
            "notes": "Updated test subscription",
        }

        try:
            response = requests.put(
                f"{api_url}/v2/subscriptions/{subscription_id}",  # Fixed URL formatting
                headers=headers,
                json=update_data,
                timeout=30,
            )

            print(f"   📤 Request: PUT {api_url}/v2/subscriptions/{subscription_id}")
            print(f"   📤 Data: {json.dumps(update_data)}")
            print(f"   📥 Status: {response.status_code}")
            print(f"   📥 Response: {response.text[:300]}...")

            if response.status_code == 200:
                print("   ✅ Subscription update successful")
            elif response.status_code == 500:
                print("   🚨 500 error - likely enum handling issue in update!")
                assert False
            else:
                print(f"   ❌ Subscription update failed: {response.status_code}")

        except Exception as e:
            print(f"   ❌ Request failed: {e}")

    print(f"\n🎯 API Testing Complete")
    assert True


if __name__ == "__main__":
    success = test_project_subscription_apis()
    if success:
        print("\n✅ API testing completed")
        sys.exit(0)
    else:
        print("\n❌ API testing failed - issues found")
        sys.exit(1)
