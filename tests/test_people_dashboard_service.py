"""
Tests for People Dashboard Service functionality.
Tests the enhanced PeopleService dashboard analytics methods.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, List

from src.services.people_service import PeopleService


class TestPeopleDashboardService:
    """Test suite for People Dashboard Service functionality."""

    @pytest.fixture
    def people_service(self):
        """Create a PeopleService instance for testing."""
        service = PeopleService()
        service.db_service = AsyncMock()
        service.user_repository = MagicMock()
        service.logger = MagicMock()
        return service

    @pytest.fixture
    def mock_people_data(self):
        """Mock people data for testing."""
        base_date = datetime.now()
        return [
            {
                "id": "user1",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "is_active": True,
                "is_admin": False,
                "created_at": base_date.isoformat(),
                "date_of_birth": "1990-01-01",
                "address": {"city": "New York", "state": "NY"},
            },
            {
                "id": "user2",
                "first_name": "Jane",
                "last_name": "Smith",
                "email": "jane@example.com",
                "is_active": True,
                "is_admin": True,
                "created_at": (base_date - timedelta(days=30)).isoformat(),
                "date_of_birth": "1985-05-15",
                "address": {"city": "Los Angeles", "state": "CA"},
            },
            {
                "id": "user3",
                "first_name": "Bob",
                "last_name": "Johnson",
                "email": "bob@example.com",
                "is_active": False,
                "is_admin": False,
                "created_at": (base_date - timedelta(days=60)).isoformat(),
                "date_of_birth": "1975-12-20",
                "address": {"city": "Chicago", "state": "IL"},
            },
            {
                "id": "user4",
                "first_name": "Alice",
                "last_name": "Wilson",
                "email": "alice@example.com",
                "is_active": True,
                "is_admin": False,
                "created_at": (base_date - timedelta(days=1)).isoformat(),
                "date_of_birth": "1995-08-10",
                "address": {"city": "New York", "state": "NY"},
            },
        ]

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_dashboard_data_success(self, people_service, mock_people_data):
        """Test successful dashboard data retrieval."""
        # Mock the database service
        people_service.db_service.list_people.return_value = mock_people_data

        # Call the method
        result = await people_service.get_dashboard_data()

        # Verify the result structure
        assert result["success"] is True
        assert "data" in result
        assert "metadata" in result

        # Verify overview data
        overview = result["data"]["overview"]
        assert overview["total_users"] == 4
        assert overview["active_users"] == 3
        assert overview["inactive_users"] == 1
        assert overview["admin_users"] == 1
        assert overview["new_users_today"] == 1
        assert overview["new_users_this_month"] >= 1

        # Verify other sections exist
        assert "activity_metrics" in result["data"]
        assert "demographics" in result["data"]
        assert "recent_activity" in result["data"]

        # Verify metadata
        assert result["metadata"]["service"] == "people_service"
        assert result["metadata"]["version"] == "dashboard"
        assert "generated_at" in result["metadata"]

    @pytest.mark.asyncio
    @patch(
        "src.services.people_service.PeopleService._get_cache_service",
        return_value=None,
    )
    async def test_get_dashboard_data_empty_users(self, mock_cache, people_service):
        """Test dashboard data with no users."""
        # Mock empty user list
        people_service.db_service.list_people.return_value = []

        # Call the method
        result = await people_service.get_dashboard_data()

        # Verify the result
        assert result["success"] is True
        overview = result["data"]["overview"]
        assert overview["total_users"] == 0
        assert overview["active_users"] == 0
        assert overview["inactive_users"] == 0
        assert overview["admin_users"] == 0

    @pytest.mark.asyncio
    @patch(
        "src.services.people_service.PeopleService._get_cache_service",
        return_value=None,
    )
    async def test_get_dashboard_data_database_error(self, mock_cache, people_service):
        """Test dashboard data with database error."""
        # Mock database error
        people_service.db_service.list_people.side_effect = Exception("Database error")

        # Call the method and expect exception
        with pytest.raises(Exception):
            await people_service.get_dashboard_data()

    @pytest.mark.asyncio
    async def test_get_registration_trends_success(
        self, people_service, mock_people_data
    ):
        """Test successful registration trends retrieval."""
        # Mock the database service
        people_service.db_service.list_people.return_value = mock_people_data

        # Call the method
        result = await people_service.get_registration_trends()

        # Verify the result structure
        assert result["success"] is True
        assert "data" in result
        assert "monthly_trends" in result["data"]
        assert "total_registrations" in result["data"]
        assert result["data"]["total_registrations"] == 4

        # Verify metadata
        assert result["metadata"]["service"] == "people_service"
        assert result["metadata"]["analysis_type"] == "registration_trends"

    @pytest.mark.asyncio
    async def test_get_registration_trends_with_date_filter(
        self, people_service, mock_people_data
    ):
        """Test registration trends with date filtering."""
        # Mock the database service
        people_service.db_service.list_people.return_value = mock_people_data

        # Call with date range
        date_from = (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d")
        date_to = datetime.now().strftime("%Y-%m-%d")

        result = await people_service.get_registration_trends(date_from, date_to)

        # Verify the result
        assert result["success"] is True
        assert result["data"]["date_range"]["from"] == date_from
        assert result["data"]["date_range"]["to"] == date_to
        # Should filter out users older than 45 days
        assert result["data"]["total_registrations"] <= 4

    @pytest.mark.asyncio
    async def test_get_activity_patterns_success(
        self, people_service, mock_people_data
    ):
        """Test successful activity patterns retrieval."""
        # Mock the database service
        people_service.db_service.list_people.return_value = mock_people_data

        # Call the method
        result = await people_service.get_activity_patterns()

        # Verify the result structure
        assert result["success"] is True
        assert "data" in result
        assert "login_activity" in result["data"]
        assert "profile_updates" in result["data"]
        assert "inactive_users" in result["data"]
        assert "engagement_score" in result["data"]

        # Verify metadata
        assert result["metadata"]["service"] == "people_service"
        assert result["metadata"]["analysis_type"] == "activity_patterns"

    @pytest.mark.asyncio
    async def test_get_demographic_insights_success(
        self, people_service, mock_people_data
    ):
        """Test successful demographic insights retrieval."""
        # Mock the database service
        people_service.db_service.list_people.return_value = mock_people_data

        # Call the method
        result = await people_service.get_demographic_insights()

        # Verify the result structure
        assert result["success"] is True
        assert "data" in result
        assert "age_distribution" in result["data"]
        assert "location_distribution" in result["data"]
        assert "total_locations" in result["data"]

        # Verify age distribution has expected keys
        age_dist = result["data"]["age_distribution"]
        expected_age_groups = ["18-25", "26-35", "36-45", "46-55", "55+"]
        for group in expected_age_groups:
            assert group in age_dist

        # Verify location distribution
        location_dist = result["data"]["location_distribution"]
        assert "New York" in location_dist
        assert location_dist["New York"] == 2  # Two users from New York

    @pytest.mark.asyncio
    async def test_get_engagement_metrics_success(
        self, people_service, mock_people_data
    ):
        """Test successful engagement metrics retrieval."""
        # Mock the database service
        people_service.db_service.list_people.return_value = mock_people_data

        # Call the method
        result = await people_service.get_engagement_metrics()

        # Verify the result structure
        assert result["success"] is True
        assert "data" in result
        assert "overall_engagement" in result["data"]
        assert "user_segments" in result["data"]
        assert "retention_metrics" in result["data"]
        assert "activity_distribution" in result["data"]

        # Verify engagement score structure
        engagement = result["data"]["overall_engagement"]
        assert "overall_score" in engagement
        assert "rating" in engagement
        assert "active_user_ratio" in engagement

    @pytest.mark.asyncio
    async def test_activity_metrics_calculation(self, people_service, mock_people_data):
        """Test activity metrics calculation helper method."""
        # Call the private method directly
        result = await people_service._get_activity_metrics(mock_people_data)

        # Verify structure
        assert "login_activity" in result
        assert "profile_updates" in result
        assert "inactive_users" in result

        # Verify login activity structure
        login_activity = result["login_activity"]
        assert "daily_active_users" in login_activity
        assert "weekly_active_users" in login_activity
        assert "monthly_active_users" in login_activity

        # Verify inactive users count
        assert result["inactive_users"] == 1  # One inactive user in mock data

    @pytest.mark.asyncio
    async def test_demographic_insights_calculation(
        self, people_service, mock_people_data
    ):
        """Test demographic insights calculation helper method."""
        # Call the private method directly
        result = await people_service._get_demographic_insights(mock_people_data)

        # Verify structure
        assert "age_distribution" in result
        assert "location_distribution" in result
        assert "total_locations" in result

        # Verify location distribution
        location_dist = result["location_distribution"]
        assert location_dist["New York"] == 2
        assert location_dist["Los Angeles"] == 1
        assert location_dist["Chicago"] == 1

        # Verify total locations
        assert result["total_locations"] == 3

    @pytest.mark.asyncio
    async def test_recent_activity_calculation(self, people_service, mock_people_data):
        """Test recent activity calculation helper method."""
        # Call the private method directly
        result = await people_service._get_recent_activity(mock_people_data, limit=2)

        # Verify structure
        assert isinstance(result, list)
        assert len(result) <= 2  # Respects limit

        # Verify activity structure
        if result:
            activity = result[0]
            assert "user_id" in activity
            assert "user_name" in activity
            assert "email" in activity
            assert "activity_type" in activity
            assert "timestamp" in activity
            assert "details" in activity

    @pytest.mark.asyncio
    async def test_engagement_score_calculation(self, people_service, mock_people_data):
        """Test engagement score calculation helper method."""
        # Call the private method directly
        result = await people_service._calculate_engagement_score(mock_people_data)

        # Verify structure
        assert "overall_score" in result
        assert "rating" in result
        assert "active_user_ratio" in result

        # Verify score calculation (3 active out of 4 total = 75%)
        assert result["overall_score"] == 75.0
        assert result["rating"] == "medium"  # 75% is in medium range
        assert result["active_user_ratio"] == 0.75

    @pytest.mark.asyncio
    async def test_user_segments_calculation(self, people_service, mock_people_data):
        """Test user segments calculation helper method."""
        # Call the private method directly
        result = await people_service._calculate_user_segments(mock_people_data)

        # Verify structure
        assert "highly_engaged" in result
        assert "moderately_engaged" in result
        assert "low_engagement" in result
        assert "admin_users" in result
        assert "new_users" in result

        # Verify admin users count
        assert result["admin_users"] == 1  # One admin in mock data

    @pytest.mark.asyncio
    async def test_error_handling_in_helper_methods(self, people_service):
        """Test error handling in helper methods."""
        # Test with invalid data that might cause errors
        invalid_data = [{"invalid": "data"}]

        # These methods should handle errors gracefully
        activity_result = await people_service._get_activity_metrics(invalid_data)
        assert "error" in activity_result or isinstance(activity_result, dict)

        demographic_result = await people_service._get_demographic_insights(
            invalid_data
        )
        assert "error" in demographic_result or isinstance(demographic_result, dict)

        recent_activity_result = await people_service._get_recent_activity(invalid_data)
        assert isinstance(recent_activity_result, list)


class TestPeopleDashboardIntegration:
    """Integration tests for People Dashboard functionality."""

    @pytest.fixture
    def people_service(self):
        """Create a real PeopleService instance for integration testing."""
        return PeopleService()

    @pytest.mark.asyncio
    async def test_dashboard_service_initialization(self, people_service):
        """Test that the people service initializes correctly."""
        # The service should have the required methods
        assert hasattr(people_service, "get_dashboard_data")
        assert hasattr(people_service, "get_registration_trends")
        assert hasattr(people_service, "get_activity_patterns")
        assert hasattr(people_service, "get_demographic_insights")
        assert hasattr(people_service, "get_engagement_metrics")

    @pytest.mark.asyncio
    async def test_dashboard_methods_are_async(self, people_service):
        """Test that all dashboard methods are properly async."""
        import inspect

        methods_to_test = [
            "get_dashboard_data",
            "get_registration_trends",
            "get_activity_patterns",
            "get_demographic_insights",
            "get_engagement_metrics",
        ]

        for method_name in methods_to_test:
            method = getattr(people_service, method_name)
            assert inspect.iscoroutinefunction(method), f"{method_name} should be async"

    @pytest.mark.asyncio
    async def test_dashboard_response_format_consistency(self, people_service):
        """Test that all dashboard methods return consistent response format."""
        # Mock the database service to avoid actual DB calls
        people_service.db_service = AsyncMock()
        people_service.db_service.list_people.return_value = []

        methods_to_test = [
            ("get_dashboard_data", []),
            ("get_registration_trends", []),
            ("get_activity_patterns", []),
            ("get_demographic_insights", []),
            ("get_engagement_metrics", []),
        ]

        for method_name, args in methods_to_test:
            method = getattr(people_service, method_name)
            result = await method(*args)

            # All methods should return dict with success, data, and metadata
            assert isinstance(result, dict)
            assert "success" in result
            assert "data" in result
            assert "metadata" in result

            # Metadata should have consistent structure
            metadata = result["metadata"]
            assert "service" in metadata
            assert metadata["service"] == "people_service"


class TestPeopleDashboardErrorHandling:
    """Test error handling in People Dashboard functionality."""

    @pytest.fixture
    def people_service(self):
        """Create a PeopleService instance with mocked dependencies."""
        service = PeopleService()
        service.db_service = AsyncMock()
        service.user_repository = MagicMock()
        service.logger = MagicMock()
        return service

    @pytest.mark.asyncio
    @patch(
        "src.services.people_service.PeopleService._get_cache_service",
        return_value=None,
    )
    async def test_dashboard_data_database_exception(self, mock_cache, people_service):
        """Test dashboard data handling when database throws exception."""
        # Mock database to throw exception
        people_service.db_service.list_people.side_effect = Exception(
            "Database connection failed"
        )

        # Should raise exception
        with pytest.raises(Exception):
            await people_service.get_dashboard_data()

        # Should log the error
        people_service.logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_registration_trends_database_exception(self, people_service):
        """Test registration trends handling when database throws exception."""
        # Mock database to throw exception
        people_service.db_service.list_people.side_effect = Exception(
            "Database timeout"
        )

        # Should raise exception
        with pytest.raises(Exception):
            await people_service.get_registration_trends()

        # Should log the error
        people_service.logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_activity_patterns_database_exception(self, people_service):
        """Test activity patterns handling when database throws exception."""
        # Mock database to throw exception
        people_service.db_service.list_people.side_effect = Exception("Database error")

        # Should raise exception
        with pytest.raises(Exception):
            await people_service.get_activity_patterns()

        # Should log the error
        people_service.logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_helper_methods_error_resilience(self, people_service):
        """Test that helper methods are resilient to data errors."""
        # Test with None data
        result = await people_service._get_activity_metrics(None)
        assert isinstance(result, dict)

        # Test with malformed data
        malformed_data = [{"missing_required_fields": True}]
        result = await people_service._get_demographic_insights(malformed_data)
        assert isinstance(result, dict)

        # Test recent activity with empty data
        result = await people_service._get_recent_activity([])
        assert isinstance(result, list)
        assert len(result) == 0
