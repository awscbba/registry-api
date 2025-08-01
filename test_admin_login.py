#!/usr/bin/env python3
"""
Test admin login functionality with a real admin user.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from fastapi.testclient import TestClient
from src.handlers.versioned_api_handler import app
from src.services.dynamodb_service import DynamoDBService
from src.models.person import PersonCreate
from src.utils.password_utils import PasswordHasher
import asyncio

async def setup_test_admin():
    """Create a test admin user if it doesn't exist."""
    db_service = DynamoDBService()
    
    # Test admin email from environment or default
    admin_email = os.getenv("TEST_ADMIN_EMAIL", "sergio.rodriguez.inclan@gmail.com")
    
    print(f"🔍 Checking for admin user: {admin_email}")
    
    try:
        # Check if admin user exists
        existing_user = await db_service.get_person_by_email(admin_email)
        
        if existing_user:
            print(f"✅ Admin user exists: {existing_user.first_name} {existing_user.last_name}")
            
            # Check if user has password set
            if not hasattr(existing_user, 'password_hash') or not existing_user.password_hash:
                print("⚠️ Admin user exists but has no password set")
                # Set a test password using the correct method
                password_hash = PasswordHasher.hash_password("admin123")
                
                # Update using the person object directly
                existing_user.password_hash = password_hash
                existing_user.is_admin = True
                
                # Save the updated person
                await db_service.save_person(existing_user)
                print("✅ Test password set for admin user")
            else:
                print("✅ Admin user has password set")
                
            return admin_email, "admin123"
        else:
            print("❌ Admin user not found")
            return None, None
            
    except Exception as e:
        print(f"❌ Error checking admin user: {e}")
        return None, None

def test_admin_login():
    """Test admin login flow."""
    print("🔐 Testing admin login flow...")
    
    # Setup admin user
    admin_email, admin_password = asyncio.run(setup_test_admin())
    
    if not admin_email:
        print("❌ Cannot test login - no admin user available")
        return
    
    client = TestClient(app)
    
    print(f"1. Testing login with admin credentials...")
    response = client.post("/auth/login", json={
        "email": admin_email,
        "password": admin_password
    })
    
    print(f"   Login response: {response.status_code}")
    
    if response.status_code == 200:
        login_data = response.json()
        print(f"   ✅ Login successful!")
        print(f"   User: {login_data['user']['firstName']} {login_data['user']['lastName']}")
        print(f"   Token type: {login_data['token_type']}")
        print(f"   Expires in: {login_data['expires_in']} seconds")
        
        # Test authenticated endpoint
        print("2. Testing authenticated endpoint...")
        token = login_data['access_token']
        headers = {"Authorization": f"Bearer {token}"}
        
        me_response = client.get("/auth/me", headers=headers)
        print(f"   Me endpoint: {me_response.status_code}")
        
        if me_response.status_code == 200:
            me_data = me_response.json()
            print(f"   ✅ Authenticated request successful!")
            print(f"   User info: {me_data['user']['firstName']} {me_data['user']['lastName']}")
        else:
            print(f"   ❌ Authenticated request failed: {me_response.json()}")
            
        # Test admin endpoint
        print("3. Testing admin endpoint...")
        admin_response = client.get("/v2/admin/test", headers=headers)
        print(f"   Admin test: {admin_response.status_code}")
        
        if admin_response.status_code == 200:
            print(f"   ✅ Admin endpoint accessible!")
            admin_data = admin_response.json()
            print(f"   Admin user: {admin_data.get('admin_user', {}).get('firstName', 'Unknown')}")
        else:
            print(f"   ❌ Admin endpoint failed: {admin_response.json()}")
            
    else:
        print(f"   ❌ Login failed: {response.json()}")
    
    print("✅ Admin login test completed!")

if __name__ == "__main__":
    test_admin_login()