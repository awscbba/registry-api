#!/usr/bin/env python3
"""
Test script to verify the duplicate subscription prevention fix
"""

import asyncio
from src.services.defensive_dynamodb_service import DefensiveDynamoDBService
from src.models.subscription import SubscriptionCreate


async def test_duplicate_subscription_prevention():
    """Test that duplicate subscriptions are prevented"""
    
    # Create service instance
    service = DefensiveDynamoDBService()
    
    # Test data
    person_id = "test-person-123"
    project_id = "test-project-456"
    
    print("🧪 Testing duplicate subscription prevention...\n")
    
    # Test 1: Create first subscription
    print("1️⃣ Creating first subscription...")
    subscription_data_1 = SubscriptionCreate(
        personId=person_id,
        projectId=project_id,
        status="pending",
        notes="First subscription"
    )
    
    try:
        result_1 = await service.create_subscription(subscription_data_1)
        print(f"✅ First subscription created: {result_1['id']}")
        print(f"   Status: {result_1['status']}")
        print(f"   Notes: {result_1['notes']}")
    except Exception as e:
        print(f"❌ Failed to create first subscription: {e}")
        return False
    
    # Test 2: Try to create duplicate subscription
    print("\n2️⃣ Attempting to create duplicate subscription...")
    subscription_data_2 = SubscriptionCreate(
        personId=person_id,
        projectId=project_id,
        status="pending",
        notes="Duplicate subscription attempt"
    )
    
    try:
        result_2 = await service.create_subscription(subscription_data_2)
        print(f"✅ Duplicate handled gracefully: {result_2['id']}")
        print(f"   Status: {result_2['status']}")
        print(f"   Same ID as first: {result_1['id'] == result_2['id']}")
        
        if result_1['id'] == result_2['id']:
            print("✅ Duplicate prevention working - returned existing subscription")
        else:
            print("❌ Duplicate prevention failed - created new subscription")
            return False
            
    except Exception as e:
        print(f"❌ Failed to handle duplicate subscription: {e}")
        return False
    
    # Test 3: Test reactivation of inactive subscription
    print("\n3️⃣ Testing reactivation of declined subscription...")
    
    # First, decline the subscription
    from src.models.subscription import SubscriptionUpdate
    decline_update = SubscriptionUpdate(status="inactive")
    
    try:
        await service.update_subscription(result_1['id'], decline_update)
        print("✅ Subscription declined (set to inactive)")
        
        # Now try to create a new subscription (should reactivate)
        subscription_data_3 = SubscriptionCreate(
            personId=person_id,
            projectId=project_id,
            status="pending",
            notes="Reactivation attempt"
        )
        
        result_3 = await service.create_subscription(subscription_data_3)
        print(f"✅ Reactivation handled: {result_3['id']}")
        print(f"   Status: {result_3['status']}")
        print(f"   Same ID: {result_1['id'] == result_3['id']}")
        
        if result_3['status'] == "pending":
            print("✅ Reactivation working - subscription is now pending")
        else:
            print(f"❌ Reactivation failed - status is {result_3['status']}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to test reactivation: {e}")
        return False
    
    print("\n🎉 All duplicate subscription prevention tests passed!")
    return True


async def test_existing_subscription_check():
    """Test the get_existing_subscription method"""
    
    service = DefensiveDynamoDBService()
    
    print("\n🧪 Testing existing subscription check...\n")
    
    person_id = "test-person-789"
    project_id = "test-project-101"
    
    # Test 1: Check for non-existent subscription
    print("1️⃣ Checking for non-existent subscription...")
    try:
        existing = await service.get_existing_subscription(person_id, project_id)
        if existing is None:
            print("✅ Correctly returned None for non-existent subscription")
        else:
            print(f"❌ Expected None, got: {existing}")
            return False
    except Exception as e:
        print(f"❌ Error checking non-existent subscription: {e}")
        return False
    
    # Test 2: Create subscription and check it exists
    print("\n2️⃣ Creating subscription and checking it exists...")
    subscription_data = SubscriptionCreate(
        personId=person_id,
        projectId=project_id,
        status="active",
        notes="Test subscription"
    )
    
    try:
        created = await service.create_subscription(subscription_data)
        print(f"✅ Subscription created: {created['id']}")
        
        # Now check if it exists
        existing = await service.get_existing_subscription(person_id, project_id)
        if existing and existing['id'] == created['id']:
            print("✅ Correctly found existing subscription")
        else:
            print(f"❌ Failed to find existing subscription. Got: {existing}")
            return False
            
    except Exception as e:
        print(f"❌ Error in subscription existence test: {e}")
        return False
    
    print("\n🎉 Existing subscription check tests passed!")
    return True


async def main():
    print("🔧 Testing duplicate subscription prevention fix...\n")
    
    success1 = await test_duplicate_subscription_prevention()
    success2 = await test_existing_subscription_check()
    
    if success1 and success2:
        print("\n🎉 All tests passed! The duplicate subscription fix is working.")
        print("\n📋 What this fix provides:")
        print("   ✅ Prevents duplicate subscriptions for same person+project")
        print("   ✅ Returns existing subscription instead of creating duplicate")
        print("   ✅ Reactivates declined subscriptions when user re-applies")
        print("   ✅ Maintains data integrity")
    else:
        print("\n💥 Some tests failed! The fix needs more work.")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
