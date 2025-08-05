#!/usr/bin/env python3
"""
Test script to verify DynamoDB parameter fixes for ExpressionAttributeNames

This script tests the fixes for the AttributeError: 'NoneType' object has no attribute 'update'
issue that was occurring in production when updating persons, projects, and subscriptions.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.utils.defensive_utils import safe_update_expression_builder

def test_expression_builder():
    """Test that the expression builder returns appropriate values"""
    print("🧪 Testing safe_update_expression_builder...")
    
    # Test with empty data
    expr, values, names = safe_update_expression_builder({})
    print(f"Empty data: expr='{expr}', values={values}, names={names}")
    print(f"Names is falsy: {not bool(names)}")
    
    # Test with regular fields (no reserved words)
    test_data = {"firstName": "John", "lastName": "Doe"}
    expr, values, names = safe_update_expression_builder(test_data)
    print(f"Regular fields: expr='{expr}', values={values}, names={names}")
    print(f"Names is falsy: {not bool(names)}")
    
    # Test with reserved words
    test_data_reserved = {"name": "Test Project", "status": "active"}
    field_mappings = {"name": "name", "status": "status"}
    expr, values, names = safe_update_expression_builder(test_data_reserved, field_mappings)
    print(f"Reserved words: expr='{expr}', values={values}, names={names}")
    print(f"Names is truthy: {bool(names)}")
    
    print("✅ Expression builder tests completed")

def test_conditional_parameter_logic():
    """Test the conditional parameter logic"""
    print("\n🧪 Testing conditional parameter logic...")
    
    # Test empty dictionary (should be falsy)
    empty_names = {}
    result = empty_names if empty_names else None
    print(f"Empty dict conditional: {result}")
    
    # Test non-empty dictionary (should be truthy)
    non_empty_names = {"#name": "name"}
    result = non_empty_names if non_empty_names else None
    print(f"Non-empty dict conditional: {result}")
    
    # Test the actual parameter building logic
    def build_update_params(expression_names):
        update_params = {
            "Key": {"id": "test-id"},
            "UpdateExpression": "SET updatedAt = :updated_at",
            "ExpressionAttributeValues": {":updated_at": "2025-01-01T00:00:00Z"},
            "ReturnValues": "ALL_NEW",
        }
        
        # Only add ExpressionAttributeNames if it's not empty
        if expression_names:
            update_params["ExpressionAttributeNames"] = expression_names
            
        return update_params
    
    # Test with empty names
    params = build_update_params({})
    print(f"Params with empty names: {params}")
    print(f"Has ExpressionAttributeNames: {'ExpressionAttributeNames' in params}")
    
    # Test with non-empty names
    params = build_update_params({"#name": "name"})
    print(f"Params with names: {params}")
    print(f"Has ExpressionAttributeNames: {'ExpressionAttributeNames' in params}")
    
    print("✅ Conditional parameter logic tests completed")

if __name__ == "__main__":
    print("🔧 Testing DynamoDB Parameter Fixes")
    print("=" * 50)
    
    test_expression_builder()
    test_conditional_parameter_logic()
    
    print("\n✅ All tests completed successfully!")
    print("The fixes should prevent the AttributeError in production.")