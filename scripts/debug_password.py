#!/usr/bin/env python3
"""
Debug script to check if passwords are stored in the database
"""
import sys
import asyncio
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import boto3


async def check_password_in_db():
    """Check if passwords are stored in the database"""
    try:
        # Connect to DynamoDB
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        # Try common table names
        table_names = ["people", "PeopleTable", "PeopleTableV2"]

        for table_name in table_names:
            try:
                table = dynamodb.Table(table_name)
                response = table.scan()

                print(f"✅ Found table: {table_name}")
                print(f"Items in table: {len(response['Items'])}")

                admin_found = False
                for item in response["Items"]:
                    email = item.get("email", "No email")
                    if "admin@cbba.cloud.org.bo" in email:
                        print(f"\n🔍 Admin user found in {table_name}:")
                        print(f"  Email: {email}")

                        # Check for password field (multiple possible names)
                        password_fields = ["password", "password_hash", "passwordHash"]
                        password_found = False
                        for field in password_fields:
                            if field in item and item[field]:
                                password_hash = item[field]
                                print(
                                    f"  Password ({field}): ✅ EXISTS - {password_hash[:20]}..."
                                )
                                password_found = True
                                break

                        if not password_found:
                            print(
                                f"  Password: ❌ NOT FOUND (checked: {password_fields})"
                            )

                        # Show all fields
                        print(f"  All fields: {list(item.keys())}")
                        admin_found = True
                        break

                if not admin_found:
                    print(f"\n📋 All users in {table_name}:")
                    for i, item in enumerate(response["Items"], 1):
                        email = item.get("email", "No email")
                        name = f"{item.get('firstName', '')} {item.get('lastName', '')}".strip()
                        password_fields = ["password", "password_hash", "passwordHash"]
                        has_password = (
                            "✅"
                            if any(
                                field in item and item[field]
                                for field in password_fields
                            )
                            else "❌"
                        )
                        print(f"  {i}. {email} ({name}) - Password: {has_password}")
                        if i == 1:  # Show fields for first user
                            print(f"     Fields: {list(item.keys())}")
                        if i >= 3:  # Limit output
                            print(f"  ... and {len(response['Items']) - 3} more")
                            break

                break  # Found a working table

            except Exception as e:
                print(f"❌ Table {table_name} not accessible: {e}")
                continue

    except Exception as e:
        print(f"❌ Error checking database: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_password_in_db())
