#!/usr/bin/env python3
"""
Test script to debug admin stats endpoint locally.
"""

import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from services.admin_service import AdminService
from services.performance_service import PerformanceService
from services.logging_service import EnterpriseLoggingService


async def test_admin_stats():
    """Test the admin stats functionality locally."""
    try:
        print("🔍 Testing Admin Stats Endpoint...")

        # Initialize services
        admin_service = AdminService()
        logging_service = EnterpriseLoggingService()
        performance_service = PerformanceService(logging_service)

        print("✅ Services initialized successfully")

        # Test dashboard data
        print("\n📊 Testing dashboard data...")
        dashboard_data = await admin_service.get_dashboard_data()
        print(f"Dashboard data: {dashboard_data}")

        # Test performance stats
        print("\n⚡ Testing performance stats...")
        performance_stats = await performance_service.get_performance_stats()
        print(f"Performance stats: {performance_stats}")

        # Test combined stats (like the /admin/stats endpoint)
        print("\n📈 Testing combined stats...")
        stats = {
            **dashboard_data,
            "performance": performance_stats,
            "system": {
                "version": "2.0.0",
                "environment": "production",
                "timestamp": dashboard_data.get("lastUpdated"),
            },
        }
        print(f"Combined stats: {stats}")

        print("\n✅ All tests passed! Admin stats endpoint should work.")

    except Exception as e:
        print(f"\n❌ Error testing admin stats: {str(e)}")
        import traceback

        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = asyncio.run(test_admin_stats())
    sys.exit(0 if success else 1)
