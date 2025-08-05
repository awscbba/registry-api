#!/usr/bin/env python3
"""
Test the actual project and subscription API endpoints to identify real issues
"""

import requests
import json
import sys
import subprocess

def test_project_subscription_apis():
    """Test the actual API endpoints for projects and subscriptions"""
    
    print("🌐 Testing Project and Subscription API Endpoints")
    print("=" * 60)
    
    # Get the API URL
    try:
        result = subprocess.run([
            "aws", "cloudformation", "describe-stacks", 
            "--stack-name", "PeopleRegisterInfrastructureStack",
            "--query", "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue",
            "--output", "text", "--region", "us-east-1"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            api_url = result.stdout.strip()
            print(f"📡 API URL: {api_url}")
        else:
            print("❌ Could not get API URL from CloudFormation")
            return False
    except Exception as e:
        print(f"❌ Error getting API URL: {e}")
        return False
    
    # Test 1: Create a project
    print(f"\n1️⃣ Testing project creation...")
    project_data = {
        "name": "Test Project API",
        "description": "Test project for API validation",
        "startDate": "2025-01-01",
        "endDate": "2025-12-31",
        "maxParticipants": 50,
        "status": "active",  # String enum
        "category": "test",
        "location": "Test Location",
        "requirements": "None"
    }
    
    try:
        response = requests.post(
            f"{api_url}v2/projects",
            headers={"Content-Type": "application/json"},
            json=project_data,
            timeout=30
        )
        
        print(f"   📤 Request: POST {api_url}v2/projects")
        print(f"   📤 Data: {json.dumps(project_data, indent=2)}")
        print(f"   📥 Status: {response.status_code}")
        print(f"   📥 Response: {response.text[:300]}...")
        
        if response.status_code == 201:
            print("   ✅ Project creation successful")
            project_response = response.json()
            project_id = project_response.get("id")
        elif response.status_code == 500:
            print("   🚨 500 error - likely enum handling issue!")
            return False
        else:
            print(f"   ❌ Project creation failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Request failed: {e}")
        return False
    
    # Test 2: Update the project
    if 'project_id' in locals():
        print(f"\n2️⃣ Testing project update...")
        update_data = {
            "name": "Updated Test Project",
            "status": "completed",  # String enum
            "maxParticipants": 75
        }
        
        try:
            response = requests.put(
                f"{api_url}v2/projects/{project_id}",
                headers={"Content-Type": "application/json"},
                json=update_data,
                timeout=30
            )
            
            print(f"   📤 Request: PUT {api_url}v2/projects/{project_id}")
            print(f"   📤 Data: {json.dumps(update_data)}")
            print(f"   📥 Status: {response.status_code}")
            print(f"   📥 Response: {response.text[:300]}...")
            
            if response.status_code == 200:
                print("   ✅ Project update successful")
            elif response.status_code == 500:
                print("   🚨 500 error - likely enum handling issue in update!")
                return False
            else:
                print(f"   ❌ Project update failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Request failed: {e}")
    
    # Test 3: Create a subscription
    print(f"\n3️⃣ Testing subscription creation...")
    subscription_data = {
        "personId": "02724257-4c6a-4aac-9c19-89c87c499bc8",  # Known test person
        "projectId": project_id if 'project_id' in locals() else "test-project-id",
        "status": "active",  # String enum
        "notes": "Test subscription"
    }
    
    try:
        response = requests.post(
            f"{api_url}v2/subscriptions",
            headers={"Content-Type": "application/json"},
            json=subscription_data,
            timeout=30
        )
        
        print(f"   📤 Request: POST {api_url}v2/subscriptions")
        print(f"   📤 Data: {json.dumps(subscription_data)}")
        print(f"   📥 Status: {response.status_code}")
        print(f"   📥 Response: {response.text[:300]}...")
        
        if response.status_code == 201:
            print("   ✅ Subscription creation successful")
            subscription_response = response.json()
            subscription_id = subscription_response.get("id")
        elif response.status_code == 500:
            print("   🚨 500 error - likely enum handling issue!")
            return False
        else:
            print(f"   ❌ Subscription creation failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Request failed: {e}")
    
    # Test 4: Update the subscription
    if 'subscription_id' in locals():
        print(f"\n4️⃣ Testing subscription update...")
        update_data = {
            "status": "completed",  # String enum
            "notes": "Updated test subscription"
        }
        
        try:
            response = requests.put(
                f"{api_url}v2/subscriptions/{subscription_id}",
                headers={"Content-Type": "application/json"},
                json=update_data,
                timeout=30
            )
            
            print(f"   📤 Request: PUT {api_url}v2/subscriptions/{subscription_id}")
            print(f"   📤 Data: {json.dumps(update_data)}")
            print(f"   📥 Status: {response.status_code}")
            print(f"   📥 Response: {response.text[:300]}...")
            
            if response.status_code == 200:
                print("   ✅ Subscription update successful")
            elif response.status_code == 500:
                print("   🚨 500 error - likely enum handling issue in update!")
                return False
            else:
                print(f"   ❌ Subscription update failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Request failed: {e}")
    
    print(f"\n🎯 API Testing Complete")
    return True

if __name__ == "__main__":
    success = test_project_subscription_apis()
    if success:
        print("\n✅ API testing completed")
        sys.exit(0)
    else:
        print("\n❌ API testing failed - issues found")
        sys.exit(1)