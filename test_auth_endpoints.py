#!/usr/bin/env python3
"""
Quick test script to verify auth endpoints are working.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from fastapi.testclient import TestClient
from src.handlers.versioned_api_handler import app

def test_auth_endpoints():
    """Test that auth endpoints are accessible."""
    client = TestClient(app)
    
    print("🔍 Testing auth endpoints...")
    
    # Test health endpoint
    print("1. Testing health endpoint...")
    response = client.get("/health")
    print(f"   Health: {response.status_code} - {response.json()}")
    
    # Test login endpoint exists (should return 422 for missing body)
    print("2. Testing login endpoint exists...")
    response = client.post("/auth/login")
    print(f"   Login (no body): {response.status_code}")
    
    # Test login with invalid credentials
    print("3. Testing login with invalid credentials...")
    response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "wrongpassword"
    })
    print(f"   Login (invalid): {response.status_code} - {response.json()}")
    
    # Test /auth/me without token
    print("4. Testing /auth/me without token...")
    response = client.get("/auth/me")
    print(f"   Me (no token): {response.status_code} - {response.json()}")
    
    # Test logout
    print("5. Testing logout...")
    response = client.post("/auth/logout")
    print(f"   Logout: {response.status_code} - {response.json()}")
    
    print("✅ Auth endpoints test completed!")

if __name__ == "__main__":
    test_auth_endpoints()