"""
Pytest configuration and fixtures for the versioned API handler tests.
"""

import pytest
import os
import sys
from unittest.mock import AsyncMock, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Set environment variables to avoid AWS connection issues during testing
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_SECURITY_TOKEN"] = "testing"
os.environ["AWS_SESSION_TOKEN"] = "testing"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment variables and configurations"""
    # Set test-specific environment variables
    os.environ["TEST_ADMIN_EMAIL"] = "test-admin@example.com"
    os.environ["JWT_SECRET"] = "test-jwt-secret"
    os.environ["JWT_EXPIRATION_HOURS"] = "1"
    
    # Ensure we're in test mode
    os.environ["TESTING"] = "true"
    
    yield
    
    # Cleanup after tests
    test_vars = ["TEST_ADMIN_EMAIL", "JWT_SECRET", "JWT_EXPIRATION_HOURS", "TESTING"]
    for var in test_vars:
        if var in os.environ:
            del os.environ[var]


@pytest.fixture
def mock_person():
    """Mock person object for testing"""
    person = MagicMock()
    person.id = "test-person-id"
    person.email = "test@example.com"
    person.first_name = "Test"
    person.last_name = "User"
    person.is_admin = False
    person.dict.return_value = {
        "id": "test-person-id",
        "email": "test@example.com",
        "firstName": "Test",
        "lastName": "User",
        "isAdmin": False
    }
    return person


@pytest.fixture
def mock_admin_person():
    """Mock admin person object for testing"""
    person = MagicMock()
    person.id = "admin-person-id"
    person.email = "admin@example.com"
    person.first_name = "Admin"
    person.last_name = "User"
    person.is_admin = True
    person.dict.return_value = {
        "id": "admin-person-id",
        "email": "admin@example.com",
        "firstName": "Admin",
        "lastName": "User",
        "isAdmin": True
    }
    return person


@pytest.fixture
def mock_project():
    """Mock project object for testing"""
    return {
        "id": "test-project-id",
        "name": "Test Project",
        "description": "A test project",
        "status": "active"
    }


@pytest.fixture
def mock_subscription():
    """Mock subscription object for testing"""
    return {
        "id": "test-subscription-id",
        "projectId": "test-project-id",
        "personId": "test-person-id",
        "status": "active",
        "notes": "Test subscription"
    }


@pytest.fixture
def sample_person_data():
    """Sample person data for testing"""
    return {
        "firstName": "John",
        "lastName": "Doe",
        "email": "john.doe@example.com",
        "phone": "+1-555-123-4567",
        "dateOfBirth": "1990-01-01",
        "address": {
            "street": "123 Main St",
            "city": "Anytown",
            "state": "CA",
            "zipCode": "12345",
            "country": "USA"
        }
    }


@pytest.fixture
def sample_subscription_data(sample_person_data):
    """Sample subscription data for testing"""
    return {
        "person": sample_person_data,
        "projectId": "test-project-id",
        "notes": "Test subscription notes"
    }


@pytest.fixture
def comprehensive_db_mock():
    """Comprehensive database service mock with all methods configured"""
    mock = MagicMock()
    
    # Configure async methods
    mock.get_all_subscriptions = AsyncMock(return_value=[])
    mock.get_all_projects = AsyncMock(return_value=[])
    mock.get_person_by_email = AsyncMock(return_value=None)
    mock.create_person = AsyncMock(return_value=MagicMock(id="new-person-id"))
    mock.create_subscription = AsyncMock(return_value={"id": "new-subscription-id"})
    mock.get_subscriptions_by_person = AsyncMock(return_value=[])
    mock.get_all_people = AsyncMock(return_value=[])
    mock.get_person_by_id = AsyncMock(return_value=None)
    mock.update_person = AsyncMock(return_value=MagicMock(id="updated-person-id"))
    
    # Configure sync methods
    mock.get_project_by_id = MagicMock(return_value={"id": "test-project-id", "name": "Test Project"})
    
    return mock


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "async_test: mark test as testing async functionality"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically"""
    for item in items:
        # Add async_test marker to tests that test async functionality
        if "async" in item.name.lower() or "await" in item.name.lower():
            item.add_marker(pytest.mark.async_test)
        
        # Add integration marker to integration tests
        if "integration" in item.name.lower() or "test_integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add unit marker to unit tests (default)
        if not any(marker.name in ["integration", "slow"] for marker in item.iter_markers()):
            item.add_marker(pytest.mark.unit)


# Custom assertions
def assert_response_success(response, expected_status=200):
    """Assert that a response is successful"""
    assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}: {response.text}"


def assert_response_error(response, expected_status, expected_message=None):
    """Assert that a response is an error with expected status and message"""
    assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}"
    
    if expected_message:
        data = response.json()
        assert expected_message in data.get("detail", ""), f"Expected '{expected_message}' in error detail"


def assert_has_version(data, expected_version):
    """Assert that response data has the expected version"""
    assert "version" in data, "Response should include version field"
    assert data["version"] == expected_version, f"Expected version {expected_version}, got {data.get('version')}"


# Make custom assertions available globally
pytest.assert_response_success = assert_response_success
pytest.assert_response_error = assert_response_error
pytest.assert_has_version = assert_has_version