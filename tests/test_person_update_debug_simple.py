"""
Simple debug test for PersonUpdate model
"""

import pytest

def test_person_update_model_creation():
    """Test creating PersonUpdate object with isAdmin field"""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))
    
    from src.models.person import PersonUpdate
    
    # Test 1: Create with alias
    try:
        person_update = PersonUpdate(isAdmin=True)
        print(f"✅ PersonUpdate with alias worked: {person_update}")
        print(f"is_admin value: {person_update.is_admin}")
    except Exception as e:
        print(f"❌ PersonUpdate with alias failed: {e}")
    
    # Test 2: Create with field name
    try:
        person_update = PersonUpdate(is_admin=True)
        print(f"✅ PersonUpdate with field name worked: {person_update}")
        print(f"is_admin value: {person_update.is_admin}")
    except Exception as e:
        print(f"❌ PersonUpdate with field name failed: {e}")
    
    # Test 3: Create with dict unpacking
    try:
        data = {"isAdmin": True}
        person_update = PersonUpdate(**data)
        print(f"✅ PersonUpdate with dict unpacking worked: {person_update}")
        print(f"is_admin value: {person_update.is_admin}")
    except Exception as e:
        print(f"❌ PersonUpdate with dict unpacking failed: {e}")

if __name__ == "__main__":
    test_person_update_model_creation()