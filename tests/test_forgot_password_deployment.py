#!/usr/bin/env python3
"""
Quick test script for Forgot Password functionality.

This script tests the deployed forgot password API to verify it works correctly.
Run this after deploying changes to verify the functionality.

Usage:
    python test_forgot_password_deployment.py
"""

import requests
import json
import time
import sys


def test_forgot_password_api():
    """Test the forgot password API endpoint."""

    BASE_URL = "https://2t9blvt2c1.execute-api.us-east-1.amazonaws.com/prod"

    print("🧪 Testing Forgot Password API")
    print("=" * 50)

    # Test 1: Basic endpoint test
    print("\n1️⃣ Testing endpoint availability...")
    try:
        url = f"{BASE_URL}/auth/forgot-password"
        response = requests.post(
            url,
            json={"email": "test@example.com"},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        if response.status_code == 404:
            print("❌ FAIL: Endpoint not found (404)")
            return False
        else:
            print(f"✅ PASS: Endpoint exists (status: {response.status_code})")

    except requests.exceptions.RequestException as e:
        print(f"❌ FAIL: Network error - {e}")
        return False

    # Test 2: Test with real email
    print("\n2️⃣ Testing with real email...")
    try:
        response = requests.post(
            url,
            json={"email": "sergio.rodriguez@cbba.cloud.org.bo"},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Response: {response.text}")

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print("✅ PASS: Forgot password request successful!")
                print(f"📧 Message: {data.get('message', 'No message')}")
                return True
            else:
                print("❌ FAIL: Request failed")
                print(f"💬 Error: {data.get('message', 'No error message')}")
                return False
        else:
            print(f"❌ FAIL: Unexpected status code {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ FAIL: Network error - {e}")
        return False
    except json.JSONDecodeError:
        print(f"❌ FAIL: Invalid JSON response")
        return False


def test_validation():
    """Test input validation."""

    BASE_URL = "https://2t9blvt2c1.execute-api.us-east-1.amazonaws.com/prod"
    url = f"{BASE_URL}/auth/forgot-password"

    print("\n3️⃣ Testing input validation...")

    # Test invalid email format
    try:
        response = requests.post(
            url,
            json={"email": "invalid-email"},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        if response.status_code == 422:
            print("✅ PASS: Invalid email format properly rejected")
        elif response.status_code == 200:
            print("⚠️  INFO: Invalid email handled gracefully (security)")
        else:
            print(f"❓ INFO: Unexpected validation response: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"❌ FAIL: Network error during validation test - {e}")

    # Test missing email field
    try:
        response = requests.post(
            url, json={}, headers={"Content-Type": "application/json"}, timeout=10
        )

        if response.status_code == 422:
            print("✅ PASS: Missing email field properly rejected")
        else:
            print(f"❓ INFO: Missing email response: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"❌ FAIL: Network error during missing field test - {e}")


def test_other_endpoints():
    """Test related endpoints."""

    BASE_URL = "https://2t9blvt2c1.execute-api.us-east-1.amazonaws.com/prod"

    print("\n4️⃣ Testing related endpoints...")

    # Test reset password endpoint
    try:
        url = f"{BASE_URL}/auth/reset-password"
        response = requests.post(
            url,
            json={"reset_token": "dummy", "new_password": "Test123!"},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        if response.status_code != 404:
            print("✅ PASS: Reset password endpoint exists")
        else:
            print("❌ FAIL: Reset password endpoint not found")

    except requests.exceptions.RequestException as e:
        print(f"❌ FAIL: Reset password endpoint error - {e}")

    # Test validate token endpoint
    try:
        url = f"{BASE_URL}/auth/validate-reset-token/dummy-token"
        response = requests.get(url, timeout=10)

        if response.status_code != 404:
            print("✅ PASS: Validate token endpoint exists")
        else:
            print("❌ FAIL: Validate token endpoint not found")

    except requests.exceptions.RequestException as e:
        print(f"❌ FAIL: Validate token endpoint error - {e}")


def main():
    """Run all tests."""

    print("🚀 Forgot Password API Test Suite")
    print("🎯 Testing deployed API functionality")
    print("🌐 API: https://2t9blvt2c1.execute-api.us-east-1.amazonaws.com/prod")

    start_time = time.time()

    # Run main test
    success = test_forgot_password_api()

    # Run additional tests
    test_validation()
    test_other_endpoints()

    end_time = time.time()
    duration = end_time - start_time

    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)

    if success:
        print("🎉 OVERALL RESULT: SUCCESS")
        print("✅ Forgot password functionality is working!")
        print("📧 Password reset emails should be sent for valid requests")
    else:
        print("💥 OVERALL RESULT: FAILURE")
        print("❌ Forgot password functionality needs attention")
        print("🔧 Check the deployment and logs for issues")

    print(f"⏱️  Total test time: {duration:.2f} seconds")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())