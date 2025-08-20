#!/usr/bin/env python3
"""
Test script to verify subscription repository field mapping fix
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from repositories.subscription_repository import SubscriptionRepository


def test_subscription_field_mapping():
    """Test that subscription repository can handle DynamoDB field mapping"""

    # Create repository instance
    repo = SubscriptionRepository()

    # Test data that matches what we see in the logs
    test_item = {
        "projectId": "cc195c15-8c51-4892-8ddb-a44b520934a3",
        "subscribedAt": "2025-07-01T02:45:09.280716",
        "notes": "Asignado desde edición de persona",
        "status": "active",
        "id": "6fe874f5-5d3a-4333-a758-e45c760e2c7e",
        "personId": "2cefa393-c180-4663-aca8-a247aaecc03d",
        "subscribedBy": "admin",
    }

    try:
        # Test conversion from DynamoDB item to entity
        subscription = repo._to_entity(test_item)

        print("✅ Successfully converted DynamoDB item to Subscription entity")
        print(f"   ID: {subscription.id}")
        print(f"   Person ID: {subscription.person_id}")
        print(f"   Project ID: {subscription.project_id}")
        print(f"   Person Name: {subscription.person_name}")
        print(f"   Person Email: {subscription.person_email}")
        print(f"   Status: {subscription.status}")
        print(f"   Notes: {subscription.notes}")
        print(f"   Created At: {subscription.created_at}")

        # Test conversion back to DynamoDB item
        item = repo._to_item(subscription)
        print("\n✅ Successfully converted Subscription entity back to DynamoDB item")
        print(f"   Item keys: {list(item.keys())}")

        return True

    except Exception as e:
        print(f"❌ Failed to convert DynamoDB item: {str(e)}")
        return False


if __name__ == "__main__":
    print("🧪 Testing Subscription Repository Field Mapping Fix")
    print("=" * 60)

    success = test_subscription_field_mapping()

    if success:
        print("\n🎉 All tests passed! The subscription repository fix should work.")
    else:
        print(
            "\n💥 Tests failed! There are still issues with the subscription repository."
        )
        sys.exit(1)
