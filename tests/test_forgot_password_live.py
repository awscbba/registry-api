"""
Live tests for Forgot Password functionality.

These tests can be run against the deployed API to verify
the forgot password feature works end-to-end.
"""

import pytest
import requests
import json
import time
from typing import Dict, Any


# Production dependency test - now enabled after deployment fixes
# TODO: Re-enable these tests after dependency fix deployment is complete
class TestForgotPasswordLive:
    """Live tests for forgot password API endpoints."""

    # API base URL - update this to match your deployment
    BASE_URL = "https://2t9blvt2c1.execute-api.us-east-1.amazonaws.com/prod"

    def test_forgot_password_endpoint_exists(self):
        """Test that the forgot password endpoint exists and responds."""
        url = f"{self.BASE_URL}/auth/forgot-password"

        response = requests.post(
            url,
            json={"email": "test@example.com"},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        # Should not return 404 (endpoint exists)
        assert response.status_code != 404, f"Endpoint not found: {url}"

        # Should return either 200 (success) or 422 (validation error)
        assert response.status_code in [
            200,
            422,
        ], f"Unexpected status: {response.status_code}"

        # Response should be JSON
        try:
            data = response.json()
            assert isinstance(data, dict), "Response should be JSON object"
        except json.JSONDecodeError:
            pytest.fail("Response is not valid JSON")

    def test_forgot_password_with_valid_email_format(self):
        """Test forgot password with valid email format."""
        url = f"{self.BASE_URL}/auth/forgot-password"

        response = requests.post(
            url,
            json={"email": "sergio.rodriguez@cbba.cloud.org.bo"},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        # Should return 200 (security: always return success for valid format)
        assert (
            response.status_code == 200
        ), f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()

        # Response should have expected structure
        assert "success" in data, "Response missing 'success' field"
        assert "message" in data, "Response missing 'message' field"
        assert isinstance(data["success"], bool), "'success' should be boolean"
        assert isinstance(data["message"], str), "'message' should be string"

        # If successful, message should indicate email was processed
        if data["success"]:
            assert (
                "email" in data["message"].lower() or "reset" in data["message"].lower()
            )

        print(f"✅ Forgot password response: {data}")

    def test_forgot_password_with_invalid_email_format(self):
        """Test forgot password with invalid email format."""
        url = f"{self.BASE_URL}/auth/forgot-password"

        response = requests.post(
            url,
            json={"email": "invalid-email-format"},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        # Should return validation error (422) or handle gracefully (200)
        assert response.status_code in [
            200,
            422,
        ], f"Unexpected status: {response.status_code}"

        if response.status_code == 422:
            data = response.json()
            assert "detail" in data, "Validation error should have 'detail' field"

        print(f"✅ Invalid email response: {response.status_code}")

    def test_forgot_password_missing_email_field(self):
        """Test forgot password without email field."""
        url = f"{self.BASE_URL}/auth/forgot-password"

        response = requests.post(
            url,
            json={},  # Missing email field
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        # Should return validation error
        assert (
            response.status_code == 422
        ), f"Expected 422 for missing email, got {response.status_code}"

        data = response.json()
        assert "detail" in data, "Validation error should have 'detail' field"

        print(f"✅ Missing email validation works")

    def test_forgot_password_response_time(self):
        """Test that forgot password responds within reasonable time."""
        url = f"{self.BASE_URL}/auth/forgot-password"

        start_time = time.time()

        response = requests.post(
            url,
            json={"email": "test@example.com"},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        end_time = time.time()
        response_time = end_time - start_time

        assert response.status_code in [
            200,
            422,
        ], f"Unexpected status: {response.status_code}"
        assert response_time < 10.0, f"Response too slow: {response_time:.2f}s"

        print(f"✅ Response time: {response_time:.2f}s")

    def test_reset_password_endpoint_exists(self):
        """Test that the reset password endpoint exists."""
        url = f"{self.BASE_URL}/auth/reset-password"

        response = requests.post(
            url,
            json={"reset_token": "dummy-token", "new_password": "NewPassword123!"},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        # Should not return 404 (endpoint exists)
        assert response.status_code != 404, f"Endpoint not found: {url}"

        # Should return 400 (invalid token) or 422 (validation error)
        assert response.status_code in [
            200,
            400,
            422,
        ], f"Unexpected status: {response.status_code}"

        print(f"✅ Reset password endpoint exists: {response.status_code}")

    def test_validate_reset_token_endpoint_exists(self):
        """Test that the validate reset token endpoint exists."""
        url = f"{self.BASE_URL}/auth/validate-reset-token/dummy-token"

        response = requests.get(url, timeout=30)

        # Should not return 404 (endpoint exists)
        assert response.status_code != 404, f"Endpoint not found: {url}"

        # Should return 200 with validation result
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()
        assert "valid" in data, "Response should have 'valid' field"
        assert isinstance(data["valid"], bool), "'valid' should be boolean"

        print(f"✅ Validate token endpoint works: {data}")

    def test_forgot_password_security_headers(self):
        """Test that forgot password endpoint handles security properly."""
        url = f"{self.BASE_URL}/auth/forgot-password"

        # Test with potential XSS payload
        response = requests.post(
            url,
            json={"email": "<script>alert('xss')</script>@example.com"},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        # Should handle gracefully
        assert response.status_code in [
            200,
            422,
        ], f"Unexpected status: {response.status_code}"

        # Response should not contain the script tag
        response_text = response.text.lower()
        assert "<script>" not in response_text, "Response contains potential XSS"

        print(f"✅ Security test passed")

    def test_forgot_password_rate_limiting_behavior(self):
        """Test forgot password rate limiting behavior."""
        url = f"{self.BASE_URL}/auth/forgot-password"

        # Make multiple requests quickly
        responses = []
        for i in range(3):
            response = requests.post(
                url,
                json={"email": f"test{i}@example.com"},
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            responses.append(response.status_code)
            time.sleep(0.1)  # Small delay between requests

        # All should succeed or be rate limited gracefully
        for status in responses:
            assert status in [200, 422, 429], f"Unexpected status: {status}"

        print(f"✅ Rate limiting test: {responses}")

    def test_forgot_password_with_real_email(self):
        """Test forgot password with the actual email from the system."""
        url = f"{self.BASE_URL}/auth/forgot-password"

        # Use the actual email that should exist in the system
        response = requests.post(
            url,
            json={"email": "sergio.rodriguez@cbba.cloud.org.bo"},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        print(f"🔍 Testing with real email: sergio.rodriguez@cbba.cloud.org.bo")
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Response: {response.text}")

        # Should return 200 (success or security response)
        assert (
            response.status_code == 200
        ), f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()

        # Should have proper structure
        assert "success" in data, "Response missing 'success' field"
        assert "message" in data, "Response missing 'message' field"

        # Print detailed results for debugging
        if data["success"]:
            print(f"✅ SUCCESS: {data['message']}")
        else:
            print(f"❌ FAILED: {data['message']}")
            # Print additional debug info if available
            for key, value in data.items():
                if key not in ["success", "message"]:
                    print(f"   {key}: {value}")

        return data  # Return for manual inspection


def run_live_tests():
    """Run all live tests and report results."""
    test_instance = TestForgotPasswordLive()

    tests = [
        ("Endpoint Exists", test_instance.test_forgot_password_endpoint_exists),
        (
            "Valid Email Format",
            test_instance.test_forgot_password_with_valid_email_format,
        ),
        (
            "Invalid Email Format",
            test_instance.test_forgot_password_with_invalid_email_format,
        ),
        ("Missing Email Field", test_instance.test_forgot_password_missing_email_field),
        ("Response Time", test_instance.test_forgot_password_response_time),
        ("Reset Password Endpoint", test_instance.test_reset_password_endpoint_exists),
        (
            "Validate Token Endpoint",
            test_instance.test_validate_reset_token_endpoint_exists,
        ),
        ("Security Headers", test_instance.test_forgot_password_security_headers),
        ("Rate Limiting", test_instance.test_forgot_password_rate_limiting_behavior),
        ("Real Email Test", test_instance.test_forgot_password_with_real_email),
    ]

    results = []

    print("🚀 Running Forgot Password Live Tests")
    print("=" * 50)

    for test_name, test_func in tests:
        try:
            print(f"\n🧪 Running: {test_name}")
            result = test_func()
            results.append((test_name, "PASS", None))
            print(f"✅ {test_name}: PASSED")
        except Exception as e:
            results.append((test_name, "FAIL", str(e)))
            print(f"❌ {test_name}: FAILED - {e}")

    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)

    passed = sum(1 for _, status, _ in results if status == "PASS")
    failed = sum(1 for _, status, _ in results if status == "FAIL")

    for test_name, status, error in results:
        status_icon = "✅" if status == "PASS" else "❌"
        print(f"{status_icon} {test_name}: {status}")
        if error:
            print(f"   Error: {error}")

    print(f"\n📈 Total: {len(results)} tests")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Success Rate: {(passed / len(results) * 100):.1f}%")

    return results


if __name__ == "__main__":
    # Run tests when script is executed directly
    run_live_tests()
