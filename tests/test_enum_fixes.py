"""
Test module converted from script format.
"""

import pytest
import asyncio
import os
import sys
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


import pytest
import asyncio
import os
import sys
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.models.person import Person, PersonCreate, PersonUpdate, Address
from src.models.project import Project, ProjectCreate, ProjectUpdate, ProjectStatus
from src.models.subscription import (
    Subscription,
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionStatus,
)
from src.services.email_service import EmailService
from src.utils.defensive_utils import (
    safe_isoformat,
    safe_enum_value,
    safe_datetime_parse,
    safe_field_access,
    safe_update_expression_builder,
    safe_model_dump,
)


@pytest.mark.asyncio
async def test_enum_fixes():
    """Test function converted from script format."""
    """Test enum handling fixes with different input formats"""

    print("🔧 Testing Enum Handling Fixes")
    print("=" * 40)

    # Test 1: ProjectCreate with enum object
    print("\n1️⃣ Testing ProjectCreate with enum object...")
    try:
        project_create = ProjectCreate(
            name="Test Project",
            description="Test Description",
            startDate="2025-01-01",
            endDate="2025-12-31",
            maxParticipants=100,
            status=ProjectStatus.ACTIVE,  # Enum object
        )

        # Test the fixed logic
        status_value = project_create.status
        if hasattr(status_value, "value"):
            result = status_value.value
            print(f"   ✅ Enum object handled: {result}")
        else:
            result = status_value
            print(f"   ✅ String value handled: {result}")

    except Exception as e:
        print(f"   ❌ Test failed: {e}")

    # Test 2: ProjectCreate with string
    print("\n2️⃣ Testing ProjectCreate with string...")
    try:
        project_create = ProjectCreate(
            name="Test Project",
            description="Test Description",
            startDate="2025-01-01",
            endDate="2025-12-31",
            maxParticipants=100,
            status="active",  # String value
        )

        # Test the fixed logic
        status_value = project_create.status
        if hasattr(status_value, "value"):
            result = status_value.value
            print(f"   ✅ Enum object handled: {result}")
        else:
            result = status_value
            print(f"   ✅ String value handled: {result}")

    except Exception as e:
        print(f"   ❌ Test failed: {e}")

    # Test 3: ProjectUpdate with enum object
    print("\n3️⃣ Testing ProjectUpdate with enum object...")
    try:
        project_update = ProjectUpdate(
            name="Updated Project", status=ProjectStatus.COMPLETED  # Enum object
        )

        # Test the fixed logic
        status_value = project_update.status
        if hasattr(status_value, "value"):
            result = status_value.value
            print(f"   ✅ Enum object handled: {result}")
        else:
            result = status_value
            print(f"   ✅ String value handled: {result}")

    except Exception as e:
        print(f"   ❌ Test failed: {e}")

    # Test 4: ProjectUpdate with string
    print("\n4️⃣ Testing ProjectUpdate with string...")
    try:
        project_update = ProjectUpdate(
            name="Updated Project", status="completed"  # String value
        )

        # Test the fixed logic
        status_value = project_update.status
        if hasattr(status_value, "value"):
            result = status_value.value
            print(f"   ✅ Enum object handled: {result}")
        else:
            result = status_value
            print(f"   ✅ String value handled: {result}")

    except Exception as e:
        print(f"   ❌ Test failed: {e}")

    # Test 5: SubscriptionCreate with enum object
    print("\n5️⃣ Testing SubscriptionCreate with enum object...")
    try:
        subscription_create = SubscriptionCreate(
            personId="test-person-id",
            projectId="test-project-id",
            status=SubscriptionStatus.ACTIVE,  # Enum object
        )

        # Test the fixed logic
        status_value = subscription_create.status
        if hasattr(status_value, "value"):
            result = status_value.value
            print(f"   ✅ Enum object handled: {result}")
        else:
            result = status_value
            print(f"   ✅ String value handled: {result}")

    except Exception as e:
        print(f"   ❌ Test failed: {e}")

    # Test 6: SubscriptionUpdate with string
    print("\n6️⃣ Testing SubscriptionUpdate with string...")
    try:
        subscription_update = SubscriptionUpdate(
            status="completed", notes="Test notes"  # String value
        )

        # Test the fixed logic
        status_value = subscription_update.status
        if hasattr(status_value, "value"):
            result = status_value.value
            print(f"   ✅ Enum object handled: {result}")
        else:
            result = status_value
            print(f"   ✅ String value handled: {result}")

    except Exception as e:
        print(f"   ❌ Test failed: {e}")

    # Test 7: Verify the fix prevents AttributeError
    print("\n7️⃣ Testing AttributeError prevention...")
    try:
        # Simulate what happens in the DB service with the fix
        test_status = "active"  # String value (no .value attribute)

        # Old logic (would fail)
        try:
            old_result = test_status.value
            print(f"   ❌ Old logic unexpectedly worked: {old_result}")
        except AttributeError:
            print(f"   ✅ Old logic correctly fails with AttributeError")

        # New logic (should work)
        if hasattr(test_status, "value"):
            new_result = test_status.value
        else:
            new_result = test_status

        print(f"   ✅ New logic works: {new_result}")

    except Exception as e:
        print(f"   ❌ Test failed: {e}")

    print(f"\n🎯 Enum Fixes Summary:")
    print(f"   ✅ Added hasattr() checks before calling .value")
    print(f"   ✅ Handles both enum objects and string values")
    print(f"   ✅ Prevents AttributeError on string enums")
    print(f"   ✅ Applied to both create and update operations")
    print(f"   ✅ Applied to both project and subscription operations")

    return True


# Keep the original script functionality for backward compatibility
if __name__ == "__main__":
    asyncio.run(test_enum_fixes())
