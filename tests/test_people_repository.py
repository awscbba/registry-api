"""Tests for People Repository - Core data operations"""

import pytest
from unittest.mock import Mock, patch
from src.repositories.people_repository import PeopleRepository
from src.models.person import PersonCreate, Person


class TestPeopleRepository:
    """Test People Repository functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.people_repository = PeopleRepository()
        self.people_repository.db = Mock()

    def test_create_person_success(self):
        """Test successful person creation"""
        # Arrange
        person_data = PersonCreate(
            firstName="John", lastName="Doe", email="john.doe@example.com"
        )

        mock_response = {
            "id": "person123",
            "firstName": "John",
            "lastName": "Doe",
            "email": "john.doe@example.com",
        }

        self.people_repository.db.put_item.return_value = mock_response

        # Act
        result = self.people_repository.create(person_data)

        # Assert
        assert isinstance(result, Person)
        assert result.id == "person123"
        assert result.firstName == "John"
        self.people_repository.db.put_item.assert_called_once()

    def test_get_by_id_success(self):
        """Test getting person by ID"""
        # Arrange
        person_id = "person123"
        mock_response = {
            "id": "person123",
            "firstName": "John",
            "lastName": "Doe",
            "email": "john.doe@example.com",
        }

        self.people_repository.db.get_item.return_value = mock_response

        # Act
        result = self.people_repository.get_by_id(person_id)

        # Assert
        assert isinstance(result, Person)
        assert result.id == "person123"
        self.people_repository.db.get_item.assert_called_once_with(person_id)

    def test_get_by_id_not_found(self):
        """Test getting person by ID when not found"""
        # Arrange
        person_id = "nonexistent"
        self.people_repository.db.get_item.return_value = None

        # Act
        result = self.people_repository.get_by_id(person_id)

        # Assert
        assert result is None

    def test_get_by_email_success(self):
        """Test getting person by email"""
        # Arrange
        email = "john.doe@example.com"
        mock_response = {
            "id": "person123",
            "firstName": "John",
            "lastName": "Doe",
            "email": email,
        }

        self.people_repository.db.query_by_email.return_value = mock_response

        # Act
        result = self.people_repository.get_by_email(email)

        # Assert
        assert isinstance(result, Person)
        assert result.email == email

    def test_list_all_success(self):
        """Test listing all people"""
        # Arrange
        mock_response = [
            {
                "id": "person1",
                "firstName": "John",
                "lastName": "Doe",
                "email": "john@example.com",
            },
            {
                "id": "person2",
                "firstName": "Jane",
                "lastName": "Smith",
                "email": "jane@example.com",
            },
        ]

        self.people_repository.db.scan.return_value = mock_response

        # Act
        result = self.people_repository.list_all()

        # Assert
        assert len(result) == 2
        assert all(isinstance(person, Person) for person in result)

    def test_update_person_success(self):
        """Test updating person"""
        # Arrange
        person_id = "person123"
        update_data = {"firstName": "Johnny"}

        mock_response = {
            "id": "person123",
            "firstName": "Johnny",
            "lastName": "Doe",
            "email": "john.doe@example.com",
        }

        self.people_repository.db.update_item.return_value = mock_response

        # Act
        result = self.people_repository.update(person_id, update_data)

        # Assert
        assert isinstance(result, Person)
        assert result.firstName == "Johnny"

    def test_delete_person_success(self):
        """Test deleting person"""
        # Arrange
        person_id = "person123"
        self.people_repository.db.delete_item.return_value = True

        # Act
        result = self.people_repository.delete(person_id)

        # Assert
        assert result is True
        self.people_repository.db.delete_item.assert_called_once_with(person_id)

    def test_people_repository_initialization(self):
        """Test people repository initializes correctly"""
        # Act
        repository = PeopleRepository()

        # Assert
        assert hasattr(repository, "db")
