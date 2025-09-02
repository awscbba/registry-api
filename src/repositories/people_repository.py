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
        self.table_name = "people"

    async def create(self, person_data: PersonCreate) -> Person:
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
        success = await db.put_item(self.table_name, db_item)
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

    async def get_by_id(self, person_id: str) -> Optional[Person]:
        """Get a person by their ID."""
        person_data = await db.get_item(self.table_name, {"id": person_id})
        if not person_data:
            return None

        return Person(**person_data)

    async def get_by_email(self, email: str) -> Optional[Person]:
        """Get a person by their email address."""
        # Normalize email to lowercase for case-insensitive comparison
        email_lower = email.lower().strip()

        # Scan for person with matching email (case-insensitive)
        all_people = await db.scan_table(self.table_name)
        for person_data in all_people:
            stored_email = person_data.get("email", "").lower().strip()
            if stored_email == email_lower:
                return Person(**person_data)
        return None

    async def get_by_email_for_auth(self, email: str) -> Optional[dict]:
        """Get a person by email with password hash for authentication."""
        # Normalize email to lowercase for case-insensitive comparison
        email_lower = email.lower().strip()

        # Scan for person with matching email (case-insensitive)
        all_people = await db.scan_table(self.table_name)
        for person_data in all_people:
            stored_email = person_data.get("email", "").lower().strip()
            if stored_email == email_lower:
                return person_data  # Return raw dict with passwordHash
        return None

    async def update(self, person_id: str, updates: PersonUpdate) -> Optional[Person]:
        """Update an existing person."""
        # Check if person exists
        existing_person = await self.get_by_id(person_id)
        if not existing_person:
            return None

        # Prepare update data (exclude None values)
        update_data = updates.model_dump(exclude_none=True)
        if update_data:
            update_data["updatedAt"] = datetime.utcnow().isoformat()

            # Update in database (no field conversion needed!)
            success = await db.update_item(
                self.table_name, {"id": person_id}, update_data
            )
            if not success:
                raise Exception("Failed to update person in database")

        # Return updated person
        return await self.get_by_id(person_id)

    async def delete(self, person_id: str) -> bool:
        """Delete a person by their ID."""
        return await db.delete_item(self.table_name, {"id": person_id})

    async def list_all(self, limit: Optional[int] = None) -> List[Person]:
        """List all people with optional limit."""
        people_data = await db.scan_table(self.table_name, limit=limit)
        return [Person(**person_data) for person_data in people_data]

    async def exists(self, person_id: str) -> bool:
        """Check if a person exists."""
        person = await self.get_by_id(person_id)
        return person is not None

    async def email_exists(self, email: str) -> bool:
        """Check if an email address is already in use."""
        person = await self.get_by_email(email)
        return person is not None

    async def update_admin_status(
        self, person_id: str, is_admin: bool
    ) -> Optional[Person]:
        """Update a person's admin status."""
        update_data = PersonUpdate(isAdmin=is_admin)
        return await self.update(person_id, update_data)

    async def activate_person(self, person_id: str) -> Optional[Person]:
        """Activate a person's account."""
        update_data = PersonUpdate(isActive=True)
        return await self.update(person_id, update_data)

    async def deactivate_person(self, person_id: str) -> Optional[Person]:
        """Deactivate a person's account."""
        update_data = PersonUpdate(isActive=False)
        return await self.update(person_id, update_data)
