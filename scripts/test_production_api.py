#!/usr/bin/env python3
"""
Test the production API endpoint to debug the authentication issue.
"""

import requests
import json


def test_production_login():
    """Test the production login endpoint."""
    print("🔍 Testing Production API Endpoint")
    print("=" * 50)

    # Production endpoint
    url = "https://2t9blvt2c1.execute-api.us-east-1.amazonaws.com/prod/auth/login"

    # Test credentials (same as UI)
    payload = {
        "email": "sergio.rodriguez@cbba.cloud.org.bo",
        "password": "AdminCbba2025!",
    }

    headers = {"Content-Type": "application/json"}

    print(f"🌐 URL: {url}")
    print(f"📧 Email: {payload['email']}")
    print(f"🔑 Password: {'*' * len(payload['password'])}")
    print()

    try:
        print("🚀 Making request to production API...")
        response = requests.post(url, json=payload, headers=headers, timeout=30)

        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Response Headers: {dict(response.headers)}")
        print()

        # Parse response
        try:
            response_data = response.json()
            print("📄 Response Body:")
            print(json.dumps(response_data, indent=2))
        except Exception:
            print("📄 Raw Response:")
            print(response.text)

        print()

        if response.status_code == 200:
            print("✅ Production API working correctly!")
        else:
            print(f"❌ Production API returned error: {response.status_code}")

    except requests.exceptions.Timeout:
        print("❌ Request timed out")
    except requests.exceptions.ConnectionError:
        print("❌ Connection error")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    test_production_login()
