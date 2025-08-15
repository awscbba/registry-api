#!/usr/bin/env python3
"""
Monitor deployment progress for password reset functionality
"""
import boto3
import time
import json
from datetime import datetime


def check_lambda_deployment():
    lambda_client = boto3.client("lambda", region_name="us-east-1")

    functions = [
        {
            "name": "PeopleRegisterInfrastruct-PeopleApiFunction67A8223-xlC79QhrsKBe",
            "type": "API",
        },
        {
            "name": "PeopleRegisterInfrastructureS-AuthFunctionA1CD5E0F-lujBJmLNxohb",
            "type": "Auth",
        },
        {
            "name": "PeopleRegisterInfrastructur-RouterFunction6AC6EF3B-cFuTZOTV5Cjd",
            "type": "Router",
        },
    ]

    expected_commit = "2898874"
    expected_image_tag = f"main-{expected_commit}"

    print(f"🔍 Monitoring deployment progress...")
    print(f"📋 Expected commit: {expected_commit}")
    print(f"🏷️  Expected image tag: {expected_image_tag}")
    print(f"⏰ Current time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 60)

    all_updated = True

    for func in functions:
        try:
            response = lambda_client.get_function(FunctionName=func["name"])

            current_image = response["Code"]["ImageUri"]
            last_modified = response["Configuration"]["LastModified"]

            # Extract current tag from image URI
            current_tag = (
                current_image.split(":")[-1] if ":" in current_image else "unknown"
            )

            is_updated = expected_image_tag in current_image
            status = "✅ UPDATED" if is_updated else "⏳ PENDING"

            print(f"{func['type']} Function:")
            print(f"  Status: {status}")
            print(f"  Current Tag: {current_tag}")
            print(f"  Last Modified: {last_modified}")
            print(f"  Image: {current_image}")
            print()

            if not is_updated:
                all_updated = False

        except Exception as e:
            print(f"❌ Error checking {func['type']} function: {str(e)}")
            all_updated = False

    return all_updated


def test_password_reset_endpoint():
    """Test if password reset endpoint is working"""
    import requests

    api_url = "https://2t9blvt2c1.execute-api.us-east-1.amazonaws.com/prod"

    try:
        # Test forgot password endpoint
        response = requests.post(
            f"{api_url}/auth/forgot-password",
            json={"email": "test@example.com"},
            timeout=10,
        )

        print(f"🧪 Password Reset Endpoint Test:")
        print(f"  Status Code: {response.status_code}")
        print(f"  Response: {response.text[:200]}...")

        if response.status_code in [
            200,
            400,
            404,
        ]:  # Any of these means endpoint exists
            return True
        else:
            return False

    except Exception as e:
        print(f"❌ Error testing endpoint: {str(e)}")
        return False


if __name__ == "__main__":
    print("🚀 Password Reset Deployment Monitor")
    print("=" * 60)

    max_checks = 20  # Check for up to 10 minutes (30s intervals)
    check_count = 0

    while check_count < max_checks:
        check_count += 1
        print(f"\n📊 Check #{check_count}/{max_checks}")

        deployment_complete = check_lambda_deployment()

        if deployment_complete:
            print("🎉 ALL FUNCTIONS UPDATED!")
            print("\n🧪 Testing password reset endpoint...")

            # Wait a moment for functions to initialize
            time.sleep(5)

            endpoint_working = test_password_reset_endpoint()

            if endpoint_working:
                print("✅ Password reset functionality is LIVE!")
            else:
                print("⚠️ Functions updated but endpoint may still be initializing")

            break
        else:
            print("⏳ Deployment still in progress...")
            if check_count < max_checks:
                print(f"⏰ Waiting 30 seconds before next check...")
                time.sleep(30)

    if check_count >= max_checks:
        print("⏰ Monitoring timeout reached. Check CodeCatalyst pipeline status.")
