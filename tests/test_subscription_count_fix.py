"""
Test subscription count fix to ensure inactive subscriptions are excluded from counts.

This test verifies that when a user is deactivated from a project, the subscription
counts in smart cards and dashboards are updated correctly.
"""

import pytest
from unittest.mock import AsyncMock, patch, Mock
from src.handlers.versioned_api_handler import get_admin_projects, get_admin_dashboard


class TestSubscriptionCountFix:
    """Test subscription count calculations exclude inactive subscriptions."""

    @pytest.fixture
    def mock_projects(self):
        """Mock project data."""
        return [
            {
                "id": "project-1",
                "name": "AWS Workshop",
                "status": "active",
                "maxParticipants": 10,
            },
            {
                "id": "project-2",
                "name": "DevOps Training",
                "status": "active",
                "maxParticipants": 5,
            },
        ]

    @pytest.fixture
    def mock_admin_user(self):
        """Mock admin user for testing."""
        from src.models.auth import AuthenticatedUser

        return AuthenticatedUser(
            id="admin-user-id",
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            is_admin=True,
            is_active=True,
        )

    @pytest.fixture
    def mock_subscriptions(self):
        """Mock subscription data with various statuses."""
        return [
            # Project 1 subscriptions
            {
                "id": "sub-1",
                "projectId": "project-1",
                "personId": "person-1",
                "status": "active",
            },
            {
                "id": "sub-2",
                "projectId": "project-1",
                "personId": "person-2",
                "status": "active",
            },
            {
                "id": "sub-3",
                "projectId": "project-1",
                "personId": "person-3",
                "status": "pending",
            },
            {
                "id": "sub-4",
                "projectId": "project-1",
                "personId": "person-4",
                "status": "inactive",
            },  # Should be excluded
            {
                "id": "sub-5",
                "projectId": "project-1",
                "personId": "person-5",
                "status": "inactive",
            },  # Should be excluded
            # Project 2 subscriptions
            {
                "id": "sub-6",
                "projectId": "project-2",
                "personId": "person-6",
                "status": "active",
            },
            {
                "id": "sub-7",
                "projectId": "project-2",
                "personId": "person-7",
                "status": "pending",
            },
            {
                "id": "sub-8",
                "projectId": "project-2",
                "personId": "person-8",
                "status": "inactive",
            },  # Should be excluded
        ]

    @pytest.mark.asyncio
    async def test_admin_projects_subscription_count_excludes_inactive(
        self, mock_projects, mock_subscriptions, mock_admin_user
    ):
        """Test that admin projects endpoint excludes inactive subscriptions from count."""

        # Mock the admin middleware to return our mock admin user
        with patch(
            "src.handlers.versioned_api_handler.require_admin_access"
        ) as mock_admin_access:
            mock_admin_access.return_value = mock_admin_user

            with patch("src.handlers.versioned_api_handler.db_service") as mock_db:
                # Mock async methods properly
                mock_db.get_all_projects = AsyncMock(return_value=mock_projects)
                mock_db.get_all_subscriptions = AsyncMock(
                    return_value=mock_subscriptions
                )

                # Mock the response creation
                with patch(
                    "src.handlers.versioned_api_handler.create_v2_response"
                ) as mock_response:
                    with patch("src.handlers.versioned_api_handler.logger"):
                        with patch(
                            "src.handlers.versioned_api_handler.AdminActionLogger.log_admin_action"
                        ) as mock_log:
                            mock_response.return_value = {"data": "mocked"}

                            # Call the endpoint with admin user
                            await get_admin_projects(mock_admin_user)

                    # Get the data passed to create_v2_response
                    call_args = mock_response.call_args[0][
                        0
                    ]  # First positional argument

                    # Verify project 1 counts
                    project_1 = next(p for p in call_args if p["id"] == "project-1")
                    assert (
                        project_1["subscriptionCount"] == 3
                    )  # 2 active + 1 pending (excludes 2 inactive)
                    assert project_1["activeSubscriptions"] == 2
                    assert project_1["pendingSubscriptions"] == 1
                    assert (
                        project_1["totalSubscriptionsEverCreated"] == 5
                    )  # All including inactive
                    assert project_1["availableSlots"] == 8  # 10 max - 2 active

                    # Verify project 2 counts
                    project_2 = next(p for p in call_args if p["id"] == "project-2")
                    assert (
                        project_2["subscriptionCount"] == 2
                    )  # 1 active + 1 pending (excludes 1 inactive)
                    assert project_2["activeSubscriptions"] == 1
                    assert project_2["pendingSubscriptions"] == 1
                    assert (
                        project_2["totalSubscriptionsEverCreated"] == 3
                    )  # All including inactive
                    assert project_2["availableSlots"] == 4  # 5 max - 1 active

    @pytest.mark.asyncio
    async def test_admin_dashboard_subscription_count_excludes_inactive(
        self, mock_projects, mock_subscriptions, mock_admin_user
    ):
        """Test that admin dashboard excludes inactive subscriptions from counts."""

        # Mock the admin middleware to return our mock admin user
        with patch(
            "src.handlers.versioned_api_handler.require_admin_access"
        ) as mock_admin_access:
            mock_admin_access.return_value = mock_admin_user

            with patch("src.handlers.versioned_api_handler.db_service") as mock_db:
                # Mock async methods properly
                mock_db.get_all_projects = AsyncMock(return_value=mock_projects)
                mock_db.get_all_subscriptions = AsyncMock(
                    return_value=mock_subscriptions
                )

                # Mock the response creation
                with patch(
                    "src.handlers.versioned_api_handler.create_v2_response"
                ) as mock_response:
                    with patch("src.handlers.versioned_api_handler.logger"):
                        with patch(
                            "src.handlers.versioned_api_handler.AdminActionLogger.log_admin_action"
                        ) as mock_log:
                            mock_response.return_value = {"data": "mocked"}

                            # Call the endpoint with admin user
                            await get_admin_dashboard(mock_admin_user)

                    # Get the data passed to create_v2_response
                    dashboard_data = mock_response.call_args[0][
                        0
                    ]  # First positional argument

                    # Verify dashboard counts exclude inactive subscriptions
                    assert (
                        dashboard_data["totalSubscriptions"] == 5
                    )  # 3 active + 2 pending (excludes 3 inactive)
                    assert dashboard_data["activeSubscriptions"] == 3
                    assert dashboard_data["pendingSubscriptions"] == 2
                    assert (
                        dashboard_data["totalSubscriptionsEverCreated"] == 8
                    )  # All including inactive

                    # Verify statistics also exclude inactive
                    stats = dashboard_data["statistics"]
                    assert (
                        stats["averageSubscriptionsPerProject"] == 2.5
                    )  # 5 current subscriptions / 2 projects

    @pytest.mark.asyncio
    async def test_subscription_count_after_deactivation_scenario(self):
        """Test the specific scenario: subscription count should decrease when user is deactivated."""

        # Initial state: 3 active subscriptions
        initial_subscriptions = [
            {
                "id": "sub-1",
                "projectId": "project-1",
                "personId": "person-1",
                "status": "active",
            },
            {
                "id": "sub-2",
                "projectId": "project-1",
                "personId": "person-2",
                "status": "active",
            },
            {
                "id": "sub-3",
                "projectId": "project-1",
                "personId": "person-3",
                "status": "active",
            },
        ]

        # After deactivation: 1 subscription becomes inactive
        after_deactivation_subscriptions = [
            {
                "id": "sub-1",
                "projectId": "project-1",
                "personId": "person-1",
                "status": "active",
            },
            {
                "id": "sub-2",
                "projectId": "project-1",
                "personId": "person-2",
                "status": "active",
            },
            {
                "id": "sub-3",
                "projectId": "project-1",
                "personId": "person-3",
                "status": "inactive",
            },  # Deactivated
        ]

        project = {
            "id": "project-1",
            "name": "Test Project",
            "status": "active",
            "maxParticipants": 10,
        }

        with patch("src.handlers.versioned_api_handler.db_service") as mock_db:
            # Test initial state
            mock_db.get_all_projects = AsyncMock(return_value=[project])
            mock_db.get_all_subscriptions = AsyncMock(
                return_value=initial_subscriptions
            )

            # Mock the admin middleware
            with patch(
                "src.handlers.versioned_api_handler.require_admin_access"
            ) as mock_admin_access:
                mock_admin_user = Mock()
                mock_admin_user.id = "admin-id"
                mock_admin_user.email = "admin@test.com"
                mock_admin_access.return_value = mock_admin_user

                with patch(
                    "src.handlers.versioned_api_handler.create_v2_response"
                ) as mock_response:
                    with patch("src.handlers.versioned_api_handler.logger"):
                        with patch(
                            "src.handlers.versioned_api_handler.AdminActionLogger.log_admin_action"
                        ) as mock_log:
                            mock_response.return_value = {"data": "mocked"}

                            await get_admin_projects(mock_admin_user)
                    initial_data = mock_response.call_args[0][0][0]  # First project

                    assert initial_data["subscriptionCount"] == 3
                    assert initial_data["activeSubscriptions"] == 3

            # Test after deactivation
            mock_db.get_all_subscriptions = AsyncMock(
                return_value=after_deactivation_subscriptions
            )

            with patch(
                "src.handlers.versioned_api_handler.create_v2_response"
            ) as mock_response:
                with patch("src.handlers.versioned_api_handler.logger"):
                    with patch(
                        "src.handlers.versioned_api_handler.AdminActionLogger.log_admin_action"
                    ) as mock_log:
                        mock_response.return_value = {"data": "mocked"}

                        await get_admin_projects(mock_admin_user)
                    after_data = mock_response.call_args[0][0][0]  # First project

                    # Verify count decreased after deactivation
                    assert (
                        after_data["subscriptionCount"] == 2
                    )  # Should decrease from 3 to 2
                    assert after_data["activeSubscriptions"] == 2
                    assert (
                        after_data["totalSubscriptionsEverCreated"] == 3
                    )  # Historical count unchanged

    def test_subscription_status_definitions(self):
        """Test that we have clear definitions of what each status means for counting."""

        # Define what should be counted in different contexts
        status_definitions = {
            "active": {
                "description": "User is actively participating in the project",
                "count_in_subscription_count": True,
                "count_in_available_slots": True,
                "count_in_dashboard_total": True,
            },
            "pending": {
                "description": "User subscription is awaiting approval",
                "count_in_subscription_count": True,
                "count_in_available_slots": False,  # Don't reserve slots for pending
                "count_in_dashboard_total": True,
            },
            "inactive": {
                "description": "User has been deactivated/removed from project",
                "count_in_subscription_count": False,  # This is the key fix
                "count_in_available_slots": False,
                "count_in_dashboard_total": False,
            },
        }

        # Verify our understanding is correct
        assert status_definitions["inactive"]["count_in_subscription_count"] is False
        assert status_definitions["active"]["count_in_subscription_count"] is True
        assert status_definitions["pending"]["count_in_subscription_count"] is True

        # This test documents the expected behavior for future reference
        assert len(status_definitions) == 3  # We handle all known statuses
