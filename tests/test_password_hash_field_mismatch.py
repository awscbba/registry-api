#!/usr/bin/env python3
"""
Test to reproduce and verify the password hash field mismatch bug.

This test demonstrates the issue where:
1. DynamoDB stores password hash as "passwordHash" (camelCase)
2. Person model expects "password_hash" (snake_case)
3. Authentication code fails to find the password hash
"""

import pytest
from datetime import datetime
from src.models.person import Person
from src.services.defensive_dynamodb_service import DefensiveDynamoDBService


class TestPasswordHashFieldMismatch:
    """Test class for password hash field mismatch debugging"""

    def test_password_hash_field_mismatch_with_complete_data(self):
        """Test that demonstrates the password hash field mismatch issue with complete data"""

        # Simulate COMPLETE DynamoDB item with passwordHash (camelCase) - as stored in DB
        dynamodb_item = {
            "id": "test-user-123",
            "firstName": "Test",
            "lastName": "User",
            "email": "test@example.com",
            "phone": "+1234567890",
            "dateOfBirth": "1990-01-01",
            "address": {
                "street": "123 Test St",
                "city": "Test City",
                "state": "TS",
                "postalCode": "12345",
                "country": "Test Country",
            },
            "isAdmin": False,
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z",
            "passwordHash": "$2b$12$abcdefghijklmnopqrstuvwxyz123456789",  # This is camelCase
            "passwordSalt": "test-salt",
            "isActive": True,
            "requirePasswordChange": False,
            "failedLoginAttempts": 0,
        }

        # Create DynamoDB service instance
        db_service = DefensiveDynamoDBService()

        # Convert DynamoDB item to Person model
        person = db_service._safe_item_to_person(dynamodb_item)

        # Test 1: Verify person object is created successfully
        assert person is not None
        assert person.id == "test-user-123"
        assert person.email == "test@example.com"

        # Test 2: Check if password_hash is properly set (this should pass after fix)
        print(f"Person password_hash: {person.password_hash}")
        print(f"Has password_hash attribute: {hasattr(person, 'password_hash')}")
        print(f"Password hash value: {getattr(person, 'password_hash', 'NOT_FOUND')}")

        # Test 3: Simulate the authentication check that's currently failing
        has_password = hasattr(person, "password_hash") and person.password_hash
        print(f"Authentication check result: {has_password}")

        # This assertion should pass after the fix
        assert has_password, "Person should have a password hash for authentication"
        assert person.password_hash == "$2b$12$abcdefghijklmnopqrstuvwxyz123456789"

    def test_real_world_authentication_scenario(self):
        """Test a real-world authentication scenario to identify the actual issue"""

        # Simulate a user that exists in production with a password
        production_like_item = {
            "id": "prod-user-123",
            "firstName": "Production",
            "lastName": "User",
            "email": "prod.user@example.com",
            "phone": "+1555123456",
            "dateOfBirth": "1985-12-25",
            "address": {
                "street": "123 Production Blvd",
                "city": "Production City",
                "state": "PC",
                "postalCode": "12345",
                "country": "Production Country",
            },
            "isAdmin": False,
            "isActive": True,
            "createdAt": "2024-01-01T10:00:00Z",
            "updatedAt": "2024-08-09T15:30:00Z",
            "passwordHash": "$2b$12$LKjhgfdsa.qwertyuiop1234567890abcdef",
            "passwordSalt": "prod-salt-xyz789",
            "requirePasswordChange": False,
            "failedLoginAttempts": 0,
            "emailVerified": True,
        }

        db_service = DefensiveDynamoDBService()
        person = db_service._safe_item_to_person(production_like_item)

        print(f"\n🔍 Production-like user analysis:")
        print(f"  User ID: {person.id}")
        print(f"  Email: {person.email}")
        print(f"  Has password_hash: {hasattr(person, 'password_hash')}")
        print(f"  Password hash value: {person.password_hash}")
        print(f"  Password hash type: {type(person.password_hash)}")
        print(f"  Is active: {person.is_active}")

        # Simulate the exact authentication checks from the code
        auth_service_check = hasattr(person, "password_hash") and person.password_hash
        user_login_check = hasattr(person, "password_hash") and person.password_hash

        print(f"  Auth service check: {auth_service_check}")
        print(f"  User login check: {user_login_check}")

        # Both should pass for a user with a password
        assert (
            auth_service_check
        ), "Auth service check should pass for user with password"
        assert user_login_check, "User login check should pass for user with password"

        print("✅ All authentication checks passed for production-like user")
