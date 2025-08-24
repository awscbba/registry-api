#!/usr/bin/env python3
"""
Test script to verify health check fixes for service registry.
This script tests that services return proper HealthCheck objects instead of dictionaries.
"""

import sys
import os
import asyncio
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.core.base_service import HealthCheck, ServiceStatus
from src.services.people_service import PeopleService
from src.services.projects_service import ProjectsService
from src.services.subscriptions_service import SubscriptionsService
from src.services.audit_service import AuditService
from src.services.cache_service import CacheService


async def test_service_health_check(service_class, service_name):
    """Test a single service's health check method."""
    print(f"\n🔍 Testing {service_name} health check...")

    try:
        # Initialize service
        service = service_class()

        # Call health check
        health_result = await service.health_check()

        # Verify it's a HealthCheck object
        if isinstance(health_result, HealthCheck):
            print(f"✅ {service_name}: Returns proper HealthCheck object")
            print(f"   - Service Name: {health_result.service_name}")
            print(f"   - Status: {health_result.status.value}")
            print(f"   - Message: {health_result.message}")
            print(f"   - Response Time: {health_result.response_time_ms}ms")
            return True
        else:
            print(
                f"❌ {service_name}: Returns {type(health_result)} instead of HealthCheck"
            )
            print(f"   - Actual result: {health_result}")
            return False

    except Exception as e:
        print(f"⚠️ {service_name}: Exception during test: {str(e)}")
        return False


async def main():
    """Test all service health checks."""
    print("🩺 Testing Service Health Check Fixes")
    print("=" * 50)

    # Services to test
    services_to_test = [
        (PeopleService, "PeopleService"),
        (ProjectsService, "ProjectsService"),
        (SubscriptionsService, "SubscriptionsService"),
        (AuditService, "AuditService"),
        (CacheService, "CacheService"),
    ]

    results = []

    for service_class, service_name in services_to_test:
        success = await test_service_health_check(service_class, service_name)
        results.append((service_name, success))

    # Summary
    print("\n" + "=" * 50)
    print("📊 HEALTH CHECK TEST RESULTS")
    print("=" * 50)

    passed = 0
    failed = 0

    for service_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {service_name}")
        if success:
            passed += 1
        else:
            failed += 1

    print(f"\nSummary: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All health checks now return proper HealthCheck objects!")
        return True
    else:
        print("⚠️ Some health checks still need fixing.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
