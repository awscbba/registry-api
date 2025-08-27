"""
Global pytest configuration and fixtures.
Sets up Python path for all tests to import from src directory.
"""

import sys
import os
from pathlib import Path
import pytest
from moto import mock_aws
import boto3

# Add the project root and src directory to Python path
project_root = Path(__file__).parent
src_dir = project_root / "src"

# Add both paths to ensure imports work
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(src_dir))

# Also add the src directory as a module path
if str(src_dir) not in sys.path:
    sys.path.append(str(src_dir))

# Set up environment for tests
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

# Standardized V2 tables for tests
os.environ.setdefault("PEOPLE_TABLE_V2_NAME", "test-people-table-v2")
os.environ.setdefault("PROJECTS_TABLE_V2_NAME", "test-projects-table-v2")
os.environ.setdefault("SUBSCRIPTIONS_TABLE_V2_NAME", "test-subscriptions-table-v2")

# Legacy tables (for migration compatibility)
os.environ.setdefault("PEOPLE_TABLE_NAME", "test-people-table")
os.environ.setdefault("PROJECTS_TABLE_NAME", "test-projects-table")
os.environ.setdefault("SUBSCRIPTIONS_TABLE_NAME", "test-subscriptions-table")
os.environ.setdefault("AUDIT_TABLE_NAME", "test-audit-table")
os.environ.setdefault("LOCKOUT_TABLE_NAME", "test-lockout-table")
os.environ.setdefault("AUTH_FUNCTION_NAME", "test-auth-function")
os.environ.setdefault("API_FUNCTION_NAME", "test-api-function")

# Set fake AWS credentials for testing
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")


@pytest.fixture(scope="function", autouse=True)
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"


@pytest.fixture(scope="function")
def dynamodb_mock():
    """Mock DynamoDB for tests."""
    with mock_aws():
        # Create mock DynamoDB resource
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        # Create test tables
        tables_to_create = [
            ("test-people-table", "id"),  # The actual key used in the code
            ("test-projects-table", "id"),  # Likely also uses "id"
            ("test-subscriptions-table", "id"),  # Likely also uses "id"
            ("test-audit-table", "id"),  # Likely also uses "id"
            ("test-lockout-table", "email"),  # This one uses email as key
        ]

        for table_name, key_name in tables_to_create:
            try:
                dynamodb.create_table(
                    TableName=table_name,
                    KeySchema=[{"AttributeName": key_name, "KeyType": "HASH"}],
                    AttributeDefinitions=[
                        {"AttributeName": key_name, "AttributeType": "S"}
                    ],
                    BillingMode="PAY_PER_REQUEST",
                )
            except Exception as e:
                # Table might already exist
                pass

        yield dynamodb
