"""
People repository implementation.
Handles all data access operations for people/users.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from .base_repository import BaseRepository
from ..core.database import db
from ..models.person import Person, PersonCreate, PersonUpdate


class PeopleRepository(BaseRepository[Person]):
    """Repository for people/users data access operations."""

    def __init__(self):
        from ..core.config import config

        self.table_name = config.database.people_table

    def create(self, person_data: PersonCreate) -> Person:
        """Create a new person in the database with input validation."""
        from ..security.input_validator import InputValidator
        from ..services.logging_service import logging_service, LogCategory, LogLevel

        # Validate inputs before database operation
        email_result = InputValidator.validate_email(person_data.email)
        if not email_result.is_valid:
            logging_service.log_security_event(
                event_type="invalid_email_format",
                severity="medium",
                details={"email": person_data.email, "errors": email_result.errors},
            )
            raise ValueError(f"Invalid email: {', '.join(email_result.errors)}")

        # Validate string fields
        for field_name, field_value in [
            ("firstName", person_data.firstName),
            ("lastName", person_data.lastName),
            ("phone", person_data.phone or ""),
        ]:
            if field_value:
                result = InputValidator.validate_and_sanitize_string(
                    field_value, max_length=100
                )
                if not result.is_valid:
                    raise ValueError(
                        f"Invalid {field_name}: {', '.join(result.errors)}"
                    )

        # Generate ID and timestamps
        person_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # Convert to database format with sanitized data
        db_item = person_data.model_dump()

        # Sanitize string fields
        db_item["firstName"] = InputValidator.validate_and_sanitize_string(
            person_data.firstName
        ).sanitized_data
        db_item["lastName"] = InputValidator.validate_and_sanitize_string(
            person_data.lastName
        ).sanitized_data
        db_item["email"] = email_result.sanitized_data
        if person_data.phone:
            db_item["phone"] = InputValidator.validate_and_sanitize_string(
                person_data.phone
            ).sanitized_data

        db_item.update(
            {
                "id": person_id,
                "createdAt": now.isoformat(),
                "updatedAt": now.isoformat(),
                "isActive": True,
                "requirePasswordChange": False,
                "emailVerified": False,
            }
        )

        # Handle password hash if provided
        if hasattr(person_data, "passwordHash") and person_data.passwordHash:
            db_item["passwordHash"] = person_data.passwordHash

        # Log data creation
        logging_service.log_data_operation(
            operation="create",
            resource_type="person",
            resource_id=person_id,
            success=True,
            details={"email": email_result.sanitized_data},
        )

        # Save to database
        success = db.put_item(self.table_name, db_item)
        if not success:
            logging_service.log_data_operation(
                operation="create",
                resource_type="person",
                resource_id=person_id,
                success=False,
                details={"error": "Database operation failed"},
            )
            raise Exception("Failed to create person in database")

        return Person(**db_item)

    def get_by_id(self, person_id: str) -> Optional[Person]:
        """Get a person by their ID."""
        person_data = db.get_item(self.table_name, {"id": person_id})
        if not person_data:
            return None

        return Person(**person_data)

    def get_by_email(self, email: str) -> Optional[Person]:
        """Get a person by their email address."""
        # Normalize email to lowercase for case-insensitive comparison
        email_lower = email.lower().strip()

        # Scan for person with matching email (case-insensitive)
        all_people = db.scan_table(self.table_name)
        for person_data in all_people:
            stored_email = person_data.get("email", "").lower().strip()
            if stored_email == email_lower:
                return Person(**person_data)
        return None

    def get_by_email_for_auth(self, email: str) -> Optional[dict]:
        """Get a person by email with password hash for authentication."""
        # Normalize email to lowercase for case-insensitive comparison
        email_lower = email.lower().strip()

        # Scan for person with matching email (case-insensitive)
        all_people = db.scan_table(self.table_name)
        for person_data in all_people:
            stored_email = person_data.get("email", "").lower().strip()
            if stored_email == email_lower:
                return person_data  # Return raw dict with passwordHash
        return None

    def update(self, person_id: str, updates: PersonUpdate) -> Optional[Person]:
        """Update an existing person."""
        from ..services.logging_service import logging_service, LogCategory, LogLevel

        # Check if person exists
        existing_person = self.get_by_id(person_id)
        if not existing_person:
            return None

        # Prepare update data (exclude None values)
        update_data = updates.model_dump(exclude_none=True)

        # Log what we're trying to update
        logging_service.log_structured(
            level=LogLevel.INFO,
            category=LogCategory.DATA_OPERATIONS,
            message=f"Updating person {person_id}",
            additional_data={
                "person_id": person_id,
                "update_fields": list(update_data.keys()),
                "update_data": update_data,
            },
        )

        if update_data:
            update_data["updatedAt"] = datetime.utcnow().isoformat()

            # Update in database (no field conversion needed!)
            success = db.update_item(self.table_name, {"id": person_id}, update_data)
            if not success:
                raise Exception("Failed to update person in database")

        # Return updated person
        return self.get_by_id(person_id)

    def delete(self, person_id: str) -> bool:
        """Delete a person by their ID."""
        return db.delete_item(self.table_name, {"id": person_id})

    def list_all(self, limit: Optional[int] = None) -> List[Person]:
        """List all people with optional limit."""
        people_data = db.scan_table(self.table_name, limit=limit)
        return [Person(**person_data) for person_data in people_data]

    def list_paginated(
        self,
        page: int = 1,
        page_size: int = 10,
        sort_by: Optional[str] = None,
        sort_direction: str = "asc",
        search: Optional[str] = None,
        filters: Optional[dict] = None,
    ) -> tuple[List[Person], int]:
        """
        List people with pagination, sorting, and filtering.

        Returns:
            tuple: (people_list, total_count)
        """
        # Get all people data
        all_people_data = db.scan_table(self.table_name)

        # Apply search filter
        if search:
            search_lower = search.lower().strip()
            filtered_data = []
            for person_data in all_people_data:
                if (
                    search_lower in person_data.get("firstName", "").lower()
                    or search_lower in person_data.get("lastName", "").lower()
                    or search_lower in person_data.get("email", "").lower()
                ):
                    filtered_data.append(person_data)
            all_people_data = filtered_data

        # Apply additional filters
        if filters:
            filtered_data = []
            for person_data in all_people_data:
                include_item = True

                # Filter by admin status
                if "isAdmin" in filters and filters["isAdmin"] is not None:
                    if person_data.get("isAdmin", False) != filters["isAdmin"]:
                        include_item = False

                # Filter by active status
                if "isActive" in filters and filters["isActive"] is not None:
                    if person_data.get("isActive", True) != filters["isActive"]:
                        include_item = False

                # Filter by email verification
                if "emailVerified" in filters and filters["emailVerified"] is not None:
                    if (
                        person_data.get("emailVerified", False)
                        != filters["emailVerified"]
                    ):
                        include_item = False

                if include_item:
                    filtered_data.append(person_data)

            all_people_data = filtered_data

        # Apply sorting
        if sort_by:
            reverse_sort = sort_direction.lower() == "desc"
            try:
                all_people_data.sort(
                    key=lambda x: x.get(sort_by, ""), reverse=reverse_sort
                )
            except (TypeError, KeyError):
                # Fallback to default sorting if sort field is invalid
                all_people_data.sort(key=lambda x: x.get("firstName", ""))
        else:
            # Default sort by firstName
            all_people_data.sort(key=lambda x: x.get("firstName", ""))

        # Calculate pagination
        total_count = len(all_people_data)
        start_index = (page - 1) * page_size
        end_index = start_index + page_size

        # Get page data
        page_data = all_people_data[start_index:end_index]

        # Convert to Person objects
        people = [Person(**person_data) for person_data in page_data]

        return people, total_count

    def exists(self, person_id: str) -> bool:
        """Check if a person exists."""
        person = self.get_by_id(person_id)
        return person is not None

    def email_exists(self, email: str) -> bool:
        """Check if an email address is already in use."""
        person = self.get_by_email(email)
        return person is not None

    def update_admin_status(self, person_id: str, is_admin: bool) -> Optional[Person]:
        """Update a person's admin status."""
        update_data = PersonUpdate(isAdmin=is_admin)
        return self.update(person_id, update_data)

    def activate_person(self, person_id: str) -> Optional[Person]:
        """Activate a person's account."""
        update_data = PersonUpdate(isActive=True)
        return self.update(person_id, update_data)

    def deactivate_person(self, person_id: str) -> Optional[Person]:
        """Deactivate a person's account."""
        update_data = PersonUpdate(isActive=False)
        return self.update(person_id, update_data)
