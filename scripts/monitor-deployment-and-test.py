#!/usr/bin/env python3
"""
Monitor deployment status and test the person update fix once deployed
"""

import requests
import time
import sys
from datetime import datetime

API_BASE_URL = "https://2t9blvt2c1.execute-api.us-east-1.amazonaws.com/prod"
TEST_PERSON_ID = "8a22f71c-b3ba-46f0-912a-8eb44b1037ac"


def test_person_endpoints():
    """Test if the person endpoints are working after deployment"""

    print(f"🧪 Testing Person Endpoints")
    print(f"Time: {datetime.now().isoformat()}")
    print("-" * 50)

    # Test 1: Get person (this was failing before)
    print("1️⃣ Testing GET person...")
    try:
        response = requests.get(f"{API_BASE_URL}/v2/people/{TEST_PERSON_ID}")
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            print("   ✅ GET person working!")
            person_data = response.json()
            print(
                f"   Person: {person_data.get('data', {}).get('firstName', 'Unknown')} {person_data.get('data', {}).get('lastName', 'Unknown')}"
            )
        else:
            print(f"   ❌ GET person failed: {response.text}")
            return False

    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False

    # Test 2: Update person (this was the main issue)
    print("\n2️⃣ Testing PUT person...")
    update_data = {"firstName": "Test", "lastName": "Fixed", "phone": "+591 70123456"}

    try:
        response = requests.put(
            f"{API_BASE_URL}/v2/people/{TEST_PERSON_ID}",
            headers={"Content-Type": "application/json"},
            json=update_data,
        )
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            print("   ✅ PUT person working!")
            updated_data = response.json()
            print(
                f"   Updated: {updated_data.get('data', {}).get('firstName', 'Unknown')} {updated_data.get('data', {}).get('lastName', 'Unknown')}"
            )
        else:
            print(f"   ❌ PUT person failed: {response.text}")
            return False

    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False

    # Test 3: List people (general endpoint test)
    print("\n3️⃣ Testing GET people list...")
    try:
        response = requests.get(f"{API_BASE_URL}/v2/people")
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            print("   ✅ GET people list working!")
            people_data = response.json()
            count = len(people_data.get("data", []))
            print(f"   Found {count} people")
        else:
            print(f"   ❌ GET people list failed: {response.text}")
            return False

    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False

    return True


def monitor_deployment():
    """Monitor deployment by testing endpoints periodically"""

    print("🚀 Monitoring Deployment Status")
    print("=" * 60)
    print("Waiting for deployment to complete...")
    print("Testing endpoints every 30 seconds...")
    print("Press Ctrl+C to stop monitoring")

    attempt = 1
    max_attempts = 20  # 10 minutes max

    while attempt <= max_attempts:
        print(f"\n📊 Attempt {attempt}/{max_attempts}")

        if test_person_endpoints():
            print("\n🎉 SUCCESS! Deployment appears to be working!")
            print("✅ Person endpoints are responding correctly")
            print("✅ Frontend should now be able to update persons")
            return True

        if attempt < max_attempts:
            print(f"\n⏳ Deployment not ready yet. Waiting 30 seconds...")
            time.sleep(30)

        attempt += 1

    print("\n⚠️  Deployment monitoring timed out")
    print("The deployment might still be in progress or there might be an issue")
    return False


def main():
    """Main function"""

    if len(sys.argv) > 1 and sys.argv[1] == "--test-only":
        # Just test once, don't monitor
        success = test_person_endpoints()
        if success:
            print("\n✅ All tests passed!")
            sys.exit(0)
        else:
            print("\n❌ Tests failed!")
            sys.exit(1)
    else:
        # Monitor deployment
        try:
            success = monitor_deployment()
            if success:
                print("\n✅ Monitoring completed successfully!")
                sys.exit(0)
            else:
                print("\n❌ Monitoring completed with issues!")
                sys.exit(1)
        except KeyboardInterrupt:
            print("\n\n⏹️  Monitoring stopped by user")
            print(
                "You can test manually with: python scripts/monitor-deployment-and-test.py --test-only"
            )
            sys.exit(0)


if __name__ == "__main__":
    main()
