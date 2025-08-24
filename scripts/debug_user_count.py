#!/usr/bin/env python3
"""
Debug script to investigate why admin dashboard shows zero users.
This script will check the database directly and trace the issue.
"""

import os
import sys
import asyncio
import boto3
from datetime import datetime

# Add the src directory to the path so we can import our modules
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, "..", "src")
sys.path.insert(0, src_dir)

# Set up the environment
os.environ.setdefault("PEOPLE_TABLE_NAME", "PeopleTable")
os.environ.setdefault("PROJECTS_TABLE_NAME", "ProjectsTable")
os.environ.setdefault("AUDIT_LOGS_TABLE_NAME", "AuditLogsTable")

try:
    from services.defensive_dynamodb_service import DefensiveDynamoDBService
    from core.service_manager import ServiceManager
except ImportError as e:
    print(f"Import error: {e}")
    print("Available modules in src:")
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.endswith(".py"):
                print(f"  {os.path.relpath(os.path.join(root, file), src_dir)}")
    sys.exit(1)


async def debug_user_count():
    """Debug the user count issue step by step."""
    print("🔍 Debugging User Count Issue")
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

        # Scan the table directly
        response = table.scan(Limit=10)
        items = response.get("Items", [])
        print(f"   Direct scan returned: {len(items)} items")

        if items:
            print("   Sample item keys:", list(items[0].keys()))

    except Exception as e:
        print(f"   ❌ Error accessing table: {e}")
        return

    # Step 3: Check DefensiveDynamoDBService
    print("\n3. DefensiveDynamoDBService Check:")
    try:
        db_service = DefensiveDynamoDBService()
        people = await db_service.list_people(limit=200)  # Increase limit
        print(f"   DefensiveDynamoDBService returned: {len(people)} people")

        if people:
            print(
                "   Sample person:",
                {
                    "id": people[0].id,
                    "email": people[0].email,
                    "firstName": people[0].firstName,
                    "lastName": people[0].lastName,
                },
            )

    except Exception as e:
        print(f"   ❌ Error with DefensiveDynamoDBService: {e}")
        import traceback

        traceback.print_exc()

    # Step 4: Check PeopleService dashboard data (simplified)
    print("\n4. PeopleService Dashboard Data:")
    try:
        print("   ⚠️ Skipping PeopleService test due to import complexity")
        print("   This would require full FastAPI app initialization")

    except Exception as e:
        print(f"   ❌ Error with PeopleService: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 50)
    print("🎯 Debug Complete")


if __name__ == "__main__":
    asyncio.run(debug_user_count())
