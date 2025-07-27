import pytest
from datetime import datetime
from src.models.person import Person, PersonCreate, PersonUpdate, Address


def test_person_create():
    """Test PersonCreate model"""
    address = Address(
        street="123 Main St",
        city="Anytown",
        state="CA",
        zipCode="12345",
        country="USA"
    )

    person_data = PersonCreate(
        firstName="John",
        lastName="Doe",
        email="john.doe@example.com",
        phone="+1-555-123-4567",
        dateOfBirth="1990-01-01",
        address=address
    )

    assert person_data.first_name == "John"
    assert person_data.last_name == "Doe"
    assert person_data.email == "john.doe@example.com"
    assert person_data.phone == "+1-555-123-4567"
    assert person_data.date_of_birth == "1990-01-01"
    assert person_data.address.street == "123 Main St"


def test_person_create_new():
    """Test Person.create_new method"""
    address = Address(
        street="123 Main St",
        city="Anytown",
        state="CA",
        zipCode="12345",
        country="USA"
    )

    person_data = PersonCreate(
        firstName="Jane",
        lastName="Smith",
        email="jane.smith@example.com",
        phone="+1-555-987-6543",
        dateOfBirth="1985-05-15",
        address=address
    )

    person = Person.create_new(person_data)

    assert person.id is not None
    assert len(person.id) == 36  # UUID length
    assert person.first_name == "Jane"
    assert person.last_name == "Smith"
    assert person.email == "jane.smith@example.com"
    assert isinstance(person.created_at, datetime)
    assert isinstance(person.updated_at, datetime)


def test_person_update():
    """Test PersonUpdate model"""
    person_update = PersonUpdate(
        firstName="Updated Name",
        email="updated@example.com"
    )

    assert person_update.first_name == "Updated Name"
    assert person_update.email == "updated@example.com"
    assert person_update.last_name is None
    assert person_update.phone is None
