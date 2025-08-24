#!/usr/bin/env python3
"""
Simple debug script to check DynamoDB table directly.
This bypasses the service layer to identify the root cause.
"""

import os
import boto3
from decimal import Decimal


def debug_user_count():
    """Debug the user count issue by checking DynamoDB directly."""
    print("🔍 Simple User Count Debug")
    print("=" * 50)

    # Step 1: Check environment variables
    print("\n1. Environment Variables:")
    table_name = os.environ.get("PEOPLE_TABLE_NAME", "PeopleTable")
    print(f"   PEOPLE_TABLE_NAME: {table_name}")

    # Step 2: Check DynamoDB table directly
    print("\n2. Direct DynamoDB Table Check:")
    try:
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(table_name)

        # Get table description
        table_desc = table.meta.client.describe_table(TableName=table_name)
        item_count = table_desc["Table"]["ItemCount"]
        print(f"   Table exists: ✅")
        print(f"   Item count (approximate): {item_count}")

        # Scan the table directly (limited to 10 items for safety)
        response = table.scan(Limit=10)
        items = response.get("Items", [])
        print(f"   Direct scan returned: {len(items)} items")

        if items:
            print("   Sample item keys:", list(items[0].keys()))

            # Check for email field in first item
            first_item = items[0]
            if "email" in first_item:
                print(f"   Sample email: {first_item['email']}")
            if "firstName" in first_item:
                print(f"   Sample firstName: {first_item['firstName']}")
            if "lastName" in first_item:
                print(f"   Sample lastName: {first_item['lastName']}")

            # Count items with valid email addresses
            valid_users = 0
            for item in items:
                email = item.get("email", "")
                if email and "@" in str(email):
                    valid_users += 1
            print(f"   Valid users (with email): {valid_users}/{len(items)}")
        else:
            print("   ❌ No items found in table!")

        # Try to scan more items to get a better count
        print("\n3. Extended Scan (up to 100 items):")
        response = table.scan(Limit=100)
        all_items = response.get("Items", [])
        print(f"   Extended scan returned: {len(all_items)} items")

        if all_items:
            # Analyze the data structure
            valid_emails = 0
            admin_users = 0
            active_users = 0

            for item in all_items:
                # Check email
                email = item.get("email", "")
                if email and "@" in str(email):
                    valid_emails += 1

                # Check admin status
                is_admin = item.get("isAdmin", item.get("is_admin", False))
                if is_admin:
                    admin_users += 1

                # Check active status (assume active if not specified)
                is_active = item.get("isActive", item.get("is_active", True))
                if is_active:
                    active_users += 1

            print(f"   Users with valid emails: {valid_emails}")
            print(f"   Admin users: {admin_users}")
            print(f"   Active users: {active_users}")

            # Show field name variations
            print("\n4. Field Name Analysis:")
            field_variations = {}
            for item in all_items[:5]:  # Check first 5 items
                for key in item.keys():
                    if key not in field_variations:
                        field_variations[key] = 0
                    field_variations[key] += 1

            print("   Common fields found:")
            for field, count in sorted(field_variations.items()):
                print(f"     {field}: {count}/5 items")

    except Exception as e:
        print(f"   ❌ Error accessing table: {e}")
        import traceback

        traceback.print_exc()
        return

    print("\n" + "=" * 50)
    print("🎯 Debug Complete")


if __name__ == "__main__":
    debug_user_count()
