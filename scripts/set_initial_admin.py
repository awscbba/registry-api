#!/usr/bin/env python3
"""
Script to set initial admin user in the People Registry system.
This should be run once to bootstrap the first admin user.
"""

import boto3
import sys
import os
from datetime import datetime


def set_admin_user(email: str):
    """Set a user as admin by email."""
    try:
        # Initialize DynamoDB
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.Table("PeopleTable")

        # Find user by email using EmailIndex GSI
        response = table.query(
            IndexName="EmailIndex",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("email").eq(email),
        )

        if not response["Items"]:
            print(f"❌ User with email {email} not found in database")
            print("   Please make sure the user is registered first")
            return False

        user = response["Items"][0]
        user_id = user["id"]

        # Update user to be admin
        table.update_item(
            Key={"id": user_id},
            UpdateExpression="SET isAdmin = :admin, updatedAt = :updated",
            ExpressionAttributeValues={
                ":admin": True,
                ":updated": datetime.utcnow().isoformat(),
            },
        )

        print(f"✅ Successfully set {email} as admin")
        print(f"   User ID: {user_id}")
        print(f"   Name: {user.get('firstName', '')} {user.get('lastName', '')}")
        return True

    except Exception as e:
        print(f"❌ Error setting admin user: {str(e)}")
        return False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python set_initial_admin.py <email>")
        print("Example: python set_initial_admin.py sergio.rodriguez@cbba.cloud.org.bo")
        sys.exit(1)

    email = sys.argv[1]
    print(f"🔧 Setting {email} as admin user...")

    if set_admin_user(email):
        print("🎉 Admin user setup completed successfully!")
    else:
        print("💥 Failed to set admin user")
        sys.exit(1)
