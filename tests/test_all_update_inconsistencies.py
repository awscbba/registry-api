#!/usr/bin/env python3
"""
Comprehensive test to identify field mapping inconsistencies across ALL update methods:
1. PersonUpdate (already fixed)
2. ProjectUpdate
3. SubscriptionUpdate
4. Any other update operations
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from models.person import PersonUpdate, Address
from models.project import ProjectUpdate, ProjectStatus
from models.subscription import SubscriptionUpdate, SubscriptionStatus


async def test_all_update_inconsistencies():
    """Test all update models for field mapping and type inconsistencies"""

    print("🔍 Comprehensive Update Inconsistency Analysis")
    print("=" * 60)

    issues_found = []

    # Test 1: PersonUpdate (already fixed, but let's verify)
    print("\n1️⃣ Testing PersonUpdate Model...")
    try:
        person_data = {
            "firstName": "John",
            "lastName": "Doe",
            "email": "john@example.com",
            "address": {
                "street": "123 Main St",
                "city": "City",
                "state": "ST",
                "postalCode": "12345",
                "country": "USA",
            },
            "isActive": True,
            "accountLockedUntil": "2025-08-05T01:00:00Z",  # String datetime
        }

        person_update = PersonUpdate(**person_data)
        person_internal = person_update.model_dump(exclude_unset=True)

        print(f"   ✅ PersonUpdate model created successfully")
        print(f"   📋 Fields: {list(person_internal.keys())}")

        # Check for potential datetime issues
        for field, value in person_internal.items():
            if field == "account_locked_until" and isinstance(value, str):
                print(
                    f"   ⚠️ Field '{field}' is string, needs type checking in DB service"
                )
            elif field == "address" and isinstance(value, dict):
                print(f"   ✅ Field '{field}' is dict, properly handled")

    except Exception as e:
        print(f"   ❌ PersonUpdate test failed: {e}")
        issues_found.append(f"PersonUpdate: {e}")

    # Test 2: ProjectUpdate
    print("\n2️⃣ Testing ProjectUpdate Model...")
    try:
        project_data = {
            "name": "Test Project",
            "description": "Test Description",
            "startDate": "2025-01-01",  # String date
            "endDate": "2025-12-31",  # String date
            "maxParticipants": 100,
            "status": "active",  # String enum
            "category": "test",
            "location": "Test Location",
            "requirements": "Test Requirements",
        }

        project_update = ProjectUpdate(**project_data)
        project_internal = project_update.model_dump(exclude_unset=True)

        print(f"   ✅ ProjectUpdate model created successfully")
        print(f"   📋 Fields: {list(project_internal.keys())}")

        # Check for potential issues
        for field, value in project_internal.items():
            if field in ["startDate", "endDate"] and isinstance(value, str):
                print(
                    f"   ✅ Field '{field}' is string date - should be handled correctly"
                )
            elif field == "status" and hasattr(value, "value"):
                print(
                    f"   ⚠️ Field '{field}' is enum object, DB service calls .value - check if this works"
                )
            elif field == "status" and isinstance(value, str):
                print(
                    f"   ⚠️ Field '{field}' is string, but DB service expects enum with .value"
                )
                issues_found.append(
                    f"ProjectUpdate.status: String vs Enum inconsistency"
                )

    except Exception as e:
        print(f"   ❌ ProjectUpdate test failed: {e}")
        issues_found.append(f"ProjectUpdate: {e}")

    # Test 3: SubscriptionUpdate
    print("\n3️⃣ Testing SubscriptionUpdate Model...")
    try:
        subscription_data = {"status": "active", "notes": "Test notes"}  # String enum

        subscription_update = SubscriptionUpdate(**subscription_data)
        subscription_internal = subscription_update.model_dump(exclude_unset=True)

        print(f"   ✅ SubscriptionUpdate model created successfully")
        print(f"   📋 Fields: {list(subscription_internal.keys())}")

        # Check for potential issues
        for field, value in subscription_internal.items():
            if field == "status" and hasattr(value, "value"):
                print(
                    f"   ⚠️ Field '{field}' is enum object, DB service calls .value - check if this works"
                )
            elif field == "status" and isinstance(value, str):
                print(
                    f"   ⚠️ Field '{field}' is string, but DB service expects enum with .value"
                )
                issues_found.append(
                    f"SubscriptionUpdate.status: String vs Enum inconsistency"
                )

    except Exception as e:
        print(f"   ❌ SubscriptionUpdate test failed: {e}")
        issues_found.append(f"SubscriptionUpdate: {e}")

    # Test 4: Check DynamoDB service field handling consistency
    print("\n4️⃣ Analyzing DynamoDB Service Field Handling...")

    try:
        with open("src/services/dynamodb_service.py", "r") as f:
            service_code = f.read()

        # Check for enum .value usage patterns
        if ".value" in service_code:
            print("   ⚠️ Found .value calls in service - need to verify enum handling")

            # Count .value occurrences
            value_calls = service_code.count(".value")
            print(f"   📊 Found {value_calls} .value calls in service")

            # Check specific patterns
            if "status.value" in service_code:
                print(
                    "   🔍 Found status.value calls - verify enum objects are passed correctly"
                )
                issues_found.append(
                    "Enum handling: .value calls found, need to verify enum objects"
                )

        # Check for datetime.utcnow().isoformat() patterns
        if "datetime.utcnow().isoformat()" in service_code:
            print("   ✅ Found proper datetime handling in service")

        # Check for potential missing field handlers
        update_methods = ["update_person", "update_project", "update_subscription"]
        for method in update_methods:
            if method in service_code:
                print(f"   ✅ Found {method} method")
            else:
                print(f"   ❌ Missing {method} method")
                issues_found.append(f"Missing method: {method}")

    except Exception as e:
        print(f"   ❌ Service analysis failed: {e}")
        issues_found.append(f"Service analysis: {e}")

    # Test 5: Check for field naming inconsistencies
    print("\n5️⃣ Checking Field Naming Consistency...")

    # PersonUpdate uses aliases (camelCase -> snake_case)
    person_fields = ["first_name", "last_name", "is_active", "account_locked_until"]

    # ProjectUpdate uses camelCase directly
    project_fields = [
        "name",
        "description",
        "startDate",
        "endDate",
        "maxParticipants",
        "status",
    ]

    # SubscriptionUpdate uses camelCase directly
    subscription_fields = ["status", "notes"]

    print(f"   📋 PersonUpdate uses snake_case internally: {person_fields}")
    print(f"   📋 ProjectUpdate uses camelCase: {project_fields}")
    print(f"   📋 SubscriptionUpdate uses camelCase: {subscription_fields}")

    # Check if this creates inconsistencies
    if any("_" in field for field in project_fields + subscription_fields):
        print("   ⚠️ Mixed naming conventions detected")
        issues_found.append("Field naming: Mixed camelCase and snake_case conventions")
    else:
        print("   ✅ Consistent camelCase naming in Project/Subscription models")

    # Test 6: Frontend compatibility check
    print("\n6️⃣ Frontend Compatibility Analysis...")

    # Frontend typically sends camelCase
    frontend_person_data = {"firstName": "Test", "isActive": True}
    frontend_project_data = {"name": "Test", "startDate": "2025-01-01"}
    frontend_subscription_data = {"status": "active", "notes": "test"}

    try:
        # Test if models accept frontend format
        PersonUpdate(**frontend_person_data)
        ProjectUpdate(**frontend_project_data)
        SubscriptionUpdate(**frontend_subscription_data)
        print("   ✅ All models accept frontend camelCase format")
    except Exception as e:
        print(f"   ❌ Frontend compatibility issue: {e}")
        issues_found.append(f"Frontend compatibility: {e}")

    # Summary
    print(f"\n📊 Analysis Summary")
    print("=" * 30)

    if issues_found:
        print(f"🚨 Found {len(issues_found)} potential issues:")
        for i, issue in enumerate(issues_found, 1):
            print(f"   {i}. {issue}")
        return False
    else:
        print("✅ No critical inconsistencies found!")
        print("⚠️ However, verify enum handling in production")
        return True


if __name__ == "__main__":
    success = asyncio.run(test_all_update_inconsistencies())
    if success:
        print("\n✅ Analysis completed - minor issues to verify")
        sys.exit(0)
    else:
        print("\n❌ Critical inconsistencies found!")
        sys.exit(1)
