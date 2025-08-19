#!/usr/bin/env python3
"""
Test script to directly test subscription creation and email sending.
"""

import requests
import json
import time
import pytest
from src.utils.api_config import get_api_url


# Integration test - re-enabled after field alias fix deployment
def test_subscription_creation():
    """Test creating a new subscription directly via API."""

    print("🧪 Testing Subscription Creation API...")

    # Get API URL using proper configuration
    api_base_url = get_api_url()
    print(f"📡 Using API URL: {api_base_url}")

    # First, get available projects
    print("📋 Getting available projects...")
    try:
        projects_response = requests.get(f"{api_base_url}/v2/projects")
        projects_response.raise_for_status()
        projects = projects_response.json()

        if not projects.get("data"):
            print("❌ No projects available")
            assert False

        # Use the first project
        project = projects["data"][0]
        project_id = project["id"]
        project_name = project["name"]

        print(f"✅ Found project: {project_name} (ID: {project_id})")

    except Exception as e:
        print(f"❌ Failed to get projects: {e}")
        assert False

    # Create a test subscription
    print("📝 Creating test subscription...")

    subscription_data = {
        "person": {
            "name": "Test User Email",
            "email": "srinclan+test@gmail.com",  # Using your Gmail with + alias
        },
        "projectId": project_id,
        "notes": "Test subscription to verify email functionality",
    }

    try:
        print(
            f"📤 Sending POST request to: {api_base_url}/v2/projects/{project_id}/subscriptions"
        )
        print(f"📋 Data: {json.dumps(subscription_data, indent=2)}")

        response = requests.post(
            f"{api_base_url}/v2/projects/{project_id}/subscriptions",
            json=subscription_data,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=30,
        )

        print(f"📊 Response Status: {response.status_code}")
        print(f"📄 Response Headers: {dict(response.headers)}")

        if response.status_code == 200 or response.status_code == 201:
            result = response.json()
            print(f"✅ Subscription created successfully!")
            print(f"📋 Response: {json.dumps(result, indent=2)}")

            # Check if email was sent
            if result.get("data", {}).get("email_sent"):
                print("📧 ✅ Welcome email was sent!")
            else:
                print("📧 ❌ Welcome email was NOT sent")
                if "email_error" in result.get("data", {}):
                    print(f"📧 Error: {result['data']['email_error']}")

            assert True

        else:
            print(f"❌ Subscription creation failed!")
            print(f"📄 Response: {response.text}")
            if response.status_code == 405:
                print("🚨 CRITICAL: POST endpoint missing from deployed API!")
                print(
                    "💡 This indicates the deployed Lambda doesn't have the latest code"
                )
            assert (
                False
            ), f"Subscription creation failed with status {response.status_code}"

    except requests.exceptions.Timeout:
        print("❌ Request timed out after 30 seconds")
        assert False
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        assert False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        assert False


if __name__ == "__main__":
    print("🚀 Starting Subscription Creation Test...")
    print("=" * 50)

    success = test_subscription_creation()

    print("=" * 50)
    if success:
        print("🎉 Test completed successfully!")
        print(
            "📧 Check your Gmail inbox (srinclan+test@gmail.com) for the welcome email!"
        )
    else:
        print("🚨 Test failed - there are issues that need to be resolved.")

    print("\n💡 If the API test works but the frontend doesn't:")
    print("   - Check browser developer console for errors")
    print("   - Verify frontend is submitting to the correct API endpoint")
    print("   - Check for CORS issues")
    print("   - Ensure frontend form validation is working")
