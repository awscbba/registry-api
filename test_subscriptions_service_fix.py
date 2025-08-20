#!/usr/bin/env python3
"""
Test the subscriptions service with the fixed repository
"""

import sys
import os
import asyncio

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.services.subscriptions_service import SubscriptionsService


async def test_subscriptions_service():
    """Test that the subscriptions service works with the fixed repository"""
    print("🧪 Testing Subscriptions Service...")

    try:
        # Initialize service
        service = SubscriptionsService()
        print("✅ Service initialized successfully")

        # Test health check
        print("🏥 Testing health check...")
        health = await service.health_check()
        print(f"Health check result: {health}")

        if health.get("status") != "healthy":
            print("⚠️  Service health check shows degraded status")

        # Test get_all_subscriptions_v2 (the failing endpoint)
        print("📋 Testing get_all_subscriptions_v2...")
        result = await service.get_all_subscriptions_v2()

        if result.get("success"):
            data = result.get("data", [])
            print(f"✅ Successfully retrieved {len(data)} subscriptions")
            print(f"Response format: {list(result.keys())}")

            if data:
                print(
                    f"First subscription keys: {list(data[0].keys()) if isinstance(data[0], dict) else 'Not a dict'}"
                )
        else:
            print(f"❌ get_all_subscriptions_v2 failed: {result}")
            return False

        print("🎉 All tests passed! Service is working correctly.")
        return True

    except Exception as e:
        print(f"❌ Test failed with exception: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_subscriptions_service())
    sys.exit(0 if success else 1)
