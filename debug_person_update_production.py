#!/usr/bin/env python3
"""
Debug script to reproduce the person update issue in production
"""

import sys
import asyncio
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models.person import PersonUpdate, Address
from services.dynamodb_service import DynamoDBService

async def debug_person_update():
    """Debug the person update issue with the exact person ID from production"""
    
    person_id = "02724257-4c6a-4aac-9c19-89c87c499bc8"
    
    print(f"🔍 Debugging person update for ID: {person_id}")
    
    # Initialize the database service
    try:
        db_service = DynamoDBService()
        print("✅ DynamoDB service initialized")
    except Exception as e:
        print(f"❌ Failed to initialize DynamoDB service: {e}")
        return
    
    # Try to get the existing person
    try:
        print(f"📋 Getting existing person...")
        existing_person = await db_service.get_person(person_id)
        if existing_person:
            print("✅ Person found in database")
            print(f"   Name: {existing_person.first_name} {existing_person.last_name}")
            print(f"   Email: {existing_person.email}")
            print(f"   Has address: {existing_person.address is not None}")
            if existing_person.address:
                print(f"   Address fields: {dir(existing_person.address)}")
            print(f"   Person fields: {[attr for attr in dir(existing_person) if not attr.startswith('_')]}")
        else:
            print("❌ Person not found in database")
            return
    except Exception as e:
        print(f"❌ Failed to get person: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Try to create a PersonUpdate object (like the API would)
    try:
        print(f"📝 Creating PersonUpdate object...")
        # Simulate a typical update request
        update_data = {
            "firstName": "Updated Name",
            "isAdmin": False
        }
        
        person_update_obj = PersonUpdate(**update_data)
        print("✅ PersonUpdate object created successfully")
        print(f"   Fields: {person_update_obj.model_dump(exclude_unset=True)}")
    except Exception as e:
        print(f"❌ Failed to create PersonUpdate: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Try to update the person
    try:
        print(f"💾 Updating person in database...")
        updated_person = await db_service.update_person(person_id, person_update_obj)
        if updated_person:
            print("✅ Person updated successfully")
            print(f"   Updated name: {updated_person.first_name} {updated_person.last_name}")
            print(f"   Has address: {updated_person.address is not None}")
            
            # Test the fields that might be causing AttributeError
            print(f"🔍 Testing field access...")
            try:
                print(f"   is_active: {getattr(updated_person, 'is_active', 'NOT_SET')}")
                print(f"   require_password_change: {getattr(updated_person, 'require_password_change', 'NOT_SET')}")
                print(f"   failed_login_attempts: {getattr(updated_person, 'failed_login_attempts', 'NOT_SET')}")
                print(f"   last_login_at: {getattr(updated_person, 'last_login_at', 'NOT_SET')}")
                
                if updated_person.address:
                    print(f"   address.postal_code: {getattr(updated_person.address, 'postal_code', 'NOT_SET')}")
                    print(f"   address.country: {getattr(updated_person.address, 'country', 'NOT_SET')}")
                
                print("✅ All field access successful")
            except Exception as field_error:
                print(f"❌ Field access error: {field_error}")
                import traceback
                traceback.print_exc()
                
        else:
            print("❌ Person update returned None")
    except Exception as e:
        print(f"❌ Failed to update person: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Try to simulate the API response creation
    try:
        print(f"📤 Testing API response creation...")
        person_data = {
            "id": updated_person.id,
            "email": updated_person.email,
            "firstName": updated_person.first_name,
            "lastName": updated_person.last_name,
            "phone": updated_person.phone or "",
            "dateOfBirth": (
                updated_person.date_of_birth.isoformat()
                if updated_person.date_of_birth
                else ""
            ),
            "address": {
                "country": (
                    getattr(updated_person.address, 'country', '') if updated_person.address else ""
                ),
                "state": getattr(updated_person.address, 'state', '') if updated_person.address else "",
                "city": getattr(updated_person.address, 'city', '') if updated_person.address else "",
                "street": (
                    getattr(updated_person.address, 'street', '') if updated_person.address else ""
                ),
                "postalCode": (
                    getattr(updated_person.address, 'postal_code', '') if updated_person.address else ""
                ),
            },
            "isAdmin": updated_person.is_admin,
            "createdAt": (
                updated_person.created_at.isoformat()
                if updated_person.created_at
                else ""
            ),
            "updatedAt": (
                updated_person.updated_at.isoformat()
                if updated_person.updated_at
                else ""
            ),
            "isActive": getattr(updated_person, "is_active", True),
            "requirePasswordChange": getattr(
                updated_person, "require_password_change", False
            ),
            "lastLoginAt": (
                updated_person.last_login_at.isoformat()
                if getattr(updated_person, "last_login_at", None)
                else None
            ),
            "failedLoginAttempts": getattr(updated_person, "failed_login_attempts", 0),
        }
        
        print("✅ API response data created successfully")
        print(f"   Response keys: {list(person_data.keys())}")
        
    except Exception as e:
        print(f"❌ Failed to create API response: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("🎉 Debug completed successfully - no AttributeError found!")

if __name__ == "__main__":
    asyncio.run(debug_person_update())