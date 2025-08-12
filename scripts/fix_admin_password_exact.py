#!/usr/bin/env python3
"""
Fix admin password using the exact same method as the deployed code.
"""

import boto3
import bcrypt
from datetime import datetime


def fix_admin_password_exact():
    """Fix admin password using exact same method as deployed code."""

    print("🔧 Fixing Admin Password (Exact Method)")
    print("=" * 50)

    # Correct admin credentials
    admin_email = "admin@awsugcbba.org"
    admin_password = "awsugcbba2025"

    try:
        # Initialize DynamoDB
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.Table("PeopleTable")

        print(f"1. Finding user: {admin_email}")

        # Query by email using EmailIndex GSI
        response = table.query(
            IndexName="EmailIndex",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("email").eq(
                admin_email
            ),
        )

        if not response["Items"]:
            print(f"   ❌ User not found!")
            return

        user = response["Items"][0]
        user_id = user["id"]

        print(f"   ✅ Found user: {user_id}")

        print(f"2. Hashing password using exact deployed method...")

        # Use the exact same method as PasswordHasher class (12 rounds)
        SALT_ROUNDS = 12
        salt = bcrypt.gensalt(rounds=SALT_ROUNDS)
        hashed = bcrypt.hashpw(admin_password.encode("utf-8"), salt)
        password_hash = hashed.decode("utf-8")

        print(f"   Password hash: {password_hash[:50]}...")

        # Verify the hash works
        if bcrypt.checkpw(
            admin_password.encode("utf-8"), password_hash.encode("utf-8")
        ):
            print(f"   ✅ Hash verification successful!")
        else:
            print(f"   ❌ Hash verification failed!")
            return

        print(f"3. Updating user in DynamoDB...")

        # Update the user with the exact hash
        table.update_item(
            Key={"id": user_id},
            UpdateExpression="SET password_hash = :pwd, password_salt = :salt, isAdmin = :admin, is_active = :active, updatedAt = :updated",
            ExpressionAttributeValues={
                ":pwd": password_hash,
                ":salt": "",  # Modern bcrypt doesn't use separate salt
                ":admin": True,
                ":active": True,
                ":updated": datetime.utcnow().isoformat(),
            },
        )

        print(f"   ✅ User updated successfully!")

        print(f"\n4. Final verification...")

        # Get the updated user
        updated_response = table.query(
            IndexName="EmailIndex",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("email").eq(
                admin_email
            ),
        )

        if updated_response["Items"]:
            updated_user = updated_response["Items"][0]
            stored_hash = updated_user.get("password_hash", "")

            # Verify the stored hash
            if bcrypt.checkpw(
                admin_password.encode("utf-8"), stored_hash.encode("utf-8")
            ):
                print(f"   ✅ Final verification successful!")
                print(f"   ✅ Admin user is ready for login!")
                print(f"\n📋 Login Details:")
                print(f"   Email: {admin_email}")
                print(f"   Password: {admin_password}")
                print(
                    f"   API URL: https://2t9blvt2c1.execute-api.us-east-1.amazonaws.com/prod/auth/login"
                )
            else:
                print(f"   ❌ Final verification failed!")
        else:
            print(f"   ❌ Could not retrieve updated user!")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    fix_admin_password_exact()
