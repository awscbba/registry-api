"""
People Service - Domain service for person-related operations.
Implements the Service Registry pattern with Repository pattern integration.
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
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
        # Use environment variable for table name
        table_name = os.getenv("PEOPLE_TABLE_NAME", "PeopleTable")
        # Initialize repository for clean data access
        self.user_repository = UserRepository(table_name=table_name)
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

            # Try to get from cache first
            cache_service = self._get_cache_service()
            if cache_service:
                cache_key = cache_service.generate_cache_key("dashboard_data")
                cached_result = await cache_service.get(cache_key)
                if cached_result:
                    self.logger.debug("Dashboard data retrieved from cache")
                    return cached_result

            # Execute optimized database query with performance tracking
            async def fetch_dashboard_data():
                # Get all people for analysis
                all_people = await self.db_service.list_people()
                return all_people

            # Use optimized query execution with performance tracking
            all_people = await self._execute_optimized_query(
                "dashboard_data_fetch", fetch_dashboard_data
            )

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

            # Cache the result for 15 minutes (dashboard data doesn't change frequently)
            if cache_service:
                await cache_service.set(cache_key, response, ttl=900)  # 15 minutes
                self.logger.debug("Dashboard data cached for 15 minutes")

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

    # Phase 2: Advanced User Management Methods

    async def advanced_search_users(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        limit: int = 25,
    ) -> Dict[str, Any]:
        """
        Advanced search with comprehensive filtering and sorting.

        Args:
            query: Full-text search query
            filters: Dictionary of filters to apply
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
            page: Page number for pagination
            limit: Number of results per page
        """
        try:
            self.logger.log_api_request("POST", "/admin/people/search")

            # Get all people for filtering (in production, this would be optimized with database queries)
            all_people = await self.db_service.list_people()

            # Apply text search if provided
            if query:
                all_people = await self._apply_text_search(all_people, query)

            # Apply filters if provided
            if filters:
                all_people = await self._apply_filters(all_people, filters)

            # Apply sorting
            all_people = await self._apply_sorting(all_people, sort_by, sort_order)

            # Calculate pagination
            total_count = len(all_people)
            start_index = (page - 1) * limit
            end_index = start_index + limit
            paginated_people = all_people[start_index:end_index]

            # Calculate pagination metadata
            total_pages = (total_count + limit - 1) // limit
            has_next = page < total_pages
            has_prev = page > 1

            response = create_v2_response(
                paginated_people,
                metadata={
                    "service": "people_service",
                    "version": "advanced_search",
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "total_count": total_count,
                        "total_pages": total_pages,
                        "has_next": has_next,
                        "has_prev": has_prev,
                    },
                    "search_criteria": {
                        "query": query,
                        "filters": filters,
                        "sort_by": sort_by,
                        "sort_order": sort_order,
                    },
                },
            )

            self.logger.log_api_response(
                "POST",
                "/admin/people/search",
                200,
                additional_context={"results_count": len(paginated_people)},
            )
            return response

        except Exception as e:
            self.logger.error(
                "Failed to perform advanced search",
                operation="advanced_search_users",
                error_type=type(e).__name__,
            )
            raise handle_database_error("performing advanced search", e)

    async def execute_bulk_operation(
        self,
        operation: str,
        user_ids: List[str],
        parameters: Optional[Dict[str, Any]] = None,
        admin_user: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute bulk operations on multiple users.

        Args:
            operation: Type of operation to perform
            user_ids: List of user IDs to operate on
            parameters: Additional parameters for the operation
            admin_user: Admin user performing the operation
        """
        try:
            self.logger.log_api_request("POST", "/admin/people/bulk-operation")

            # Initialize result tracking
            results = {
                "operation": operation,
                "total_requested": len(user_ids),
                "successful": [],
                "failed": [],
                "skipped": [],
                "summary": {},
            }

            # Validate operation type
            valid_operations = [
                "activate",
                "deactivate",
                "suspend",
                "delete",
                "assign_role",
                "remove_role",
                "update_status",
                "send_notification",
                "export",
            ]

            if operation not in valid_operations:
                raise ValueError(f"Invalid operation: {operation}")

            # Process each user
            for user_id in user_ids:
                try:
                    result = await self._execute_single_user_operation(
                        operation, user_id, parameters, admin_user
                    )
                    if result["success"]:
                        results["successful"].append(
                            {"user_id": user_id, "result": result["data"]}
                        )
                    else:
                        results["failed"].append(
                            {"user_id": user_id, "error": result["error"]}
                        )
                except Exception as e:
                    results["failed"].append({"user_id": user_id, "error": str(e)})

            # Generate summary
            results["summary"] = {
                "success_count": len(results["successful"]),
                "failure_count": len(results["failed"]),
                "skip_count": len(results["skipped"]),
                "success_rate": (
                    len(results["successful"]) / len(user_ids) * 100 if user_ids else 0
                ),
            }

            response = create_v2_response(
                results,
                metadata={
                    "service": "people_service",
                    "version": "bulk_operation",
                    "operation_type": operation,
                    "admin_user": admin_user.get("id") if admin_user else None,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            self.logger.log_api_response(
                "POST",
                "/admin/people/bulk-operation",
                200,
                additional_context={
                    "operation": operation,
                    "success_count": results["summary"]["success_count"],
                    "failure_count": results["summary"]["failure_count"],
                },
            )
            return response

        except Exception as e:
            self.logger.error(
                "Failed to execute bulk operation",
                operation="execute_bulk_operation",
                bulk_operation=operation,
                error_type=type(e).__name__,
            )
            raise handle_database_error("executing bulk operation", e)

    async def manage_user_lifecycle(
        self,
        user_id: str,
        action: str,
        parameters: Optional[Dict[str, Any]] = None,
        admin_user: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Manage user lifecycle operations.

        Args:
            user_id: ID of the user to manage
            action: Lifecycle action to perform
            parameters: Additional parameters for the action
            admin_user: Admin user performing the action
        """
        try:
            self.logger.log_api_request("POST", f"/admin/people/{user_id}/lifecycle")

            # Validate action
            valid_actions = [
                "activate",
                "deactivate",
                "suspend",
                "unsuspend",
                "lock",
                "unlock",
                "reset_password",
                "force_password_change",
                "archive",
                "restore",
            ]

            if action not in valid_actions:
                raise ValueError(f"Invalid lifecycle action: {action}")

            # Get current user data
            current_user = await self.db_service.get_person(user_id)
            if not current_user:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
                )

            # Execute lifecycle action
            result = await self._execute_lifecycle_action(
                user_id, action, parameters, admin_user, current_user
            )

            response = create_v2_response(
                result,
                metadata={
                    "service": "people_service",
                    "version": "lifecycle_management",
                    "action": action,
                    "user_id": user_id,
                    "admin_user": admin_user.get("id") if admin_user else None,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            self.logger.log_api_response(
                "POST",
                f"/admin/people/{user_id}/lifecycle",
                200,
                additional_context={"action": action, "success": result["success"]},
            )
            return response

        except Exception as e:
            if hasattr(e, "status_code"):
                raise e
            self.logger.error(
                "Failed to manage user lifecycle",
                operation="manage_user_lifecycle",
                user_id=user_id,
                action=action,
                error_type=type(e).__name__,
            )
            raise handle_database_error("managing user lifecycle", e)

    async def export_users(
        self,
        filters: Optional[Dict[str, Any]] = None,
        format: str = "csv",
        admin_user: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Export users based on search criteria.

        Args:
            filters: Filters to apply for export
            format: Export format (csv, json, xlsx)
            admin_user: Admin user performing the export
        """
        try:
            self.logger.log_api_request("POST", "/admin/people/export")

            # Get users based on filters
            all_people = await self.db_service.list_people()

            if filters:
                all_people = await self._apply_filters(all_people, filters)

            # Generate export data
            export_data = await self._generate_export_data(all_people, format)

            # Create export metadata
            export_metadata = {
                "total_records": len(all_people),
                "format": format,
                "exported_by": admin_user.get("id") if admin_user else None,
                "export_timestamp": datetime.now().isoformat(),
                "filters_applied": filters or {},
            }

            response = create_v2_response(
                {
                    "export_data": export_data,
                    "metadata": export_metadata,
                    "download_info": {
                        "filename": f"users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}",
                        "size_bytes": len(str(export_data)),
                        "record_count": len(all_people),
                    },
                },
                metadata={
                    "service": "people_service",
                    "version": "export",
                    "export_format": format,
                },
            )

            self.logger.log_api_response(
                "POST",
                "/admin/people/export",
                200,
                additional_context={
                    "format": format,
                    "record_count": len(all_people),
                },
            )
            return response

        except Exception as e:
            self.logger.error(
                "Failed to export users",
                operation="export_users",
                format=format,
                error_type=type(e).__name__,
            )
            raise handle_database_error("exporting users", e)

    # Private helper methods for Phase 2 functionality

    async def _apply_text_search(
        self, people: List[Dict[str, Any]], query: str
    ) -> List[Dict[str, Any]]:
        """Apply full-text search to people list."""
        if not query:
            return people

        query_lower = query.lower()
        filtered_people = []

        for person in people:
            # Search in multiple fields
            searchable_fields = [
                person.get("first_name", ""),
                person.get("last_name", ""),
                person.get("email", ""),
                person.get("phone", ""),
            ]

            # Include address fields if present
            if person.get("address"):
                address = person["address"]
                searchable_fields.extend(
                    [
                        address.get("city", ""),
                        address.get("state", ""),
                        address.get("country", ""),
                    ]
                )

            # Check if query matches any field
            if any(query_lower in str(field).lower() for field in searchable_fields):
                filtered_people.append(person)

        return filtered_people

    async def _apply_filters(
        self, people: List[Dict[str, Any]], filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply filters to people list."""
        filtered_people = people.copy()

        # Status filter
        if filters.get("status"):
            status_list = filters["status"]
            if isinstance(status_list, str):
                status_list = [status_list]

            filtered_people = [
                p for p in filtered_people if self._get_user_status(p) in status_list
            ]

        # Date range filters
        if filters.get("registration_date_range"):
            date_from, date_to = filters["registration_date_range"]
            filtered_people = [
                p
                for p in filtered_people
                if self._is_in_date_range(p.get("created_at"), date_from, date_to)
            ]

        if filters.get("activity_date_range"):
            date_from, date_to = filters["activity_date_range"]
            filtered_people = [
                p
                for p in filtered_people
                if self._is_in_date_range(p.get("last_activity"), date_from, date_to)
            ]

        # Age range filter
        if filters.get("age_range"):
            age_min = filters["age_range"].get("min", 0)
            age_max = filters["age_range"].get("max", 150)
            filtered_people = [
                p
                for p in filtered_people
                if self._is_in_age_range(p.get("date_of_birth"), age_min, age_max)
            ]

        # Location filter
        if filters.get("location"):
            location = filters["location"].lower()
            filtered_people = [
                p
                for p in filtered_people
                if p.get("address") and location in p["address"].get("city", "").lower()
            ]

        # Has projects filter
        if filters.get("has_projects") is not None:
            has_projects = filters["has_projects"]
            # Mock implementation - in real system would check project associations
            filtered_people = [
                p
                for p in filtered_people
                if bool(p.get("project_count", 0) > 0) == has_projects
            ]

        return filtered_people

    async def _apply_sorting(
        self, people: List[Dict[str, Any]], sort_by: str, sort_order: str
    ) -> List[Dict[str, Any]]:
        """Apply sorting to people list."""
        reverse = sort_order.lower() == "desc"

        # Define sort key function
        def get_sort_key(person):
            if sort_by == "name":
                return f"{person.get('first_name', '')} {person.get('last_name', '')}"
            elif sort_by == "email":
                return person.get("email", "")
            elif sort_by == "created_at":
                return person.get("created_at", "")
            elif sort_by == "last_activity":
                return person.get("last_activity", "")
            else:
                return person.get(sort_by, "")

        try:
            return sorted(people, key=get_sort_key, reverse=reverse)
        except Exception:
            # Fallback to original order if sorting fails
            return people

    def _get_user_status(self, person: Dict[str, Any]) -> str:
        """Determine user status based on person data."""
        if not person.get("is_active", True):
            return "inactive"
        elif person.get("account_locked_until"):
            return "locked"
        elif person.get("is_suspended", False):
            return "suspended"
        else:
            return "active"

    def _is_in_date_range(
        self, date_str: Optional[str], date_from: Optional[str], date_to: Optional[str]
    ) -> bool:
        """Check if date is within specified range."""
        if not date_str:
            return not date_from and not date_to

        try:
            date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()

            if date_from:
                from_date = datetime.fromisoformat(date_from).date()
                if date_obj < from_date:
                    return False

            if date_to:
                to_date = datetime.fromisoformat(date_to).date()
                if date_obj > to_date:
                    return False

            return True
        except (ValueError, AttributeError):
            return False

    def _is_in_age_range(
        self, birth_date_str: Optional[str], age_min: int, age_max: int
    ) -> bool:
        """Check if user age is within specified range."""
        if not birth_date_str:
            return False

        try:
            birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
            age = (datetime.now() - birth_date).days // 365
            return age_min <= age <= age_max
        except (ValueError, AttributeError):
            return False

    async def _execute_single_user_operation(
        self,
        operation: str,
        user_id: str,
        parameters: Optional[Dict[str, Any]],
        admin_user: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Execute a single user operation."""
        try:
            # Get current user data
            current_user = await self.db_service.get_person(user_id)
            if not current_user:
                return {"success": False, "error": "User not found"}

            # Execute operation based on type
            if operation == "activate":
                return await self._activate_user(user_id, current_user, admin_user)
            elif operation == "deactivate":
                return await self._deactivate_user(user_id, current_user, admin_user)
            elif operation == "suspend":
                return await self._suspend_user(user_id, current_user, admin_user)
            elif operation == "delete":
                return await self._delete_user(user_id, current_user, admin_user)
            elif operation == "assign_role":
                role = parameters.get("role") if parameters else None
                return await self._assign_role(user_id, role, current_user, admin_user)
            elif operation == "remove_role":
                role = parameters.get("role") if parameters else None
                return await self._remove_role(user_id, role, current_user, admin_user)
            elif operation == "send_notification":
                message = parameters.get("message") if parameters else None
                return await self._send_notification(
                    user_id, message, current_user, admin_user
                )
            elif operation == "export":
                return {"success": True, "data": current_user}
            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _execute_lifecycle_action(
        self,
        user_id: str,
        action: str,
        parameters: Optional[Dict[str, Any]],
        admin_user: Optional[Dict[str, Any]],
        current_user: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a lifecycle action on a user."""
        try:
            # Create update data based on action
            update_data = {}

            if action == "activate":
                update_data = {"is_active": True, "is_suspended": False}
            elif action == "deactivate":
                update_data = {"is_active": False}
            elif action == "suspend":
                update_data = {"is_suspended": True}
            elif action == "unsuspend":
                update_data = {"is_suspended": False}
            elif action == "lock":
                update_data = {
                    "account_locked_until": (
                        datetime.now() + timedelta(hours=24)
                    ).isoformat()
                }
            elif action == "unlock":
                update_data = {"account_locked_until": None}
            elif action == "force_password_change":
                update_data = {"require_password_change": True}
            elif action == "archive":
                update_data = {"is_active": False, "archived": True}
            elif action == "restore":
                update_data = {"is_active": True, "archived": False}

            # Apply the update (mock implementation)
            # In real implementation, this would update the database
            result = {
                "success": True,
                "action": action,
                "user_id": user_id,
                "changes_applied": update_data,
                "previous_state": {
                    "is_active": current_user.get("is_active", True),
                    "is_suspended": current_user.get("is_suspended", False),
                },
                "timestamp": datetime.now().isoformat(),
            }

            return result

        except Exception as e:
            return {
                "success": False,
                "action": action,
                "user_id": user_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def _generate_export_data(
        self, people: List[Dict[str, Any]], format: str
    ) -> Any:
        """Generate export data in specified format."""
        if format == "json":
            return people
        elif format == "csv":
            # Mock CSV generation - in real implementation would use pandas or csv module
            csv_data = "id,first_name,last_name,email,phone,is_active,created_at\n"
            for person in people:
                csv_data += (
                    f"{person.get('id', '')},"
                    f"{person.get('first_name', '')},"
                    f"{person.get('last_name', '')},"
                    f"{person.get('email', '')},"
                    f"{person.get('phone', '')},"
                    f"{person.get('is_active', True)},"
                    f"{person.get('created_at', '')}\n"
                )
            return csv_data
        else:
            return people  # Default to JSON format

    # Mock implementations for bulk operations
    async def _activate_user(
        self, user_id: str, current_user: Dict[str, Any], admin_user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Activate a user account."""
        return {
            "success": True,
            "data": {"user_id": user_id, "status": "activated", "is_active": True},
        }

    async def _deactivate_user(
        self, user_id: str, current_user: Dict[str, Any], admin_user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deactivate a user account."""
        return {
            "success": True,
            "data": {"user_id": user_id, "status": "deactivated", "is_active": False},
        }

    async def _suspend_user(
        self, user_id: str, current_user: Dict[str, Any], admin_user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Suspend a user account."""
        return {
            "success": True,
            "data": {"user_id": user_id, "status": "suspended", "is_suspended": True},
        }

    async def _delete_user(
        self, user_id: str, current_user: Dict[str, Any], admin_user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Delete a user account (soft delete)."""
        return {
            "success": True,
            "data": {"user_id": user_id, "status": "deleted", "deleted": True},
        }

    async def _assign_role(
        self,
        user_id: str,
        role: str,
        current_user: Dict[str, Any],
        admin_user: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Assign a role to a user."""
        if not role:
            return {"success": False, "error": "Role parameter required"}
        return {
            "success": True,
            "data": {"user_id": user_id, "role_assigned": role},
        }

    async def _remove_role(
        self,
        user_id: str,
        role: str,
        current_user: Dict[str, Any],
        admin_user: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Remove a role from a user."""
        if not role:
            return {"success": False, "error": "Role parameter required"}
        return {
            "success": True,
            "data": {"user_id": user_id, "role_removed": role},
        }

    async def _send_notification(
        self,
        user_id: str,
        message: str,
        current_user: Dict[str, Any],
        admin_user: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Send a notification to a user."""
        if not message:
            return {"success": False, "error": "Message parameter required"}
        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "notification_sent": True,
                "message": message,
            },
        }

    # Phase 2: Advanced User Management - Import/Export and Communication Methods

    async def import_users_from_file(
        self,
        file,
        validate_only: bool = False,
        skip_duplicates: bool = True,
        update_existing: bool = False,
        imported_by: str = None,
    ) -> Dict[str, Any]:
        """Import users from uploaded CSV/Excel file with comprehensive validation."""
        try:
            # Import pandas only when needed
            try:
                import pandas as pd
                import io
            except ImportError:
                return {
                    "success": False,
                    "error": "File import functionality requires pandas and openpyxl packages. Please install them or contact your administrator.",
                }

            from datetime import datetime

            self.logger.info(
                f"Starting user import: validate_only={validate_only}, skip_duplicates={skip_duplicates}"
            )

            # Read file content
            file_content = await file.read()

            # Determine file type and parse
            if file.filename.lower().endswith(".csv"):
                df = pd.read_csv(io.BytesIO(file_content))
            elif file.filename.lower().endswith((".xlsx", ".xls")):
                df = pd.read_excel(io.BytesIO(file_content))
            else:
                return {
                    "success": False,
                    "error": "Unsupported file format. Only CSV and Excel files are supported.",
                }

            # Validate required columns
            required_columns = ["name", "email"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return {
                    "success": False,
                    "error": f"Missing required columns: {', '.join(missing_columns)}",
                    "required_columns": required_columns,
                    "found_columns": list(df.columns),
                }

            # Process and validate data
            processed_count = len(df)
            success_count = 0
            error_count = 0
            duplicate_count = 0
            errors = []
            created_users = []

            for index, row in df.iterrows():
                try:
                    # Basic validation
                    if pd.isna(row["name"]) or pd.isna(row["email"]):
                        error_count += 1
                        errors.append(
                            {
                                "row": index + 1,
                                "error": "Name and email are required fields",
                            }
                        )
                        continue

                    # Email format validation
                    email = str(row["email"]).strip().lower()
                    if "@" not in email or "." not in email:
                        error_count += 1
                        errors.append(
                            {
                                "row": index + 1,
                                "error": f"Invalid email format: {email}",
                            }
                        )
                        continue

                    # Check for duplicates
                    existing_user = await self.get_person_by_email(email)
                    if existing_user.get("success") and existing_user.get("data"):
                        if skip_duplicates:
                            duplicate_count += 1
                            continue
                        elif update_existing:
                            # Update existing user logic would go here
                            success_count += 1
                            continue
                        else:
                            error_count += 1
                            errors.append(
                                {
                                    "row": index + 1,
                                    "error": f"Email already exists: {email}",
                                }
                            )
                            continue

                    # Prepare user data
                    user_data = {
                        "name": str(row["name"]).strip(),
                        "email": email,
                        "phone": (
                            str(row.get("phone", "")).strip()
                            if pd.notna(row.get("phone"))
                            else None
                        ),
                        "address": (
                            str(row.get("address", "")).strip()
                            if pd.notna(row.get("address"))
                            else None
                        ),
                        "city": (
                            str(row.get("city", "")).strip()
                            if pd.notna(row.get("city"))
                            else None
                        ),
                        "country": (
                            str(row.get("country", "")).strip()
                            if pd.notna(row.get("country"))
                            else None
                        ),
                        "date_of_birth": (
                            str(row.get("date_of_birth", "")).strip()
                            if pd.notna(row.get("date_of_birth"))
                            else None
                        ),
                        "occupation": (
                            str(row.get("occupation", "")).strip()
                            if pd.notna(row.get("occupation"))
                            else None
                        ),
                    }

                    # Remove empty string values
                    user_data = {
                        k: v for k, v in user_data.items() if v not in [None, "", "nan"]
                    }

                    if not validate_only:
                        # Create the user
                        from ..models.person import PersonCreate

                        person_create = PersonCreate(**user_data)
                        result = await self.create_person_v2(person_create)

                        if result.get("success"):
                            success_count += 1
                            created_users.append(result.get("data", {}).get("id"))
                        else:
                            error_count += 1
                            errors.append(
                                {
                                    "row": index + 1,
                                    "error": f"Failed to create user: {result.get('error', 'Unknown error')}",
                                }
                            )
                    else:
                        # Just validation, count as success
                        success_count += 1

                except Exception as e:
                    error_count += 1
                    errors.append(
                        {"row": index + 1, "error": f"Processing error: {str(e)}"}
                    )

            # Prepare result
            result = {
                "success": True,
                "processed_count": processed_count,
                "success_count": success_count,
                "error_count": error_count,
                "duplicate_count": duplicate_count,
                "validation_only": validate_only,
                "errors": errors[:50],  # Limit errors to first 50
                "total_errors": len(errors),
                "imported_by": imported_by,
                "import_timestamp": datetime.utcnow().isoformat(),
            }

            if not validate_only and created_users:
                result["created_user_ids"] = created_users

            self.logger.info(
                f"User import completed: {success_count} success, {error_count} errors, {duplicate_count} duplicates"
            )

            return result

        except Exception as e:
            self.logger.error(f"Failed to import users from file: {str(e)}")
            return {"success": False, "error": f"Import failed: {str(e)}"}

    async def send_communication(
        self,
        communication_type: str,
        subject: str,
        content: str,
        target_users: List[str],
        sender: Dict[str, Any],
        schedule_time: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send communication to users with comprehensive tracking."""
        try:
            from datetime import datetime
            import uuid

            communication_id = f"comm_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

            self.logger.info(
                f"Sending {communication_type} communication to {len(target_users)} users",
                extra={"communication_id": communication_id},
            )

            # Validate communication type
            valid_types = ["email", "notification", "announcement", "sms"]
            if communication_type not in valid_types:
                return {
                    "success": False,
                    "error": f"Invalid communication type. Must be one of: {', '.join(valid_types)}",
                }

            # Validate target users exist
            valid_users = []
            invalid_users = []

            for user_id in target_users:
                user_result = await self.get_person_by_id_v2(user_id)
                if user_result.get("success") and user_result.get("data"):
                    valid_users.append(user_id)
                else:
                    invalid_users.append(user_id)

            if not valid_users:
                return {
                    "success": False,
                    "error": "No valid target users found",
                    "invalid_users": invalid_users,
                }

            # Simulate communication sending (in real implementation, integrate with email/SMS services)
            sent_count = 0
            failed_count = 0
            delivery_results = []

            for user_id in valid_users:
                try:
                    # Mock delivery logic - replace with actual service integration
                    delivery_result = {
                        "user_id": user_id,
                        "status": "sent",
                        "sent_at": datetime.utcnow().isoformat(),
                        "delivery_id": f"del_{str(uuid.uuid4())[:8]}",
                    }

                    # Simulate 95% success rate
                    import random

                    if random.random() < 0.95:
                        sent_count += 1
                        delivery_result["status"] = "sent"
                    else:
                        failed_count += 1
                        delivery_result["status"] = "failed"
                        delivery_result["error"] = "Delivery service unavailable"

                    delivery_results.append(delivery_result)

                except Exception as e:
                    failed_count += 1
                    delivery_results.append(
                        {
                            "user_id": user_id,
                            "status": "failed",
                            "error": str(e),
                            "sent_at": datetime.utcnow().isoformat(),
                        }
                    )

            # Store communication record (mock implementation)
            communication_record = {
                "communication_id": communication_id,
                "type": communication_type,
                "subject": subject,
                "content": content[:500] + "..." if len(content) > 500 else content,
                "sender_id": sender.get("id"),
                "sender_name": sender.get("name", "Unknown"),
                "target_count": len(target_users),
                "sent_count": sent_count,
                "failed_count": failed_count,
                "invalid_users_count": len(invalid_users),
                "created_at": datetime.utcnow().isoformat(),
                "scheduled_time": schedule_time,
                "metadata": metadata or {},
                "delivery_results": delivery_results[
                    :10
                ],  # Store first 10 for reference
            }

            result = {
                "success": True,
                "communication_id": communication_id,
                "type": communication_type,
                "target_count": len(target_users),
                "valid_users": len(valid_users),
                "invalid_users": len(invalid_users),
                "sent_count": sent_count,
                "failed_count": failed_count,
                "scheduled": bool(schedule_time),
                "delivery_summary": {
                    "total_targeted": len(target_users),
                    "successfully_sent": sent_count,
                    "failed_delivery": failed_count,
                    "invalid_recipients": len(invalid_users),
                },
            }

            if invalid_users:
                result["invalid_user_ids"] = invalid_users

            self.logger.info(
                f"Communication sent: {sent_count} successful, {failed_count} failed",
                extra={"communication_id": communication_id},
            )

            return result

        except Exception as e:
            self.logger.error(f"Failed to send communication: {str(e)}")
            return {"success": False, "error": f"Communication failed: {str(e)}"}

    async def get_communication_history(
        self,
        communication_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        admin_user_id: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Get communication history with analytics and filtering."""
        try:
            from datetime import datetime, timedelta
            import random

            self.logger.info(
                f"Getting communication history: type={communication_type}, page={page}, limit={limit}"
            )

            # Mock communication history data (in real implementation, query from database)
            mock_communications = []

            # Generate mock data for the last 30 days
            base_date = datetime.utcnow()
            for i in range(50):  # Generate 50 mock communications
                comm_date = base_date - timedelta(days=random.randint(0, 30))
                comm_type = random.choice(
                    ["email", "notification", "announcement", "sms"]
                )

                # Apply filters
                if communication_type and comm_type != communication_type:
                    continue

                if date_from:
                    try:
                        from_date = datetime.fromisoformat(
                            date_from.replace("Z", "+00:00")
                        )
                        if comm_date < from_date:
                            continue
                    except (ValueError, TypeError):
                        pass

                if date_to:
                    try:
                        to_date = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
                        if comm_date > to_date:
                            continue
                    except (ValueError, TypeError):
                        pass

                target_count = random.randint(10, 500)
                sent_count = int(target_count * random.uniform(0.85, 0.98))

                mock_comm = {
                    "communication_id": f"comm_{comm_date.strftime('%Y%m%d_%H%M%S')}_{i:03d}",
                    "type": comm_type,
                    "subject": f"Sample {comm_type.title()} Communication #{i + 1}",
                    "content_preview": f"This is a sample {comm_type} message content preview...",
                    "sender_id": "admin_001",
                    "sender_name": "Admin User",
                    "target_count": target_count,
                    "sent_count": sent_count,
                    "failed_count": target_count - sent_count,
                    "delivery_rate": round((sent_count / target_count) * 100, 2),
                    "created_at": comm_date.isoformat(),
                    "status": "completed",
                    "analytics": {
                        "open_rate": (
                            round(random.uniform(15, 45), 2)
                            if comm_type == "email"
                            else None
                        ),
                        "click_rate": (
                            round(random.uniform(2, 8), 2)
                            if comm_type == "email"
                            else None
                        ),
                        "bounce_rate": (
                            round(random.uniform(1, 5), 2)
                            if comm_type == "email"
                            else None
                        ),
                    },
                }

                if admin_user_id and mock_comm["sender_id"] != admin_user_id:
                    continue

                mock_communications.append(mock_comm)

            # Sort by date (newest first)
            mock_communications.sort(key=lambda x: x["created_at"], reverse=True)

            # Apply pagination
            total_count = len(mock_communications)
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            paginated_communications = mock_communications[start_idx:end_idx]

            # Calculate summary statistics
            total_sent = sum(comm["sent_count"] for comm in mock_communications)
            total_targeted = sum(comm["target_count"] for comm in mock_communications)
            avg_delivery_rate = round(
                (total_sent / total_targeted * 100) if total_targeted > 0 else 0, 2
            )

            # Type distribution
            type_distribution = {}
            for comm in mock_communications:
                comm_type = comm["type"]
                if comm_type not in type_distribution:
                    type_distribution[comm_type] = {
                        "count": 0,
                        "sent": 0,
                        "targeted": 0,
                    }
                type_distribution[comm_type]["count"] += 1
                type_distribution[comm_type]["sent"] += comm["sent_count"]
                type_distribution[comm_type]["targeted"] += comm["target_count"]

            result = {
                "success": True,
                "communications": paginated_communications,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_count": total_count,
                    "total_pages": (total_count + limit - 1) // limit,
                    "has_next": end_idx < total_count,
                    "has_previous": page > 1,
                },
                "summary": {
                    "total_communications": total_count,
                    "total_messages_sent": total_sent,
                    "total_recipients_targeted": total_targeted,
                    "average_delivery_rate": avg_delivery_rate,
                    "type_distribution": type_distribution,
                },
                "filters_applied": {
                    "communication_type": communication_type,
                    "date_from": date_from,
                    "date_to": date_to,
                    "admin_user_id": admin_user_id,
                },
            }

            return result

        except Exception as e:
            self.logger.error(f"Failed to get communication history: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to retrieve communication history: {str(e)}",
            }

    async def save_search_query(
        self,
        name: str,
        criteria: Dict[str, Any],
        admin_user_id: str,
        is_shared: bool = False,
    ) -> Dict[str, Any]:
        """Save a search query for future use."""
        try:
            from datetime import datetime
            import uuid

            search_id = str(uuid.uuid4())

            self.logger.info(
                f"Saving search query '{name}' for admin user {admin_user_id}"
            )

            # Validate search criteria
            if not criteria:
                return {"success": False, "error": "Search criteria cannot be empty"}

            # Mock saved search record (in real implementation, store in database)
            saved_search = {
                "search_id": search_id,
                "name": name,
                "criteria": criteria,
                "admin_user_id": admin_user_id,
                "is_shared": is_shared,
                "created_at": datetime.utcnow().isoformat(),
                "last_used": None,
                "usage_count": 0,
                "description": f"Saved search: {name}",
                "tags": self._extract_search_tags(criteria),
            }

            # In a real implementation, you would save this to a database
            # For now, we'll return the saved search data

            result = {
                "success": True,
                "saved_search": saved_search,
                "message": f"Search query '{name}' saved successfully",
            }

            self.logger.info(f"Search query '{name}' saved with ID {search_id}")

            return result

        except Exception as e:
            self.logger.error(f"Failed to save search query: {str(e)}")
            return {"success": False, "error": f"Failed to save search query: {str(e)}"}

    def _extract_search_tags(self, criteria: Dict[str, Any]) -> List[str]:
        """Extract tags from search criteria for categorization."""
        tags = []

        if criteria.get("status"):
            tags.extend([f"status:{status}" for status in criteria["status"]])

        if criteria.get("query"):
            tags.append("text-search")

        if criteria.get("registration_date_from") or criteria.get(
            "registration_date_to"
        ):
            tags.append("date-filter")

        if criteria.get("location"):
            tags.append("location-filter")

        if criteria.get("age_range"):
            tags.append("age-filter")

        if criteria.get("has_projects") is not None:
            tags.append("project-filter")

        return tags

    # Performance Optimization Helper Methods

    def _get_cache_service(self):
        """Get cache service from service registry."""
        try:
            from ..services.service_registry_manager import service_manager

            return service_manager.get_service("cache")
        except Exception as e:
            self.logger.debug(f"Cache service not available: {str(e)}")
            return None

    def _get_database_optimization_service(self):
        """Get database optimization service from service registry."""
        try:
            from ..services.service_registry_manager import service_manager

            return service_manager.get_service("database_optimization")
        except Exception as e:
            self.logger.debug(f"Database optimization service not available: {str(e)}")
            return None

    async def _execute_optimized_query(
        self, query_type: str, execute_func: callable, *args, **kwargs
    ):
        """Execute database query with optimization tracking and performance monitoring."""
        import time

        start_time = time.time()

        try:
            # Execute the query
            result = await execute_func(*args, **kwargs)

            # Track performance
            execution_time = time.time() - start_time
            result_count = len(result) if isinstance(result, (list, dict)) else 1

            # Report to database optimization service
            db_opt_service = self._get_database_optimization_service()
            if db_opt_service:
                await db_opt_service.track_query_performance(
                    query_type=query_type,
                    execution_time=execution_time,
                    result_count=result_count,
                    optimization_used=(
                        "projection_expression" if execution_time < 0.1 else None
                    ),
                )

            self.logger.debug(
                f"Optimized query {query_type} completed in {execution_time:.3f}s"
            )
            return result

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(
                f"Optimized query {query_type} failed after {execution_time:.3f}s: {str(e)}"
            )

            # Still track failed queries for analysis
            db_opt_service = self._get_database_optimization_service()
            if db_opt_service:
                await db_opt_service.track_query_performance(
                    query_type=f"{query_type}_failed",
                    execution_time=execution_time,
                    result_count=0,
                )

            raise

    # ==================== PASSWORD RESET SUPPORT METHODS ====================

    async def get_person(self, person_id: str) -> Optional[Person]:
        """
        Get person by ID for internal service use (e.g., password reset).
        Returns the Person object directly, not wrapped in API response format.
        """
        try:
            self.logger.debug(f"Getting person for internal use: {person_id}")
            person = await self.db_service.get_person(person_id)
            return person
        except Exception as e:
            self.logger.error(
                "Failed to get person for internal use",
                operation="get_person",
                person_id=person_id,
                error_type=type(e).__name__,
            )
            return None

    async def update_person(
        self, person_id: str, person_data: PersonUpdate
    ) -> Optional[Person]:
        """
        Update person for internal service use (e.g., password reset).
        Returns the updated Person object directly, not wrapped in API response format.
        """
        try:
            self.logger.debug(f"Updating person for internal use: {person_id}")

            # Check if person exists
            existing_person = await self.db_service.get_person(person_id)
            if not existing_person:
                self.logger.warning(f"Person not found for update: {person_id}")
                return None

            # Update person
            updated_person = await self.db_service.update_person(person_id, person_data)
            return updated_person

        except Exception as e:
            self.logger.error(
                "Failed to update person for internal use",
                operation="update_person",
                person_id=person_id,
                error_type=type(e).__name__,
            )
            return None

    async def _get_cached_or_execute(
        self, cache_key: str, execute_func: callable, ttl: int = 3600, *args, **kwargs
    ):
        """Generic method to get cached result or execute function."""
        try:
            cache_service = self._get_cache_service()
            if cache_service:
                # Try cache first
                cached_result = await cache_service.get(cache_key)
                if cached_result:
                    self.logger.debug(f"Cache hit for key: {cache_key[:20]}...")
                    return cached_result

            # Execute function
            result = await execute_func(*args, **kwargs)

            # Cache successful results
            if (
                cache_service
                and isinstance(result, dict)
                and result.get("success", True)
            ):
                await cache_service.set(cache_key, result, ttl)
                self.logger.debug(f"Cached result for key: {cache_key[:20]}...")

            return result

        except Exception as e:
            self.logger.error(f"Error in cached execution: {str(e)}")
            # Fallback to direct execution
            return await execute_func(*args, **kwargs)

    async def clear_user_cache(self, user_id: Optional[str] = None):
        """Clear user-related cache entries."""
        try:
            cache_service = self._get_cache_service()
            if not cache_service:
                return False

            if user_id:
                # Clear specific user cache
                await cache_service.clear_prefix(f"user:{user_id}")
                self.logger.info(f"Cleared cache for user: {user_id}")
            else:
                # Clear all people-related cache
                await cache_service.clear_prefix("people_")
                await cache_service.clear_prefix("dashboard_")
                await cache_service.clear_prefix("analytics_")
                self.logger.info("Cleared all people-related cache")

            return True

        except Exception as e:
            self.logger.error(f"Error clearing user cache: {str(e)}")
            return False

    async def warm_dashboard_cache(self):
        """Warm up dashboard cache with frequently accessed data."""
        try:
            self.logger.info("Starting dashboard cache warming")

            # Pre-load dashboard data
            await self.get_dashboard_data()

            # Pre-load analytics data
            await self.get_registration_trends()
            await self.get_activity_patterns()
            await self.get_demographic_insights()
            await self.get_engagement_metrics()

            self.logger.info("Dashboard cache warming completed")
            return True

        except Exception as e:
            self.logger.error(f"Error warming dashboard cache: {str(e)}")
            return False
