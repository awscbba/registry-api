#!/usr/bin/env python3
"""
Debug script to check how the Person model handles the database record.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.services.dynamodb_service import DynamoDBService
import asyncio

async def debug_person_model():
    """Debug the Person model parsing."""
    db_service = DynamoDBService()
    
    admin_email = "admin@awsugcbba.org"
    
    print(f"🔍 Getting person by email: {admin_email}")
    
    try:
        person = await db_service.get_person_by_email(admin_email)
        
        if person:
            print(f"✅ Person found!")
            print(f"   ID: {person.id}")
            print(f"   Email: {person.email}")
            print(f"   Name: {person.first_name} {person.last_name}")
            print(f"   Has password_hash attribute: {hasattr(person, 'password_hash')}")
            
            if hasattr(person, 'password_hash'):
                print(f"   Password hash exists: {person.password_hash is not None}")
                if person.password_hash:
                    print(f"   Password hash length: {len(person.password_hash)}")
                    print(f"   Password hash starts with: {person.password_hash[:10]}...")
            else:
                print(f"   ❌ No password_hash attribute!")
                
            print(f"   All attributes: {dir(person)}")
            print(f"   Person dict: {person.__dict__}")
        else:
            print(f"❌ Person not found!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_person_model())