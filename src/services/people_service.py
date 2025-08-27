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

    async def create_person(self, person_data: PersonCreate) -> PersonResponse:
        """Create a new person with business validation."""
        # Check if email already exists
        if await self.people_repository.email_exists(person_data.email):
            raise ValueError(f"Email {person_data.email} is already in use")

        # Create person
        person = await self.people_repository.create(person_data)

        # Convert to response model
        return PersonResponse(**person.model_dump())

    async def get_person(self, person_id: str) -> Optional[PersonResponse]:
        """Get a person by ID."""
        person = await self.people_repository.get_by_id(person_id)
        if not person:
            return None

        return PersonResponse(**person.model_dump())

    async def get_person_by_email(self, email: str) -> Optional[PersonResponse]:
        """Get a person by email address."""
        person = await self.people_repository.get_by_email(email)
        if not person:
            return None

        return PersonResponse(**person.model_dump())

    async def update_person(
        self, person_id: str, updates: PersonUpdate
    ) -> Optional[PersonResponse]:
        """Update a person with business validation."""
        # If updating email, check for duplicates
        if updates.email:
            existing_person = await self.people_repository.get_by_email(updates.email)
            if existing_person and existing_person.id != person_id:
                raise ValueError(f"Email {updates.email} is already in use")

        # Update person
        person = await self.people_repository.update(person_id, updates)
        if not person:
            return None

        return PersonResponse(**person.model_dump())

    async def delete_person(self, person_id: str) -> bool:
        """Delete a person."""
        # TODO: Add business rules (e.g., check for active subscriptions)
        return await self.people_repository.delete(person_id)

    async def list_people(self, limit: Optional[int] = None) -> List[PersonResponse]:
        """List all people."""
        people = await self.people_repository.list_all(limit)
        return [PersonResponse(**person.model_dump()) for person in people]

    async def check_email_exists(self, email: str) -> bool:
        """Check if an email address is already in use."""
        return await self.people_repository.email_exists(email)

    async def update_admin_status(
        self, person_id: str, is_admin: bool
    ) -> Optional[PersonResponse]:
        """Update a person's admin status."""
        person = await self.people_repository.update_admin_status(person_id, is_admin)
        if not person:
            return None

        return PersonResponse(**person.model_dump())

    async def activate_person(self, person_id: str) -> Optional[PersonResponse]:
        """Activate a person's account."""
        person = await self.people_repository.activate_person(person_id)
        if not person:
            return None

        return PersonResponse(**person.model_dump())

    async def deactivate_person(self, person_id: str) -> Optional[PersonResponse]:
        """Deactivate a person's account."""
        person = await self.people_repository.deactivate_person(person_id)
        if not person:
            return None

        return PersonResponse(**person.model_dump())

    async def unlock_account(self, person_id: str) -> dict:
        """Unlock a person's account."""
        person = await self.people_repository.activate_person(person_id)
        if not person:
            raise ValueError("Person not found")

        return {"unlocked": True, "personId": person_id}
