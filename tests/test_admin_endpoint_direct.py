#!/usr/bin/env python3
"""
Test admin endpoint directly to see if it exists.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from fastapi.testclient import TestClient
from src.handlers.versioned_api_handler import app


@pytest.mark.skip(reason="Temporarily skipped - uses deprecated versioned_api_handler")
def test_admin_endpoint():
    """Test admin endpoint directly."""
    client = TestClient(app)

    print("🔍 Testing admin endpoint availability...")

    # Test without authentication first
    print("1. Testing /v2/admin/test without auth...")
    response = client.get("/v2/admin/test")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")

    # Test health endpoint for comparison
    print("2. Testing /health for comparison...")
    health_response = client.get("/health")
    print(f"   Status: {health_response.status_code}")
    print(f"   Response: {health_response.json()}")

    # List all available routes
    print("3. Available routes:")
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            methods = ", ".join(route.methods) if route.methods else "N/A"
            print(f"   {methods} {route.path}")


if __name__ == "__main__":
    test_admin_endpoint()
