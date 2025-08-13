"""
People Service - Domain service for person-related operations.
Implements the Service Registry pattern with Repository pattern integration.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from ..core.base_service import BaseService
from ..models.person import PersonCreate, PersonUpdate, PersonResponse, Person
from ..repositories.user_repository import UserRepository
from ..services.defensive_dynamodb_service import DefensiveDynamoDBService
from ..utils.logging_config import get_handler_logger
from ..utils.error_handler import handle_database_error
from ..utils.response_models import create_v1_response, create_v2_response


class PeopleService(BaseService):
    """Service for managing people-related operations with repository pattern."""

    def __init__(self):
        super().__init__("people_service")
        # Initialize repository for clean data access
        self.user_repository = UserRepository(table_name="people")
        # Keep legacy db_service for backward compatibility during transition
        self.db_service = DefensiveDynamoDBService()
        self.logger = get_handler_logger("people_service")

    async def initialize(self):
        """Initialize the people service with repository pattern."""
        try:
            # Test repository connectivity with a simple count operation
            count_result = await self.user_repository.count()
            if count_result.success:
                self.logger.info(
                    f"People service initialized successfully. Found {count_result.data} users."
                )
                return True
            else:
                self.logger.error(
                    f"Repository health check failed: {count_result.error}"
                )
                return False
        except Exception as e:
            self.logger.error(f"Failed to initialize people service: {str(e)}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the people service using repository pattern."""
        try:
            import asyncio

            # Test repository connectivity with timeout
            try:
                count_result = await asyncio.wait_for(
                    self.user_repository.count(), timeout=1.0
                )
                performance_stats = self.user_repository.get_performance_stats()

                if count_result.success:
                    return {
                        "service": "people_service",
                        "status": "healthy",
                        "repository": "connected",
                        "user_count": count_result.data,
                        "performance": performance_stats,
                        "timestamp": datetime.now().isoformat(),
                    }
                else:
                    return {
                        "service": "people_service",
                        "status": "unhealthy",
                        "repository": "disconnected",
                        "error": count_result.error,
                        "timestamp": datetime.now().isoformat(),
                    }
            except asyncio.TimeoutError:
                return {
                    "service": "people_service",
                    "status": "degraded",
                    "repository": "timeout",
                    "message": "Repository check timed out",
                    "timestamp": datetime.now().isoformat(),
                }
        except Exception as e:
            self.logger.error(f"People service health check failed: {str(e)}")
            return {
                "service": "people_service",
                "status": "unhealthy",
                "repository": "disconnected",
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

    async def get_all_people(self) -> Dict[str, Any]:
        """Get all people (backward compatibility method)."""
        return await self.get_all_people_v1()

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

    async def get_person_by_id(self, person_id: str) -> Dict[str, Any]:
        """Get person by ID (backward compatibility method)."""
        return await self.get_person_by_id_v1(person_id)

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
            existing_person = await self.db_service.get_person(person_id)
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
            existing_person = await self.db_service.get_person(person_id)
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
            existing_person = await self.db_service.get_person(person_id)
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
            existing_person = await self.db_service.get_person(person_id)
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

    # New Repository-Based Methods for Enhanced Functionality

    async def get_all_people_repository(
        self, limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get all people using repository pattern with enhanced features."""
        try:
            self.logger.log_api_request("GET", "/repository/people")

            from ..repositories.base_repository import QueryOptions

            options = QueryOptions(limit=limit) if limit else None

            result = await self.user_repository.list_all(options)

            if result.success:
                # Convert Person objects to dict for response
                people_data = (
                    [person.dict() for person in result.data] if result.data else []
                )

                response = create_v2_response(
                    people_data,
                    metadata={
                        "total_count": len(people_data),
                        "service": "people_service",
                        "version": "repository",
                        "performance": self.user_repository.get_performance_stats(),
                    },
                )

                # Add result metadata if available
                if result.metadata:
                    response["metadata"].update(result.metadata)
                self.logger.log_api_response(
                    "GET",
                    "/repository/people",
                    200,
                    additional_context={"count": len(people_data)},
                )
                return response
            else:
                raise Exception(f"Repository error: {result.error}")

        except Exception as e:
            self.logger.error(
                "Failed to retrieve people via repository",
                operation="get_all_people_repository",
                error_type=type(e).__name__,
            )
            raise handle_database_error("retrieving people", e)

    async def get_person_by_email(self, email: str) -> Dict[str, Any]:
        """Get person by email using repository pattern."""
        try:
            self.logger.log_api_request("GET", f"/repository/people/email/{email}")

            result = await self.user_repository.get_by_email(email)

            if result.success:
                if result.data:
                    person_data = result.data.dict()
                    response = create_v2_response(
                        person_data,
                        metadata={
                            "email": email,
                            "service": "people_service",
                            "version": "repository",
                        },
                    )
                    self.logger.log_api_response(
                        "GET", f"/repository/people/email/{email}", 200
                    )
                    return response
                else:
                    from fastapi import HTTPException, status

                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND, detail="Person not found"
                    )
            else:
                raise Exception(f"Repository error: {result.error}")

        except Exception as e:
            if hasattr(e, "status_code"):
                raise e
            self.logger.error(
                "Failed to retrieve person by email",
                operation="get_person_by_email",
                email=email,
                error_type=type(e).__name__,
            )
            raise handle_database_error("retrieving person by email", e)

    async def get_active_people(self) -> Dict[str, Any]:
        """Get all active people using repository pattern."""
        try:
            self.logger.log_api_request("GET", "/repository/people/active")

            result = await self.user_repository.get_active_users()

            if result.success:
                people_data = (
                    [person.dict() for person in result.data] if result.data else []
                )

                response = create_v2_response(
                    people_data,
                    metadata={
                        "active_count": len(people_data),
                        "service": "people_service",
                        "version": "repository",
                        "filter": "active_only",
                    },
                )
                self.logger.log_api_response(
                    "GET",
                    "/repository/people/active",
                    200,
                    additional_context={"active_count": len(people_data)},
                )
                return response
            else:
                raise Exception(f"Repository error: {result.error}")

        except Exception as e:
            self.logger.error(
                "Failed to retrieve active people",
                operation="get_active_people",
                error_type=type(e).__name__,
            )
            raise handle_database_error("retrieving active people", e)

    async def get_people_performance_stats(self) -> Dict[str, Any]:
        """Get repository performance statistics."""
        try:
            stats = self.user_repository.get_performance_stats()
            return create_v2_response(
                stats,
                metadata={
                    "service": "people_service",
                    "version": "repository",
                    "stats_type": "performance",
                    "timestamp": datetime.now().isoformat(),
                },
            )
        except Exception as e:
            self.logger.error(
                "Failed to get performance stats",
                operation="get_people_performance_stats",
                error_type=type(e).__name__,
            )
            raise handle_database_error("getting performance stats", e)
