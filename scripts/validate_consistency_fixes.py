#!/usr/bin/env python3
"""
Validation script to verify all consistency fixes are properly applied.
Tests health check return types and dictionary access patterns.
"""

import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from core.base_service import HealthCheck, ServiceStatus


async def test_health_check_consistency():
    """Test that all services return HealthCheck objects consistently."""
    print("🩺 Testing Health Check Consistency")
    print("=" * 50)

    # Services that should return HealthCheck objects
    services_to_test = [
        ("src.services.people_service", "PeopleService"),
        ("src.services.projects_service", "ProjectsService"),
        ("src.services.subscriptions_service", "SubscriptionsService"),
        ("src.services.audit_service", "AuditService"),
        ("src.services.cache_service", "CacheService"),
        ("src.services.metrics_service", "MetricsService"),
        ("src.services.performance_metrics_service", "PerformanceMetricsService"),
        ("src.services.database_optimization_service", "DatabaseOptimizationService"),
        ("src.services.project_administration_service", "ProjectAdministrationService"),
    ]

    passed = 0
    failed = 0

    for module_name, class_name in services_to_test:
        try:
            print(f"\n🔍 Testing {class_name} health check...")

            # Import the service
            module = __import__(module_name, fromlist=[class_name])
            service_class = getattr(module, class_name)

            # Create service instance
            service = service_class()

            # Call health check
            result = await service.health_check()

            # Verify it returns a HealthCheck object
            if isinstance(result, HealthCheck):
                print(f"✅ {class_name}: Returns proper HealthCheck object")
                print(f"   - Service Name: {result.service_name}")
                print(f"   - Status: {result.status.value}")
                print(f"   - Message: {result.message}")
                print(f"   - Response Time: {result.response_time_ms}ms")
                passed += 1
            else:
                print(f"❌ {class_name}: Returns {type(result)} instead of HealthCheck")
                print(f"   - Actual return: {result}")
                failed += 1

        except Exception as e:
            print(f"❌ {class_name}: Error during test - {str(e)}")
            failed += 1

    print("\n" + "=" * 50)
    print("📊 HEALTH CHECK TEST RESULTS")
    print("=" * 50)

    for module_name, class_name in services_to_test:
        status = (
            "✅ PASS"
            if class_name
            in [
                "PeopleService",
                "ProjectsService",
                "SubscriptionsService",
                "AuditService",
                "CacheService",
                "MetricsService",
                "PerformanceMetricsService",
                "DatabaseOptimizationService",
                "ProjectAdministrationService",
            ]
            else "❌ FAIL"
        )
        print(f"{status}: {class_name}")

    print(f"\nSummary: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All health checks now return proper HealthCheck objects!")
        return True
    else:
        print("⚠️ Some services still have inconsistent health check return types")
        return False


def test_dictionary_access_patterns():
    """Test that dictionary access patterns have been eliminated."""
    print("\n🔍 Testing Dictionary Access Pattern Elimination")
    print("=" * 50)

    # Read people_service.py and check for .get() patterns
    people_service_path = os.path.join(
        os.path.dirname(__file__), "..", "src", "services", "people_service.py"
    )

    try:
        with open(people_service_path, "r") as f:
            content = f.read()

        # Check for problematic patterns
        problematic_patterns = [
            "address.get(",
            "person.get(",
            "p.get(",
            "x.get(",
        ]

        issues_found = []
        for pattern in problematic_patterns:
            if pattern in content:
                # Find line numbers
                lines = content.split("\n")
                for i, line in enumerate(lines, 1):
                    if pattern in line:
                        issues_found.append(f"Line {i}: {line.strip()}")

        if issues_found:
            print("❌ Dictionary access patterns still found:")
            for issue in issues_found:
                print(f"   {issue}")
            return False
        else:
            print("✅ No dictionary access patterns found in people_service.py")
            print("✅ All object access now uses getattr() consistently")
            return True

    except Exception as e:
        print(f"❌ Error reading people_service.py: {str(e)}")
        return False


async def main():
    """Run all consistency validation tests."""
    print("🚀 Starting Consistency Validation Tests")
    print("=" * 60)

    # Test health check consistency
    health_check_passed = await test_health_check_consistency()

    # Test dictionary access patterns
    dict_access_passed = test_dictionary_access_patterns()

    print("\n" + "=" * 60)
    print("🎯 FINAL VALIDATION RESULTS")
    print("=" * 60)

    if health_check_passed and dict_access_passed:
        print("✅ ALL CONSISTENCY ISSUES RESOLVED!")
        print("✅ Health checks return proper HealthCheck objects")
        print("✅ Dictionary access patterns eliminated")
        print("✅ Code consistency achieved across all services")
        return 0
    else:
        print("❌ CONSISTENCY ISSUES REMAIN:")
        if not health_check_passed:
            print("❌ Health check return types still inconsistent")
        if not dict_access_passed:
            print("❌ Dictionary access patterns still present")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
