#!/usr/bin/env python3
"""
Simple diagnostic script to check admin login issues.
"""

import boto3
import json
from datetime import datetime
import bcrypt


def check_admin_users():
    """Check admin users in DynamoDB."""

    print("🔍 Checking Admin Users in DynamoDB")
    print("=" * 50)

    try:
        # Initialize DynamoDB
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.Table("PeopleTable")

        # Test both possible admin emails
        admin_emails = ["admin@awsugcbba.org", "admin@cbba.cloud.org.bo"]

        found_admin = False

        for email in admin_emails:
            print(f"\n1. Checking user: {email}")

            try:
                # Query by email using EmailIndex GSI
                response = table.query(
                    IndexName="EmailIndex",
                    KeyConditionExpression=boto3.dynamodb.conditions.Key("email").eq(
                        email
                    ),
                )

                if response["Items"]:
                    user = response["Items"][0]
                    print(f"   ✅ Found user!")
                    print(f"      ID: {user.get('id', 'N/A')}")
                    print(
                        f"      Name: {user.get('firstName', 'N/A')} {user.get('lastName', 'N/A')}"
                    )
                    print(f"      Email: {user.get('email', 'N/A')}")
                    print(f"      Is Admin: {user.get('isAdmin', False)}")
                    print(
                        f"      Has Password Hash: {'password_hash' in user and user['password_hash'] is not None}"
                    )
                    print(f"      Is Active: {user.get('is_active', True)}")

                    if user.get("isAdmin", False):
                        found_admin = True
                        print(f"   🎯 This is an admin user!")

                        # Test password verification
                        if "password_hash" in user and user["password_hash"]:
                            test_passwords = ["admin123", "AdminPassword123!"]
                            for pwd in test_passwords:
                                try:
                                    if bcrypt.checkpw(
                                        pwd.encode("utf-8"),
                                        user["password_hash"].encode("utf-8"),
                                    ):
                                        print(f"   ✅ Password '{pwd}' matches!")
                                    else:
                                        print(f"   ❌ Password '{pwd}' does not match")
                                except Exception as e:
                                    print(
                                        f"   ❌ Error testing password '{pwd}': {str(e)}"
                                    )
                        else:
                            print(f"   ❌ No password hash found!")
                else:
                    print(f"   ❌ User not found")

            except Exception as e:
                print(f"   ❌ Error querying user: {str(e)}")

        if not found_admin:
            print(f"\n❌ No admin user found! Creating one...")
            create_admin_user(table)

    except Exception as e:
        print(f"❌ Error accessing DynamoDB: {str(e)}")
        print("   Make sure you have AWS credentials configured")


def create_admin_user(table):
    """Create admin user in DynamoDB."""

    admin_email = "admin@awsugcbba.org"
    admin_password = "admin123"

    print(f"\n2. Creating admin user: {admin_email}")

    try:
        import uuid

        # Hash the password
        password_hash = bcrypt.hashpw(
            admin_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        # Create user item
        user_id = str(uuid.uuid4())
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

        # Put item in table
        table.put_item(Item=item)

        print(f"   ✅ Admin user created successfully!")
        print(f"      ID: {user_id}")
        print(f"      Email: {admin_email}")
        print(f"      Password: {admin_password}")
        print(f"      Password Hash: {password_hash[:50]}...")

    except Exception as e:
        print(f"   ❌ Error creating admin user: {str(e)}")


if __name__ == "__main__":
    check_admin_users()
