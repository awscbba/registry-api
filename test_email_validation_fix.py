#!/usr/bin/env python3
"""
Test script to verify the email validation fix
"""

import asyncio
from src.services.defensive_dynamodb_service import DefensiveDynamoDBService
from src.models.person import Person


async def test_email_validation_fix():
    """Test that invalid emails are handled gracefully"""
    
    # Create service instance
    service = DefensiveDynamoDBService()
    
    # Test item with invalid .local email (like the one causing errors in production)
    test_item = {
        "id": "test-123",
        "firstName": "Test",
        "lastName": "User", 
        "email": "noreply@people-register.local",  # This was causing the error
        "phone": "+1234567890",
        "dateOfBirth": "1990-01-01",
        "address": {
            "country": "Bolivia",
            "state": "La Paz", 
            "city": "La Paz",
            "street": "Av. 6 de Agosto #1234",
            "postalCode": "12345"
        },
        "isAdmin": False,
        "createdAt": "2025-08-05T20:00:00Z",
        "updatedAt": "2025-08-05T20:00:00Z"
    }
    
    try:
        # This should now work without errors
        person = service._safe_item_to_person(test_item)
        
        print("✅ SUCCESS: Person created successfully")
        print(f"   Name: {person.first_name} {person.last_name}")
        print(f"   Original Email: noreply@people-register.local")
        print(f"   Converted Email: {person.email}")
        print(f"   Address: {person.address.street}, {person.address.city}")
        print(f"   Postal Code: '{person.address.postal_code}'")
        
        # Verify email was converted properly
        assert person.email == "noreply@people-register.com", f"Expected converted email, got: {person.email}"
        print("✅ Email conversion is correct")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


async def test_other_email_cases():
    """Test other email edge cases"""
    
    service = DefensiveDynamoDBService()
    
    test_cases = [
        {
            "name": "Empty email",
            "email": "",
            "expected": "unknown@example.com"
        },
        {
            "name": "Missing @ symbol",
            "email": "invalid-email",
            "expected": "unknown@example.com"
        },
        {
            "name": "Valid email",
            "email": "user@example.com",
            "expected": "user@example.com"
        },
        {
            "name": "Another .local email",
            "email": "admin@test.local",
            "expected": "admin@test.com"
        }
    ]
    
    for case in test_cases:
        test_item = {
            "id": "test-123",
            "firstName": "Test",
            "lastName": "User", 
            "email": case["email"],
            "phone": "+1234567890",
            "dateOfBirth": "1990-01-01",
            "address": {
                "country": "Bolivia",
                "state": "La Paz", 
                "city": "La Paz",
                "street": "Av. 6 de Agosto #1234",
                "postalCode": "12345"
            },
            "isAdmin": False,
            "createdAt": "2025-08-05T20:00:00Z",
            "updatedAt": "2025-08-05T20:00:00Z"
        }
        
        try:
            person = service._safe_item_to_person(test_item)
            if person.email == case["expected"]:
                print(f"✅ {case['name']}: '{case['email']}' → '{person.email}'")
            else:
                print(f"❌ {case['name']}: Expected '{case['expected']}', got '{person.email}'")
                return False
        except Exception as e:
            print(f"❌ {case['name']}: Failed with error: {e}")
            return False
    
    return True


async def main():
    print("🧪 Testing email validation fix...\n")
    
    success1 = await test_email_validation_fix()
    print()
    
    print("🧪 Testing other email cases...\n")
    success2 = await test_other_email_cases()
    
    if success1 and success2:
        print("\n🎉 All tests passed! The email validation fix is working.")
        print("The subscribers endpoint should now work properly.")
    else:
        print("\n💥 Some tests failed! The fix needs more work.")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
