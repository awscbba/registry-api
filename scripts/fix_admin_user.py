#!/usr/bin/env python3
"""
Fix admin user with correct credentials.
"""

import boto3
import json
from datetime import datetime
import bcrypt
import uuid


def fix_admin_user():
    """Fix admin user with correct credentials."""

    print("🔧 Fixing Admin User")
    print("=" * 50)

    # Correct admin credentials
    admin_email = "admin@awsugcbba.org"
    admin_password = "awsugcbba2025"

    try:
        # Initialize DynamoDB
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.Table("PeopleTable")

        print(f"1. Checking for existing user: {admin_email}")

        # Query by email using EmailIndex GSI
        response = table.query(
            IndexName="EmailIndex",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("email").eq(
                admin_email
            ),
        )

        if response["Items"]:
            # User exists, update password and admin status
            user = response["Items"][0]
            user_id = user["id"]

            print(f"   ✅ Found existing user!")
            print(f"      ID: {user_id}")
            print(
                f"      Name: {user.get('firstName', 'N/A')} {user.get('lastName', 'N/A')}"
            )
            print(f"      Current Admin Status: {user.get('isAdmin', False)}")

            # Hash the correct password
            password_hash = bcrypt.hashpw(
                admin_password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")

            print(f"2. Updating user with correct password and admin status...")

            # Update the user
            table.update_item(
                Key={"id": user_id},
                UpdateExpression="SET password_hash = :pwd, isAdmin = :admin, is_active = :active, updatedAt = :updated",
                ExpressionAttributeValues={
                    ":pwd": password_hash,
                    ":admin": True,
                    ":active": True,
                    ":updated": datetime.utcnow().isoformat(),
                },
            )

            print(f"   ✅ User updated successfully!")

        else:
            # User doesn't exist, create new admin user
            print(f"   ❌ User not found. Creating new admin user...")

            user_id = str(uuid.uuid4())
            password_hash = bcrypt.hashpw(
                admin_password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")
            now = datetime.utcnow().isoformat()

            item = {
                "id": user_id,
                "firstName": "Admin",
                "lastName": "User",
                "email": admin_email,
                "phone": "000-000-0000",
                "dateOfBirth": "1990-01-01",
                "address": {
                    "street": "Admin Street",
                    "city": "Admin City",
                    "state": "Admin State",
                    "postalCode": "00000",
                    "country": "Bolivia",
                },
                "isAdmin": True,
                "is_active": True,
                "password_hash": password_hash,
                "password_salt": "",
                "createdAt": now,
                "updatedAt": now,
            }

            table.put_item(Item=item)
            print(f"   ✅ New admin user created!")

        print(f"\n3. Verifying password hash...")

        # Verify the password works
        if bcrypt.checkpw(
            admin_password.encode("utf-8"), password_hash.encode("utf-8")
        ):
            print(f"   ✅ Password verification successful!")
        else:
            print(f"   ❌ Password verification failed!")

        print(f"\n✅ Admin user is ready!")
        print(f"   Email: {admin_email}")
        print(f"   Password: {admin_password}")
        print(f"   Admin Status: True")
        print(f"   Active Status: True")

        print(f"\n🔗 You can now login at:")
        print(
            f"   https://2t9blvt2c1.execute-api.us-east-1.amazonaws.com/prod/auth/login"
        )
        print(f"   with email: {admin_email}")
        print(f"   and password: {admin_password}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    fix_admin_user()
