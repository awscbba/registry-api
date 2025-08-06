#!/usr/bin/env python3
"""
Database health check script - checks for duplicates and data integrity issues
"""

import asyncio
from collections import defaultdict
from src.services.defensive_dynamodb_service import DefensiveDynamoDBService


async def check_duplicate_subscriptions():
    """Check for duplicate subscriptions"""

    service = DefensiveDynamoDBService()

    print("🔍 Checking for duplicate subscriptions...")

    try:
        all_subscriptions = await service.get_all_subscriptions()

        # Group by person_id + project_id
        subscription_groups = defaultdict(list)

        for subscription in all_subscriptions:
            person_id = subscription.get("personId")
            project_id = subscription.get("projectId")

            if person_id and project_id:
                key = f"{person_id}:{project_id}"
                subscription_groups[key].append(subscription)

        # Find duplicates
        duplicates = {}
        for key, subscriptions in subscription_groups.items():
            if len(subscriptions) > 1:
                duplicates[key] = subscriptions

        if duplicates:
            print(f"⚠️  Found {len(duplicates)} sets of duplicate subscriptions")
            for key, subs in duplicates.items():
                person_id, project_id = key.split(":", 1)
                print(
                    f"   👤 Person {person_id[:8]}... 📁 Project {project_id[:8]}... → {len(subs)} duplicates"
                )
        else:
            print("✅ No duplicate subscriptions found")

        return len(duplicates)

    except Exception as e:
        print(f"❌ Error checking subscriptions: {e}")
        return -1


async def check_duplicate_users():
    """Check for duplicate users by email"""

    service = DefensiveDynamoDBService()

    print("🔍 Checking for duplicate users...")

    try:
        all_people = await service.list_people(limit=1000)

        # Group by email address
        email_groups = defaultdict(list)

        for person in all_people:
            email = getattr(person, "email", None)
            if email:
                email_groups[email].append(
                    {
                        "id": getattr(person, "id", "unknown"),
                        "firstName": getattr(person, "first_name", "unknown"),
                        "lastName": getattr(person, "last_name", "unknown"),
                        "email": email,
                    }
                )

        # Find duplicates
        duplicates = {}
        for email, users in email_groups.items():
            if len(users) > 1:
                duplicates[email] = users

        if duplicates:
            print(f"⚠️  Found {len(duplicates)} duplicate email addresses")
            for email, users in duplicates.items():
                print(f"   📧 {email} → {len(users)} users")
        else:
            print("✅ No duplicate users found")

        return len(duplicates)

    except Exception as e:
        print(f"❌ Error checking users: {e}")
        return -1


async def check_orphaned_subscriptions():
    """Check for subscriptions with missing persons or projects"""

    service = DefensiveDynamoDBService()

    print("🔍 Checking for orphaned subscriptions...")

    try:
        # Get all data
        all_subscriptions = await service.get_all_subscriptions()
        all_people = await service.list_people(limit=1000)
        all_projects = await service.get_all_projects()

        # Create lookup sets
        person_ids = {getattr(p, "id") for p in all_people if getattr(p, "id", None)}
        project_ids = {p.get("id") for p in all_projects if p.get("id")}

        orphaned_subscriptions = []

        for subscription in all_subscriptions:
            person_id = subscription.get("personId")
            project_id = subscription.get("projectId")

            if person_id not in person_ids:
                orphaned_subscriptions.append(
                    {
                        "id": subscription.get("id"),
                        "type": "missing_person",
                        "person_id": person_id,
                        "project_id": project_id,
                    }
                )
            elif project_id not in project_ids:
                orphaned_subscriptions.append(
                    {
                        "id": subscription.get("id"),
                        "type": "missing_project",
                        "person_id": person_id,
                        "project_id": project_id,
                    }
                )

        if orphaned_subscriptions:
            print(f"⚠️  Found {len(orphaned_subscriptions)} orphaned subscriptions")
            for orphan in orphaned_subscriptions:
                print(f"   🔗 {orphan['id'][:8]}... → {orphan['type']}")
        else:
            print("✅ No orphaned subscriptions found")

        return len(orphaned_subscriptions)

    except Exception as e:
        print(f"❌ Error checking orphaned subscriptions: {e}")
        return -1


async def get_database_stats():
    """Get basic database statistics"""

    service = DefensiveDynamoDBService()

    print("📊 Database Statistics:")

    try:
        all_people = await service.list_people(limit=1000)
        all_subscriptions = await service.get_all_subscriptions()
        all_projects = await service.get_all_projects()

        print(f"   👥 Total Users: {len(all_people)}")
        print(f"   📁 Total Projects: {len(all_projects)}")
        print(f"   🔗 Total Subscriptions: {len(all_subscriptions)}")

        # Subscription status breakdown
        status_counts = defaultdict(int)
        for sub in all_subscriptions:
            status = sub.get("status", "unknown")
            status_counts[status] += 1

        print("   📈 Subscription Status:")
        for status, count in status_counts.items():
            print(f"      {status}: {count}")

    except Exception as e:
        print(f"❌ Error getting database stats: {e}")


async def main():
    print("🏥 Database Health Check\n")

    # Get basic stats
    await get_database_stats()
    print()

    # Run health checks
    duplicate_subs = await check_duplicate_subscriptions()
    duplicate_users = await check_duplicate_users()
    orphaned_subs = await check_orphaned_subscriptions()

    print(f"\n📋 Health Check Summary:")

    issues_found = 0

    if duplicate_subs > 0:
        print(f"   ⚠️  {duplicate_subs} duplicate subscription sets")
        issues_found += duplicate_subs

    if duplicate_users > 0:
        print(f"   ⚠️  {duplicate_users} duplicate user emails")
        issues_found += duplicate_users

    if orphaned_subs > 0:
        print(f"   ⚠️  {orphaned_subs} orphaned subscriptions")
        issues_found += orphaned_subs

    if issues_found == 0:
        print("   ✅ Database is healthy - no issues found!")
    else:
        print(f"   ⚠️  Found {issues_found} total issues")
        print(f"\n💡 Consider running cleanup scripts to resolve issues")


if __name__ == "__main__":
    asyncio.run(main())
