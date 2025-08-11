"""
People Service - Domain service for person-related operations.
Implements the Service Registry pattern for person management.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from ..core.base_service import BaseService
from ..models.person import PersonCreate, PersonUpdate, PersonResponse
from ..services.defensive_dynamodb_service import DefensiveDynamoDBService
from ..utils.logging_config import get_handler_logger
from ..utils.error_handler import handle_database_error
from ..utils.response_models import create_v1_response, create_v2_response


class PeopleService(BaseService):
    """Service for managing people-related operations."""

    def __init__(self):
        super().__init__("people_service")
        self.db_service = DefensiveDynamoDBService()
        self.logger = get_handler_logger("people_service")

    async def initialize(self):
        """Initialize the people service."""
        try:
            # Test database connectivity
            await self.db_service.list_people()
            self.logger.info("People service initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize people service: {str(e)}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the people service."""
        try:
            # Test database connectivity
            await self.db_service.list_people()
            return {
                "service": "people_service",
                "status": "healthy",
                "database": "connected",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"People service health check failed: {str(e)}")
            return {
                "service": "people_service",
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def get_all_people_v1(self) -> Dict[str, Any]:
        """Get all people (v1 format)."""
        try:
            self.logger.log_api_request("GET", "/v1/people")
            people = await self.db_service.list_people()

            response = create_v1_response(people)
            self.logger.log_api_response("GET", "/v1/people", 200)
            return response
        except Exception as e:
            self.logger.error(
                "Failed to retrieve people",
                operation="get_all_people_v1",
                error_type=type(e).__name__,
            )
            raise handle_database_error("retrieving people", e)

    async def get_all_people_v2(self) -> Dict[str, Any]:
        """Get all people (v2 format with enhanced metadata)."""
        try:
            self.logger.log_api_request("GET", "/v2/people")
            people = await self.db_service.list_people()

            response = create_v2_response(
                people,
                metadata={
                    "total_count": len(people),
                    "service": "people_service",
                    "version": "v2",
                },
            )
            self.logger.log_api_response(
                "GET", "/v2/people", 200, additional_context={"count": len(people)}
            )
            return response
        except Exception as e:
            self.logger.error(
                "Failed to retrieve people",
                operation="get_all_people_v2",
                error_type=type(e).__name__,
            )
            raise handle_database_error("retrieving people", e)

    async def get_person_by_id_v1(self, person_id: str) -> Dict[str, Any]:
        """Get person by ID (v1 format)."""
        try:
            self.logger.log_api_request("GET", f"/v1/people/{person_id}")
            person = await self.db_service.get_person(person_id)

            if not person:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Person not found"
                )

            response = create_v1_response(person)
            self.logger.log_api_response("GET", f"/v1/people/{person_id}", 200)
            return response
        except Exception as e:
            if hasattr(e, "status_code"):
                raise e
            self.logger.error(
                "Failed to retrieve person",
                operation="get_person_by_id_v1",
                person_id=person_id,
                error_type=type(e).__name__,
            )
            raise handle_database_error("retrieving person", e)

    async def get_person_by_id_v2(self, person_id: str) -> Dict[str, Any]:
        """Get person by ID (v2 format with enhanced metadata)."""
        try:
            self.logger.log_api_request("GET", f"/v2/people/{person_id}")
            person = await self.db_service.get_person(person_id)

            if not person:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Person not found"
                )

            response = create_v2_response(
                person,
                metadata={
                    "person_id": person_id,
                    "service": "people_service",
                    "version": "v2",
                },
            )
            self.logger.log_api_response("GET", f"/v2/people/{person_id}", 200)
            return response
        except Exception as e:
            if hasattr(e, "status_code"):
                raise e
            self.logger.error(
                "Failed to retrieve person",
                operation="get_person_by_id_v2",
                person_id=person_id,
                error_type=type(e).__name__,
            )
            raise handle_database_error("retrieving person", e)

    async def create_person_v1(self, person_data: PersonCreate) -> Dict[str, Any]:
        """Create a new person (v1 format)."""
        try:
            self.logger.log_api_request("POST", "/v1/people")

            # Generate ID if not provided
            person_id = str(uuid.uuid4())

            # Create person using database service
            created_person = await self.db_service.create_person(person_data, person_id)

            response = create_v1_response(created_person)
            self.logger.log_api_response("POST", "/v1/people", 201)
            return response
        except Exception as e:
            self.logger.error(
                "Failed to create person",
                operation="create_person_v1",
                error_type=type(e).__name__,
            )
            raise handle_database_error("creating person", e)

    async def create_person_v2(self, person_data: PersonCreate) -> Dict[str, Any]:
        """Create a new person (v2 format with enhanced features)."""
        try:
            self.logger.log_api_request("POST", "/v2/people")

            # Generate ID if not provided
            person_id = str(uuid.uuid4())

            # Create person using database service
            created_person = await self.db_service.create_person(person_data, person_id)

            response = create_v2_response(
                created_person,
                metadata={
                    "person_id": person_id,
                    "service": "people_service",
                    "version": "v2",
                    "created_at": datetime.now().isoformat(),
                },
            )
            self.logger.log_api_response("POST", "/v2/people", 201)
            return response
        except Exception as e:
            self.logger.error(
                "Failed to create person",
                operation="create_person_v2",
                error_type=type(e).__name__,
            )
            raise handle_database_error("creating person", e)

    async def update_person_v1(
        self, person_id: str, person_data: PersonUpdate
    ) -> Dict[str, Any]:
        """Update person (v1 format)."""
        try:
            self.logger.log_api_request("PUT", f"/v1/people/{person_id}")

            # Check if person exists
            existing_person = await self.db_service.get_person_by_id(person_id)
            if not existing_person:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Person not found"
                )

            # Update person
            updated_person = await self.db_service.update_person(person_id, person_data)

            response = create_v1_response(updated_person)
            self.logger.log_api_response("PUT", f"/v1/people/{person_id}", 200)
            return response
        except Exception as e:
            if hasattr(e, "status_code"):
                raise e
            self.logger.error(
                "Failed to update person",
                operation="update_person_v1",
                person_id=person_id,
                error_type=type(e).__name__,
            )
            raise handle_database_error("updating person", e)

    async def update_person_v2(
        self, person_id: str, person_data: PersonUpdate
    ) -> Dict[str, Any]:
        """Update person (v2 format with enhanced features)."""
        try:
            self.logger.log_api_request("PUT", f"/v2/people/{person_id}")

            # Check if person exists
            existing_person = await self.db_service.get_person_by_id(person_id)
            if not existing_person:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Person not found"
                )

            # Update person
            updated_person = await self.db_service.update_person(person_id, person_data)

            response = create_v2_response(
                updated_person,
                metadata={
                    "person_id": person_id,
                    "service": "people_service",
                    "version": "v2",
                    "updated_at": datetime.now().isoformat(),
                },
            )
            self.logger.log_api_response("PUT", f"/v2/people/{person_id}", 200)
            return response
        except Exception as e:
            if hasattr(e, "status_code"):
                raise e
            self.logger.error(
                "Failed to update person",
                operation="update_person_v2",
                person_id=person_id,
                error_type=type(e).__name__,
            )
            raise handle_database_error("updating person", e)

    async def delete_person_v1(self, person_id: str) -> Dict[str, Any]:
        """Delete person (v1 format)."""
        try:
            self.logger.log_api_request("DELETE", f"/v1/people/{person_id}")

            # Check if person exists
            existing_person = await self.db_service.get_person_by_id(person_id)
            if not existing_person:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Person not found"
                )

            # Delete person
            success = await self.db_service.delete_person(person_id)
            if not success:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete person",
                )

            response = create_v1_response(
                {"message": "Person deleted successfully", "personId": person_id}
            )
            self.logger.log_api_response("DELETE", f"/v1/people/{person_id}", 200)
            return response
        except Exception as e:
            if hasattr(e, "status_code"):
                raise e
            self.logger.error(
                "Failed to delete person",
                operation="delete_person_v1",
                person_id=person_id,
                error_type=type(e).__name__,
            )
            raise handle_database_error("deleting person", e)

    async def delete_person_v2(self, person_id: str) -> Dict[str, Any]:
        """Delete person (v2 format with enhanced features)."""
        try:
            self.logger.log_api_request("DELETE", f"/v2/people/{person_id}")

            # Check if person exists
            existing_person = await self.db_service.get_person_by_id(person_id)
            if not existing_person:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Person not found"
                )

            # Delete person
            success = await self.db_service.delete_person(person_id)
            if not success:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete person",
                )

            response = create_v2_response(
                {"message": "Person deleted successfully", "personId": person_id},
                metadata={
                    "person_id": person_id,
                    "service": "people_service",
                    "version": "v2",
                    "deleted_at": datetime.now().isoformat(),
                },
            )
            self.logger.log_api_response("DELETE", f"/v2/people/{person_id}", 200)
            return response
        except Exception as e:
            if hasattr(e, "status_code"):
                raise e
            self.logger.error(
                "Failed to delete person",
                operation="delete_person_v2",
                person_id=person_id,
                error_type=type(e).__name__,
            )
            raise handle_database_error("deleting person", e)
