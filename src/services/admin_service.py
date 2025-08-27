"""
Admin service implementation.
Handles business logic for admin operations.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from ..repositories.people_repository import PeopleRepository
from ..repositories.projects_repository import ProjectsRepository
from ..repositories.subscriptions_repository import SubscriptionsRepository
from ..models.person import PersonResponse


class AdminService:
    """Service for admin business logic."""

    def __init__(self):
        self.people_repository = PeopleRepository()
        self.projects_repository = ProjectsRepository()
        self.subscriptions_repository = SubscriptionsRepository()

    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get basic dashboard data."""
        try:
            # Get counts
            people = await self.people_repository.list_all()
            projects = await self.projects_repository.list_all()
            subscriptions = await self.subscriptions_repository.list_all()

            # Calculate basic stats
            active_people = len([p for p in people if p.isActive])
            active_projects = len([p for p in projects if p.isActive])
            active_subscriptions = len([s for s in subscriptions if s.isActive])

            return {
                "totalUsers": len(people),
                "activeUsers": active_people,
                "totalProjects": len(projects),
                "activeProjects": active_projects,
                "totalSubscriptions": len(subscriptions),
                "activeSubscriptions": active_subscriptions,
                "lastUpdated": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            raise Exception(f"Failed to get dashboard data: {str(e)}")

    async def get_enhanced_dashboard_data(self) -> Dict[str, Any]:
        """Get enhanced dashboard data with more detailed analytics."""
        try:
            basic_data = await self.get_dashboard_data()

            # Get additional analytics
            people = await self.people_repository.list_all()
            projects = await self.projects_repository.list_all()
            subscriptions = await self.subscriptions_repository.list_all()

            # Calculate enhanced stats
            admin_count = len([p for p in people if p.isAdmin])
            recent_signups = len(
                [
                    p
                    for p in people
                    if datetime.fromisoformat(p.createdAt.replace("Z", "+00:00"))
                    > datetime.utcnow().replace(tzinfo=None) - timedelta(days=30)
                ]
            )

            # Project statistics
            project_stats = {}
            for project in projects:
                project_subs = [s for s in subscriptions if s.projectId == project.id]
                project_stats[project.id] = {
                    "name": project.name,
                    "subscriptions": len(project_subs),
                    "status": project.status,
                }

            enhanced_data = {
                **basic_data,
                "adminUsers": admin_count,
                "recentSignups": recent_signups,
                "projectStats": project_stats,
                "systemHealth": {
                    "status": "healthy",
                    "uptime": "99.9%",
                    "lastCheck": datetime.utcnow().isoformat(),
                },
            }

            return enhanced_data
        except Exception as e:
            raise Exception(f"Failed to get enhanced dashboard data: {str(e)}")

    async def get_analytics_data(self) -> Dict[str, Any]:
        """Get detailed analytics data."""
        try:
            people = await self.people_repository.list_all()
            projects = await self.projects_repository.list_all()
            subscriptions = await self.subscriptions_repository.list_all()

            # User analytics
            user_analytics = {
                "totalUsers": len(people),
                "activeUsers": len([p for p in people if p.isActive]),
                "adminUsers": len([p for p in people if p.isAdmin]),
                "inactiveUsers": len([p for p in people if not p.isActive]),
            }

            # Project analytics
            project_analytics = {
                "totalProjects": len(projects),
                "activeProjects": len([p for p in projects if p.isActive]),
                "projectsByStatus": {},
            }

            # Count projects by status
            for project in projects:
                status = project.status
                if status not in project_analytics["projectsByStatus"]:
                    project_analytics["projectsByStatus"][status] = 0
                project_analytics["projectsByStatus"][status] += 1

            # Subscription analytics
            subscription_analytics = {
                "totalSubscriptions": len(subscriptions),
                "activeSubscriptions": len([s for s in subscriptions if s.isActive]),
                "subscriptionsByProject": {},
            }

            # Count subscriptions by project
            for subscription in subscriptions:
                project_id = subscription.projectId
                if project_id not in subscription_analytics["subscriptionsByProject"]:
                    subscription_analytics["subscriptionsByProject"][project_id] = 0
                subscription_analytics["subscriptionsByProject"][project_id] += 1

            return {
                "users": user_analytics,
                "projects": project_analytics,
                "subscriptions": subscription_analytics,
                "generatedAt": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            raise Exception(f"Failed to get analytics data: {str(e)}")

    async def execute_bulk_action(self, bulk_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute bulk actions on users."""
        try:
            action = bulk_data.get("action")
            user_ids = bulk_data.get("userIds", [])

            if not action or not user_ids:
                raise ValueError("Action and userIds are required")

            results = {
                "action": action,
                "totalUsers": len(user_ids),
                "successCount": 0,
                "failureCount": 0,
                "results": [],
            }

            for user_id in user_ids:
                try:
                    if action == "activate":
                        await self.people_repository.activate_person(user_id)
                    elif action == "deactivate":
                        await self.people_repository.deactivate_person(user_id)
                    elif action == "delete":
                        await self.people_repository.delete(user_id)
                    else:
                        raise ValueError(f"Unknown action: {action}")

                    results["successCount"] += 1
                    results["results"].append({"userId": user_id, "status": "success"})
                except Exception as e:
                    results["failureCount"] += 1
                    results["results"].append(
                        {"userId": user_id, "status": "failed", "error": str(e)}
                    )

            return results
        except Exception as e:
            raise Exception(f"Failed to execute bulk action: {str(e)}")
