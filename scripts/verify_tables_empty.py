#!/usr/bin/env python3
"""
Script to verify that API tables are empty
Usage: python scripts/verify_tables_empty.py
"""
import sys
import asyncio
import os
import boto3

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.core.config import config


async def verify_tables_empty():
    """Verify that all API tables are empty"""
    try:
        # Connect to DynamoDB
        dynamodb = boto3.resource("dynamodb", region_name=config.database.region)

        # Get the actual table names from config
        tables_to_check = {
            "People": config.database.people_table,
            "Projects": config.database.projects_table,
            "Subscriptions": config.database.subscriptions_table,
        }

        print("🔍 Verifying API tables are empty...")
        print()

        all_empty = True

        for table_type, table_name in tables_to_check.items():
            try:
                table = dynamodb.Table(table_name)
                response = table.scan()
                items = response["Items"]

                print(f"📋 {table_type} ({table_name}):")
                print(f"  Items count: {len(items)}")

                if len(items) == 0:
                    print(f"  ✅ Empty - Ready for production")
                else:
                    print(f"  ⚠️  Contains {len(items)} items:")
                    all_empty = False

                    # Show first few items
                    for i, item in enumerate(items[:3]):
                        if table_type == "People":
                            email = item.get("email", "No email")
                            name = f"{item.get('firstName', '')} {item.get('lastName', '')}".strip()
                            print(f"    {i + 1}. {email} ({name})")
                        elif table_type == "Projects":
                            name = item.get("name", "No name")
                            print(f"    {i + 1}. Project: {name}")
                        elif table_type == "Subscriptions":
                            sub_id = item.get("id", "No ID")
                            person_id = item.get("personId", "No person")
                            project_id = item.get("projectId", "No project")
                            print(
                                f"    {i + 1}. Subscription: {sub_id} (Person: {person_id}, Project: {project_id})"
                            )

                    if len(items) > 3:
                        print(f"    ... and {len(items) - 3} more")

                print()

            except Exception as e:
                print(f"❌ Error checking table {table_name}: {e}")
                all_empty = False
                continue

        if all_empty:
            print("🎉 All API tables are empty and ready for production!")
        else:
            print("⚠️  Some tables still contain data.")

        return all_empty

    except Exception as e:
        print(f"❌ Error during verification: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(verify_tables_empty())
    sys.exit(0 if success else 1)
