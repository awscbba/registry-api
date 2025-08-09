#!/usr/bin/env python3
"""
Test script to verify X-Ray tracing configuration.
This script can be run locally to test X-Ray integration.
"""

import os
import sys
import json
from unittest.mock import Mock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_xray_config():
    """Test X-Ray configuration module"""
    print("Testing X-Ray configuration...")

    try:
        from src.utils.xray_config import (
            XRAY_ENABLED,
            configure_xray,
            create_subsegment,
            add_annotation,
            add_metadata,
        )

        print(f"✓ X-Ray imports successful")
        print(f"✓ X-Ray enabled: {XRAY_ENABLED}")

        # Test subsegment creation (will be no-op outside Lambda)
        with create_subsegment("test_subsegment") as subsegment:
            print("✓ Subsegment creation works (no-op outside Lambda)")

            # Test annotations and metadata (will be no-op outside Lambda)
            add_annotation("test_key", "test_value")
            add_metadata("test_namespace", "test_key", {"test": "data"})
            print("✓ Annotations and metadata work (no-op outside Lambda)")

        # Test that X-Ray is properly disabled outside Lambda
        if not XRAY_ENABLED:
            print("✓ X-Ray correctly disabled outside Lambda environment")

        return True

    except Exception as e:
        print(f"✗ X-Ray configuration error: {e}")
        return False


def test_lambda_handler():
    """Test the Lambda handler with X-Ray tracing"""
    print("\nTesting Lambda handler...")

    try:
        # Mock Lambda environment
        os.environ["AWS_LAMBDA_FUNCTION_NAME"] = "test-function"
        os.environ["_X_AMZN_TRACE_ID"] = "Root=1-test-trace"

        # Import the main handler
        from main import traced_lambda_handler

        # Create mock event and context
        mock_event = {
            "httpMethod": "GET",
            "path": "/api/v2/people",
            "headers": {},
            "body": None,
        }

        mock_context = Mock()
        mock_context.function_name = "test-function"
        mock_context.aws_request_id = "test-request-id"

        print("✓ Lambda handler imports successful")
        print("✓ Mock event and context created")

        # Note: We can't actually call the handler without a full FastAPI setup
        # but we can verify the imports work

        return True

    except Exception as e:
        print(f"✗ Lambda handler error: {e}")
        return False


def test_dynamodb_service():
    """Test DynamoDB service X-Ray integration"""
    print("\nTesting DynamoDB service...")

    try:
        from src.services.defensive_dynamodb_service import DefensiveDynamoDBService

        print("✓ DynamoDB service imports successful")

        # We can't test actual DynamoDB operations without AWS credentials
        # but we can verify the imports work

        return True

    except Exception as e:
        print(f"✗ DynamoDB service error: {e}")
        return False


def main():
    """Run all X-Ray tests"""
    print("🔍 X-Ray Tracing Configuration Test")
    print("=" * 50)

    tests = [test_xray_config, test_lambda_handler, test_dynamodb_service]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append(False)

    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"✓ Passed: {sum(results)}")
    print(f"✗ Failed: {len(results) - sum(results)}")

    if all(results):
        print("\n🎉 All X-Ray tests passed!")
        print("\nNext steps:")
        print("1. Deploy the infrastructure changes with CDK")
        print("2. Deploy the API code with X-Ray SDK")
        print("3. Test in AWS environment")
        print("4. Check X-Ray console for traces")
        return 0
    else:
        print("\n❌ Some X-Ray tests failed!")
        print("Please fix the issues before deploying.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
