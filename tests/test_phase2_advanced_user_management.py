"""
Test Phase 2 Advanced User Management functionality.
Tests for import, communication, history, and saved search features.
"""

import pytest
import asyncio
import io
import pandas as pd
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.services.people_service import PeopleService
from src.models.person import PersonCreate


class TestPhase2AdvancedUserManagement:
    """Test suite for Phase 2 Advanced User Management features."""

    @pytest.fixture
    def people_service(self):
        """Create a PeopleService instance for testing."""
        service = PeopleService()
        return service

    @pytest.fixture
    def mock_file_csv(self):
        """Create a mock CSV file for testing."""
        csv_content = """name,email,phone,city,country
John Doe,john.doe@example.com,+1234567890,New York,USA
Jane Smith,jane.smith@example.com,+0987654321,London,UK
Bob Johnson,bob.johnson@example.com,,Toronto,Canada
Alice Brown,alice.brown@example.com,+1122334455,Sydney,Australia"""

        mock_file = Mock()
        mock_file.filename = "test_users.csv"
        mock_file.read = AsyncMock(return_value=csv_content.encode("utf-8"))
        return mock_file

    @pytest.fixture
    def mock_file_excel(self):
        """Create a mock Excel file for testing."""
        # Create a simple Excel file in memory
        df = pd.DataFrame(
            {
                "name": ["John Doe", "Jane Smith", "Bob Johnson"],
                "email": [
                    "john.doe@example.com",
                    "jane.smith@example.com",
                    "bob.johnson@example.com",
                ],
                "phone": ["+1234567890", "+0987654321", ""],
                "city": ["New York", "London", "Toronto"],
                "country": ["USA", "UK", "Canada"],
            }
        )

        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_content = excel_buffer.getvalue()

        mock_file = Mock()
        mock_file.filename = "test_users.xlsx"
        mock_file.read = AsyncMock(return_value=excel_content)
        return mock_file

    @pytest.fixture
    def mock_admin_user(self):
        """Create a mock admin user for testing."""
        return {
            "id": "admin_001",
            "name": "Test Admin",
            "email": "admin@example.com",
            "role": "admin",
        }

    # Import Functionality Tests

    @pytest.mark.asyncio
    async def test_import_users_csv_validation_only(
        self, people_service, mock_file_csv
    ):
        """Test CSV import with validation only mode."""
        result = await people_service.import_users_from_file(
            file=mock_file_csv, validate_only=True, imported_by="admin_001"
        )

        assert result["success"] is True
        assert result["validation_only"] is True
        assert result["processed_count"] == 4
        assert result["success_count"] > 0
        assert "errors" in result
        assert "import_timestamp" in result

    @pytest.mark.asyncio
    async def test_import_users_excel_validation_only(
        self, people_service, mock_file_excel
    ):
        """Test Excel import with validation only mode."""
        result = await people_service.import_users_from_file(
            file=mock_file_excel, validate_only=True, imported_by="admin_001"
        )

        assert result["success"] is True
        assert result["validation_only"] is True
        assert result["processed_count"] == 3
        assert result["success_count"] > 0

    @pytest.mark.asyncio
    async def test_import_users_invalid_file_format(self, people_service):
        """Test import with invalid file format."""
        mock_file = Mock()
        mock_file.filename = "test.txt"
        mock_file.read = AsyncMock(return_value=b"invalid content")

        result = await people_service.import_users_from_file(
            file=mock_file, validate_only=True
        )

        assert result["success"] is False
        assert "Unsupported file format" in result["error"]

    @pytest.mark.asyncio
    async def test_import_users_missing_required_columns(self, people_service):
        """Test import with missing required columns."""
        csv_content = """phone,city,country
+1234567890,New York,USA"""

        mock_file = Mock()
        mock_file.filename = "invalid.csv"
        mock_file.read = AsyncMock(return_value=csv_content.encode("utf-8"))

        result = await people_service.import_users_from_file(
            file=mock_file, validate_only=True
        )

        assert result["success"] is False
        assert "Missing required columns" in result["error"]
        assert "name" in result["error"]
        assert "email" in result["error"]

    @pytest.mark.asyncio
    async def test_import_users_with_validation_errors(self, people_service):
        """Test import with validation errors in data."""
        csv_content = """name,email,phone
John Doe,invalid-email,+1234567890
,jane.smith@example.com,+0987654321
Bob Johnson,bob@example.com,"""

        mock_file = Mock()
        mock_file.filename = "errors.csv"
        mock_file.read = AsyncMock(return_value=csv_content.encode("utf-8"))

        result = await people_service.import_users_from_file(
            file=mock_file, validate_only=True
        )

        assert result["success"] is True
        assert result["error_count"] > 0
        assert len(result["errors"]) > 0
        assert any(
            "Invalid email format" in error["error"] for error in result["errors"]
        )

    @pytest.mark.asyncio
    @patch("src.services.people_service.PeopleService.get_person_by_email")
    @patch("src.services.people_service.PeopleService.create_person_v2")
    async def test_import_users_actual_import(
        self, mock_create, mock_get_email, people_service, mock_file_csv
    ):
        """Test actual user import (not validation only)."""
        # Mock no existing users
        mock_get_email.return_value = {"success": False}

        # Mock successful user creation
        mock_create.return_value = {"success": True, "data": {"id": "user_001"}}

        result = await people_service.import_users_from_file(
            file=mock_file_csv, validate_only=False, imported_by="admin_001"
        )

        assert result["success"] is True
        assert result["validation_only"] is False
        assert result["success_count"] > 0
        assert "created_user_ids" in result

    # Communication Functionality Tests

    @pytest.mark.asyncio
    @patch("src.services.people_service.PeopleService.get_person_by_id_v2")
    async def test_send_communication_email(
        self, mock_get_user, people_service, mock_admin_user
    ):
        """Test sending email communication."""
        # Mock valid users
        mock_get_user.return_value = {
            "success": True,
            "data": {"id": "user_001", "name": "Test User"},
        }

        result = await people_service.send_communication(
            communication_type="email",
            subject="Test Email",
            content="This is a test email message.",
            target_users=["user_001", "user_002"],
            sender=mock_admin_user,
        )

        assert result["success"] is True
        assert result["type"] == "email"
        assert result["target_count"] == 2
        assert result["sent_count"] >= 0
        assert "communication_id" in result
        assert "delivery_summary" in result

    @pytest.mark.asyncio
    async def test_send_communication_invalid_type(
        self, people_service, mock_admin_user
    ):
        """Test sending communication with invalid type."""
        result = await people_service.send_communication(
            communication_type="invalid_type",
            subject="Test",
            content="Test content",
            target_users=["user_001"],
            sender=mock_admin_user,
        )

        assert result["success"] is False
        assert "Invalid communication type" in result["error"]

    @pytest.mark.asyncio
    @patch("src.services.people_service.PeopleService.get_person_by_id_v2")
    async def test_send_communication_no_valid_users(
        self, mock_get_user, people_service, mock_admin_user
    ):
        """Test sending communication with no valid target users."""
        # Mock no valid users found
        mock_get_user.return_value = {"success": False}

        result = await people_service.send_communication(
            communication_type="email",
            subject="Test",
            content="Test content",
            target_users=["invalid_user"],
            sender=mock_admin_user,
        )

        assert result["success"] is False
        assert "No valid target users found" in result["error"]

    @pytest.mark.asyncio
    @patch("src.services.people_service.PeopleService.get_person_by_id_v2")
    async def test_send_communication_with_metadata(
        self, mock_get_user, people_service, mock_admin_user
    ):
        """Test sending communication with metadata."""
        mock_get_user.return_value = {"success": True, "data": {"id": "user_001"}}

        metadata = {"campaign_id": "camp_001", "source": "admin_panel"}

        result = await people_service.send_communication(
            communication_type="notification",
            subject="Test Notification",
            content="Test content",
            target_users=["user_001"],
            sender=mock_admin_user,
            metadata=metadata,
        )

        assert result["success"] is True
        assert result["type"] == "notification"

    # Communication History Tests

    @pytest.mark.asyncio
    async def test_get_communication_history_basic(self, people_service):
        """Test getting basic communication history."""
        result = await people_service.get_communication_history()

        assert result["success"] is True
        assert "communications" in result
        assert "pagination" in result
        assert "summary" in result
        assert isinstance(result["communications"], list)

    @pytest.mark.asyncio
    async def test_get_communication_history_with_filters(self, people_service):
        """Test getting communication history with filters."""
        result = await people_service.get_communication_history(
            communication_type="email",
            date_from="2024-01-01",
            date_to="2024-12-31",
            admin_user_id="admin_001",
            page=1,
            limit=10,
        )

        assert result["success"] is True
        assert result["pagination"]["page"] == 1
        assert result["pagination"]["limit"] == 10
        assert "filters_applied" in result
        assert result["filters_applied"]["communication_type"] == "email"

    @pytest.mark.asyncio
    async def test_get_communication_history_pagination(self, people_service):
        """Test communication history pagination."""
        result = await people_service.get_communication_history(page=2, limit=5)

        assert result["success"] is True
        assert result["pagination"]["page"] == 2
        assert result["pagination"]["limit"] == 5
        assert "has_next" in result["pagination"]
        assert "has_previous" in result["pagination"]

    # Saved Search Tests

    @pytest.mark.asyncio
    async def test_save_search_query_basic(self, people_service):
        """Test saving a basic search query."""
        criteria = {
            "query": "test search",
            "status": ["active"],
            "sort_by": "created_at",
        }

        result = await people_service.save_search_query(
            name="Test Search", criteria=criteria, admin_user_id="admin_001"
        )

        assert result["success"] is True
        assert result["saved_search"]["name"] == "Test Search"
        assert result["saved_search"]["criteria"] == criteria
        assert result["saved_search"]["admin_user_id"] == "admin_001"
        assert "search_id" in result["saved_search"]

    @pytest.mark.asyncio
    async def test_save_search_query_shared(self, people_service):
        """Test saving a shared search query."""
        criteria = {"status": ["active", "inactive"], "location": "New York"}

        result = await people_service.save_search_query(
            name="Shared Search",
            criteria=criteria,
            admin_user_id="admin_001",
            is_shared=True,
        )

        assert result["success"] is True
        assert result["saved_search"]["is_shared"] is True
        assert "tags" in result["saved_search"]

    @pytest.mark.asyncio
    async def test_save_search_query_empty_criteria(self, people_service):
        """Test saving search query with empty criteria."""
        result = await people_service.save_search_query(
            name="Empty Search", criteria={}, admin_user_id="admin_001"
        )

        assert result["success"] is False
        assert "Search criteria cannot be empty" in result["error"]

    @pytest.mark.asyncio
    async def test_extract_search_tags(self, people_service):
        """Test search tag extraction functionality."""
        criteria = {
            "query": "test",
            "status": ["active", "inactive"],
            "registration_date_from": "2024-01-01",
            "location": "New York",
            "age_range": {"min": 18, "max": 65},
            "has_projects": True,
        }

        tags = people_service._extract_search_tags(criteria)

        assert "text-search" in tags
        assert "status:active" in tags
        assert "status:inactive" in tags
        assert "date-filter" in tags
        assert "location-filter" in tags
        assert "age-filter" in tags
        assert "project-filter" in tags

    # Integration Tests

    @pytest.mark.asyncio
    async def test_phase2_integration_workflow(
        self, people_service, mock_file_csv, mock_admin_user
    ):
        """Test complete Phase 2 workflow integration."""
        # 1. Import users (validation only)
        import_result = await people_service.import_users_from_file(
            file=mock_file_csv, validate_only=True, imported_by=mock_admin_user["id"]
        )
        assert import_result["success"] is True

        # 2. Save a search query
        search_criteria = {"query": "test", "status": ["active"]}
        save_result = await people_service.save_search_query(
            name="Integration Test Search",
            criteria=search_criteria,
            admin_user_id=mock_admin_user["id"],
        )
        assert save_result["success"] is True

        # 3. Get communication history
        history_result = await people_service.get_communication_history(
            admin_user_id=mock_admin_user["id"]
        )
        assert history_result["success"] is True

    # Error Handling Tests

    @pytest.mark.asyncio
    async def test_import_pandas_not_available(self, people_service, mock_file_csv):
        """Test import when pandas is not available."""
        with patch(
            "src.services.people_service.pd",
            side_effect=ImportError("pandas not available"),
        ):
            result = await people_service.import_users_from_file(
                file=mock_file_csv, validate_only=True
            )

            assert result["success"] is False
            assert "pandas library not available" in result["error"]

    @pytest.mark.asyncio
    async def test_communication_exception_handling(
        self, people_service, mock_admin_user
    ):
        """Test communication error handling."""
        with patch(
            "src.services.people_service.PeopleService.get_person_by_id_v2",
            side_effect=Exception("Database error"),
        ):
            result = await people_service.send_communication(
                communication_type="email",
                subject="Test",
                content="Test",
                target_users=["user_001"],
                sender=mock_admin_user,
            )

            assert result["success"] is False
            assert "Communication failed" in result["error"]

    @pytest.mark.asyncio
    async def test_history_exception_handling(self, people_service):
        """Test communication history error handling."""
        with patch(
            "src.services.people_service.datetime", side_effect=Exception("Date error")
        ):
            result = await people_service.get_communication_history()

            assert result["success"] is False
            assert "Failed to retrieve communication history" in result["error"]

    @pytest.mark.asyncio
    async def test_save_search_exception_handling(self, people_service):
        """Test save search error handling."""
        with patch(
            "src.services.people_service.uuid.uuid4",
            side_effect=Exception("UUID error"),
        ):
            result = await people_service.save_search_query(
                name="Test", criteria={"query": "test"}, admin_user_id="admin_001"
            )

            assert result["success"] is False
            assert "Failed to save search query" in result["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
