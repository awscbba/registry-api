#!/usr/bin/env python3
"""
Simple test script to verify email service functionality.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.services.email_service import EmailService
from src.models.email import EmailType


async def test_email_service():
    """Test the email service with a simple welcome email."""

    print("🧪 Testing Email Service...")
    print(
        f"📧 SES From Email: {os.getenv('SES_FROM_EMAIL', 'noreply@people-register.local')}"
    )
    print(f"🌐 AWS Region: {os.getenv('AWS_REGION', 'us-east-1')}")
    print(
        f"🔗 Frontend URL: {os.getenv('FRONTEND_URL', 'https://d28z2il3z2vmpc.cloudfront.net')}"
    )

    # Initialize email service
    email_service = EmailService()

    # Test email details
    test_email = "sergio.rodriguez@example.com"  # Replace with your email
    test_first_name = "Test"
    test_last_name = "User"
    test_project_name = "Test Project"

    # Generate a temporary password
    temp_password = email_service.generate_temporary_password()
    print(f"🔑 Generated temporary password: {temp_password}")

    try:
        print(f"📤 Attempting to send welcome email to: {test_email}")

        # Send welcome email
        response = await email_service.send_welcome_email(
            email=test_email,
            first_name=test_first_name,
            last_name=test_last_name,
            project_name=test_project_name,
            temporary_password=temp_password,
        )

        if response.success:
            print(f"✅ Email sent successfully!")
            print(f"📨 Message ID: {response.message_id}")
            print(f"💬 Response: {response.message}")
        else:
            print(f"❌ Email failed to send!")
            print(f"💬 Error: {response.message}")

    except Exception as e:
        print(f"💥 Exception occurred: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_email_service())
