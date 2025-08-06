#!/usr/bin/env python3
"""Debug the safe_enum_value function"""

import sys
sys.path.insert(0, 'src')

from models.subscription import SubscriptionStatus
from typing import Any

def debug_safe_enum_value(enum_obj: Any, default: str = "") -> str:
    """Debug version of safe_enum_value with detailed logging"""
    print(f"Input: {enum_obj} (type: {type(enum_obj)})")
    
    if enum_obj is None:
        print("Returning default (None case)")
        return default

    # If it's already a string, return as-is
    if isinstance(enum_obj, str):
        print("Returning as-is (string case)")
        return enum_obj

    # If it has value attribute (enum), use it
    if hasattr(enum_obj, "value"):
        print(f"Has value attribute: {enum_obj.value} (type: {type(enum_obj.value)})")
        try:
            result = str(enum_obj.value)
            print(f"Converted to string: {result} (type: {type(result)})")
            return result
        except Exception as e:
            print(f"Exception in value conversion: {e}")
            fallback = str(enum_obj) if enum_obj else default
            print(f"Returning fallback: {fallback}")
            return fallback

    # Fallback to string conversion
    fallback = str(enum_obj) if enum_obj else default
    print(f"Returning final fallback: {fallback}")
    return fallback

if __name__ == "__main__":
    status = SubscriptionStatus.ACTIVE
    print("=== Testing debug_safe_enum_value ===")
    result = debug_safe_enum_value(status)
    print(f"Final result: '{result}' (type: {type(result)})")
    
    print("\n=== Testing original safe_enum_value ===")
    from utils.defensive_utils import safe_enum_value
    original_result = safe_enum_value(status)
    print(f"Original result: '{original_result}' (type: {type(original_result)})")
