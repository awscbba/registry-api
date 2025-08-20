"""
User Repository - Data access layer for user/person entities

Provides clean data access patterns for user management operations.
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from src.repositories.base_repository import (
    BaseRepository,
    RepositoryResult,
    QueryOptions,
    QueryFilter,
    QueryOperator,
)
from src.models.person import Person


class UserRepository(BaseRepository[Person]):
    """Repository for user/person data access operations"""

    def __init__(self, table_name: str = None):
        if table_name is None:
            table_name = os.getenv("PEOPLE_TABLE_NAME", "PeopleTable")
        super().__init__(table_name)

    def _to_entity(self, item: Dict[str, Any]) -> Person:
        """Convert DynamoDB item to Person entity"""
        try:
            # Handle address conversion
            address_data = item.get("address", {})
            if address_data and isinstance(address_data, dict):
                from src.models.person import Address

                # Follow the same pattern as DefensiveDynamoDBService
                # Normalize postal code field - handle ALL variants
                address_data_copy = address_data.copy()

                if "postal_code" in address_data_copy:
                    address_data_copy["postalCode"] = address_data_copy.pop(
                        "postal_code"
                    )
                elif "zip_code" in address_data_copy:
                    address_data_copy["postalCode"] = address_data_copy.pop("zip_code")
                elif "zipCode" in address_data_copy:
                    address_data_copy["postalCode"] = address_data_copy.pop("zipCode")

                # Ensure postalCode exists - provide default if missing
                if "postalCode" not in address_data_copy:
                    address_data_copy["postalCode"] = ""

                address = Address(**address_data_copy)
            else:
                address = None

            # Convert DynamoDB item to Person
            person_data = {
                "id": item.get("id"),
                "first_name": item.get("firstName", item.get("first_name")),
                "last_name": item.get("lastName", item.get("last_name")),
                "email": item.get("email"),
                "phone": item.get("phone"),
                "date_of_birth": item.get("dateOfBirth", item.get("date_of_birth")),
                "address": address,
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "last_login_at": item.get("last_login_at"),
                "is_active": item.get("is_active", True),
                "email_verified": item.get("email_verified", False),
                "email_verification_token": item.get("email_verification_token"),
                "pending_email_change": item.get("pending_email_change"),
                "password_hash": item.get("password_hash"),
                "password_salt": item.get("password_salt"),
                "require_password_change": item.get("require_password_change", False),
            }

            return Person(**{k: v for k, v in person_data.items() if v is not None})

        except Exception as e:
            # Log the validation error but don't fail the entire operation
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to convert DynamoDB item to Person entity: {str(e)}")
            logger.error(f"Item data: {item}")
            raise e  # Re-raise for now to debug, but we could handle this more gracefully

    def _to_item(self, entity: Person) -> Dict[str, Any]:
        """Convert Person entity to DynamoDB item"""
        item = {
            "id": entity.id,
            "firstName": entity.first_name,
            "lastName": entity.last_name,
            "email": entity.email,
            "phone": entity.phone,
            "dateOfBirth": entity.date_of_birth,
            "is_active": getattr(entity, "is_active", True),
            "email_verified": getattr(entity, "email_verified", False),
        }

        # Handle address
        if entity.address:
            item["address"] = {
                "street": entity.address.street,
                "city": entity.address.city,
                "state": entity.address.state,
                "postal_code": entity.address.postal_code,
                "country": entity.address.country,
            }

        # Handle optional fields
        optional_fields = [
            "created_at",
            "updated_at",
            "last_login_at",
            "email_verification_token",
            "pending_email_change",
            "password_hash",
            "password_salt",
            "require_password_change",
        ]

        for field in optional_fields:
            value = getattr(entity, field, None)
            if value is not None:
                item[field] = value

        return item

    def _get_primary_key(self, entity: Person) -> Dict[str, Any]:
        """Get primary key from Person entity"""
        return {"id": entity.id}

    async def get_by_email(self, email: str) -> RepositoryResult[Person]:
        """Get user by email address"""
        filters = [
            QueryFilter(field="email", operator=QueryOperator.EQUALS, value=email)
        ]
        options = QueryOptions(filters=filters, limit=1)

        result = await self.list_all(options)

        if result.success and result.data:
            return RepositoryResult[Person](success=True, data=result.data[0])

        return RepositoryResult[Person](success=True, data=None)

    async def get_active_users(self) -> RepositoryResult[List[Person]]:
        """Get all active users"""
        filters = [
            QueryFilter(field="is_active", operator=QueryOperator.EQUALS, value=True)
        ]
        options = QueryOptions(filters=filters)

        return await self.list_all(options)
