#!/usr/bin/env python3
"""
Test the subscription repository fix with actual DynamoDB data
"""

import sys
import os
import asyncio

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.repositories.subscription_repository import SubscriptionRepository


async def test_subscription_repository():
    """Test that the subscription repository can read actual DynamoDB data"""
    print("🧪 Testing Subscription Repository with actual DynamoDB data...")

    try:
        # Initialize repository
        repo = SubscriptionRepository()
        print("✅ Repository initialized successfully")

        # Test list_all method
        print("📋 Testing list_all method...")
        result = await repo.list_all()

        if result.success:
            subscriptions = result.data
            print(f"✅ Successfully retrieved {len(subscriptions)} subscriptions")

            if subscriptions:
                # Check the first subscription
                first_sub = subscriptions[0]
                print(f"📄 First subscription: {first_sub}")

                # Verify required fields are present
                required_fields = ["id", "person_id", "project_id", "status"]
                missing_fields = [
                    field
                    for field in required_fields
                    if not hasattr(first_sub, field)
                    or getattr(first_sub, field) is None
                ]

                if missing_fields:
                    print(f"❌ Missing required fields: {missing_fields}")
                    return False
                else:
                    print("✅ All required fields present")

                # Test get_by_id with the first subscription
                print(f"🔍 Testing get_by_id with ID: {first_sub.id}")
                get_result = await repo.get_by_id(first_sub.id)

                if get_result.success and get_result.data:
                    print("✅ get_by_id works correctly")
                else:
                    print(f"❌ get_by_id failed: {get_result.error}")
                    return False

            else:
                print("⚠️  No subscriptions found in database")

        else:
            print(f"❌ Failed to retrieve subscriptions: {result.error}")
            return False

        print("🎉 All tests passed! Repository is working correctly.")
        return True

    except Exception as e:
        print(f"❌ Test failed with exception: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_subscription_repository())
    sys.exit(0 if success else 1)
