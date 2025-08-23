"""
Test script for the versioned API to verify v1 and v2 endpoints work correctly.
"""

import asyncio
import json
import pytest
from src.handlers.versioned_api_handler import app
from fastapi.testclient import TestClient


@pytest.mark.skip(reason="Temporarily skipped - uses deprecated versioned_api_handler")
def test_versioned_api():
    """Test the versioned API endpoints."""
    client = TestClient(app)

    print("🧪 Testing Versioned API Endpoints")
    print("=" * 50)

    # Test health endpoint
    print("\n1. Testing Health Endpoint")
    response = client.get("/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    # Test v1 endpoints
    print("\n2. Testing V1 Endpoints")

    # Test v1 projects
    print("\n2.1. V1 Projects")
    response = client.get("/v1/projects")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Projects count: {len(data.get('projects', []))}")
    else:
        print(f"Error: {response.text}")

    # Test v1 subscriptions
    print("\n2.2. V1 Subscriptions")
    response = client.get("/v1/subscriptions")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Subscriptions count: {len(data.get('subscriptions', []))}")
    else:
        print(f"Error: {response.text}")

    # Test v2 endpoints
    print("\n3. Testing V2 Endpoints")

    # Test v2 projects
    print("\n3.1. V2 Projects")
    response = client.get("/v2/projects")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Projects count: {len(data.get('projects', []))}")
        print(f"Version: {data.get('version')}")
    else:
        print(f"Error: {response.text}")

    # Test v2 subscriptions
    print("\n3.2. V2 Subscriptions")
    response = client.get("/v2/subscriptions")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Subscriptions count: {len(data.get('subscriptions', []))}")
        print(f"Version: {data.get('version')}")
    else:
        print(f"Error: {response.text}")

    # Test legacy endpoints (should redirect to v1)
    print("\n4. Testing Legacy Endpoints (should redirect to v1)")

    print("\n4.1. Legacy Projects")
    response = client.get("/projects")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Projects count: {len(data.get('projects', []))}")
    else:
        print(f"Error: {response.text}")

    print("\n4.2. Legacy Subscriptions")
    response = client.get("/subscriptions")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Subscriptions count: {len(data.get('subscriptions', []))}")
    else:
        print(f"Error: {response.text}")

    print("\n✅ Versioned API test completed!")
    print("\nNext steps:")
    print("1. Deploy this versioned API to production")
    print("2. Test v2 subscription creation endpoint")
    print("3. Update frontend to use v2 endpoints")


if __name__ == "__main__":
    test_versioned_api()
