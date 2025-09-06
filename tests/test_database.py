"""Tests for Database - Core database operations"""

import pytest
from unittest.mock import Mock, patch
from src.core.database import DatabaseClient


class TestDatabaseClient:
    """Test DatabaseClient functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        with patch("boto3.resource") as mock_boto3:
            self.mock_dynamodb = Mock()
            mock_boto3.return_value = self.mock_dynamodb
            self.database = DatabaseClient()

    def test_database_initialization(self):
        """Test database initializes correctly"""
        # Assert
        assert hasattr(self.database, "dynamodb")

    def test_put_item_success(self):
        """Test successful item creation"""
        # Arrange
        mock_table = Mock()
        self.mock_dynamodb.Table.return_value = mock_table
        mock_table.put_item.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}

        item_data = {"id": "test123", "name": "Test Item"}

        # Act
        result = self.database.put_item(item_data)

        # Assert
        assert result == item_data
        mock_table.put_item.assert_called_once()

    def test_get_item_success(self):
        """Test successful item retrieval"""
        # Arrange
        mock_table = Mock()
        self.mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {
            "Item": {"id": "test123", "name": "Test Item"}
        }

        item_id = "test123"

        # Act
        result = self.database.get_item(item_id)

        # Assert
        assert result == {"id": "test123", "name": "Test Item"}
        mock_table.get_item.assert_called_once_with(Key={"id": item_id})

    def test_get_item_not_found(self):
        """Test item retrieval when not found"""
        # Arrange
        mock_table = Mock()
        self.mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {}

        item_id = "nonexistent"

        # Act
        result = self.database.get_item(item_id)

        # Assert
        assert result is None

    def test_scan_success(self):
        """Test successful table scan"""
        # Arrange
        mock_table = Mock()
        self.mock_dynamodb.Table.return_value = mock_table
        mock_table.scan.return_value = {
            "Items": [
                {"id": "item1", "name": "Item 1"},
                {"id": "item2", "name": "Item 2"},
            ]
        }

        # Act
        result = self.database.scan()

        # Assert
        assert len(result) == 2
        assert result[0]["id"] == "item1"
        mock_table.scan.assert_called_once()

    def test_update_item_success(self):
        """Test successful item update"""
        # Arrange
        mock_table = Mock()
        self.mock_dynamodb.Table.return_value = mock_table
        mock_table.update_item.return_value = {
            "Attributes": {"id": "test123", "name": "Updated Item"}
        }

        item_id = "test123"
        update_data = {"name": "Updated Item"}

        # Act
        result = self.database.update_item(item_id, update_data)

        # Assert
        assert result == {"id": "test123", "name": "Updated Item"}
        mock_table.update_item.assert_called_once()

    def test_delete_item_success(self):
        """Test successful item deletion"""
        # Arrange
        mock_table = Mock()
        self.mock_dynamodb.Table.return_value = mock_table
        mock_table.delete_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200}
        }

        item_id = "test123"

        # Act
        result = self.database.delete_item(item_id)

        # Assert
        assert result is True
        mock_table.delete_item.assert_called_once_with(Key={"id": item_id})

    def test_query_by_email_success(self):
        """Test querying by email"""
        # Arrange
        mock_table = Mock()
        self.mock_dynamodb.Table.return_value = mock_table
        mock_table.query.return_value = {
            "Items": [{"id": "user123", "email": "user@example.com"}]
        }

        email = "user@example.com"

        # Act
        result = self.database.query_by_email(email)

        # Assert
        assert result == {"id": "user123", "email": "user@example.com"}
        mock_table.query.assert_called_once()

    def test_health_check_success(self):
        """Test database health check"""
        # Arrange
        mock_table = Mock()
        self.mock_dynamodb.Table.return_value = mock_table
        mock_table.table_status = "ACTIVE"

        # Act
        result = self.database.health_check()

        # Assert
        assert result is True

    def test_health_check_failure(self):
        """Test database health check failure"""
        # Arrange
        mock_table = Mock()
        self.mock_dynamodb.Table.return_value = mock_table
        mock_table.table_status = "CREATING"

        # Act
        result = self.database.health_check()

        # Assert
        assert result is False
