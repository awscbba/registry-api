#!/usr/bin/env python3
"""
Simple test script to verify SES configuration.
"""

import boto3
import os
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

    # Initialize SES client
    try:
        ses_client = boto3.client("ses", region_name=region)
        print("✅ SES client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize SES client: {e}")
        return False

    # Test SES sending quota
    try:
        quota = ses_client.get_send_quota()
        print(
            f"📊 SES Quota - Max24Hour: {quota['Max24HourSend']}, MaxSendRate: {quota['MaxSendRate']}, SentLast24Hours: {quota['SentLast24Hours']}"
        )
    except ClientError as e:
        print(f"⚠️ Could not get SES quota: {e}")

    # Check verified email addresses
    try:
        identities = ses_client.list_verified_email_addresses()
        verified_emails = identities.get("VerifiedEmailAddresses", [])
        print(f"✉️ Verified email addresses: {verified_emails}")

        if from_email not in verified_emails:
            print(f"⚠️ WARNING: From email '{from_email}' is not verified in SES!")
            print("This could be why emails are not being sent.")
            return False

    except ClientError as e:
        print(f"❌ Could not list verified emails: {e}")
        return False

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

        message_id = response["MessageId"]
        print(f"✅ Test email sent successfully!")
        print(f"📨 Message ID: {message_id}")
        return True

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        print(f"❌ Failed to send test email!")
        print(f"🔴 Error Code: {error_code}")
        print(f"💬 Error Message: {error_message}")

        if error_code == "MessageRejected":
            print("💡 This usually means the email address is not verified in SES.")
        elif error_code == "SendingPausedException":
            print("💡 SES sending is paused for your account.")

        return False

    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = test_ses_configuration()
    if success:
        print("\n🎉 SES configuration appears to be working correctly!")
    else:
        print(
            "\n🚨 There are issues with the SES configuration that need to be resolved."
        )
