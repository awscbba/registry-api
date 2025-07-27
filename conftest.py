"""
Global pytest configuration and fixtures for the registry API tests.
"""
import os
import pytest
from moto import mock_aws
import boto3


@pytest.fixture(scope="session", autouse=True)
def setup_aws_environment():
    """Set up AWS environment variables for testing."""
    # Set default AWS region if not already set
    if not os.environ.get('AWS_DEFAULT_REGION'):
        os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

    if not os.environ.get('AWS_REGION'):
        os.environ['AWS_REGION'] = 'us-east-1'

    # Set dummy AWS credentials for testing
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'


@pytest.fixture(scope="function")
def mock_dynamodb_tables():
    """Create mock DynamoDB tables for testing."""
    with mock_aws():
        # Create a mock DynamoDB resource
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

        # Create the main people table
        people_table = dynamodb.create_table(
            TableName='PeopleTable',
            KeySchema=[
                {
                    'AttributeName': 'id',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'email',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST',
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'EmailIndex',
                    'KeySchema': [
                        {
                            'AttributeName': 'email',
                            'KeyType': 'HASH'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    }
                }
            ]
        )

        # Create audit logs table
        audit_table = dynamodb.create_table(
            TableName='AuditLogsTable',
            KeySchema=[
                {
                    'AttributeName': 'id',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        # Create account lockout table
        lockout_table = dynamodb.create_table(
            TableName='AccountLockoutTable',
            KeySchema=[
                {
                    'AttributeName': 'personId',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'personId',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        # Create projects table
        projects_table = dynamodb.create_table(
            TableName='ProjectsTable',
            KeySchema=[
                {
                    'AttributeName': 'id',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        # Create subscriptions table
        subscriptions_table = dynamodb.create_table(
            TableName='SubscriptionsTable',
            KeySchema=[
                {
                    'AttributeName': 'id',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        # Wait for tables to be created
        people_table.wait_until_exists()
        audit_table.wait_until_exists()
        lockout_table.wait_until_exists()
        projects_table.wait_until_exists()
        subscriptions_table.wait_until_exists()

        yield {
            'people_table': people_table,
            'audit_table': audit_table,
            'lockout_table': lockout_table,
            'projects_table': projects_table,
            'subscriptions_table': subscriptions_table
        }


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up environment variables for each test."""
    # Set table names
    os.environ['PEOPLE_TABLE_NAME'] = 'PeopleTable'
    os.environ['AUDIT_TABLE_NAME'] = 'AuditLogsTable'
    os.environ['LOCKOUT_TABLE_NAME'] = 'AccountLockoutTable'
    os.environ['PROJECTS_TABLE_NAME'] = 'ProjectsTable'
    os.environ['SUBSCRIPTIONS_TABLE_NAME'] = 'SubscriptionsTable'

    # Set JWT secret for testing
    os.environ['JWT_SECRET'] = 'test-secret-key-for-testing-only'

    yield

    # Cleanup is handled automatically by pytest
