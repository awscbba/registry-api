#!/usr/bin/env python3
"""
Script to create DynamoDB tables required for the database-driven RBAC system.
"""

import boto3
import logging
import sys
import os
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_roles_table(dynamodb_client, table_name="people-registry-roles"):
    """Create the roles table for RBAC system."""
    try:
        logger.info(f"Creating roles table: {table_name}")

        table = dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": "email", "KeyType": "HASH"},  # Partition key
                {"AttributeName": "role_type", "KeyType": "RANGE"},  # Sort key
            ],
            AttributeDefinitions=[
                {"AttributeName": "email", "AttributeType": "S"},
                {"AttributeName": "role_type", "AttributeType": "S"},
                {"AttributeName": "user_id", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "UserIdIndex",
                    "KeySchema": [{"AttributeName": "user_id", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                    "BillingMode": "PAY_PER_REQUEST",
                }
            ],
            BillingMode="PAY_PER_REQUEST",
            Tags=[
                {"Key": "Environment", "Value": os.getenv("ENVIRONMENT", "dev")},
                {"Key": "Project", "Value": "people-registry"},
                {"Key": "Component", "Value": "rbac-system"},
            ],
        )

        # Wait for table to be created
        logger.info(f"Waiting for table {table_name} to be created...")
        waiter = dynamodb_client.get_waiter("table_exists")
        waiter.wait(TableName=table_name)

        logger.info(f"✅ Successfully created roles table: {table_name}")
        return True

    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            logger.info(f"✅ Table {table_name} already exists")
            return True
        else:
            logger.error(f"❌ Error creating roles table: {e}")
            return False


def create_audit_logs_table(dynamodb_client, table_name="people-registry-audit-logs"):
    """Create the audit logs table for RBAC system."""
    try:
        logger.info(f"Creating audit logs table: {table_name}")

        table = dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": "log_id", "KeyType": "HASH"},  # Partition key
            ],
            AttributeDefinitions=[
                {"AttributeName": "log_id", "AttributeType": "S"},
                {"AttributeName": "timestamp", "AttributeType": "S"},
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "action", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "TimestampIndex",
                    "KeySchema": [{"AttributeName": "timestamp", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                    "BillingMode": "PAY_PER_REQUEST",
                },
                {
                    "IndexName": "UserIdIndex",
                    "KeySchema": [{"AttributeName": "user_id", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                    "BillingMode": "PAY_PER_REQUEST",
                },
                {
                    "IndexName": "ActionIndex",
                    "KeySchema": [{"AttributeName": "action", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                    "BillingMode": "PAY_PER_REQUEST",
                },
            ],
            BillingMode="PAY_PER_REQUEST",
            Tags=[
                {"Key": "Environment", "Value": os.getenv("ENVIRONMENT", "dev")},
                {"Key": "Project", "Value": "people-registry"},
                {"Key": "Component", "Value": "rbac-audit"},
            ],
        )

        # Wait for table to be created
        logger.info(f"Waiting for table {table_name} to be created...")
        waiter = dynamodb_client.get_waiter("table_exists")
        waiter.wait(TableName=table_name)

        logger.info(f"✅ Successfully created audit logs table: {table_name}")
        return True

    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            logger.info(f"✅ Table {table_name} already exists")
            return True
        else:
            logger.error(f"❌ Error creating audit logs table: {e}")
            return False


def verify_tables(dynamodb_client):
    """Verify that the tables were created successfully."""
    tables_to_check = ["people-registry-roles", "people-registry-audit-logs"]

    for table_name in tables_to_check:
        try:
            response = dynamodb_client.describe_table(TableName=table_name)
            status = response["Table"]["TableStatus"]
            logger.info(f"✅ Table {table_name} status: {status}")

            # Check indexes
            if "GlobalSecondaryIndexes" in response["Table"]:
                for index in response["Table"]["GlobalSecondaryIndexes"]:
                    index_name = index["IndexName"]
                    index_status = index["IndexStatus"]
                    logger.info(f"  📊 Index {index_name} status: {index_status}")

        except ClientError as e:
            logger.error(f"❌ Error checking table {table_name}: {e}")
            return False

    return True


def main():
    """Main function to create all required tables."""
    logger.info("🚀 Starting RBAC system DynamoDB tables creation...")

    # Get AWS region
    region = os.getenv("AWS_REGION", "us-east-1")
    logger.info(f"Using AWS region: {region}")

    # Initialize DynamoDB client
    try:
        dynamodb_client = boto3.client("dynamodb", region_name=region)
        logger.info("✅ Successfully initialized DynamoDB client")
    except Exception as e:
        logger.error(f"❌ Failed to initialize DynamoDB client: {e}")
        sys.exit(1)

    # Create tables
    success = True

    # Create roles table
    if not create_roles_table(dynamodb_client):
        success = False

    # Create audit logs table
    if not create_audit_logs_table(dynamodb_client):
        success = False

    # Verify tables
    if success:
        logger.info("🔍 Verifying table creation...")
        if verify_tables(dynamodb_client):
            logger.info("🎉 All RBAC system tables created successfully!")
            logger.info("\n📋 Next steps:")
            logger.info(
                "1. Run the migration script: python scripts/migrate_admin_roles.py"
            )
            logger.info("2. Update handlers to use admin_middleware_v2")
            logger.info("3. Test the new RBAC system")
            logger.info("4. Remove hardcoded admin emails from admin_middleware.py")
        else:
            logger.error("❌ Table verification failed")
            sys.exit(1)
    else:
        logger.error("❌ Failed to create some tables")
        sys.exit(1)


if __name__ == "__main__":
    main()
