#!/usr/bin/env python3
"""
Simple script to verify RBAC system is working.
"""

import boto3
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def verify_rbac_system():
    """Verify the RBAC system is working correctly."""

    # Initialize DynamoDB
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table("people-registry-roles")

    logger.info("🔍 Verifying RBAC system...")

    # Test cases
    test_users = [
        {
            "user_id": "admin-cbba-cloud",
            "email": "admin@cbba.cloud.org.bo",
            "expected_role": "super_admin",
        },
        {
            "user_id": "admin-awsug-cbba",
            "email": "admin@awsugcbba.org",
            "expected_role": "super_admin",
        },
        {
            "user_id": "admin-sergio-rodriguez",
            "email": "sergio.rodriguez.inclan@gmail.com",
            "expected_role": "super_admin",
        },
    ]

    all_passed = True

    for user in test_users:
        try:
            # Test direct user_id lookup
            response = table.get_item(
                Key={"user_id": user["user_id"], "role_type": user["expected_role"]}
            )

            if "Item" in response:
                item = response["Item"]
                is_active = item.get("is_active", False)

                if is_active:
                    logger.info(
                        f"✅ {user['email']}: {user['expected_role']} role verified"
                    )
                else:
                    logger.error(f"❌ {user['email']}: Role exists but is inactive")
                    all_passed = False
            else:
                logger.error(
                    f"❌ {user['email']}: Expected role {user['expected_role']} not found"
                )
                all_passed = False

            # Test email-based lookup using GSI
            response = table.query(
                IndexName="email-index",
                KeyConditionExpression=boto3.dynamodb.conditions.Key("email").eq(
                    user["email"]
                ),
            )

            if response["Items"]:
                roles = [
                    item["role_type"]
                    for item in response["Items"]
                    if item.get("is_active", False)
                ]
                if user["expected_role"] in roles:
                    logger.info(f"✅ {user['email']}: Email-based lookup successful")
                else:
                    logger.error(f"❌ {user['email']}: Email-based lookup failed")
                    all_passed = False
            else:
                logger.error(f"❌ {user['email']}: No roles found via email lookup")
                all_passed = False

        except Exception as e:
            logger.error(f"❌ Error testing {user['email']}: {str(e)}")
            all_passed = False

    # Summary
    logger.info("\n" + "=" * 60)
    if all_passed:
        logger.info("🎉 RBAC SYSTEM VERIFICATION: PASSED")
        logger.info("✅ All admin users have correct roles")
        logger.info("✅ Both user_id and email lookups work")
        logger.info("✅ Ready to switch to admin_middleware_v2")

        logger.info("\n📋 NEXT STEPS:")
        logger.info("1. Update handler imports to use admin_middleware_v2")
        logger.info("2. Test admin endpoints with new middleware")
        logger.info("3. Remove hardcoded emails from admin_middleware.py")

    else:
        logger.error("❌ RBAC SYSTEM VERIFICATION: FAILED")
        logger.error("Please fix the issues above before proceeding")

    logger.info("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = verify_rbac_system()
    exit(0 if success else 1)
