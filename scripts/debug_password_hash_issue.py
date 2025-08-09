#!/usr/bin/env python3
"""
Debug script for password hash field mismatch issue.

This script helps debug the authentication issue where users with passwords
set cannot login due to field name mismatch between DynamoDB storage and
the authentication code.

Usage:
    python scripts/debug_password_hash_issue.py
"""

import sys
import os
import asyncio
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from models.person import Person
from services.defensive_dynamodb_service import DefensiveDynamoDBService


async def debug_password_hash_issue():
    """Debug the password hash field mismatch issue"""

    print("🔍 Debugging Password Hash Field Mismatch Issue")
    print("=" * 60)

    # Test Case 1: User with password (should work but currently fails)
    print("\n📋 Test Case 1: User with password set")
    print("-" * 40)

    dynamodb_item_with_password = {
        "id": "user-123",
        "firstName": "John",
        "lastName": "Doe",
        "email": "john.doe@example.com",
        "phone": "+1234567890",
        "isAdmin": False,
        "isActive": True,
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z",
        "passwordHash": "$2b$12$abcdefghijklmnopqrstuvwxyz123456789",  # camelCase as stored in DynamoDB
        "passwordSalt": "random-salt-123",
        "requirePasswordChange": False,
        "failedLoginAttempts": 0,
    }

    db_service = DefensiveDynamoDBService()
    person_with_password = db_service._safe_item_to_person(dynamodb_item_with_password)

    print(
        f"✓ Person created: {person_with_password.firstName} {person_with_password.lastName}"
    )
    print(f"✓ Email: {person_with_password.email}")
    print(
        f"✓ Has password_hash attribute: {hasattr(person_with_password, 'password_hash')}"
    )
    print(
        f"✓ Password hash value: {getattr(person_with_password, 'password_hash', 'NOT_FOUND')}"
    )
    print(
        f"✓ Password hash type: {type(getattr(person_with_password, 'password_hash', None))}"
    )

    # Simulate the authentication check
    auth_check_result = (
        hasattr(person_with_password, "password_hash")
        and person_with_password.password_hash
    )
    print(f"🔐 Authentication check result: {auth_check_result}")

    if auth_check_result:
        print("✅ SUCCESS: User with password would authenticate correctly")
    else:
        print("❌ FAILURE: User with password would be rejected (THIS IS THE BUG)")

    # Test Case 2: User without password (should fail authentication)
    print("\n📋 Test Case 2: User without password set")
    print("-" * 40)

    dynamodb_item_no_password = {
        "id": "user-456",
        "firstName": "Jane",
        "lastName": "Smith",
        "email": "jane.smith@example.com",
        "isAdmin": False,
        "isActive": True,
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z",
        # No passwordHash field
    }

    person_no_password = db_service._safe_item_to_person(dynamodb_item_no_password)

    print(
        f"✓ Person created: {person_no_password.firstName} {person_no_password.lastName}"
    )
    print(f"✓ Email: {person_no_password.email}")
    print(
        f"✓ Has password_hash attribute: {hasattr(person_no_password, 'password_hash')}"
    )
    print(
        f"✓ Password hash value: {getattr(person_no_password, 'password_hash', 'NOT_FOUND')}"
    )

    # Simulate the authentication check
    auth_check_result_no_pwd = (
        hasattr(person_no_password, "password_hash")
        and person_no_password.password_hash
    )
    print(f"🔐 Authentication check result: {auth_check_result_no_pwd}")

    if not auth_check_result_no_pwd:
        print("✅ SUCCESS: User without password correctly rejected")
    else:
        print("❌ FAILURE: User without password would be allowed (unexpected)")

    # Test Case 3: Examine the Person model structure
    print("\n📋 Test Case 3: Person model analysis")
    print("-" * 40)

    print("Person model attributes:")
    for attr in dir(person_with_password):
        if not attr.startswith("_"):
            value = getattr(person_with_password, attr, "N/A")
            if not callable(value):
                print(f"  {attr}: {value}")

    # Test Case 4: Check DynamoDB field mapping
    print("\n📋 Test Case 4: DynamoDB field mapping analysis")
    print("-" * 40)

    print("DynamoDB item fields (camelCase):")
    for key, value in dynamodb_item_with_password.items():
        if "password" in key.lower():
            print(f"  {key}: {value}")

    print("\nPerson model fields (snake_case):")
    password_fields = ["password_hash", "password_salt"]
    for field in password_fields:
        value = getattr(person_with_password, field, "NOT_FOUND")
        print(f"  {field}: {value}")

    # Summary
    print("\n📊 SUMMARY")
    print("=" * 60)

    if auth_check_result:
        print("✅ No bug detected - authentication working correctly")
    else:
        print("🐛 BUG CONFIRMED: Field mismatch preventing authentication")
        print("   - DynamoDB stores: 'passwordHash' (camelCase)")
        print("   - Code expects: 'password_hash' (snake_case)")
        print("   - Mapping in _safe_item_to_person needs verification")

    print("\n🔧 RECOMMENDED ACTIONS:")
    print("1. Verify field mapping in DefensiveDynamoDBService._safe_item_to_person")
    print("2. Ensure 'passwordHash' -> 'password_hash' conversion is working")
    print("3. Add X-Ray tracing to authentication flow for production debugging")
    print("4. Add comprehensive tests for field mapping")


def analyze_authentication_code():
    """Analyze the authentication code paths"""

    print("\n🔍 Authentication Code Analysis")
    print("=" * 60)

    print("Authentication check locations:")
    print("1. src/services/auth_service.py:93")
    print('   if not hasattr(person, "password_hash") or not person.password_hash:')
    print()
    print("2. src/handlers/versioned_api_handler.py:609")
    print('   if not hasattr(person, "password_hash") or not person.password_hash:')
    print()
    print("Field mapping location:")
    print("3. src/services/defensive_dynamodb_service.py:254")
    print('   "password_hash": item.get("passwordHash"),')
    print()
    print(
        "This mapping should convert DynamoDB 'passwordHash' to Person 'password_hash'"
    )


if __name__ == "__main__":
    print("🚀 Starting Password Hash Debug Script")

    try:
        asyncio.run(debug_password_hash_issue())
        analyze_authentication_code()

        print("\n✅ Debug script completed successfully")
        print("Check the output above for bug analysis and recommendations")

    except Exception as e:
        print(f"\n❌ Debug script failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
