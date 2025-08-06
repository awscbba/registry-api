#!/usr/bin/env python3
"""
Fix cascade deletion issues for user subscriptions.

This script:
1. Analyzes orphaned subscriptions
2. Optionally cleans them up
3. Provides the code fix for proper cascade deletion
"""

import boto3
import sys
import os
from typing import List, Dict, Any


def fix_cascade_deletion():
    """Fix cascade deletion issues using boto3 directly."""
    print("🔍 Analyzing and fixing cascade deletion issues...")

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

        print(f"📊 Found {len(orphaned_subscriptions)} orphaned subscriptions")

        if orphaned_subscriptions:
            # Ask for confirmation
            print(f"")
            print(
                f"🤔 Do you want to delete these {len(orphaned_subscriptions)} orphaned subscriptions?"
            )
            print(
                f"   This will clean up the data inconsistency and fix your smart card count."
            )
            response = input("   Type 'yes' to confirm: ")

            if response.lower() == "yes":
                print(f"🧹 Cleaning up orphaned subscriptions...")
                cleaned_count = 0
                failed_count = 0

                for subscription in orphaned_subscriptions:
                    try:
                        subscription_id = subscription.get("id")
                        person_id = subscription.get("personId")

                        if subscription_id:
                            subscriptions_table.delete_item(Key={"id": subscription_id})
                            cleaned_count += 1
                            print(
                                f"   ✅ Deleted subscription {subscription_id} (person: {person_id})"
                            )
                        else:
                            failed_count += 1
                            print(f"   ❌ Subscription missing ID: {subscription}")

                    except Exception as e:
                        failed_count += 1
                        print(
                            f"   ❌ Error deleting subscription {subscription.get('id', 'unknown')}: {e}"
                        )

                print(f"")
                print(f"🎉 Cleanup Results:")
                print(f"   Successfully deleted: {cleaned_count}")
                print(f"   Failed to delete: {failed_count}")
                print(f"")
                print(
                    f"📊 Your smart card should now show {len(all_subscriptions) - cleaned_count} subscriptions"
                )
            else:
                print("⏭️  Skipping cleanup.")

        # Show the code fix
        print_code_fix()

    except Exception as e:
        print(f"❌ Error during fix: {e}")
        print(f"   Make sure AWS credentials are configured")
        print(f"   and the DynamoDB tables exist in us-east-1")


def print_code_fix():
    """Print the code fix for cascade deletion."""
    print("")
    print("=" * 60)
    print("🔧 CODE FIX NEEDED")
    print("=" * 60)
    print(
        "Replace the delete_person method in src/services/defensive_dynamodb_service.py:"
    )
    print("")
    print('@database_operation("delete_person")')
    print("async def delete_person(")
    print("    self, person_id: str, context: Optional[ErrorContext] = None")
    print(") -> bool:")
    print('    """Delete a person with cascade deletion of subscriptions"""')
    print("    try:")
    print("        # Check if person exists first")
    print("        existing_person = await self.get_person(person_id, context)")
    print("        if not existing_person:")
    print("            return False")
    print("")
    print("        # Get all subscriptions for this person")
    print(
        "        person_subscriptions = await self.get_subscriptions_by_person(person_id)"
    )
    print("        ")
    print("        # Delete all subscriptions first (cascade deletion)")
    print("        deleted_subscriptions = 0")
    print("        for subscription in person_subscriptions:")
    print("            subscription_id = subscription.get('id')")
    print("            if subscription_id:")
    print("                try:")
    print(
        "                    success = await self.delete_subscription(subscription_id)"
    )
    print("                    if success:")
    print("                        deleted_subscriptions += 1")
    print(
        "                        self.logger.info(f'Deleted subscription {subscription_id} for person {person_id}')"
    )
    print("                except Exception as e:")
    print(
        "                    self.logger.error(f'Error deleting subscription {subscription_id}: {e}')"
    )
    print("        ")
    print(
        "        self.logger.info(f'Deleted {deleted_subscriptions} subscriptions for person {person_id}')"
    )
    print("        ")
    print("        # Now delete the person")
    print("        self.table.delete_item(Key={'id': person_id})")
    print("        return True")
    print("")
    print("    except Exception as e:")
    print("        self.logger.error(f'Error deleting person {person_id}: {e}')")
    print("        raise")
    print("")
    print("=" * 60)
    print("📝 IMPLEMENTATION STEPS")
    print("=" * 60)
    print(
        "1. Create feature branch: git checkout -b fix/cascade-deletion-subscriptions"
    )
    print("2. Update the delete_person method with the code above")
    print("3. Test the changes locally")
    print("4. Create PR for review (never push to main)")
    print("5. Deploy through CodeCatalyst pipelines")
    print("")
    print("🧪 Testing the fix:")
    print("   - Create a test user with subscriptions")
    print("   - Delete the user")
    print("   - Verify subscriptions are also deleted")
    print("   - Check that subscription count is accurate")


if __name__ == "__main__":
    try:
        fix_cascade_deletion()
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
