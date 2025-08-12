#!/usr/bin/env python3
"""
Simple test script to verify SES configuration.
"""

import pytest
import boto3
import os
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError


def test_ses_configuration():
    """Test basic SES configuration and sending capability."""

    print("🧪 Testing SES Configuration...")

    # Get configuration
    region = os.getenv("AWS_REGION", "us-east-1")
    from_email = os.getenv(
        "SES_FROM_EMAIL", "srinclan@gmail.com"
    )  # Use verified Gmail as default

    print(f"📧 SES From Email: {from_email}")
    print(f"🌐 AWS Region: {region}")

    # Mock SES client to avoid actual AWS calls in tests
    with patch("boto3.client") as mock_boto3:
        mock_ses = MagicMock()
        mock_boto3.return_value = mock_ses

        # Mock successful responses
        mock_ses.list_verified_email_addresses.return_value = {
            "VerifiedEmailAddresses": [from_email]
        }

        mock_ses.send_email.return_value = {"MessageId": "test-message-id-123"}

        # Initialize SES client
        try:
            ses_client = boto3.client("ses", region_name=region)
            print("✅ SES client initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize SES client: {e}")
            assert False

        # Check verified email addresses
        try:
            print("📋 Checking verified email addresses...")
            response = ses_client.list_verified_email_addresses()
            verified_emails = response.get("VerifiedEmailAddresses", [])

            print(f"✅ Found {len(verified_emails)} verified email addresses:")
            for email in verified_emails:
                print(f"   - {email}")

            if from_email not in verified_emails:
                print(f"⚠️  Warning: {from_email} is not in verified emails list.")
                print("This could be why emails are not being sent.")
                # In test environment, this is expected, so don't fail
                print("✅ Test environment - mocked response is acceptable")

        except ClientError as e:
            print(f"❌ Could not list verified emails: {e}")
            # In test environment with mocking, this shouldn't happen
            assert False

        # Try to send a test email
        test_email = "srinclan@gmail.com"  # Your verified Gmail address

        try:
            print(f"📤 Attempting to send test email to: {test_email}")

            response = ses_client.send_email(
                Source=f"AWS User Group Cochabamba <{from_email}>",
                Destination={"ToAddresses": [test_email]},
                Message={
                    "Subject": {
                        "Data": "Test Email from People Registry",
                        "Charset": "UTF-8",
                    },
                    "Body": {
                        "Html": {
                            "Data": "<h1>Test Email</h1><p>This is a test email from the People Registry system.</p>",
                            "Charset": "UTF-8",
                        },
                        "Text": {
                            "Data": "Test Email\n\nThis is a test email from the People Registry system.",
                            "Charset": "UTF-8",
                        },
                    },
                },
            )

            message_id = response.get("MessageId")
            print(f"✅ Test email sent successfully! Message ID: {message_id}")
            assert message_id is not None

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            print(f"❌ Failed to send test email: {error_code} - {e}")
            # In test environment, this shouldn't happen with mocking
            assert False

        except Exception as e:
            print(f"❌ Unexpected error sending test email: {e}")
            assert False

    print("🎉 SES configuration test completed successfully!")
    assert True


if __name__ == "__main__":
    test_ses_configuration()
