#!/usr/bin/env node

/**
 * Debug API Responses
 * 
 * This script helps debug the actual API responses to understand the compatibility issues.
 */

const API_BASE_URL = process.env.API_URL || 'https://2t9blvt2c1.execute-api.us-east-1.amazonaws.com/prod';

async function makeRequest(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  console.log(`\n🔍 ${options.method || 'GET'} ${url}`);
  
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

  console.log(`📊 Status: ${response.status} ${response.statusText}`);
  console.log(`📄 Response Type: ${typeof responseData}`);
  console.log(`📝 Response:`, JSON.stringify(responseData, null, 2));

  return { status: response.status, data: responseData };
}

async function debugApiResponses() {
  console.log('🔍 Debugging API Responses');
  console.log('=' .repeat(50));

  try {
    // Test list people endpoint
    console.log('\n1. Testing /people endpoint:');
    await makeRequest('/people');

    // Test create person endpoint
    console.log('\n2. Testing POST /people endpoint:');
    const testPersonData = {
      firstName: "Debug",
      lastName: "Test",
      email: "debug.test@example.com",
      phone: "+591 70123456",
      dateOfBirth: "1990-05-15",
      address: {
        street: "Test Street 123",
        city: "Test City",
        state: "Test State",
        country: "Bolivia"
      }
    };

    await makeRequest('/people', {
      method: 'POST',
      body: JSON.stringify(testPersonData)
    });

  } catch (error) {
    console.error('❌ Error:', error.message);
  }
}

debugApiResponses();