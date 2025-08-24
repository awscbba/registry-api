#!/usr/bin/env python3
"""
Simple consistency validation test.
"""

import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


async def test_health_checks():
    """Test health check consistency."""
    print("🩺 Testing Health Check Consistency")
    print("=" * 50)

    try:
        # Import required modules
        from core.base_service import HealthCheck, ServiceStatus
        from services.people_service import PeopleService
        from services.metrics_service import MetricsService
        from services.performance_metrics_service import PerformanceMetricsService
        from services.database_optimization_service import DatabaseOptimizationService
        from services.project_administration_service import ProjectAdministrationService

        services = [
            ("PeopleService", PeopleService),
            ("MetricsService", MetricsService),
            ("PerformanceMetricsService", PerformanceMetricsService),
            ("DatabaseOptimizationService", DatabaseOptimizationService),
            ("ProjectAdministrationService", ProjectAdministrationService),
        ]

        passed = 0
        failed = 0

        for name, service_class in services:
            try:
                print(f"\n🔍 Testing {name}...")
                service = service_class()
                result = await service.health_check()

                if isinstance(result, HealthCheck):
                    print(f"✅ {name}: Returns HealthCheck object")
                    print(f"   Status: {result.status.value}")
                    print(f"   Message: {result.message}")
                    passed += 1
                else:
                    print(f"❌ {name}: Returns {type(result)} instead of HealthCheck")
                    failed += 1

            except Exception as e:
                print(f"❌ {name}: Error - {str(e)}")
                failed += 1

        print(f"\n📊 Results: {passed} passed, {failed} failed")
        return failed == 0

    except Exception as e:
        print(f"❌ Import error: {str(e)}")
        return False


def test_dictionary_patterns():
    """Test dictionary access patterns."""
    print("\n🔍 Testing Dictionary Access Patterns")
    print("=" * 50)

    people_service_path = os.path.join(
        os.path.dirname(__file__), "..", "src", "services", "people_service.py"
    )

    try:
        with open(people_service_path, "r") as f:
            content = f.read()

        # Check for .get( patterns
        if ".get(" in content:
            lines = content.split("\n")
            issues = []
            for i, line in enumerate(lines, 1):
                if ".get(" in line and not line.strip().startswith("#"):
                    issues.append(f"Line {i}: {line.strip()}")

            if issues:
                print("❌ Dictionary access patterns found:")
                for issue in issues[:5]:  # Show first 5
                    print(f"   {issue}")
                return False

        print("✅ No dictionary access patterns found")
        return True

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


async def main():
    """Run validation tests."""
    print("🚀 Consistency Validation Test")
    print("=" * 60)

    health_ok = await test_health_checks()
    dict_ok = test_dictionary_patterns()

    print("\n" + "=" * 60)
    if health_ok and dict_ok:
        print("✅ ALL CONSISTENCY ISSUES RESOLVED!")
        return 0
    else:
        print("❌ ISSUES REMAIN")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
