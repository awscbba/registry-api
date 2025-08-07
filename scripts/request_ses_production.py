#!/usr/bin/env python3
"""
Script to request SES production access via AWS Support API.
Note: This requires AWS Support API access (Business or Enterprise support plan).
"""

import boto3
import json
from datetime import datetime


def request_ses_production_access():
    """Request SES production access via AWS Support."""

    try:
        # Create support client
        support_client = boto3.client("support", region_name="us-east-1")

        # Create case for SES production access
        case_subject = "Request to move Amazon SES out of sandbox mode"

        case_body = """
Dear AWS Support Team,

I am requesting to move my Amazon SES account out of sandbox mode for the following use case:

**Application**: AWS User Group Cochabamba - People Registry System
**Website**: https://d28z2il3z2vmpc.cloudfront.net
**Purpose**: Community event management system

**Email Types**:
1. Welcome emails with temporary passwords for new user registrations
2. Event subscription approval/rejection notifications
3. Password reset emails for existing users

**Expected Volume**: 50-100 transactional emails per month

**Compliance Measures**:
- All emails are transactional (no marketing)
- Users explicitly opt-in through registration forms
- We handle bounces and complaints appropriately
- Proper unsubscribe mechanisms in place
- Email content is relevant and expected by recipients

**Technical Details**:
- Sending from verified domain: srinclan@gmail.com (temporary)
- Planning to use: noreply@awsugcbba.org (when domain is configured)
- Application hosted on AWS (Lambda, API Gateway, DynamoDB)
- Emails sent via AWS SES SDK

Please approve our request to send emails to any email address (production mode).

Thank you for your consideration.

Best regards,
AWS User Group Cochabamba Team
        """.strip()

        response = support_client.create_case(
            subject=case_subject,
            serviceCode="amazon-ses",
            severityCode="low",
            categoryCode="other",
            communicationBody=case_body,
            language="en",
        )

        case_id = response["caseId"]
        print(f"✅ SES production access request submitted!")
        print(f"📋 Case ID: {case_id}")
        print(f"⏱️  Expected response time: 24-48 hours")
        print(f"📧 You'll receive updates via email")

        return case_id

    except Exception as e:
        if "SubscriptionRequiredException" in str(e):
            print("❌ AWS Support API requires Business or Enterprise support plan")
            print("💡 Please use the AWS Console method instead:")
            print("   1. Go to https://console.aws.amazon.com/ses/")
            print("   2. Click 'Account dashboard' → 'Request production access'")
            print("   3. Fill out the form with the details above")
        else:
            print(f"❌ Error creating support case: {e}")

        return None


if __name__ == "__main__":
    print("🚀 Requesting SES Production Access...")
    print("=" * 50)

    case_id = request_ses_production_access()

    if case_id:
        print("\n📋 What happens next:")
        print("1. AWS will review your request (usually 24-48 hours)")
        print("2. You may receive follow-up questions via email")
        print("3. Once approved, you can send to any email address")
        print("4. Your sending limits will increase significantly")
    else:
        print("\n💡 Alternative: Use AWS Console")
        print("Go to: https://console.aws.amazon.com/ses/")
        print("Navigate: Account dashboard → Request production access")
