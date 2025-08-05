#!/usr/bin/env python3
"""
Test script to verify the missing postal code fix
"""

import asyncio
from src.services.defensive_dynamodb_service import DefensiveDynamoDBService
from src.models.person import Person


async def test_missing_postal_code_fix():
    """Test that missing postal code is handled gracefully"""

    # Create service instance
    service = DefensiveDynamoDBService()

    # Test item with missing postal code (like the one causing errors in production)
    test_item = {
        "id": "test-123",
        "firstName": "Test",
        "lastName": "User",
        "email": "test@example.com",
        "phone": "+1234567890",
        "dateOfBirth": "1990-01-01",
        "address": {
            "country": "Bolivia",
            "state": "La Paz",
            "city": "La Paz",
            "street": "Av. 6 de Agosto #1234",
            # Note: NO postalCode field - this was causing the error
        },
        "isAdmin": False,
        "createdAt": "2025-08-05T20:00:00Z",
        "updatedAt": "2025-08-05T20:00:00Z",
    }

    try:
        # This should now work without errors
        person = service._safe_item_to_person(test_item)

        print("✅ SUCCESS: Person created successfully")
        print(f"   Name: {person.first_name} {person.last_name}")
        print(f"   Email: {person.email}")
        print(f"   Address: {person.address.street}, {person.address.city}")
        print(
            f"   Postal Code: '{person.address.postal_code}' (empty string as default)"
        )

        # Verify postal code is empty string (not None or missing)
        assert (
            person.address.postal_code == ""
        ), f"Expected empty string, got: {person.address.postal_code}"
        print("✅ Postal code default value is correct")

        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_missing_postal_code_fix())
    if success:
        print("\n🎉 All tests passed! The missing postal code fix is working.")
    else:
        print("\n💥 Test failed! The fix needs more work.")
        exit(1)
