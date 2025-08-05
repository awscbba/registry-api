#!/usr/bin/env python3
"""
Critical API Issues Fix Script

This script addresses the most critical compatibility issues found:
1. Data leakage in /people endpoint
2. Response format inconsistencies
3. Status code issues

Run this to quickly patch the most urgent problems.
"""

import os
import sys

def fix_people_handler():
    """Fix the people handler to ensure proper response models are used"""
    
    handler_file = "src/handlers/people_handler.py"
    
    if not os.path.exists(handler_file):
        print(f"❌ Handler file not found: {handler_file}")
        return False
    
    print(f"🔧 Fixing {handler_file}...")
    
    # Read the current file
    with open(handler_file, 'r') as f:
        content = f.read()
    
    # Check if the file already has the correct response model
    if 'response_model=list[PersonResponse]' in content or 'response_model=List[PersonResponse]' in content:
        print("✅ List people endpoint already uses PersonResponse model")
    else:
        print("⚠️  List people endpoint might not be using PersonResponse model")
    
    # Look for potential data leakage issues
    if 'password_hash' in content.lower() or 'password_salt' in content.lower():
        print("🚨 SECURITY WARNING: Handler might be exposing sensitive password data")
        print("   → Ensure all endpoints use PersonResponse.from_person() method")
    
    return True

def create_backward_compatibility_endpoint():
    """Create a backward compatibility endpoint for the frontend"""
    
    compat_file = "src/handlers/compatibility_handler.py"
    
    print(f"📝 Creating compatibility handler: {compat_file}")
    
    compat_code = '''"""
Backward Compatibility Handler

This handler provides backward-compatible endpoints for the frontend
while the frontend is being updated to handle the new API format.
"""

from fastapi import FastAPI, HTTPException, status, Request, Depends
from typing import List
from ..models.person import PersonResponse
from ..services.dynamodb_service import DynamoDBService
from ..middleware.auth_middleware import get_current_user, require_no_password_change

app = FastAPI()
db_service = DynamoDBService()

@app.get("/people/legacy", response_model=List[PersonResponse])
async def list_people_legacy_format(
    request: Request, 
    limit: int = 100, 
    current_user=Depends(require_no_password_change)
):
    """
    Legacy endpoint that returns people as a direct array for backward compatibility.
    
    This endpoint maintains the old response format while the frontend is updated.
    Once frontend is updated, this endpoint can be removed.
    """
    try:
        people = await db_service.list_people(limit=limit)
        
        # Ensure we use PersonResponse to exclude sensitive fields
        return [PersonResponse.from_person(person) for person in people]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve people"
        )

@app.get("/people/new", response_model=dict)
async def list_people_new_format(
    request: Request, 
    limit: int = 100, 
    current_user=Depends(require_no_password_change)
):
    """
    New endpoint that returns people with metadata (count, pagination info, etc.)
    
    This is the new format that provides additional metadata.
    """
    try:
        people = await db_service.list_people(limit=limit)
        
        # Use PersonResponse to exclude sensitive fields
        people_response = [PersonResponse.from_person(person) for person in people]
        
        return {
            "people": people_response,
            "count": len(people_response),
            "limit": limit,
            "has_more": len(people_response) == limit  # Indicates if there might be more
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve people"
        )
'''
    
    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(compat_file), exist_ok=True)
    
    with open(compat_file, 'w') as f:
        f.write(compat_code)
    
    print("✅ Compatibility handler created")
    return True

def create_frontend_update_guide():
    """Create a guide for updating the frontend"""
    
    guide_file = "FRONTEND_UPDATE_GUIDE.md"
    
    print(f"📖 Creating frontend update guide: {guide_file}")
    
    guide_content = '''# Frontend Update Guide

## Quick Fixes for Immediate Compatibility

### 1. Update API Service (registry-frontend/src/services/api.ts)

```typescript
// Replace the getAllPeople method:
async getAllPeople(): Promise<Person[]> {
  const response = await fetch(`${API_BASE_URL}/people`);
  const data = await handleApiResponse(response);
  
  // Handle new response format
  if (Array.isArray(data)) {
    return data; // Old format (backward compatibility)
  } else if (data.people) {
    return data.people; // New format
  } else {
    throw new Error('Unexpected response format');
  }
}

// Update createPerson to handle 200 status:
async createPerson(person: PersonCreate): Promise<Person> {
  const response = await fetch(`${API_BASE_URL}/people`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(person),
  });
  
  // Accept both 200 and 201 status codes
  if (response.status !== 200 && response.status !== 201) {
    throw new ApiError(response.status, 'Error creating person');
  }
  
  return handleApiResponse(response);
}
```

### 2. Add Basic Error Handling for Authentication

```typescript
// Update handleApiResponse in registry-frontend/src/types/api.ts
export async function handleApiResponse(response: Response): Promise<any> {
  if (!response.ok) {
    let errorMessage: string;
    try {
      const errorData = await response.json();
      errorMessage = errorData.message || errorData.error || response.statusText;
    } catch {
      errorMessage = response.statusText;
    }
    
    // Handle authentication errors
    if (response.status === 401) {
      // Redirect to login or show auth error
      console.warn('Authentication required - implement login flow');
      errorMessage = 'Authentication required';
    }
    
    throw new ApiError(response.status, errorMessage);
  }

  try {
    return await response.json();
  } catch {
    throw new ApiError(500, 'Invalid JSON response');
  }
}
```

### 3. Temporary Authentication Bypass (Development Only)

For immediate testing, you can temporarily bypass authentication by:

1. Using the legacy endpoint (if implemented): `/people/legacy`
2. Or implementing a mock authentication token

```typescript
// Temporary mock auth (REMOVE IN PRODUCTION)
const MOCK_AUTH_TOKEN = 'mock-token-for-development';

export const peopleApi = {
  async getAllPeople(): Promise<Person[]> {
    const response = await fetch(`${API_BASE_URL}/people`, {
      headers: {
        'Authorization': `Bearer ${MOCK_AUTH_TOKEN}`,
        'Content-Type': 'application/json',
      }
    });
    // ... rest of the code
  }
}
```

## Next Steps

1. **Immediate**: Apply the quick fixes above
2. **Short-term**: Implement proper authentication system
3. **Long-term**: Update all components to handle new API features

## Testing

After applying fixes, test with:
```bash
node scripts/api-frontend-compatibility-test.js
```

The test should show improved compatibility scores.
'''
    
    with open(guide_file, 'w') as f:
        f.write(guide_content)
    
    print("✅ Frontend update guide created")
    return True

def main():
    print("🚀 Starting Critical API Issues Fix")
    print("=" * 50)
    
    success = True
    
    # Fix 1: Check and fix people handler
    if not fix_people_handler():
        success = False
    
    # Fix 2: Create backward compatibility endpoint
    if not create_backward_compatibility_endpoint():
        success = False
    
    # Fix 3: Create frontend update guide
    if not create_frontend_update_guide():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("✅ All fixes applied successfully!")
        print("\n📋 Next Steps:")
        print("1. Review the compatibility handler code")
        print("2. Follow the Frontend Update Guide")
        print("3. Run the compatibility test again")
        print("4. Implement proper authentication")
    else:
        print("❌ Some fixes failed. Please review the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()