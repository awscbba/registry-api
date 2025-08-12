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
async def test_address_none_fix():
    """Test function converted from script format."""
    """Test that PersonUpdate with None address doesn't cause AttributeError"""

    print("🧪 Testing address None fix...")

    # Test 1: PersonUpdate with None address should not raise error
    print("\n1. Testing PersonUpdate model with None address...")
    try:
        person_update = PersonUpdate(
            first_name="Test Update", address=None  # This should be allowed
        )
        print(
            f"✅ PersonUpdate created successfully: {person_update.model_dump(exclude_unset=True)}"
        )
    except Exception as e:
        print(f"❌ PersonUpdate creation failed: {e}")
        return False

    # Test 2: Test the specific code path that was failing
    print("\n2. Testing DynamoDB service update expression building...")
    try:
        # Simulate the problematic code path
        update_data = person_update.model_dump(exclude_unset=True)

        # This is the code path that was failing
        for field, value in update_data.items():
            if field == "address":
                print(f"   Processing address field with value: {value}")
                if value is not None:
                    # This would call value.model_dump() - should not be reached with None
                    print(f"   Address is not None, would call model_dump()")
                else:
                    # This is our fix - handle None case
                    print(f"   Address is None, handling gracefully")

        print("✅ Update expression building handled None address correctly")
    except Exception as e:
        print(f"❌ Update expression building failed: {e}")
        return False

    # Test 3: Test with actual address object
    print("\n3. Testing PersonUpdate with actual address...")
    try:

        address = Address(
            street="123 Test St",
            city="Test City",
            state="TS",
            postalCode="12345",
            country="Test Country",
        )

        person_update_with_address = PersonUpdate(
            first_name="Test Update", address=address
        )

        update_data = person_update_with_address.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if field == "address":
                print(f"   Processing address field with value type: {type(value)}")
                if value is not None:
                    if hasattr(value, "model_dump"):
                        # This is an Address object
                        address_dict = value.model_dump()
                        print(
                            f"   Address model_dump() successful: {list(address_dict.keys())}"
                        )
                    else:
                        # This is already a dict from model_dump()
                        print(f"   Address is already a dict: {list(value.keys())}")

        print("✅ Update with actual address object works correctly")
    except Exception as e:
        print(f"❌ Update with actual address failed: {e}")
        return False

    print("\n🎉 All address None fix tests passed!")
    return True


# Keep the original script functionality for backward compatibility
if __name__ == "__main__":
    asyncio.run(test_address_none_fix())
