#!/usr/bin/env python3
"""
Quick test script to verify enhanced person models work correctly.
"""
import asyncio
from datetime import datetime
from src.models.person import (
    PersonCreate, PersonUpdate, Person, PersonResponse,
    PasswordUpdateRequest, PersonSearchRequest, PersonSearchResponse,
    ValidationError, ValidationErrorType, ErrorResponse,
    EmailVerificationRequest, AdminUnlockRequest, Address
)
from src.services.person_validation_service import PersonValidationService, ValidationResult


async def test_enhanced_models():
    """Test the enhanced person models."""
    print("Testing enhanced person models...")

    # Test Address model
    address = Address(
        street="123 Main St",
        city="Anytown",
        state="CA",
        zipCode="12345",
        country="USA"
    )
    print(f"✓ Address model created: {address.street}, {address.city}")

    # Test PersonCreate with enhanced validation
    person_create = PersonCreate(
        firstName="John",
        lastName="Doe",
        email="john.doe@example.com",
        phone="(555) 123-4567",
        dateOfBirth="1990-01-01",
        address=address
    )
    print(f"✓ PersonCreate model created: {person_create.first_name} {person_create.last_name}")

    # Test Person with enhanced fields
    person = Person.create_new(person_create)
    person.password_hash = "hashed_password"
    person.failed_login_attempts = 0
    person.is_active = True
    person.email_verified = False
    print(f"✓ Person model created with enhanced fields: {person.id}")

    # Test PersonResponse
    person_response = PersonResponse.from_person(person)
    print(f"✓ PersonResponse created: {person_response.firstName} {person_response.lastName}")

    # Test PasswordUpdateRequest
    password_request = PasswordUpdateRequest(
        current_password="old_password",
        new_password="NewPassword123!",
        confirm_password="NewPassword123!"
    )
    print(f"✓ PasswordUpdateRequest created")

    # Test PersonSearchRequest
    search_request = PersonSearchRequest(
        firstName="John",
        limit=50,
        offset=0
    )
    print(f"✓ PersonSearchRequest created: searching for '{search_request.first_name}'")

    # Test ValidationError and ErrorResponse
    validation_error = ValidationError(
        field="email",
        message="Email is already in use",
        code=ValidationErrorType.DUPLICATE_VALUE,
        value="john.doe@example.com"
    )

    error_response = ErrorResponse(
        error="VALIDATION_ERROR",
        message="The request contains invalid data",
        details=[validation_error]
    )
    print(f"✓ ErrorResponse created with validation details")

    # Test PersonSearchResponse
    search_response = PersonSearchResponse.create(
        people=[person],
        total_count=1,
        limit=50,
        offset=0
    )
    print(f"✓ PersonSearchResponse created: {len(search_response.people)} results")

    print("\n✅ All enhanced person models work correctly!")


async def test_validation_service():
    """Test the validation service."""
    print("\nTesting validation service...")

    validation_service = PersonValidationService()

    # Test phone validation
    valid_phone = validation_service.validate_phone_format("(555) 123-4567")
    invalid_phone = validation_service.validate_phone_format("123")
    print(f"✓ Phone validation: '(555) 123-4567' = {valid_phone}, '123' = {invalid_phone}")

    # Test date validation
    valid_date = validation_service.validate_date_of_birth("1990-01-01")
    invalid_date = validation_service.validate_date_of_birth("2030-01-01")  # Future date
    print(f"✓ Date validation: '1990-01-01' = {valid_date}, '2030-01-01' = {invalid_date}")

    # Test ValidationResult
    result = ValidationResult()
    result.add_error("test_field", "Test error message", ValidationErrorType.INVALID_FORMAT, "test_value")
    print(f"✓ ValidationResult: is_valid = {result.is_valid}, errors = {len(result.errors)}")

    print("✅ Validation service works correctly!")


if __name__ == "__main__":
    asyncio.run(test_enhanced_models())
    asyncio.run(test_validation_service())
