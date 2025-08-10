#!/usr/bin/env python3
"""
Simple script to manually migrate admin users to the roles table.
"""

import boto3
import logging
from datetime import datetime
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def migrate_admin_users():
    """Manually insert admin users into the roles table."""

    # Initialize DynamoDB
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table("people-registry-roles")

    # Admin users to migrate
    admin_users = [
        {
            "email": "admin@cbba.cloud.org.bo",
            "user_id": "admin-cbba-cloud",
            "role_type": "super_admin",
            "notes": "Migrated from hardcoded admin list - Original system admin",
        },
        {
            "email": "admin@awsugcbba.org",
            "user_id": "admin-awsug-cbba",
            "role_type": "super_admin",
            "notes": "Migrated from hardcoded admin list - AWS User Group Cochabamba admin",
        },
        {
            "email": "sergio.rodriguez.inclan@gmail.com",
            "user_id": "admin-sergio-rodriguez",
            "role_type": "super_admin",
            "notes": "Migrated from hardcoded admin list - System administrator",
        },
    ]

    current_time = datetime.utcnow().isoformat()

    for admin in admin_users:
        try:
            # Check if role already exists
            response = table.get_item(
                Key={"user_id": admin["user_id"], "role_type": admin["role_type"]}
            )

            if "Item" in response:
                logger.info(
                    f"✅ Role already exists for {admin['email']} ({admin['role_type']})"
                )
                continue

            # Insert the role
            table.put_item(
                Item={
                    "user_id": admin["user_id"],
                    "role_type": admin["role_type"],
                    "email": admin["email"],
                    "assigned_by": "system-migration",
                    "assigned_at": current_time,
                    "is_active": True,
                    "notes": admin["notes"],
                }
            )

            logger.info(
                f"✅ Successfully migrated {admin['email']} as {admin['role_type']}"
            )

        except Exception as e:
            logger.error(f"❌ Error migrating {admin['email']}: {str(e)}")

    # Verify the migration
    logger.info("\n🔍 Verifying migration...")

    for admin in admin_users:
        try:
            response = table.get_item(
                Key={"user_id": admin["user_id"], "role_type": admin["role_type"]}
            )

            if "Item" in response:
                item = response["Item"]
                logger.info(
                    f"✅ {admin['email']}: {item['role_type']} (active: {item.get('is_active', False)})"
                )
            else:
                logger.error(f"❌ {admin['email']}: Role not found!")

        except Exception as e:
            logger.error(f"❌ Error verifying {admin['email']}: {str(e)}")

    logger.info("\n🎉 Migration completed!")


if __name__ == "__main__":
    migrate_admin_users()
