#!/usr/bin/env node

/**
 * API-Frontend Compatibility Test
 * 
 * This script tests the compatibility between the updated registry-api
 * and the existing registry-frontend to identify potential breaking changes.
 */

const API_BASE_URL = process.env.API_URL || 'https://2t9blvt2c1.execute-api.us-east-1.amazonaws.com/prod';

// Test data that matches frontend expectations
const testPersonData = {
  firstName: "Juan",
  lastName: "Pérez",
  email: "juan.perez@test.com",
  phone: "+591 70123456",
  dateOfBirth: "1990-05-15",
  address: {
    street: "Av. Heroínas 123",
    city: "Cochabamba",
    state: "Cochabamba",
    country: "Bolivia",
    postalCode: "0000"
  }
};

class CompatibilityTester {
  constructor() {
    this.results = {
      passed: 0,
      failed: 0,
      issues: []
    };
  }

  async runTest(testName, testFn) {
    console.log(`\n🧪 Testing: ${testName}`);
    try {
      await testFn();
      console.log(`✅ PASSED: ${testName}`);
      this.results.passed++;
    } catch (error) {
      console.log(`❌ FAILED: ${testName}`);
      console.log(`   Error: ${error.message}`);
      this.results.failed++;
      this.results.issues.push({
        test: testName,
        error: error.message,
        details: error.details || null
      });
    }
  }

  async makeRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    console.log(`   → ${options.method || 'GET'} ${url}`);
    
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    });

    const responseText = await response.text();
    let responseData;
    
    try {
      responseData = responseText ? JSON.parse(responseText) : null;
    } catch (e) {
      responseData = responseText;
    }

    if (!response.ok) {
      const error = new Error(`HTTP ${response.status}: ${response.statusText}`);
      error.status = response.status;
      error.response = responseData;
      throw error;
    }

    return { status: response.status, data: responseData };
  }

  async testHealthEndpoint() {
    const response = await this.makeRequest('/health');
    
    if (response.status !== 200) {
      throw new Error(`Expected status 200, got ${response.status}`);
    }

    const expectedFields = ['status', 'service', 'timestamp'];
    for (const field of expectedFields) {
      if (!(field in response.data)) {
        throw new Error(`Missing field '${field}' in health response`);
      }
    }
  }

  async testListPeopleEndpoint() {
    const response = await this.makeRequest('/people');
    
    if (response.status !== 200) {
      throw new Error(`Expected status 200, got ${response.status}`);
    }

    // Check if response is an array (frontend expects array)
    if (!Array.isArray(response.data)) {
      throw new Error(`Expected array response, got ${typeof response.data}`);
    }

    // If there are people, check the structure matches frontend expectations
    if (response.data.length > 0) {
      const person = response.data[0];
      const requiredFields = [
        'id', 'firstName', 'lastName', 'email', 'phone', 
        'dateOfBirth', 'address', 'createdAt', 'updatedAt'
      ];

      for (const field of requiredFields) {
        if (!(field in person)) {
          throw new Error(`Missing required field '${field}' in person object`);
        }
      }

      // Check address structure
      const requiredAddressFields = ['street', 'city', 'state', 'country'];
      for (const field of requiredAddressFields) {
        if (!(field in person.address)) {
          throw new Error(`Missing required address field '${field}'`);
        }
      }
    }
  }

  async testCreatePersonEndpoint() {
    const response = await this.makeRequest('/people', {
      method: 'POST',
      body: JSON.stringify(testPersonData)
    });

    if (response.status !== 201) {
      throw new Error(`Expected status 201, got ${response.status}`);
    }

    // Verify response structure matches frontend expectations
    const person = response.data;
    const requiredFields = [
      'id', 'firstName', 'lastName', 'email', 'phone', 
      'dateOfBirth', 'address', 'createdAt', 'updatedAt'
    ];

    for (const field of requiredFields) {
      if (!(field in person)) {
        throw new Error(`Missing required field '${field}' in created person`);
      }
    }

    // Store created person ID for cleanup
    this.createdPersonId = person.id;
    return person;
  }

  async testGetPersonEndpoint(personId) {
    const response = await this.makeRequest(`/people/${personId}`);
    
    if (response.status !== 200) {
      throw new Error(`Expected status 200, got ${response.status}`);
    }

    const person = response.data;
    const requiredFields = [
      'id', 'firstName', 'lastName', 'email', 'phone', 
      'dateOfBirth', 'address', 'createdAt', 'updatedAt'
    ];

    for (const field of requiredFields) {
      if (!(field in person)) {
        throw new Error(`Missing required field '${field}' in person`);
      }
    }
  }

  async testUpdatePersonEndpoint(personId) {
    const updateData = {
      firstName: "Juan Carlos",
      lastName: "Pérez Mendoza"
    };

    const response = await this.makeRequest(`/people/${personId}`, {
      method: 'PUT',
      body: JSON.stringify(updateData)
    });

    if (response.status !== 200) {
      throw new Error(`Expected status 200, got ${response.status}`);
    }

    const person = response.data;
    if (person.firstName !== updateData.firstName) {
      throw new Error(`Update failed: firstName not updated correctly`);
    }
  }

  async testDeletePersonEndpoint(personId) {
    const response = await this.makeRequest(`/people/${personId}`, {
      method: 'DELETE'
    });

    // API might return 204 (No Content) or 200 with confirmation
    if (response.status !== 204 && response.status !== 200) {
      throw new Error(`Expected status 204 or 200, got ${response.status}`);
    }
  }

  async testAuthenticationEndpoints() {
    // Test login endpoint structure (even if we don't have valid credentials)
    try {
      await this.makeRequest('/auth/login', {
        method: 'POST',
        body: JSON.stringify({
          email: 'test@example.com',
          password: 'testpassword'
        })
      });
    } catch (error) {
      // We expect this to fail with 401, but let's check the error structure
      if (error.status === 401) {
        // This is expected - just checking the endpoint exists
        console.log('   ℹ️  Login endpoint exists (401 as expected)');
      } else if (error.status === 404) {
        throw new Error('Login endpoint not found - this is a breaking change');
      } else {
        console.log(`   ℹ️  Login endpoint responded with status ${error.status}`);
      }
    }

    // Test /auth/me endpoint (should require authentication)
    try {
      await this.makeRequest('/auth/me');
    } catch (error) {
      if (error.status === 401) {
        console.log('   ℹ️  /auth/me endpoint exists (401 as expected)');
      } else if (error.status === 404) {
        throw new Error('/auth/me endpoint not found - this is a breaking change');
      }
    }
  }

  async testFieldNamingConsistency() {
    // Test that the API returns camelCase field names as expected by frontend
    const response = await this.makeRequest('/people');
    
    if (response.data.length > 0) {
      const person = response.data[0];
      
      // Check for camelCase fields that frontend expects
      const expectedCamelCaseFields = [
        'firstName', 'lastName', 'dateOfBirth', 'createdAt', 'updatedAt'
      ];

      for (const field of expectedCamelCaseFields) {
        if (!(field in person)) {
          throw new Error(`Missing camelCase field '${field}' - frontend expects camelCase`);
        }
      }

      // Check for snake_case fields that would break frontend
      const problematicSnakeCaseFields = [
        'first_name', 'last_name', 'date_of_birth', 'created_at', 'updated_at'
      ];

      for (const field of problematicSnakeCaseFields) {
        if (field in person) {
          throw new Error(`Found snake_case field '${field}' - frontend expects camelCase`);
        }
      }
    }
  }

  async testAddressFieldCompatibility() {
    const response = await this.makeRequest('/people');
    
    if (response.data.length > 0) {
      const person = response.data[0];
      
      // Check address field naming
      if ('zipCode' in person.address && !('postalCode' in person.address)) {
        throw new Error('Address uses zipCode but frontend expects postalCode');
      }

      // Frontend expects postalCode to be optional
      // This should not cause an error if missing
    }
  }

  async cleanup() {
    if (this.createdPersonId) {
      try {
        console.log(`\n🧹 Cleaning up test person: ${this.createdPersonId}`);
        await this.makeRequest(`/people/${this.createdPersonId}`, {
          method: 'DELETE'
        });
        console.log('✅ Cleanup successful');
      } catch (error) {
        console.log(`⚠️  Cleanup failed: ${error.message}`);
      }
    }
  }

  async runAllTests() {
    console.log('🚀 Starting API-Frontend Compatibility Tests');
    console.log(`📡 Testing API at: ${API_BASE_URL}`);
    console.log('=' .repeat(60));

    // Basic connectivity tests
    await this.runTest('Health Endpoint', () => this.testHealthEndpoint());
    
    // Core CRUD operations that frontend depends on
    await this.runTest('List People Endpoint', () => this.testListPeopleEndpoint());
    
    let createdPerson;
    await this.runTest('Create Person Endpoint', async () => {
      createdPerson = await this.testCreatePersonEndpoint();
    });

    if (createdPerson) {
      await this.runTest('Get Person Endpoint', () => this.testGetPersonEndpoint(createdPerson.id));
      await this.runTest('Update Person Endpoint', () => this.testUpdatePersonEndpoint(createdPerson.id));
    }

    // Authentication endpoints (new in API)
    await this.runTest('Authentication Endpoints', () => this.testAuthenticationEndpoints());

    // Data format compatibility
    await this.runTest('Field Naming Consistency', () => this.testFieldNamingConsistency());
    await this.runTest('Address Field Compatibility', () => this.testAddressFieldCompatibility());

    // Cleanup
    await this.cleanup();

    // Final cleanup test
    if (createdPerson) {
      await this.runTest('Delete Person Endpoint', () => this.testDeletePersonEndpoint(createdPerson.id));
    }

    this.printResults();
  }

  printResults() {
    console.log('\n' + '=' .repeat(60));
    console.log('📊 COMPATIBILITY TEST RESULTS');
    console.log('=' .repeat(60));
    
    console.log(`✅ Passed: ${this.results.passed}`);
    console.log(`❌ Failed: ${this.results.failed}`);
    
    if (this.results.issues.length > 0) {
      console.log('\n🚨 COMPATIBILITY ISSUES FOUND:');
      console.log('-' .repeat(40));
      
      this.results.issues.forEach((issue, index) => {
        console.log(`\n${index + 1}. ${issue.test}`);
        console.log(`   Error: ${issue.error}`);
        if (issue.details) {
          console.log(`   Details: ${JSON.stringify(issue.details, null, 2)}`);
        }
      });

      console.log('\n💡 RECOMMENDATIONS:');
      console.log('-' .repeat(20));
      
      if (this.results.issues.some(i => i.error.includes('camelCase'))) {
        console.log('• Update API response models to use camelCase field names');
      }
      
      if (this.results.issues.some(i => i.error.includes('auth'))) {
        console.log('• Update frontend to handle new authentication requirements');
        console.log('• Add JWT token management to frontend services');
      }
      
      if (this.results.issues.some(i => i.error.includes('zipCode'))) {
        console.log('• Ensure address field naming consistency between API and frontend');
      }

      console.log('• Test with actual authentication tokens if available');
      console.log('• Update frontend error handling for new API error formats');
    } else {
      console.log('\n🎉 All compatibility tests passed!');
      console.log('The frontend should work well with the updated API.');
    }

    console.log('\n' + '=' .repeat(60));
  }
}

// Run the tests
async function main() {
  const tester = new CompatibilityTester();
  await tester.runAllTests();
  
  // Exit with error code if tests failed
  if (tester.results.failed > 0) {
    process.exit(1);
  }
}

// Handle errors gracefully
process.on('unhandledRejection', (error) => {
  console.error('❌ Unhandled error:', error.message);
  process.exit(1);
});

if (require.main === module) {
  main();
}

module.exports = { CompatibilityTester };