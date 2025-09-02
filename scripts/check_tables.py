#!/usr/bin/env python3
"""
Check which DynamoDB table contains the user data.
"""

import asyncio
import sys
import os

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.repositories.people_repository import PeopleRepository


async def check_tables():
    """Check which table contains the user data."""
    print("🔍 Checking DynamoDB Tables for User Data")
    print("=" * 50)

    email = "sergio.rodriguez@cbba.cloud.org.bo"
    print(f"📧 Looking for user: {email}")
    print()

    # Check current repository configuration
    people_repo = PeopleRepository()

    print("📋 Current Repository Configuration:")
    print(f"   - Table Name: {people_repo.table_name}")
    print()

    # Test get_by_email (uses current table)
    print("Step 1: Testing get_by_email (PersonResponse)...")
    try:
        person = await people_repo.get_by_email(email)
        if person:
            print(f"✅ Found user in {people_repo.table_name}")
            print(f"   - ID: {person.id}")
            print(f"   - Name: {person.firstName} {person.lastName}")
            print(f"   - Is Admin: {person.isAdmin}")
            print(f"   - Is Active: {person.isActive}")
        else:
            print(f"❌ User NOT found in {people_repo.table_name}")
    except Exception as e:
        print(f"❌ Error checking {people_repo.table_name}: {e}")

    print()

    # Test get_by_email_for_auth (uses current table)
    print("Step 2: Testing get_by_email_for_auth (with passwordHash)...")
    try:
        person_data = await people_repo.get_by_email_for_auth(email)
        if person_data:
            print(f"✅ Found auth data in {people_repo.table_name}")
            print(f"   - ID: {person_data.get('id')}")
            print(f"   - Email: {person_data.get('email')}")
            print(f"   - Has Password Hash: {'passwordHash' in person_data}")
            if "passwordHash" in person_data:
                hash_preview = person_data["passwordHash"][:20] + "..."
                print(f"   - Password Hash Preview: {hash_preview}")
        else:
            print(f"❌ Auth data NOT found in {people_repo.table_name}")
    except Exception as e:
        print(f"❌ Error checking auth data in {people_repo.table_name}: {e}")

    print()

    # Check environment variables
    print("Step 3: Environment Variables:")
    print(f"   - PEOPLE_TABLE_NAME: {os.environ.get('PEOPLE_TABLE_NAME', 'NOT SET')}")
    print(
        f"   - PEOPLE_TABLE_V2_NAME: {os.environ.get('PEOPLE_TABLE_V2_NAME', 'NOT SET')}"
    )

    # Check what table the repository is actually using
    print()
    print("Step 4: Repository Table Selection Logic:")
    print(f"   - Repository is using: {people_repo.table_name}")

    # Check if we can manually test both tables
    print()
    print("Step 5: Manual Table Check:")

    # Test PeopleTable (V1)
    print("   Testing PeopleTable (V1)...")
    try:
        import boto3

        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table_v1 = dynamodb.Table("PeopleTable")

        response = table_v1.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr("email").eq(email), Limit=1
        )

        if response["Items"]:
            item = response["Items"][0]
            print(
                f"   ✅ Found in PeopleTable: {item.get('firstName', 'N/A')} {item.get('lastName', 'N/A')}"
            )
            print(f"      - Has passwordHash: {'passwordHash' in item}")
        else:
            print("   ❌ Not found in PeopleTable")

    except Exception as e:
        print(f"   ❌ Error checking PeopleTable: {e}")

    # Test PeopleTableV2
    print("   Testing PeopleTableV2...")
    try:
        table_v2 = dynamodb.Table("PeopleTableV2")

        response = table_v2.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr("email").eq(email), Limit=1
        )

        if response["Items"]:
            item = response["Items"][0]
            print(
                f"   ✅ Found in PeopleTableV2: {item.get('firstName', 'N/A')} {item.get('lastName', 'N/A')}"
            )
            print(f"      - Has passwordHash: {'passwordHash' in item}")
        else:
            print("   ❌ Not found in PeopleTableV2")

    except Exception as e:
        print(f"   ❌ Error checking PeopleTableV2: {e}")


if __name__ == "__main__":
    asyncio.run(check_tables())
