#!/usr/bin/env python3
"""
Diagnose the deployed API to understand login issues.
"""

import requests
import json
import boto3
from datetime import datetime


def diagnose_deployed_api():
    """Diagnose the deployed API."""

    print("🔍 Diagnosing Deployed API")
    print("=" * 50)

    # API endpoints
    base_url = "https://2t9blvt2c1.execute-api.us-east-1.amazonaws.com/prod"
    login_url = f"{base_url}/auth/login"
    health_url = f"{base_url}/health"

    print(f"1. Testing API health endpoint...")
    try:
        health_response = requests.get(health_url, timeout=10)
        print(f"   Health Status: {health_response.status_code}")
        if health_response.status_code == 200:
            health_data = health_response.json()
            print(f"   ✅ API is healthy!")
            print(f"   Version: {health_data.get('version', 'N/A')}")
            print(f"   Environment: {health_data.get('environment', 'N/A')}")
        else:
            print(f"   ❌ API health check failed: {health_response.text}")
    except Exception as e:
        print(f"   ❌ Health check error: {str(e)}")

    print(f"\n2. Testing login with different approaches...")

    # Test credentials
    admin_email = "admin@awsugcbba.org"
    admin_password = "awsugcbba2025"

    # Test 1: Standard login
    print(f"   Test 1: Standard login")
    try:
        response = requests.post(
            login_url,
            json={"email": admin_email, "password": admin_password},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        print(f"      Status: {response.status_code}")
        print(f"      Response: {response.text[:200]}...")

        if response.status_code != 200:
            # Try to get more details from the response
            try:
                error_data = response.json()
                print(f"      Error Details: {json.dumps(error_data, indent=2)}")
            except Exception:
                pass

    except Exception as e:
        print(f"      Error: {str(e)}")

    # Test 2: Check if user exists via a different endpoint
    print(f"\n   Test 2: Check API structure")
    try:
        # Try the test endpoint
        test_url = f"{base_url}/v2/admin/test"
        test_response = requests.get(test_url, timeout=10)
        print(f"      Admin test endpoint: {test_response.status_code}")

        # Try the me endpoint without auth (should fail but give us info)
        me_url = f"{base_url}/auth/me"
        me_response = requests.get(me_url, timeout=10)
        print(f"      Me endpoint (no auth): {me_response.status_code}")

    except Exception as e:
        print(f"      Error: {str(e)}")

    print(f"\n3. Checking DynamoDB directly...")
    check_dynamodb_user(admin_email)

    print(f"\n4. Recommendations:")
    print(f"   - The API is deployed but login is failing")
    print(f"   - This could be due to:")
    print(f"     • Password hashing mismatch between local and deployed versions")
    print(f"     • Deployment not yet complete")
    print(f"     • Environment variable differences")
    print(f"     • Lambda function not updated with latest code")
    print(f"\n   - Try waiting 5-10 minutes for deployment to complete")
    print(f"   - Check CodeCatalyst pipeline status")
    print(f"   - Verify Lambda function has been updated")


def check_dynamodb_user(email):
    """Check user in DynamoDB."""
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.Table("PeopleTable")

        response = table.query(
            IndexName="EmailIndex",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("email").eq(email),
        )

        if response["Items"]:
            user = response["Items"][0]
            print(f"   ✅ User found in DynamoDB:")
            print(f"      ID: {user.get('id', 'N/A')}")
            print(
                f"      Name: {user.get('firstName', 'N/A')} {user.get('lastName', 'N/A')}"
            )
            print(f"      Is Admin: {user.get('isAdmin', False)}")
            print(f"      Is Active: {user.get('is_active', True)}")
            print(
                f"      Has Password: {'password_hash' in user and user['password_hash'] is not None}"
            )
            print(f"      Updated At: {user.get('updatedAt', 'N/A')}")
        else:
            print(f"   ❌ User not found in DynamoDB")

    except Exception as e:
        print(f"   ❌ DynamoDB check error: {str(e)}")


if __name__ == "__main__":
    diagnose_deployed_api()
