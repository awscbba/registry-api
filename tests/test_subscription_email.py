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
async def test_subscription_workflow():
    """Test function converted from script format."""
    """Test the complete subscription email workflow."""

    print("🧪 Testing Subscription Email Workflow...")
    print(f"📧 Using SES From Email: {os.environ['SES_FROM_EMAIL']}")

    # Initialize email service
    email_service = EmailService()

    # Test data for a new user subscription
    test_data = {
        "email": "srinclan@gmail.com",  # Your real Gmail address
        "first_name": "Sergio",
        "last_name": "Rodriguez",
        "project_name": "AWS Workshop 2025",
    }

    # Generate temporary password
    temp_password = email_service.generate_temporary_password()
    print(f"🔑 Generated temporary password: {temp_password}")

    try:
        print(f"📤 Sending welcome email to: {test_data['email']}")

        # Send welcome email (this is what should happen during subscription)
        response = await email_service.send_welcome_email(
            email=test_data["email"],
            first_name=test_data["first_name"],
            last_name=test_data["last_name"],
            project_name=test_data["project_name"],
            temporary_password=temp_password,
        )

        if response.success:
            print(f"✅ Welcome email sent successfully!")
            print(f"📨 Message ID: {response.message_id}")
            print(f"💬 Response: {response.message}")

            print("\n📋 What should happen in the subscription workflow:")
            print("1. ✅ New user account created")
            print("2. ✅ Temporary password generated")
            print("3. ✅ Welcome email sent with credentials")
            print("4. ✅ Subscription created with 'pending' status")
            print("5. 📧 Admin should receive notification (if configured)")
            print("6. 📧 User should receive approval/rejection email later")

        else:
            print(f"❌ Welcome email failed to send!")
            print(f"💬 Error: {response.message}")

    except Exception as e:
        print(f"💥 Exception occurred: {str(e)}")
        import traceback

        traceback.print_exc()


# Keep the original script functionality for backward compatibility
if __name__ == "__main__":
    asyncio.run(test_subscription_workflow())
