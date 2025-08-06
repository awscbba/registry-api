#!/usr/bin/env python3
"""
Analyze cascade deletion issues for user subscriptions.

This script uses boto3 directly to check for orphaned subscriptions
(subscriptions that reference deleted users).
"""

import boto3
import sys
import os
from typing import List, Dict, Any


def analyze_cascade_deletion():
    """Analyze cascade deletion issues using boto3 directly."""
    print("🔍 Analyzing subscription data integrity...")

    try:
        # Initialize DynamoDB
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        # Get table names from environment or use defaults
        people_table_name = os.environ.get("PEOPLE_TABLE_NAME", "PeopleTable")
        subscriptions_table_name = os.environ.get(
            "SUBSCRIPTIONS_TABLE_NAME", "SubscriptionsTable"
        )

        people_table = dynamodb.Table(people_table_name)
        subscriptions_table = dynamodb.Table(subscriptions_table_name)

        print(f"📊 Using tables: {people_table_name}, {subscriptions_table_name}")

        # Get all people
        print("   Scanning people table...")
        people_response = people_table.scan()
        all_people = people_response.get("Items", [])

        # Handle pagination if needed
        while "LastEvaluatedKey" in people_response:
            people_response = people_table.scan(
                ExclusiveStartKey=people_response["LastEvaluatedKey"]
            )
            all_people.extend(people_response.get("Items", []))

        # Get all subscriptions
        print("   Scanning subscriptions table...")
        subscriptions_response = subscriptions_table.scan()
        all_subscriptions = subscriptions_response.get("Items", [])

        # Handle pagination if needed
        while "LastEvaluatedKey" in subscriptions_response:
            subscriptions_response = subscriptions_table.scan(
                ExclusiveStartKey=subscriptions_response["LastEvaluatedKey"]
            )
            all_subscriptions.extend(subscriptions_response.get("Items", []))

        # Create lookup set for person IDs
        person_ids = {person["id"] for person in all_people}

        # Find orphaned subscriptions
        orphaned_subscriptions = []
        for subscription in all_subscriptions:
            person_id = subscription.get("personId")
            if person_id and person_id not in person_ids:
                orphaned_subscriptions.append(subscription)

        # Print results
        print(f"")
        print(f"📊 Analysis Results:")
        print(f"   Total People: {len(all_people)}")
        print(f"   Total Subscriptions: {len(all_subscriptions)}")
        print(
            f"   Valid Subscriptions: {len(all_subscriptions) - len(orphaned_subscriptions)}"
        )
        print(f"   Orphaned Subscriptions: {len(orphaned_subscriptions)}")

        if orphaned_subscriptions:
            print(f"")
            print(
                f"🚨 ISSUE CONFIRMED: Found {len(orphaned_subscriptions)} orphaned subscriptions"
            )
            print(
                f"   This explains why the smart card shows more subscriptions than expected!"
            )
            print(f"")
            print(f"📋 First 5 Orphaned Subscriptions:")
            for i, sub in enumerate(orphaned_subscriptions[:5], 1):
                print(f"   {i}. ID: {sub.get('id')}")
                print(f"      Person ID: {sub.get('personId')} (MISSING)")
                print(f"      Project ID: {sub.get('projectId')}")
                print(f"      Status: {sub.get('status')}")
                print(f"      Created: {sub.get('createdAt', 'N/A')}")

            if len(orphaned_subscriptions) > 5:
                print(f"   ... and {len(orphaned_subscriptions) - 5} more")

            print(f"")
            print(f"🔧 To fix this issue:")
            print(f"   1. Run: just fix-cascade-deletion")
            print(f"   2. This will clean up orphaned subscriptions")
            print(f"   3. And provide the code fix for future deletions")

            print(f"")
            print(f"💡 Root Cause:")
            print(f"   The delete_person method only deletes the person record")
            print(
                f"   but doesn't clean up associated subscriptions (cascade deletion)"
            )
        else:
            print(f"✅ No orphaned subscriptions found!")
            print(f"   The cascade deletion is working correctly.")

        return len(orphaned_subscriptions)

    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        print(f"   Make sure AWS credentials are configured")
        print(f"   and the DynamoDB tables exist in us-east-1")
        return -1


if __name__ == "__main__":
    result = analyze_cascade_deletion()
    sys.exit(0 if result >= 0 else 1)
