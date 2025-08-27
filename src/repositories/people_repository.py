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
        """Create a new person in the database."""
        # Generate ID and timestamps
        person_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # Convert to database format (already camelCase - no conversion needed!)
        db_item = person_data.model_dump()
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

        # Save to database
        success = await db.put_item(self.table_name, db_item)
        if not success:
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
        # Scan for person with matching email
        all_people = await db.scan_table(self.table_name)
        for person_data in all_people:
            if person_data.get("email") == email:
                return Person(**person_data)
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
