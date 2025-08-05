#!/usr/bin/env python3
"""
Debug the specific person update issue that's causing 500 errors in the frontend
"""

import requests
import json
import sys
from datetime import datetime

API_BASE_URL = "https://2t9blvt2c1.execute-api.us-east-1.amazonaws.com/prod"
PERSON_ID = "8a22f71c-b3ba-46f0-912a-8eb44b1037ac"  # The failing person ID from frontend

def test_person_update_scenarios():
    """Test different person update scenarios to identify the issue"""
    
    print("🔍 Debugging Person Update Issue")
    print("=" * 60)
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Person ID: {PERSON_ID}")
    print(f"Time: {datetime.now().isoformat()}")
    
    # Test 1: Get the person first to see current state
    print(f"\n1️⃣ Getting current person data...")
    try:
        response = requests.get(f"{API_BASE_URL}/v2/people/{PERSON_ID}")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            person_data = response.json()
            print(f"   Current data: {json.dumps(person_data, indent=2)}")
        else:
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"   Exception: {e}")
        return False
    
    # Test 2: Try minimal update (what frontend might be doing)
    print(f"\n2️⃣ Testing minimal update (frontend style)...")
    update_data = {
        "firstName": "Updated",
        "lastName": "Name"
    }
    
    try:
        response = requests.put(
            f"{API_BASE_URL}/v2/people/{PERSON_ID}",
            headers={"Content-Type": "application/json"},
            json=update_data
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        
        if response.status_code != 200:
            print(f"   ❌ Minimal update failed!")
            return False
        else:
            print(f"   ✅ Minimal update succeeded")
            
    except Exception as e:
        print(f"   Exception: {e}")
        return False
    
    # Test 3: Try update with all fields (comprehensive)
    print(f"\n3️⃣ Testing comprehensive update...")
    comprehensive_data = {
        "firstName": "Comprehensive",
        "lastName": "Update",
        "email": "test-comprehensive@example.com",
        "phone": "+591 70123456",
        "dateOfBirth": "1990-01-01",
        "address": {
            "street": "Test Street 123",
            "city": "Test City",
            "state": "Test State",
            "country": "Bolivia",
            "postalCode": "12345"
        }
    }
    
    try:
        response = requests.put(
            f"{API_BASE_URL}/v2/people/{PERSON_ID}",
            headers={"Content-Type": "application/json"},
            json=comprehensive_data
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        
        if response.status_code != 200:
            print(f"   ❌ Comprehensive update failed!")
        else:
            print(f"   ✅ Comprehensive update succeeded")
            
    except Exception as e:
        print(f"   Exception: {e}")
    
    # Test 4: Try update with problematic data (empty fields, nulls, etc.)
    print(f"\n4️⃣ Testing problematic data scenarios...")
    
    problematic_scenarios = [
        {
            "name": "Empty strings",
            "data": {"firstName": "", "lastName": ""}
        },
        {
            "name": "Null values", 
            "data": {"firstName": None, "lastName": None}
        },
        {
            "name": "Missing address fields",
            "data": {
                "firstName": "Test",
                "lastName": "Missing Address",
                "address": {}
            }
        },
        {
            "name": "Invalid date format",
            "data": {
                "firstName": "Test",
                "lastName": "Invalid Date",
                "dateOfBirth": "invalid-date"
            }
        }
    ]
    
    for scenario in problematic_scenarios:
        print(f"\n   Testing: {scenario['name']}")
        try:
            response = requests.put(
                f"{API_BASE_URL}/v2/people/{PERSON_ID}",
                headers={"Content-Type": "application/json"},
                json=scenario['data']
            )
            print(f"      Status: {response.status_code}")
            if response.status_code != 200:
                print(f"      Error: {response.text}")
                
        except Exception as e:
            print(f"      Exception: {e}")
    
    # Test 5: Test with authentication headers (simulate frontend)
    print(f"\n5️⃣ Testing with authentication headers...")
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer fake-token",  # Frontend might be sending this
        "Origin": "https://your-frontend-domain.com",
        "Referer": "https://your-frontend-domain.com/admin"
    }
    
    try:
        response = requests.put(
            f"{API_BASE_URL}/v2/people/{PERSON_ID}",
            headers=headers,
            json={"firstName": "Auth Test", "lastName": "Headers"}
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        
    except Exception as e:
        print(f"   Exception: {e}")
    
    # Test 6: Check if the issue is with the specific person ID
    print(f"\n6️⃣ Testing with different person ID...")
    try:
        # First get list of people to find another ID
        response = requests.get(f"{API_BASE_URL}/v2/people")
        if response.status_code == 200:
            people_data = response.json()
            if 'data' in people_data and len(people_data['data']) > 1:
                other_person = people_data['data'][1]  # Get second person
                other_id = other_person['id']
                print(f"   Testing with person ID: {other_id}")
                
                response = requests.put(
                    f"{API_BASE_URL}/v2/people/{other_id}",
                    headers={"Content-Type": "application/json"},
                    json={"firstName": "Other", "lastName": "Person"}
                )
                print(f"   Status: {response.status_code}")
                print(f"   Response: {response.text}")
            else:
                print("   No other people found to test with")
        else:
            print(f"   Could not get people list: {response.status_code}")
            
    except Exception as e:
        print(f"   Exception: {e}")
    
    print(f"\n🎯 Debug Analysis Complete")
    return True

if __name__ == "__main__":
    success = test_person_update_scenarios()
    if success:
        print("\n✅ Debug analysis completed")
        sys.exit(0)
    else:
        print("\n❌ Debug analysis failed")
        sys.exit(1)