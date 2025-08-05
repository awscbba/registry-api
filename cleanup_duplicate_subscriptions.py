#!/usr/bin/env python3
"""
Cleanup script to handle existing duplicate subscriptions in the database
"""

import asyncio
from collections import defaultdict
from src.services.defensive_dynamodb_service import DefensiveDynamoDBService
from src.models.subscription import SubscriptionUpdate


async def find_duplicate_subscriptions():
    """Find all duplicate subscriptions in the database"""
    
    service = DefensiveDynamoDBService()
    
    print("🔍 Scanning for duplicate subscriptions...")
    
    # Get all subscriptions
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
    
    print(f"📊 Found {len(duplicates)} sets of duplicate subscriptions")
    
    return duplicates


async def resolve_duplicate_subscriptions(duplicates, dry_run=True):
    """Resolve duplicate subscriptions by keeping the most recent active one"""
    
    service = DefensiveDynamoDBService()
    
    print(f"🔧 {'[DRY RUN] ' if dry_run else ''}Resolving duplicate subscriptions...")
    
    resolved_count = 0
    
    for key, subscriptions in duplicates.items():
        person_id, project_id = key.split(":", 1)
        
        print(f"\n📋 Processing duplicates for person {person_id[:8]}... project {project_id[:8]}...")
        print(f"   Found {len(subscriptions)} duplicate subscriptions")
        
        # Sort by creation date (most recent first)
        sorted_subscriptions = sorted(
            subscriptions,
            key=lambda x: x.get("createdAt", ""),
            reverse=True
        )
        
        # Find the best subscription to keep
        active_subscription = None
        pending_subscription = None
        
        for sub in sorted_subscriptions:
            status = sub.get("status", "")
            if status == "active" and not active_subscription:
                active_subscription = sub
            elif status == "pending" and not pending_subscription:
                pending_subscription = sub
        
        # Decide which one to keep
        keep_subscription = active_subscription or pending_subscription or sorted_subscriptions[0]
        
        print(f"   ✅ Keeping: {keep_subscription['id'][:8]}... (status: {keep_subscription.get('status')})")
        
        # Mark others as inactive
        for sub in sorted_subscriptions:
            if sub["id"] != keep_subscription["id"]:
                print(f"   🗑️  Marking as inactive: {sub['id'][:8]}... (was: {sub.get('status')})")
                
                if not dry_run:
                    try:
                        update_data = SubscriptionUpdate(
                            status="inactive",
                            notes=f"Marked inactive due to duplicate cleanup. Original status: {sub.get('status')}"
                        )
                        await service.update_subscription(sub["id"], update_data)
                        print(f"      ✅ Updated successfully")
                    except Exception as e:
                        print(f"      ❌ Failed to update: {e}")
        
        resolved_count += 1
    
    print(f"\n🎉 {'[DRY RUN] ' if dry_run else ''}Processed {resolved_count} sets of duplicates")
    
    return resolved_count


async def main():
    print("🧹 Duplicate Subscription Cleanup Tool\n")
    
    # Find duplicates
    duplicates = await find_duplicate_subscriptions()
    
    if not duplicates:
        print("✅ No duplicate subscriptions found!")
        return
    
    # Show summary
    print("\n📊 Duplicate Summary:")
    for key, subscriptions in duplicates.items():
        person_id, project_id = key.split(":", 1)
        print(f"   👤 Person {person_id[:8]}... 📁 Project {project_id[:8]}... → {len(subscriptions)} duplicates")
        
        for sub in subscriptions:
            print(f"      - {sub['id'][:8]}... ({sub.get('status')}) created: {sub.get('createdAt', 'unknown')}")
    
    # Run dry run first
    print("\n" + "="*60)
    print("🧪 DRY RUN - No changes will be made")
    print("="*60)
    
    await resolve_duplicate_subscriptions(duplicates, dry_run=True)
    
    # Ask for confirmation
    print("\n" + "="*60)
    print("⚠️  REAL RUN - This will make actual changes!")
    print("="*60)
    
    response = input("\nDo you want to proceed with the cleanup? (yes/no): ").strip().lower()
    
    if response == "yes":
        print("\n🚀 Proceeding with cleanup...")
        await resolve_duplicate_subscriptions(duplicates, dry_run=False)
        print("\n✅ Cleanup completed!")
    else:
        print("\n❌ Cleanup cancelled.")


if __name__ == "__main__":
    asyncio.run(main())
