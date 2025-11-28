"""
People service - Business logic for people/users operations.
Orchestrates repository operations and implements business rules.
"""

from typing import List, Optional

from ..repositories.people_repository import PeopleRepository
from ..models.person import Person, PersonCreate, PersonUpdate, PersonResponse


class PeopleService:
    """Service for people/users business logic."""

    def __init__(self, people_repository: PeopleRepository):
        self.people_repository = people_repository

    def create_person(self, person_data: PersonCreate) -> PersonResponse:
        """Create a new person with enterprise security validation."""
        from ..services.logging_service import logging_service, LogCategory, LogLevel
        from ..security.input_validator import InputValidator
        from ..exceptions.base_exceptions import (
            ValidationException,
            BusinessLogicException,
            ErrorCode,
        )
        from ..utils.password_utils import hash_and_validate_password

        # Validate email format
        email_result = InputValidator.validate_email(person_data.email)
        if not email_result.is_valid:
            logging_service.log_security_event(
                event_type="invalid_email_format",
                severity="medium",
                details={"email": person_data.email, "errors": email_result.errors},
            )
            raise ValidationException(
                message=f"Invalid email format: {', '.join(email_result.errors)}",
                error_code=ErrorCode.VALIDATION_ERROR,
            )

        # Check if email already exists
        if self.people_repository.email_exists(person_data.email):
            logging_service.log_data_operation(
                operation="create",
                resource_type="person",
                success=False,
                details={"email": person_data.email, "reason": "duplicate_email"},
            )
            raise BusinessLogicException(
                message=f"Email {person_data.email} is already in use",
                error_code=ErrorCode.DUPLICATE_RESOURCE,
            )

        # Hash password if provided
        if person_data.password and not person_data.passwordHash:
            is_valid, hashed_password, validation_errors = hash_and_validate_password(
                person_data.password
            )
            if not is_valid:
                raise ValidationException(
                    message=f"Password validation failed: {', '.join(validation_errors)}",
                    error_code=ErrorCode.VALIDATION_ERROR,
                )
            person_data.passwordHash = hashed_password

        # Log person creation attempt
        logging_service.log_data_operation(
            operation="create",
            resource_type="person",
            success=True,
            details={"email": email_result.sanitized_data},
        )

        # Create person
        person = self.people_repository.create(person_data)

        # Convert to response model
        return PersonResponse(**person.model_dump())

    def get_person(self, person_id: str) -> Optional[PersonResponse]:
        """Get a person by ID."""
        person = self.people_repository.get_by_id(person_id)
        if not person:
            return None

        return PersonResponse(**person.model_dump())

    async def get_person_by_email(self, email: str) -> Optional[PersonResponse]:
        """Get a person by email address."""
        person = self.people_repository.get_by_email(email)
        if not person:
            return None

        return PersonResponse(**person.model_dump())

    def update_person(
        self, person_id: str, updates: PersonUpdate
    ) -> Optional[PersonResponse]:
        """Update a person with business validation."""
        # If updating email, check for duplicates
        if updates.email:
            existing_person = self.people_repository.get_by_email(updates.email)
            if existing_person and existing_person.id != person_id:
                raise ValueError(f"Email {updates.email} is already in use")

        # Update person
        person = self.people_repository.update(person_id, updates)
        if not person:
            return None

        return PersonResponse(**person.model_dump())

    def delete_person(self, person_id: str, requesting_user_id: str) -> bool:
        """Delete a person with business rule validation."""
        from ..services.logging_service import logging_service, LogCategory, LogLevel
        from ..exceptions.base_exceptions import BusinessLogicException, ErrorCode

        # Check if person exists
        person = self.people_repository.get_by_id(person_id)
        if not person:
            raise BusinessLogicException(
                message="Person not found", error_code=ErrorCode.RESOURCE_NOT_FOUND
            )

        # Business rule: Check for active subscriptions
        try:
            from ..services.service_registry_manager import get_subscriptions_service

            subscriptions_service = get_subscriptions_service()

            # Get user's subscriptions
            subscriptions = subscriptions_service.get_person_subscriptions(person_id)
            active_subscriptions = [
                sub
                for sub in subscriptions
                if sub.status.lower() in ["active", "pending"]
            ]

            if active_subscriptions:
                logging_service.log_structured(
                    level=LogLevel.WARNING,
                    category=LogCategory.USER_OPERATIONS,
                    message=f"Attempted to delete person {person_id} with active subscriptions",
                    additional_data={
                        "person_id": person_id,
                        "requesting_user_id": requesting_user_id,
                        "active_subscriptions_count": len(active_subscriptions),
                    },
                )

                raise BusinessLogicException(
                    message="Cannot delete person with active subscriptions",
                    error_code=ErrorCode.BUSINESS_RULE_VIOLATION,
                    details={
                        "active_subscriptions": len(active_subscriptions),
                        "subscription_ids": [
                            sub.get("id") for sub in active_subscriptions
                        ],
                    },
                )

        except BusinessLogicException:
            raise
        except Exception as e:
            # Log error but don't fail deletion for subscription check failure
            logging_service.log_structured(
                level=LogLevel.WARNING,
                category=LogCategory.USER_OPERATIONS,
                message=f"Failed to check subscriptions for person {person_id}: {str(e)}",
                additional_data={"person_id": person_id, "error": str(e)},
            )

        # Log deletion attempt
        logging_service.log_data_operation(
            operation="delete",
            resource_type="person",
            resource_id=person_id,
            user_id=requesting_user_id,
            success=True,
            details={"email": person.email},
        )

        # Delete the person from database
        person_deleted = self.people_repository.delete(person_id)

        if person_deleted:
            # Clean up orphaned subscriptions after successful person deletion
            try:
                subscriptions = subscriptions_service.get_person_subscriptions(
                    person_id
                )
                for subscription in subscriptions:
                    subscriptions_service.delete_subscription(subscription.id)
                    logging_service.log_structured(
                        level=LogLevel.INFO,
                        category=LogCategory.USER_OPERATIONS,
                        message=f"Deleted orphaned subscription {subscription.id} for deleted person {person_id}",
                        additional_data={
                            "person_id": person_id,
                            "subscription_id": subscription.id,
                            "project_id": subscription.projectId,
                        },
                    )
            except Exception as e:
                # Log error but don't fail the person deletion
                logging_service.log_structured(
                    level=LogLevel.WARNING,
                    category=LogCategory.USER_OPERATIONS,
                    message=f"Failed to clean up subscriptions for deleted person {person_id}: {str(e)}",
                    additional_data={"person_id": person_id, "error": str(e)},
                )

        return person_deleted

    def list_people(self, limit: Optional[int] = None) -> List[PersonResponse]:
        """List all people."""
        people = self.people_repository.list_all(limit)
        return [PersonResponse(**person.model_dump()) for person in people]

    def list_people_paginated(
        self,
        page: int = 1,
        page_size: int = 10,
        sort_by: Optional[str] = None,
        sort_direction: str = "asc",
        search: Optional[str] = None,
        filters: Optional[dict] = None,
    ) -> tuple[List[PersonResponse], int]:
        """
        List people with enterprise pagination, sorting, and filtering.

        Returns:
            tuple: (people_responses, total_count)
        """
        from ..services.logging_service import logging_service, LogCategory, LogLevel

        # Log pagination request
        logging_service.log_structured(
            level=LogLevel.INFO,
            category=LogCategory.USER_OPERATIONS,
            message="Paginated people list requested",
            additional_data={
                "page": page,
                "page_size": page_size,
                "sort_by": sort_by,
                "sort_direction": sort_direction,
                "has_search": search is not None,
                "has_filters": filters is not None and len(filters) > 0,
            },
        )

        try:
            people, total_count = self.people_repository.list_paginated(
                page=page,
                page_size=page_size,
                sort_by=sort_by,
                sort_direction=sort_direction,
                search=search,
                filters=filters,
            )

            # Convert to response format
            people_responses = [
                PersonResponse(**person.model_dump()) for person in people
            ]

            # Log successful pagination
            logging_service.log_structured(
                level=LogLevel.INFO,
                category=LogCategory.USER_OPERATIONS,
                message="Paginated people list retrieved successfully",
                additional_data={
                    "page": page,
                    "page_size": page_size,
                    "returned_items": len(people_responses),
                    "total_items": total_count,
                },
            )

            return people_responses, total_count

        except Exception as e:
            # Log pagination error
            logging_service.log_structured(
                level=LogLevel.ERROR,
                category=LogCategory.ERROR_HANDLING,
                message=f"Paginated people list failed: {str(e)}",
                additional_data={"page": page, "page_size": page_size, "error": str(e)},
            )
            raise

    def check_email_exists(self, email: str) -> bool:
        """Check if an email address is already in use."""
        return self.people_repository.email_exists(email)

    async def update_admin_status(
        self, person_id: str, is_admin: bool
    ) -> Optional[PersonResponse]:
        """Update a person's admin status."""
        person = self.people_repository.update_admin_status(person_id, is_admin)
        if not person:
            return None

        return PersonResponse(**person.model_dump())

    async def activate_person(self, person_id: str) -> Optional[PersonResponse]:
        """Activate a person's account."""
        person = self.people_repository.activate_person(person_id)
        if not person:
            return None

        return PersonResponse(**person.model_dump())

    async def deactivate_person(self, person_id: str) -> Optional[PersonResponse]:
        """Deactivate a person's account."""
        person = self.people_repository.deactivate_person(person_id)
        if not person:
            return None

        return PersonResponse(**person.model_dump())

    async def unlock_account(self, person_id: str) -> dict:
        """Unlock a person's account."""
        person = self.people_repository.activate_person(person_id)
        if not person:
            raise ValueError("Person not found")

        return {"unlocked": True, "personId": person_id}
