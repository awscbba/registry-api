#!/usr/bin/env python3
"""
Simple test to verify administrator panel user management endpoints are available.
"""

import sys
import os

# Add src to path
sys.path.insert(0, "src")


def test_admin_endpoints():
    """Test that admin endpoints are properly configured."""
    print("🧪 Testing Administrator Panel User Management Endpoints")
    print("=" * 60)

    try:
        # Test import of main API handler
        print("\n📋 TEST 1: API Handler Import")
        print("-" * 40)

        from handlers.modular_api_handler import app

        print("✅ Main API handler imported successfully")

        # Extract all routes
        all_routes = []
        for route in app.routes:
            if hasattr(route, "path"):
                # Direct route
                methods = getattr(route, "methods", set())
                path = getattr(route, "path", "")
                name = getattr(route, "name", "")
                all_routes.append(
                    {"methods": list(methods), "path": path, "name": name}
                )
            elif hasattr(route, "routes"):
                # Router with subroutes
                for subroute in route.routes:
                    if hasattr(subroute, "path"):
                        methods = getattr(subroute, "methods", set())
                        path = getattr(subroute, "path", "")
                        name = getattr(subroute, "name", "")
                        all_routes.append(
                            {"methods": list(methods), "path": path, "name": name}
                        )

        print(f"✅ Total routes found: {len(all_routes)}")

        # Filter admin routes
        admin_routes = [r for r in all_routes if "/v2/admin/" in r["path"]]
        print(f"✅ Enhanced admin routes: {len(admin_routes)}")

        # Filter user management routes
        user_routes = [r for r in admin_routes if "/users" in r["path"]]
        print(f"✅ User management routes: {len(user_routes)}")

        print("\n📋 User Management Endpoints:")
        for route in user_routes:
            print(f"   {route['methods']} {route['path']} ({route['name']})")

        # Test 2: Check required endpoints
        print("\n🎯 TEST 2: Required Endpoints Check")
        print("-" * 40)

        required_endpoints = [
            ("GET", "/v2/admin/users", "list_users"),
            ("GET", "/v2/admin/users/{user_id}", "get_user"),
            ("POST", "/v2/admin/users", "create_user"),
            ("PUT", "/v2/admin/users/{user_id}", "edit_user"),
            ("DELETE", "/v2/admin/users/{user_id}", "delete_user"),
            ("POST", "/v2/admin/users/bulk-action", "bulk_user_action"),
        ]

        found_count = 0
        for method, path, name in required_endpoints:
            found = False
            for route in user_routes:
                if (
                    method in route["methods"]
                    and path == route["path"]
                    and name == route["name"]
                ):
                    found = True
                    found_count += 1
                    break

            status = "✅" if found else "❌"
            print(f"   {status} {method} {path}")

        coverage = (found_count / len(required_endpoints)) * 100
        print(
            f"\n📊 Coverage: {found_count}/{len(required_endpoints)} ({coverage:.1f}%)"
        )

        # Test 3: Check other important admin endpoints
        print("\n📈 TEST 3: Other Admin Endpoints")
        print("-" * 40)

        dashboard_routes = [
            r
            for r in admin_routes
            if "dashboard" in r["path"] or "analytics" in r["path"]
        ]
        print(f"✅ Dashboard/Analytics routes: {len(dashboard_routes)}")

        for route in dashboard_routes:
            print(f"   {route['methods']} {route['path']} ({route['name']})")

        # Summary
        print("\n🎉 SUMMARY")
        print("=" * 60)

        if found_count == len(required_endpoints):
            print("✅ SUCCESS: All required user management endpoints are available!")
            print("✅ Administrator panel users section should now work properly")
            print(f"✅ Total admin functionality: {len(admin_routes)} endpoints")
            print(f"✅ User CRUD operations: {len(user_routes)} endpoints")
            print(f"✅ Dashboard/Analytics: {len(dashboard_routes)} endpoints")
            return True
        else:
            missing = len(required_endpoints) - found_count
            print(f"❌ INCOMPLETE: {missing} required endpoints are missing")
            print("❌ Administrator panel may not function properly")
            return False

    except Exception as e:
        print(f"❌ TEST FAILED: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_admin_endpoints()

    if success:
        print("\n🎯 RESULT: Administrator panel user management is ready!")
        print("   The users section should now display the user list properly.")
        sys.exit(0)
    else:
        print("\n❌ RESULT: Issues found with admin endpoints")
        sys.exit(1)
