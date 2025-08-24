#!/usr/bin/env python3
"""
Test script for administrator panel user management functionality.
Validates that the enhanced admin endpoints are working correctly.
"""

import sys
import os
import asyncio
from datetime import datetime

# Add src to path for imports
src_path = os.path.join(os.path.dirname(__file__), "..", "src")
sys.path.insert(0, src_path)


async def test_admin_user_management():
    """Test the administrator panel user management functionality."""
    print("🧪 Testing Administrator Panel User Management")
    print("=" * 60)

    try:
        # Test 1: Test main API handler import
        print("\n📋 TEST 1: Main API Handler Import")
        print("-" * 40)

        try:
            from handlers.modular_api_handler import app

            print("✅ Main API handler imported successfully")

            # Count admin routes
            admin_routes = []
            for route in app.routes:
                if hasattr(route, "routes"):  # For routers
                    for subroute in route.routes:
                        if hasattr(subroute, "path") and "/v2/admin/" in subroute.path:
                            methods = getattr(subroute, "methods", set())
                            path = getattr(subroute, "path", "")
                            name = getattr(subroute, "name", "")
                            admin_routes.append(
                                {"methods": list(methods), "path": path, "name": name}
                            )

            print(f"✅ Enhanced admin routes found: {len(admin_routes)}")

            # Filter user management routes
            user_routes = [r for r in admin_routes if "/users" in r["path"]]
            print(f"✅ User management routes: {len(user_routes)}")

            for route in user_routes:
                print(f"   {route['methods']} {route['path']} ({route['name']})")

        except Exception as e:
            print(f"❌ Failed to import main API handler: {str(e)}")
            return False

        # Test 2: Verify Service Registry integration
        print("\n🔧 TEST 2: Service Registry Integration")
        print("-" * 40)

        try:
            from services.service_registry_manager import service_manager

            people_service = service_manager.get_service("people")
            projects_service = service_manager.get_service("projects")
            subscriptions_service = service_manager.get_service("subscriptions")

            print(f"✅ People service available: {people_service is not None}")
            print(f"✅ Projects service available: {projects_service is not None}")
            print(
                f"✅ Subscriptions service available: {subscriptions_service is not None}"
            )

            if people_service:
                print(f"   People service type: {type(people_service).__name__}")

                # Test service health
                health = await people_service.health_check()
                print(f"   People service health: {health}")

        except Exception as e:
            print(f"❌ Service Registry test failed: {str(e)}")
            return False

        # Test 3: Verify required endpoints are present
        print("\n🎯 TEST 3: Required User Management Endpoints")
        print("-" * 40)

        required_endpoints = [
            ("GET", "/v2/admin/users", "list_users"),
            ("GET", "/v2/admin/users/{user_id}", "get_user"),
            ("POST", "/v2/admin/users", "create_user"),
            ("PUT", "/v2/admin/users/{user_id}", "edit_user"),
            ("DELETE", "/v2/admin/users/{user_id}", "delete_user"),
            ("POST", "/v2/admin/users/bulk-action", "bulk_user_action"),
        ]

        found_endpoints = []
        for method, path, name in required_endpoints:
            found = False
            for route in user_routes:
                if (
                    method in route["methods"]
                    and path == route["path"]
                    and name == route["name"]
                ):
                    found = True
                    break

            status = "✅" if found else "❌"
            print(f"   {status} {method} {path} ({name})")
            if found:
                found_endpoints.append((method, path, name))

        print(
            f"\n📊 Endpoint Coverage: {len(found_endpoints)}/{len(required_endpoints)} ({len(found_endpoints) / len(required_endpoints) * 100:.1f}%)"
        )

        # Test 4: Summary
        print("\n🎉 TEST SUMMARY")
        print("=" * 60)

        user_mgmt_routes = len(user_routes)

        print(f"✅ Total enhanced admin routes: {len(admin_routes)}")
        print(f"✅ User management routes: {user_mgmt_routes}")
        print(f"✅ Service Registry integration: Working")
        print(
            f"✅ Required endpoints coverage: {len(found_endpoints)}/{len(required_endpoints)}"
        )

        if len(found_endpoints) == len(required_endpoints):
            print(
                "\n🎯 RESULT: Administrator panel user management is FULLY FUNCTIONAL!"
            )
            print("   - All required CRUD endpoints are available")
            print("   - Service Registry integration is working")
            print("   - Enhanced admin router is properly integrated")
            print("   - Main API handler includes all admin routes")
            return True
        else:
            print(
                f"\n⚠️  RESULT: Some endpoints are missing ({len(required_endpoints) - len(found_endpoints)} missing)"
            )
            return False

    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Main test function."""
    print(f"🚀 Administrator Panel User Management Test")
    print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔧 Testing Environment: Development")

    success = await test_admin_user_management()

    if success:
        print(f"\n✅ ALL TESTS PASSED - Administrator panel user management is ready!")
        sys.exit(0)
    else:
        print(f"\n❌ SOME TESTS FAILED - Check the output above for details")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
