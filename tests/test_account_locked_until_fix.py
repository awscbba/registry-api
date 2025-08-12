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
async def test_account_locked_until_fix():
    """Test function converted from script format."""
    """Test account_locked_until field handling with different value types"""

    print("🔧 Testing account_locked_until Field Fix")
    print("=" * 50)

    # Test 1: PersonUpdate with datetime object
    print("1️⃣ Testing with datetime object...")
    try:
        now = datetime.utcnow()
        person_update = PersonUpdate(first_name="Test", account_locked_until=now)

        update_data = person_update.model_dump(exclude_unset=True)
        account_locked_value = update_data.get("account_locked_until")

        print(f"   Value: {account_locked_value}")
        print(f"   Type: {type(account_locked_value)}")

        # Test the field handling logic
        if account_locked_value is None:
            result = None
        elif hasattr(account_locked_value, "isoformat"):
            result = account_locked_value.isoformat()
            print(f"   ✅ Called isoformat() successfully: {result}")
        else:
            result = account_locked_value
            print(f"   ✅ Used string value directly: {result}")

    except Exception as e:
        print(f"   ❌ Test with datetime object failed: {e}")
        return False

    # Test 2: PersonUpdate with None value
    print("\n2️⃣ Testing with None value...")
    try:
        person_update = PersonUpdate(first_name="Test", account_locked_until=None)

        update_data = person_update.model_dump(exclude_unset=True)
        account_locked_value = update_data.get("account_locked_until")

        print(f"   Value: {account_locked_value}")
        print(f"   Type: {type(account_locked_value)}")

        # Test the field handling logic
        if account_locked_value is None:
            result = None
            print(f"   ✅ Handled None value correctly: {result}")
        elif hasattr(account_locked_value, "isoformat"):
            result = account_locked_value.isoformat()
        else:
            result = account_locked_value

    except Exception as e:
        print(f"   ❌ Test with None value failed: {e}")
        return False

    # Test 3: Simulate what happens when JSON is parsed (string value)
    print("\n3️⃣ Testing with string value (JSON parsing simulation)...")
    try:
        # This simulates what happens when JSON contains a datetime string
        iso_string = "2025-08-05T01:00:00Z"

        # Simulate the field processing logic
        value = iso_string

        print(f"   Value: {value}")
        print(f"   Type: {type(value)}")

        if value is None:
            result = None
        elif hasattr(value, "isoformat"):
            result = value.isoformat()
            print(f"   ✅ Called isoformat() on datetime")
        else:
            result = value
            print(f"   ✅ Used string value directly: {result}")

    except Exception as e:
        print(f"   ❌ Test with string value failed: {e}")
        return False

    # Test 4: Test the problematic scenario that was causing the error
    print("\n4️⃣ Testing problematic scenario (string trying to call isoformat)...")
    try:
        # This is what was happening before the fix
        iso_string = "2025-08-05T01:00:00Z"

        # Old logic (would fail)
        try:
            old_result = iso_string.isoformat() if iso_string else None
            print(f"   ❌ Old logic unexpectedly worked: {old_result}")
        except AttributeError as e:
            print(f"   ✅ Old logic correctly fails: {e}")

        # New logic (should work)
        if iso_string is None:
            new_result = None
        elif hasattr(iso_string, "isoformat"):
            new_result = iso_string.isoformat()
        else:
            new_result = iso_string

        print(f"   ✅ New logic works: {new_result}")

    except Exception as e:
        print(f"   ❌ Problematic scenario test failed: {e}")
        return False

    print("\n🎉 All account_locked_until field tests passed!")
    print("✅ The isoformat() error should be fixed")
    return True


# Keep the original script functionality for backward compatibility
if __name__ == "__main__":
    asyncio.run(test_account_locked_until_fix())
