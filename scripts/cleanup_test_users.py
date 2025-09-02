#!/usr/bin/env python3
"""
Script to remove testing users from the API tables
Usage: python scripts/cleanup_test_users.py
"""
import sys
import asyncio
import os
import boto3
from typing import List, Dict, Any

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.core.config import config

# Test user patterns to identify and remove
TEST_USER_PATTERNS = [
    "test",
    "admin@cbba.cloud.org.bo",
    "newadmin@test.com",
    "test-admin@cbba.cloud.org.bo",
    "@test.com",
    "example.com",
    "testadmin@",
    "test-person",
    "test-success",
]


def is_test_user(email: str) -> bool:
    """Check if an email appears to be a test user"""
    email_lower = email.lower()
    return any(pattern.lower() in email_lower for pattern in TEST_USER_PATTERNS)


async def cleanup_test_users():
    """Remove test users from all API tables"""
    try:
        # Connect to DynamoDB
        dynamodb = boto3.resource("dynamodb", region_name=config.database.region)

        # Get the actual table names from config
        tables_to_clean = {
            "people": config.database.people_table,
            "projects": config.database.projects_table,
            "subscriptions": config.database.subscriptions_table,
        }

        print("🧹 Cleaning up test users from API tables...")
        print(f"Tables to clean: {list(tables_to_clean.values())}")
        print()

        total_removed = 0

        for table_type, table_name in tables_to_clean.items():
            try:
                table = dynamodb.Table(table_name)
                response = table.scan()
                items = response["Items"]

                print(f"📋 Checking {table_name} ({table_type}):")
                print(f"  Total items: {len(items)}")

                test_items = []

                if table_type == "people":
                    # For people table, check email field
                    for item in items:
                        email = item.get("email", "")
                        if email and is_test_user(email):
                            test_items.append(item)
                            print(f"  🎯 Test user found: {email}")

                elif table_type == "subscriptions":
                    # For subscriptions, we need to check if the person is a test user
                    # First get all test person IDs
                    people_table = dynamodb.Table(config.database.people_table)
                    people_response = people_table.scan()
                    test_person_ids = set()

                    for person in people_response["Items"]:
                        email = person.get("email", "")
                        if email and is_test_user(email):
                            test_person_ids.add(person.get("id"))

                    # Now find subscriptions for test users
                    for item in items:
                        person_id = item.get("personId") or item.get("person_id")
                        if person_id in test_person_ids:
                            test_items.append(item)
                            print(
                                f"  🎯 Test subscription found: {item.get('id', 'No ID')}"
                            )

                elif table_type == "projects":
                    # For projects, check if created by test users or has test-like names
                    for item in items:
                        project_name = item.get("name", "").lower()
                        description = item.get("description", "").lower()
                        if (
                            "test" in project_name
                            or "test" in description
                            or "example" in project_name
                            or "demo" in project_name
                        ):
                            test_items.append(item)
                            print(
                                f"  🎯 Test project found: {item.get('name', 'No name')}"
                            )

                # Remove test items
                if test_items:
                    print(f"  🗑️  Removing {len(test_items)} test items...")

                    for item in test_items:
                        try:
                            # Get the primary key
                            key = {"id": item["id"]}
                            table.delete_item(Key=key)
                            total_removed += 1

                            if table_type == "people":
                                print(
                                    f"    ✅ Removed user: {item.get('email', 'No email')}"
                                )
                            elif table_type == "subscriptions":
                                print(
                                    f"    ✅ Removed subscription: {item.get('id', 'No ID')}"
                                )
                            elif table_type == "projects":
                                print(
                                    f"    ✅ Removed project: {item.get('name', 'No name')}"
                                )

                        except Exception as e:
                            print(
                                f"    ❌ Error removing item {item.get('id', 'No ID')}: {e}"
                            )
                else:
                    print(f"  ✅ No test items found in {table_name}")

                print()

            except Exception as e:
                print(f"❌ Error processing table {table_name}: {e}")
                continue

        print(f"🎉 Cleanup completed! Removed {total_removed} test items total.")
        return True

    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(cleanup_test_users())
    sys.exit(0 if success else 1)
