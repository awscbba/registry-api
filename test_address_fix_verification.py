#!/usr/bin/env python3
"""
Quick test to verify the address field fix works for the admin user
"""

import sys
import os
import asyncio

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.services.defensive_dynamodb_service import DefensiveDynamoDBService


async def test_admin_user_retrieval():
    """Test that we can now retrieve the admin user without address field errors"""
    
    print("🔍 Testing admin user retrieval after address fix...")
    
    try:
        # Initialize the defensive DynamoDB service
        db_service = DefensiveDynamoDBService()
        print("✅ DynamoDB service initialized")
        
        # Try to get the admin user by email
        admin_email = "admin@awsugcbba.org"
        print(f"📋 Attempting to retrieve admin user: {admin_email}")
        
        admin_user = await db_service.get_person_by_email(admin_email)
        
        if admin_user:
            print("✅ Admin user retrieved successfully!")
            print(f"   Name: {admin_user.first_name} {admin_user.last_name}")
            print(f"   Email: {admin_user.email}")
            print(f"   Is Admin: {admin_user.is_admin}")
            print(f"   Address: {admin_user.address}")
            print(f"   Postal Code: {admin_user.address.postal_code}")
            return True
        else:
            print("❌ Admin user not found")
            return False
            
    except Exception as e:
        print(f"❌ Error retrieving admin user: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False


async def test_person_update():
    """Test that person update now works"""
    
    print("\n🔄 Testing person update functionality...")
    
    try:
        from src.models.person import PersonUpdate
        
        # Initialize the defensive DynamoDB service
        db_service = DefensiveDynamoDBService()
        
        # Get the admin user ID
        admin_user = await db_service.get_person_by_email("admin@awsugcbba.org")
        if not admin_user:
            print("❌ Cannot test update - admin user not found")
            return False
            
        admin_id = admin_user.id
        print(f"📋 Testing update for admin user ID: {admin_id}")
        
        # Create a simple update (just update phone)
        update_data = PersonUpdate(phone="+591 12345678")
        
        # Attempt the update
        updated_person = await db_service.update_person(admin_id, update_data)
        
        if updated_person:
            print("✅ Person update successful!")
            print(f"   Updated phone: {updated_person.phone}")
            return True
        else:
            print("❌ Person update failed - no person returned")
            return False
            
    except Exception as e:
        print(f"❌ Error during person update: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False


async def main():
    """Run all tests"""
    print("🧪 Address Field Fix Verification Test")
    print("=" * 50)
    
    # Test 1: Admin user retrieval
    retrieval_success = await test_admin_user_retrieval()
    
    # Test 2: Person update (only if retrieval works)
    update_success = False
    if retrieval_success:
        update_success = await test_person_update()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"   Admin User Retrieval: {'✅ PASS' if retrieval_success else '❌ FAIL'}")
    print(f"   Person Update: {'✅ PASS' if update_success else '❌ FAIL'}")
    
    if retrieval_success and update_success:
        print("\n🎉 All tests passed! The address field fix is working correctly.")
        return True
    else:
        print("\n⚠️  Some tests failed. The fix may need additional work.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
