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

    # Dashboard Analytics Methods for Phase 1 Implementation

    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data for people administration."""
        try:
            self.logger.log_api_request("GET", "/admin/people/dashboard")

            # Get all people for analysis
            all_people = await self.db_service.list_people()

            # Calculate overview metrics
            total_users = len(all_people)
            active_users = len([p for p in all_people if p.get("is_active", True)])
            inactive_users = total_users - active_users
            admin_users = len([p for p in all_people if p.get("is_admin", False)])

            # Calculate today's registrations
            today = datetime.now().date()
            new_users_today = len(
                [
                    p
                    for p in all_people
                    if p.get("created_at")
                    and datetime.fromisoformat(
                        p["created_at"].replace("Z", "+00:00")
                    ).date()
                    == today
                ]
            )

            # Calculate this month's registrations
            current_month = datetime.now().replace(day=1).date()
            new_users_this_month = len(
                [
                    p
                    for p in all_people
                    if p.get("created_at")
                    and datetime.fromisoformat(
                        p["created_at"].replace("Z", "+00:00")
                    ).date()
                    >= current_month
                ]
            )

            dashboard_data = {
                "overview": {
                    "total_users": total_users,
                    "active_users": active_users,
                    "inactive_users": inactive_users,
                    "admin_users": admin_users,
                    "new_users_today": new_users_today,
                    "new_users_this_month": new_users_this_month,
                },
                "activity_metrics": await self._get_activity_metrics(all_people),
                "demographics": await self._get_demographic_insights(all_people),
                "recent_activity": await self._get_recent_activity(
                    all_people, limit=15
                ),
            }

            response = create_v2_response(
                dashboard_data,
                metadata={
                    "service": "people_service",
                    "version": "dashboard",
                    "generated_at": datetime.now().isoformat(),
                    "total_analyzed": total_users,
                },
            )

            self.logger.log_api_response("GET", "/admin/people/dashboard", 200)
            return response

        except Exception as e:
            self.logger.error(
                "Failed to get dashboard data",
                operation="get_dashboard_data",
                error_type=type(e).__name__,
            )
            raise handle_database_error("getting dashboard data", e)

    async def get_registration_trends(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get user registration trends over time."""
        try:
            self.logger.log_api_request("GET", "/admin/people/registration-trends")

            all_people = await self.db_service.list_people()

            # Filter by date range if provided
            if date_from or date_to:
                filtered_people = []
                for person in all_people:
                    if person.get("created_at"):
                        created_date = datetime.fromisoformat(
                            person["created_at"].replace("Z", "+00:00")
                        ).date()

                        if (
                            date_from
                            and created_date < datetime.fromisoformat(date_from).date()
                        ):
                            continue
                        if (
                            date_to
                            and created_date > datetime.fromisoformat(date_to).date()
                        ):
                            continue

                        filtered_people.append(person)
                all_people = filtered_people

            # Group by month for trends
            monthly_registrations = {}
            for person in all_people:
                if person.get("created_at"):
                    created_date = datetime.fromisoformat(
                        person["created_at"].replace("Z", "+00:00")
                    )
                    month_key = created_date.strftime("%Y-%m")
                    monthly_registrations[month_key] = (
                        monthly_registrations.get(month_key, 0) + 1
                    )

            # Sort by month
            sorted_trends = dict(sorted(monthly_registrations.items()))

            response = create_v2_response(
                {
                    "monthly_trends": sorted_trends,
                    "total_registrations": len(all_people),
                    "date_range": {"from": date_from, "to": date_to},
                },
                metadata={
                    "service": "people_service",
                    "version": "analytics",
                    "analysis_type": "registration_trends",
                },
            )

            self.logger.log_api_response(
                "GET", "/admin/people/registration-trends", 200
            )
            return response

        except Exception as e:
            self.logger.error(
                "Failed to get registration trends",
                operation="get_registration_trends",
                error_type=type(e).__name__,
            )
            raise handle_database_error("getting registration trends", e)

    async def get_activity_patterns(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get user activity patterns and engagement metrics."""
        try:
            self.logger.log_api_request("GET", "/admin/people/activity-patterns")

            all_people = await self.db_service.list_people()

            # Calculate activity metrics
            activity_data = {
                "login_activity": await self._calculate_login_activity(
                    all_people, date_from, date_to
                ),
                "profile_updates": await self._calculate_profile_updates(
                    all_people, date_from, date_to
                ),
                "inactive_users": await self._calculate_inactive_users(all_people),
                "engagement_score": await self._calculate_engagement_score(all_people),
            }

            response = create_v2_response(
                activity_data,
                metadata={
                    "service": "people_service",
                    "version": "analytics",
                    "analysis_type": "activity_patterns",
                    "date_range": {"from": date_from, "to": date_to},
                },
            )

            self.logger.log_api_response("GET", "/admin/people/activity-patterns", 200)
            return response

        except Exception as e:
            self.logger.error(
                "Failed to get activity patterns",
                operation="get_activity_patterns",
                error_type=type(e).__name__,
            )
            raise handle_database_error("getting activity patterns", e)

    async def get_demographic_insights(self) -> Dict[str, Any]:
        """Get demographic distribution insights."""
        try:
            self.logger.log_api_request("GET", "/admin/people/demographics")

            all_people = await self.db_service.list_people()

            demographics = await self._get_demographic_insights(all_people)

            response = create_v2_response(
                demographics,
                metadata={
                    "service": "people_service",
                    "version": "analytics",
                    "analysis_type": "demographics",
                    "total_analyzed": len(all_people),
                },
            )

            self.logger.log_api_response("GET", "/admin/people/demographics", 200)
            return response

        except Exception as e:
            self.logger.error(
                "Failed to get demographic insights",
                operation="get_demographic_insights",
                error_type=type(e).__name__,
            )
            raise handle_database_error("getting demographic insights", e)

    async def get_engagement_metrics(self) -> Dict[str, Any]:
        """Get user engagement metrics and statistics."""
        try:
            self.logger.log_api_request("GET", "/admin/people/engagement")

            all_people = await self.db_service.list_people()

            engagement_data = {
                "overall_engagement": await self._calculate_engagement_score(
                    all_people
                ),
                "user_segments": await self._calculate_user_segments(all_people),
                "retention_metrics": await self._calculate_retention_metrics(
                    all_people
                ),
                "activity_distribution": await self._calculate_activity_distribution(
                    all_people
                ),
            }

            response = create_v2_response(
                engagement_data,
                metadata={
                    "service": "people_service",
                    "version": "analytics",
                    "analysis_type": "engagement_metrics",
                },
            )

            self.logger.log_api_response("GET", "/admin/people/engagement", 200)
            return response

        except Exception as e:
            self.logger.error(
                "Failed to get engagement metrics",
                operation="get_engagement_metrics",
                error_type=type(e).__name__,
            )
            raise handle_database_error("getting engagement metrics", e)

    # Private helper methods for analytics calculations

    async def _get_activity_metrics(
        self, all_people: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate activity metrics for dashboard."""
        try:
            # Mock activity data - in real implementation, this would come from activity logs
            return {
                "login_activity": {
                    "daily_active_users": len(
                        [p for p in all_people if p.get("is_active", True)]
                    )
                    // 3,
                    "weekly_active_users": len(
                        [p for p in all_people if p.get("is_active", True)]
                    )
                    // 2,
                    "monthly_active_users": len(
                        [p for p in all_people if p.get("is_active", True)]
                    ),
                },
                "profile_updates": {
                    "today": len(all_people) // 10,
                    "this_week": len(all_people) // 5,
                    "this_month": len(all_people) // 3,
                },
                "inactive_users": len(
                    [p for p in all_people if not p.get("is_active", True)]
                ),
            }
        except Exception as e:
            self.logger.error(f"Error calculating activity metrics: {str(e)}")
            return {"error": "Failed to calculate activity metrics"}

    async def _get_demographic_insights(
        self, all_people: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate demographic insights."""
        try:
            # Location distribution
            location_distribution = {}
            age_distribution = {
                "18-25": 0,
                "26-35": 0,
                "36-45": 0,
                "46-55": 0,
                "55+": 0,
            }

            for person in all_people:
                # Location analysis
                if person.get("address") and person["address"].get("city"):
                    city = person["address"]["city"]
                    location_distribution[city] = location_distribution.get(city, 0) + 1

                # Age analysis (mock calculation based on date_of_birth)
                if person.get("date_of_birth"):
                    try:
                        birth_date = datetime.strptime(
                            person["date_of_birth"], "%Y-%m-%d"
                        )
                        age = (datetime.now() - birth_date).days // 365

                        if age <= 25:
                            age_distribution["18-25"] += 1
                        elif age <= 35:
                            age_distribution["26-35"] += 1
                        elif age <= 45:
                            age_distribution["36-45"] += 1
                        elif age <= 55:
                            age_distribution["46-55"] += 1
                        else:
                            age_distribution["55+"] += 1
                    except ValueError:
                        pass  # Skip invalid dates

            return {
                "age_distribution": age_distribution,
                "location_distribution": dict(
                    sorted(
                        location_distribution.items(), key=lambda x: x[1], reverse=True
                    )[:10]
                ),
                "total_locations": len(location_distribution),
            }
        except Exception as e:
            self.logger.error(f"Error calculating demographic insights: {str(e)}")
            return {"error": "Failed to calculate demographic insights"}

    async def _get_recent_activity(
        self, all_people: List[Dict[str, Any]], limit: int = 15
    ) -> List[Dict[str, Any]]:
        """Get recent user activity for dashboard."""
        try:
            # Sort by creation date and get most recent
            sorted_people = sorted(
                all_people,
                key=lambda x: x.get("created_at", "1970-01-01T00:00:00Z"),
                reverse=True,
            )

            recent_activity = []
            for person in sorted_people[:limit]:
                activity = {
                    "user_id": person.get("id", "unknown"),
                    "user_name": f"{person.get('first_name', '')} {person.get('last_name', '')}".strip(),
                    "email": person.get("email", ""),
                    "activity_type": "registration",
                    "timestamp": person.get("created_at", ""),
                    "details": "New user registered",
                }
                recent_activity.append(activity)

            return recent_activity
        except Exception as e:
            self.logger.error(f"Error getting recent activity: {str(e)}")
            return []

    async def _calculate_login_activity(
        self,
        all_people: List[Dict[str, Any]],
        date_from: Optional[str],
        date_to: Optional[str],
    ) -> Dict[str, Any]:
        """Calculate login activity statistics (mock implementation)."""
        # In real implementation, this would query activity logs
        active_users = len([p for p in all_people if p.get("is_active", True)])
        return {
            "total_logins": active_users * 5,  # Mock data
            "unique_users": active_users,
            "average_sessions_per_user": 5.2,
            "peak_login_hour": "09:00",
        }

    async def _calculate_profile_updates(
        self,
        all_people: List[Dict[str, Any]],
        date_from: Optional[str],
        date_to: Optional[str],
    ) -> Dict[str, Any]:
        """Calculate profile update statistics (mock implementation)."""
        return {
            "total_updates": len(all_people) // 4,
            "users_with_updates": len(all_people) // 6,
            "most_updated_field": "phone",
            "update_frequency": "weekly",
        }

    async def _calculate_inactive_users(
        self, all_people: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate inactive user statistics."""
        inactive_count = len([p for p in all_people if not p.get("is_active", True)])
        return {
            "count": inactive_count,
            "percentage": (inactive_count / len(all_people) * 100) if all_people else 0,
            "last_activity_threshold": "30 days",
        }

    async def _calculate_engagement_score(
        self, all_people: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate overall engagement score (mock implementation)."""
        active_users = len([p for p in all_people if p.get("is_active", True)])
        engagement_score = (active_users / len(all_people) * 100) if all_people else 0

        return {
            "overall_score": round(engagement_score, 2),
            "rating": (
                "high"
                if engagement_score > 80
                else "medium" if engagement_score > 60 else "low"
            ),
            "active_user_ratio": round(engagement_score / 100, 2),
        }

    async def _calculate_user_segments(
        self, all_people: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate user segments for engagement analysis."""
        total_users = len(all_people)
        active_users = len([p for p in all_people if p.get("is_active", True)])
        admin_users = len([p for p in all_people if p.get("is_admin", False)])

        return {
            "highly_engaged": active_users // 3,
            "moderately_engaged": active_users // 2,
            "low_engagement": total_users - active_users,
            "admin_users": admin_users,
            "new_users": total_users // 10,  # Mock: assume 10% are new
        }

    async def _calculate_retention_metrics(
        self, all_people: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate user retention metrics (mock implementation)."""
        return {
            "weekly_retention": 85.5,
            "monthly_retention": 72.3,
            "quarterly_retention": 65.8,
            "churn_rate": 5.2,
        }

    async def _calculate_activity_distribution(
        self, all_people: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate activity distribution across user base."""
        total_users = len(all_people)
        return {
            "very_active": total_users // 5,
            "active": total_users // 3,
            "moderate": total_users // 4,
            "low": total_users // 6,
            "inactive": total_users
            - (
                total_users // 5
                + total_users // 3
                + total_users // 4
                + total_users // 6
            ),
        }
