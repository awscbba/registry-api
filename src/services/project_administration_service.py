"""
Project Administration Service for Phase 3 Projects Administration.

Provides advanced project management capabilities including:
- Bulk operations (create, update, delete multiple projects)
- Advanced search and filtering
- Project analytics and reporting
- Project templates management
- Enhanced project dashboard data
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from enum import Enum
import uuid
import json

from ..core.base_service import BaseService
from ..models.project import ProjectCreate, ProjectUpdate, Project, ProjectStatus
from ..repositories.project_repository import ProjectRepository
from ..utils.logging_config import get_handler_logger


class ProjectSortField(str, Enum):
    """Available fields for sorting projects."""

    NAME = "name"
    CREATED_AT = "createdAt"
    UPDATED_AT = "updatedAt"
    START_DATE = "startDate"
    END_DATE = "endDate"
    STATUS = "status"
    MAX_PARTICIPANTS = "maxParticipants"


class SortOrder(str, Enum):
    """Sort order options."""

    ASC = "asc"
    DESC = "desc"


class ProjectTemplate(dict):
    """Project template structure."""

    def __init__(self, name: str, description: str, template_data: Dict[str, Any]):
        super().__init__()
        self.update(
            {
                "id": str(uuid.uuid4()),
                "name": name,
                "description": description,
                "template_data": template_data,
                "created_at": datetime.utcnow().isoformat(),
                "usage_count": 0,
            }
        )


class BulkOperationResult:
    """Result of a bulk operation."""

    def __init__(self):
        self.successful: List[str] = []
        self.failed: List[Dict[str, Any]] = []
        self.total_processed: int = 0

    def add_success(self, item_id: str):
        """Add a successful operation."""
        self.successful.append(item_id)
        self.total_processed += 1

    def add_failure(self, item_id: str, error: str):
        """Add a failed operation."""
        self.failed.append({"id": item_id, "error": error})
        self.total_processed += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "total_processed": self.total_processed,
            "successful_count": len(self.successful),
            "failed_count": len(self.failed),
            "successful_ids": self.successful,
            "failures": self.failed,
            "success_rate": (
                (len(self.successful) / self.total_processed * 100)
                if self.total_processed > 0
                else 0
            ),
        }


class ProjectAdministrationService(BaseService):
    """
    Advanced project administration service providing enhanced management capabilities.

    Features:
    - Advanced search and filtering
    - Bulk operations
    - Project analytics
    - Template management
    - Dashboard data aggregation
    """

    def __init__(self):
        super().__init__("project_administration")
        self.project_repository = ProjectRepository(table_name="projects")
        self.templates: Dict[str, ProjectTemplate] = {}
        self._initialize_default_templates()

    async def initialize(self):
        """Initialize the project administration service."""
        try:
            # Test repository connectivity
            count_result = await self.project_repository.count()
            if count_result.success:
                self.logger.info(
                    f"Project administration service initialized successfully. "
                    f"Found {count_result.data} projects and {len(self.templates)} templates."
                )
                return True
            else:
                self.logger.error(
                    f"Repository health check failed: {count_result.error}"
                )
                return False
        except Exception as e:
            self.logger.error(
                f"Failed to initialize project administration service: {str(e)}"
            )
            return False

    def _initialize_default_templates(self):
        """Initialize default project templates."""
        default_templates = [
            {
                "name": "Software Development Project",
                "description": "Template for software development projects",
                "template_data": {
                    "name": "New Software Project",
                    "description": "A new software development project",
                    "startDate": "2024-01-01",
                    "endDate": "2024-06-01",
                    "category": "Software Development",
                    "requirements": "Programming experience required",
                    "maxParticipants": 10,
                    "status": ProjectStatus.PENDING,
                },
            },
            {
                "name": "Research Project",
                "description": "Template for research and academic projects",
                "template_data": {
                    "name": "New Research Project",
                    "description": "A new research and academic project",
                    "startDate": "2024-01-01",
                    "endDate": "2024-12-01",
                    "category": "Research",
                    "requirements": "Academic background preferred",
                    "maxParticipants": 5,
                    "status": ProjectStatus.PENDING,
                },
            },
            {
                "name": "Community Event",
                "description": "Template for community events and workshops",
                "template_data": {
                    "name": "New Community Event",
                    "description": "A new community event or workshop",
                    "startDate": "2024-01-01",
                    "endDate": "2024-01-03",
                    "category": "Community",
                    "requirements": "Open to all community members",
                    "maxParticipants": 50,
                    "status": ProjectStatus.PENDING,
                },
            },
        ]

        for template_data in default_templates:
            template = ProjectTemplate(
                name=template_data["name"],
                description=template_data["description"],
                template_data=template_data["template_data"],
            )
            self.templates[template["id"]] = template

    async def search_projects(
        self,
        query: Optional[str] = None,
        status: Optional[ProjectStatus] = None,
        category: Optional[str] = None,
        start_date_from: Optional[str] = None,
        start_date_to: Optional[str] = None,
        end_date_from: Optional[str] = None,
        end_date_to: Optional[str] = None,
        min_participants: Optional[int] = None,
        max_participants: Optional[int] = None,
        location: Optional[str] = None,
        sort_by: ProjectSortField = ProjectSortField.CREATED_AT,
        sort_order: SortOrder = SortOrder.DESC,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Advanced project search with multiple filters and sorting.

        Args:
            query: Text search in name and description
            status: Filter by project status
            category: Filter by project category
            start_date_from: Filter projects starting from this date
            start_date_to: Filter projects starting before this date
            end_date_from: Filter projects ending from this date
            end_date_to: Filter projects ending before this date
            min_participants: Minimum number of participants
            max_participants: Maximum number of participants
            location: Filter by location (partial match)
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
            limit: Maximum number of results
            offset: Number of results to skip
        """
        try:
            # Get all projects first (in a real implementation, this would be optimized with database queries)
            all_projects_result = await self.project_repository.get_all()

            if not all_projects_result.success:
                return {
                    "success": False,
                    "error": f"Failed to retrieve projects: {all_projects_result.error}",
                    "projects": [],
                    "total_count": 0,
                    "filtered_count": 0,
                }

            projects = all_projects_result.data
            total_count = len(projects)

            # Apply filters
            filtered_projects = self._apply_filters(
                projects,
                query,
                status,
                category,
                start_date_from,
                start_date_to,
                end_date_from,
                end_date_to,
                min_participants,
                max_participants,
                location,
            )

            filtered_count = len(filtered_projects)

            # Apply sorting
            sorted_projects = self._sort_projects(
                filtered_projects, sort_by, sort_order
            )

            # Apply pagination
            paginated_projects = sorted_projects[offset : offset + limit]

            return {
                "success": True,
                "projects": paginated_projects,
                "total_count": total_count,
                "filtered_count": filtered_count,
                "returned_count": len(paginated_projects),
                "offset": offset,
                "limit": limit,
                "has_more": offset + limit < filtered_count,
                "filters_applied": {
                    "query": query,
                    "status": status,
                    "category": category,
                    "date_range": {
                        "start_from": start_date_from,
                        "start_to": start_date_to,
                        "end_from": end_date_from,
                        "end_to": end_date_to,
                    },
                    "participants_range": {
                        "min": min_participants,
                        "max": max_participants,
                    },
                    "location": location,
                },
                "sorting": {"field": sort_by, "order": sort_order},
            }

        except Exception as e:
            self.logger.error(f"Failed to search projects: {str(e)}")
            return {
                "success": False,
                "error": f"Search operation failed: {str(e)}",
                "projects": [],
                "total_count": 0,
                "filtered_count": 0,
            }

    def _apply_filters(
        self,
        projects: List[Dict[str, Any]],
        query: Optional[str],
        status: Optional[ProjectStatus],
        category: Optional[str],
        start_date_from: Optional[str],
        start_date_to: Optional[str],
        end_date_from: Optional[str],
        end_date_to: Optional[str],
        min_participants: Optional[int],
        max_participants: Optional[int],
        location: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Apply filters to project list."""
        filtered = projects

        # Text search in name and description
        if query:
            query_lower = query.lower()
            filtered = [
                p
                for p in filtered
                if query_lower in p.get("name", "").lower()
                or query_lower in p.get("description", "").lower()
            ]

        # Status filter
        if status:
            filtered = [p for p in filtered if p.get("status") == status]

        # Category filter
        if category:
            filtered = [p for p in filtered if p.get("category") == category]

        # Date range filters
        if start_date_from:
            filtered = [
                p for p in filtered if p.get("startDate", "") >= start_date_from
            ]

        if start_date_to:
            filtered = [p for p in filtered if p.get("startDate", "") <= start_date_to]

        if end_date_from:
            filtered = [p for p in filtered if p.get("endDate", "") >= end_date_from]

        if end_date_to:
            filtered = [p for p in filtered if p.get("endDate", "") <= end_date_to]

        # Participants range filters
        if min_participants is not None:
            filtered = [
                p for p in filtered if p.get("maxParticipants", 0) >= min_participants
            ]

        if max_participants is not None:
            filtered = [
                p for p in filtered if p.get("maxParticipants", 0) <= max_participants
            ]

        # Location filter (partial match)
        if location:
            location_lower = location.lower()
            filtered = [
                p for p in filtered if location_lower in p.get("location", "").lower()
            ]

        return filtered

    def _sort_projects(
        self,
        projects: List[Dict[str, Any]],
        sort_by: ProjectSortField,
        sort_order: SortOrder,
    ) -> List[Dict[str, Any]]:
        """Sort projects by specified field and order."""
        reverse = sort_order == SortOrder.DESC

        # Define sort key functions
        sort_keys = {
            ProjectSortField.NAME: lambda p: p.get("name", "").lower(),
            ProjectSortField.CREATED_AT: lambda p: p.get("createdAt", ""),
            ProjectSortField.UPDATED_AT: lambda p: p.get("updatedAt", ""),
            ProjectSortField.START_DATE: lambda p: p.get("startDate", ""),
            ProjectSortField.END_DATE: lambda p: p.get("endDate", ""),
            ProjectSortField.STATUS: lambda p: p.get("status", ""),
            ProjectSortField.MAX_PARTICIPANTS: lambda p: p.get("maxParticipants", 0),
        }

        sort_key = sort_keys.get(sort_by, sort_keys[ProjectSortField.CREATED_AT])

        try:
            return sorted(projects, key=sort_key, reverse=reverse)
        except Exception as e:
            self.logger.warning(f"Failed to sort projects by {sort_by}: {str(e)}")
            return projects

    async def bulk_create_projects(
        self, projects_data: List[ProjectCreate]
    ) -> BulkOperationResult:
        """Create multiple projects in bulk."""
        result = BulkOperationResult()

        for project_data in projects_data:
            try:
                # Generate unique ID for the project
                project_id = str(uuid.uuid4())

                # Create project using repository
                create_result = await self.project_repository.create(
                    project_id, project_data.dict()
                )

                if create_result.success:
                    result.add_success(project_id)
                    self.logger.info(f"Successfully created project {project_id}")
                else:
                    result.add_failure(project_id, create_result.error)
                    self.logger.error(
                        f"Failed to create project {project_id}: {create_result.error}"
                    )

            except Exception as e:
                error_msg = f"Exception during project creation: {str(e)}"
                result.add_failure("unknown", error_msg)
                self.logger.error(error_msg)

        self.logger.info(
            f"Bulk create completed: {len(result.successful)} successful, "
            f"{len(result.failed)} failed out of {result.total_processed} projects"
        )

        return result

    async def bulk_update_projects(
        self, updates: List[Dict[str, Any]]
    ) -> BulkOperationResult:
        """Update multiple projects in bulk."""
        result = BulkOperationResult()

        for update_data in updates:
            project_id = update_data.get("id")
            if not project_id:
                result.add_failure("unknown", "Missing project ID")
                continue

            try:
                # Remove ID from update data
                update_fields = {k: v for k, v in update_data.items() if k != "id"}

                # Update project using repository
                update_result = await self.project_repository.update(
                    project_id, update_fields
                )

                if update_result.success:
                    result.add_success(project_id)
                    self.logger.info(f"Successfully updated project {project_id}")
                else:
                    result.add_failure(project_id, update_result.error)
                    self.logger.error(
                        f"Failed to update project {project_id}: {update_result.error}"
                    )

            except Exception as e:
                error_msg = f"Exception during project update: {str(e)}"
                result.add_failure(project_id, error_msg)
                self.logger.error(error_msg)

        self.logger.info(
            f"Bulk update completed: {len(result.successful)} successful, "
            f"{len(result.failed)} failed out of {result.total_processed} projects"
        )

        return result

    async def bulk_delete_projects(self, project_ids: List[str]) -> BulkOperationResult:
        """Delete multiple projects in bulk."""
        result = BulkOperationResult()

        for project_id in project_ids:
            try:
                # Delete project using repository
                delete_result = await self.project_repository.delete(project_id)

                if delete_result.success:
                    result.add_success(project_id)
                    self.logger.info(f"Successfully deleted project {project_id}")
                else:
                    result.add_failure(project_id, delete_result.error)
                    self.logger.error(
                        f"Failed to delete project {project_id}: {delete_result.error}"
                    )

            except Exception as e:
                error_msg = f"Exception during project deletion: {str(e)}"
                result.add_failure(project_id, error_msg)
                self.logger.error(error_msg)

        self.logger.info(
            f"Bulk delete completed: {len(result.successful)} successful, "
            f"{len(result.failed)} failed out of {result.total_processed} projects"
        )

        return result

    async def get_project_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive project analytics."""
        try:
            # Get all projects
            all_projects_result = await self.project_repository.get_all()

            if not all_projects_result.success:
                return {
                    "success": False,
                    "error": f"Failed to retrieve projects: {all_projects_result.error}",
                }

            projects = all_projects_result.data

            # Calculate date range for recent activity
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            # Basic statistics
            total_projects = len(projects)

            # Status distribution
            status_counts = {}
            for status in ProjectStatus:
                status_counts[status.value] = len(
                    [p for p in projects if p.get("status") == status.value]
                )

            # Category distribution
            categories = {}
            for project in projects:
                category = project.get("category", "Uncategorized")
                categories[category] = categories.get(category, 0) + 1

            # Recent activity (projects created in the last N days)
            recent_projects = [
                p
                for p in projects
                if self._parse_date(p.get("createdAt", "")) >= start_date
            ]

            # Upcoming projects (starting in the next 30 days)
            upcoming_cutoff = end_date + timedelta(days=30)
            upcoming_projects = [
                p
                for p in projects
                if start_date
                <= self._parse_date(p.get("startDate", ""))
                <= upcoming_cutoff
            ]

            # Projects by month (last 12 months)
            monthly_stats = self._calculate_monthly_stats(projects)

            # Participant statistics
            total_max_participants = sum(p.get("maxParticipants", 0) for p in projects)
            avg_max_participants = (
                total_max_participants / total_projects if total_projects > 0 else 0
            )

            return {
                "success": True,
                "analytics_period_days": days,
                "generated_at": datetime.utcnow().isoformat(),
                "overview": {
                    "total_projects": total_projects,
                    "recent_projects": len(recent_projects),
                    "upcoming_projects": len(upcoming_projects),
                    "total_max_participants": total_max_participants,
                    "average_max_participants": round(avg_max_participants, 1),
                },
                "status_distribution": status_counts,
                "category_distribution": categories,
                "monthly_trends": monthly_stats,
                "recent_activity": {
                    "new_projects": len(recent_projects),
                    "projects": recent_projects[:10],  # Show latest 10
                },
                "upcoming_projects": {
                    "count": len(upcoming_projects),
                    "projects": upcoming_projects[:10],  # Show next 10
                },
            }

        except Exception as e:
            self.logger.error(f"Failed to generate project analytics: {str(e)}")
            return {"success": False, "error": f"Analytics generation failed: {str(e)}"}

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime object."""
        try:
            # Handle ISO format with timezone
            if "T" in date_str:
                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            # Handle date-only format
            else:
                return datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            return datetime.min

    def _calculate_monthly_stats(
        self, projects: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Calculate monthly project statistics for the last 12 months."""
        monthly_stats = []
        current_date = datetime.utcnow()

        for i in range(12):
            # Calculate month start and end
            month_date = current_date.replace(day=1) - timedelta(days=i * 30)
            month_start = month_date.replace(day=1)
            next_month = (
                month_start.replace(month=month_start.month + 1)
                if month_start.month < 12
                else month_start.replace(year=month_start.year + 1, month=1)
            )

            # Count projects created in this month
            month_projects = [
                p
                for p in projects
                if month_start <= self._parse_date(p.get("createdAt", "")) < next_month
            ]

            monthly_stats.append(
                {
                    "month": month_start.strftime("%Y-%m"),
                    "month_name": month_start.strftime("%B %Y"),
                    "projects_created": len(month_projects),
                    "total_participants": sum(
                        p.get("maxParticipants", 0) for p in month_projects
                    ),
                }
            )

        return list(reversed(monthly_stats))  # Return chronological order

    async def get_project_templates(self) -> Dict[str, Any]:
        """Get all available project templates."""
        try:
            templates_list = list(self.templates.values())

            return {
                "success": True,
                "templates": templates_list,
                "total_count": len(templates_list),
            }

        except Exception as e:
            self.logger.error(f"Failed to get project templates: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to retrieve templates: {str(e)}",
                "templates": [],
            }

    async def create_project_from_template(
        self, template_id: str, project_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new project from a template."""
        try:
            if template_id not in self.templates:
                return {"success": False, "error": f"Template {template_id} not found"}

            template = self.templates[template_id]

            # Merge template data with provided data (provided data takes precedence)
            merged_data = {**template["template_data"], **project_data}

            # Create project
            project_create = ProjectCreate(**merged_data)
            project_id = str(uuid.uuid4())

            create_result = await self.project_repository.create(
                project_id, project_create.dict()
            )

            if create_result.success:
                # Increment template usage count
                template["usage_count"] += 1

                self.logger.info(
                    f"Successfully created project {project_id} from template {template_id}"
                )

                return {
                    "success": True,
                    "project_id": project_id,
                    "template_used": template_id,
                    "project_data": create_result.data,
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to create project: {create_result.error}",
                }

        except Exception as e:
            self.logger.error(f"Failed to create project from template: {str(e)}")
            return {
                "success": False,
                "error": f"Template project creation failed: {str(e)}",
            }

    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data for project administration."""
        try:
            # Get analytics
            analytics = await self.get_project_analytics(days=30)

            if not analytics.get("success"):
                return analytics

            # Get recent projects with more details
            search_result = await self.search_projects(
                sort_by=ProjectSortField.CREATED_AT, sort_order=SortOrder.DESC, limit=10
            )

            # Get projects by status for quick overview
            status_projects = {}
            for status in ProjectStatus:
                status_result = await self.search_projects(status=status, limit=5)
                status_projects[status.value] = status_result.get("projects", [])

            # Get templates info
            templates_result = await self.get_project_templates()

            return {
                "success": True,
                "generated_at": datetime.utcnow().isoformat(),
                "dashboard_data": {
                    "overview": analytics.get("overview", {}),
                    "analytics": {
                        "status_distribution": analytics.get("status_distribution", {}),
                        "category_distribution": analytics.get(
                            "category_distribution", {}
                        ),
                        "monthly_trends": analytics.get("monthly_trends", []),
                    },
                    "recent_projects": search_result.get("projects", []),
                    "projects_by_status": status_projects,
                    "templates": {
                        "available_templates": len(
                            templates_result.get("templates", [])
                        ),
                        "most_used_templates": sorted(
                            templates_result.get("templates", []),
                            key=lambda t: t.get("usage_count", 0),
                            reverse=True,
                        )[:3],
                    },
                    "quick_stats": {
                        "total_projects": analytics.get("overview", {}).get(
                            "total_projects", 0
                        ),
                        "active_projects": analytics.get("status_distribution", {}).get(
                            "active", 0
                        ),
                        "pending_projects": analytics.get(
                            "status_distribution", {}
                        ).get("pending", 0),
                        "completed_projects": analytics.get(
                            "status_distribution", {}
                        ).get("completed", 0),
                    },
                },
            }

        except Exception as e:
            self.logger.error(f"Failed to generate dashboard data: {str(e)}")
            return {
                "success": False,
                "error": f"Dashboard data generation failed: {str(e)}",
            }

    async def health_check(self) -> Dict[str, Any]:
        """Health check for project administration service."""
        try:
            # Test repository connectivity
            count_result = await self.project_repository.count()

            return {
                "healthy": count_result.success,
                "status": "operational" if count_result.success else "error",
                "repository_accessible": count_result.success,
                "templates_loaded": len(self.templates),
                "last_check": datetime.utcnow().isoformat(),
                "error": None if count_result.success else count_result.error,
            }

        except Exception as e:
            return {
                "healthy": False,
                "status": "error",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat(),
            }
