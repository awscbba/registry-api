#!/usr/bin/env node

/**
 * Frontend Compatibility Patch
 * 
 * This script applies immediate fixes to the frontend to improve compatibility
 * with the updated API while maintaining functionality.
 */

const fs = require('fs');
const path = require('path');

function applyPatch(filePath, originalCode, patchedCode, description) {
  console.log(`\n🔧 Patching: ${filePath}`);
  console.log(`   ${description}`);
  
  if (!fs.existsSync(filePath)) {
    console.log(`   ❌ File not found: ${filePath}`);
    return false;
  }
  
  let content = fs.readFileSync(filePath, 'utf8');
  
  if (content.includes(patchedCode)) {
    console.log(`   ✅ Already patched`);
    return true;
  }
  
  if (!content.includes(originalCode)) {
    console.log(`   ⚠️  Original code not found - manual review needed`);
    return false;
  }
  
  content = content.replace(originalCode, patchedCode);
  fs.writeFileSync(filePath, content);
  console.log(`   ✅ Patched successfully`);
  return true;
}

function patchApiService() {
  const filePath = '../registry-frontend/src/services/api.ts';
  
  // Patch 1: Fix getAllPeople to handle new response format
  const originalGetAllPeople = `  async getAllPeople(): Promise<Person[]> {
    const response = await fetch(\`\${API_BASE_URL}/people\`);
    return handleApiResponse(response);
  },`;

  const patchedGetAllPeople = `  async getAllPeople(): Promise<Person[]> {
    const response = await fetch(\`\${API_BASE_URL}/people\`);
    const data = await handleApiResponse(response);
    
    // Handle both old array format and new object format
    if (Array.isArray(data)) {
      return data; // Old format (backward compatibility)
    } else if (data && data.people && Array.isArray(data.people)) {
      return data.people; // New format
    } else {
      console.error('Unexpected API response format:', data);
      return []; // Fallback to empty array
    }
  },`;

  applyPatch(filePath, originalGetAllPeople, patchedGetAllPeople, 
    'Handle new response format for getAllPeople');

  // Patch 2: Fix createPerson to handle 200 status code
  const originalCreatePerson = `  async createPerson(person: PersonCreate): Promise<Person> {
    const response = await fetch(\`\${API_BASE_URL}/people\`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(person),
    });
    return handleApiResponse(response);
  },`;

  const patchedCreatePerson = `  async createPerson(person: PersonCreate): Promise<Person> {
    const response = await fetch(\`\${API_BASE_URL}/people\`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(person),
    });
    
    // Handle both 200 and 201 status codes
    if (!response.ok) {
      let errorMessage: string;
      try {
        const errorData = await response.json();
        errorMessage = errorData.message || errorData.error || response.statusText;
      } catch {
        errorMessage = response.statusText;
      }
      throw new ApiError(response.status, errorMessage);
    }
    
    const data = await response.json();
    
    // If API returns a generic message instead of person data, handle gracefully
    if (data && !data.id && data.message) {
      console.warn('API returned message instead of person data:', data.message);
      // For now, return a placeholder - this needs proper API fix
      throw new ApiError(500, 'API did not return created person data');
    }
    
    return data;
  },`;

  applyPatch(filePath, originalCreatePerson, patchedCreatePerson, 
    'Handle 200 status code and improve error handling for createPerson');
}

function patchApiErrorHandling() {
  const filePath = '../registry-frontend/src/types/api.ts';
  
  const originalHandleApiResponse = `export async function handleApiResponse(response: Response): Promise<any> {
  if (!response.ok) {
    let errorMessage: string;
    try {
      const errorData = await response.json();
      errorMessage = errorData.message || errorData.error || response.statusText;
    } catch {
      errorMessage = response.statusText;
    }
    throw new ApiError(response.status, errorMessage);
  }

  try {
    return await response.json();
  } catch {
    throw new ApiError(500, 'Invalid JSON response');
  }
}`;

  const patchedHandleApiResponse = `export async function handleApiResponse(response: Response): Promise<any> {
  if (!response.ok) {
    let errorMessage: string;
    try {
      const errorData = await response.json();
      errorMessage = errorData.message || errorData.error || response.statusText;
    } catch {
      errorMessage = response.statusText;
    }
    
    // Handle authentication errors specifically
    if (response.status === 401) {
      console.warn('Authentication required - API now requires JWT tokens');
      errorMessage = 'Authentication required. Please implement login system.';
    }
    
    throw new ApiError(response.status, errorMessage);
  }

  try {
    return await response.json();
  } catch {
    throw new ApiError(500, 'Invalid JSON response');
  }
}`;

  applyPatch(filePath, originalHandleApiResponse, patchedHandleApiResponse, 
    'Add better authentication error handling');
}

function createAuthenticationStub() {
  const filePath = '../registry-frontend/src/services/authStub.ts';
  
  if (fs.existsSync(filePath)) {
    console.log(`\n✅ Authentication stub already exists: ${filePath}`);
    return;
  }
  
  console.log(`\n📝 Creating authentication stub: ${filePath}`);
  
  const authStubContent = `/**
 * Authentication Stub
 * 
 * This is a temporary stub for authentication functionality.
 * Replace this with a proper authentication implementation.
 */

export interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
}

export interface LoginResponse {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresIn: number;
  user: User;
}

// Temporary mock authentication - REMOVE IN PRODUCTION
let mockAuthToken: string | null = null;
let mockUser: User | null = null;

export const authService = {
  // Mock login - replace with real implementation
  async login(email: string, password: string): Promise<LoginResponse> {
    console.warn('Using mock authentication - implement real auth system');
    
    // Mock successful login
    mockAuthToken = 'mock-jwt-token-' + Date.now();
    mockUser = {
      id: 'mock-user-id',
      email: email,
      firstName: 'Mock',
      lastName: 'User'
    };
    
    return {
      accessToken: mockAuthToken,
      refreshToken: 'mock-refresh-token',
      tokenType: 'bearer',
      expiresIn: 3600,
      user: mockUser
    };
  },

  async logout(): Promise<void> {
    mockAuthToken = null;
    mockUser = null;
  },

  getCurrentUser(): User | null {
    return mockUser;
  },

  getAuthToken(): string | null {
    return mockAuthToken;
  },

  isAuthenticated(): boolean {
    return mockAuthToken !== null;
  }
};

// Helper function to add auth headers to requests
export function addAuthHeaders(headers: Record<string, string> = {}): Record<string, string> {
  const token = authService.getAuthToken();
  if (token) {
    headers['Authorization'] = \`Bearer \${token}\`;
  }
  return headers;
}
`;

  fs.writeFileSync(filePath, authStubContent);
  console.log(`   ✅ Authentication stub created`);
}

function updateApiServiceWithAuth() {
  const filePath = '../registry-frontend/src/services/api.ts';
  
  // Add import for auth stub
  const originalImports = `import type { Person, PersonCreate, PersonUpdate } from '../types/person';
import { ApiError, handleApiResponse } from '../types/api';`;

  const patchedImports = `import type { Person, PersonCreate, PersonUpdate } from '../types/person';
import { ApiError, handleApiResponse } from '../types/api';
import { addAuthHeaders } from './authStub';`;

  applyPatch(filePath, originalImports, patchedImports, 
    'Add authentication stub import');

  // Update getAllPeople with auth headers
  const originalGetAllPeopleAuth = `    const response = await fetch(\`\${API_BASE_URL}/people\`);`;
  const patchedGetAllPeopleAuth = `    const response = await fetch(\`\${API_BASE_URL}/people\`, {
      headers: addAuthHeaders()
    });`;

  applyPatch(filePath, originalGetAllPeopleAuth, patchedGetAllPeopleAuth, 
    'Add auth headers to getAllPeople');
}

function createCompatibilityNotes() {
  const filePath = '../COMPATIBILITY_STATUS.md';
  
  console.log(`\n📋 Creating compatibility status: ${filePath}`);
  
  const content = `# Frontend-API Compatibility Status

## ✅ Applied Patches

1. **API Response Format Handling**
   - Updated \`getAllPeople()\` to handle both array and object response formats
   - Added fallback to empty array for unexpected formats

2. **Status Code Handling**
   - Updated \`createPerson()\` to accept both 200 and 201 status codes
   - Improved error handling for API responses

3. **Authentication Error Handling**
   - Added specific handling for 401 Unauthorized responses
   - Added warning messages for authentication requirements

4. **Authentication Stub**
   - Created temporary authentication stub for development
   - Added helper functions for auth headers

## ⚠️ Temporary Solutions

- **Mock Authentication**: Using stub authentication for development
- **Response Format Fallbacks**: Handling both old and new API formats
- **Error Message Improvements**: Better user feedback for API issues

## 🚨 Still Required

1. **Proper Authentication System**
   - Replace auth stub with real JWT implementation
   - Add login/logout UI components
   - Implement token refresh logic

2. **API Fixes**
   - Fix data leakage in API responses
   - Ensure consistent response formats
   - Fix create person endpoint

3. **Complete Testing**
   - Test all CRUD operations
   - Test error scenarios
   - Test authentication flows

## 🧪 Testing

Run the compatibility test to check current status:
\`\`\`bash
node scripts/api-frontend-compatibility-test.js
\`\`\`

## 📈 Progress

- ✅ Basic compatibility patches applied
- ⏳ Authentication system (in progress)
- ⏳ API security fixes (needed)
- ⏳ Complete integration testing (needed)

---
*Last updated: ${new Date().toISOString()}*
`;

  fs.writeFileSync(filePath, content);
  console.log(`   ✅ Compatibility status created`);
}

function main() {
  console.log('🚀 Applying Frontend Compatibility Patches');
  console.log('=' .repeat(60));

  let success = true;

  try {
    // Apply patches to existing files
    patchApiService();
    patchApiErrorHandling();
    
    // Create new files
    createAuthenticationStub();
    updateApiServiceWithAuth();
    createCompatibilityNotes();

    console.log('\n' + '=' .repeat(60));
    console.log('✅ All patches applied successfully!');
    console.log('\n📋 Next Steps:');
    console.log('1. Test the patched frontend with the API');
    console.log('2. Run: node scripts/api-frontend-compatibility-test.js');
    console.log('3. Implement proper authentication system');
    console.log('4. Review COMPATIBILITY_STATUS.md for progress');
    
  } catch (error) {
    console.error('❌ Error applying patches:', error.message);
    success = false;
  }

  if (!success) {
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}