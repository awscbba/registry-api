# Versioned API Handler Test Suite

This directory contains comprehensive tests for the versioned API handler to ensure code quality and prevent regressions.

## Test Files

### Core Test Files

1. **`test_versioned_api_handler.py`** - Main comprehensive test suite
   - Tests all endpoints (v1, v2, legacy)
   - Tests error handling
   - Tests authentication
   - Tests admin functionality
   - Integration tests

2. **`test_async_correctness.py`** - Async/await correctness tests
   - Verifies all endpoint functions are async
   - Checks database calls are properly awaited
   - Tests for blocking calls in async functions
   - Validates function signatures

3. **`test_critical_fixes.py`** - Tests for specific fixes applied
   - No duplicate function definitions
   - Proper async/await usage
   - Admin endpoints accessibility
   - Import correctness
   - Environment variable configuration

### Configuration Files

4. **`conftest.py`** - Test configuration and fixtures
   - Mock objects for testing
   - Environment setup
   - Custom assertions
   - Test markers

## Running Tests

### Quick Test Run
```bash
# Run all versioned API tests
python -m pytest tests/test_versioned_api_handler.py tests/test_async_correctness.py tests/test_critical_fixes.py -v

# Run only critical fixes tests
python -m pytest tests/test_critical_fixes.py -v

# Run only async correctness tests  
python -m pytest tests/test_async_correctness.py -v
```

### Comprehensive Test Run
```bash
# Use the test runner script
python run_versioned_api_tests.py
```

### Test with Coverage
```bash
python -m pytest tests/test_versioned_api_handler.py tests/test_async_correctness.py tests/test_critical_fixes.py --cov=src/handlers --cov-report=term-missing
```

## Test Categories

### Unit Tests (`-m unit`)
- Individual function testing
- Mock-based testing
- Fast execution

### Integration Tests (`-m integration`)
- Multi-component testing
- End-to-end workflows
- Database interaction testing

### Async Tests (`-m async_test`)
- Async/await correctness
- Concurrent execution
- Async error handling

## Key Test Areas

### 1. Endpoint Functionality
- ✅ All v1 endpoints work correctly
- ✅ All v2 endpoints work correctly  
- ✅ Legacy endpoints redirect properly
- ✅ Admin endpoints are accessible
- ✅ Health check endpoint works

### 2. Error Handling
- ✅ Database errors are handled gracefully
- ✅ Validation errors return proper status codes
- ✅ Missing data errors are descriptive
- ✅ Authentication errors are secure

### 3. Async/Await Correctness
- ✅ All endpoint functions are async
- ✅ Database calls are properly awaited
- ✅ No blocking calls in async functions
- ✅ AsyncMock is used correctly in tests

### 4. Code Quality
- ✅ No duplicate function definitions
- ✅ No redundant imports
- ✅ Proper route registration
- ✅ Consistent function signatures

### 5. Configuration
- ✅ Environment variables work correctly
- ✅ Test admin email is configurable
- ✅ JWT configuration is flexible

## Critical Tests

These tests must pass before deployment:

1. **`test_no_duplicate_function_definitions_in_source`** - Prevents duplicate functions
2. **`test_admin_test_endpoint_exists`** - Ensures admin functionality works
3. **`test_async_database_calls_work_correctly`** - Verifies async/await correctness
4. **`test_all_routes_registered`** - Ensures all endpoints are accessible
5. **`test_no_duplicate_routes`** - Prevents route conflicts

## Continuous Integration

The test suite runs automatically on:
- Push to main/develop branches
- Pull requests affecting versioned API handler
- Changes to test files

See `.github/workflows/test-versioned-api.yml` for CI configuration.

## Adding New Tests

When adding new functionality to the versioned API handler:

1. Add unit tests to `test_versioned_api_handler.py`
2. Add async correctness tests to `test_async_correctness.py` if needed
3. Add critical fix verification to `test_critical_fixes.py` if fixing bugs
4. Update this README with new test categories

## Test Data and Fixtures

Use the fixtures in `conftest.py`:
- `mock_person` - Mock person object
- `mock_admin_person` - Mock admin user
- `mock_project` - Mock project object
- `sample_person_data` - Sample person data for requests
- `comprehensive_db_mock` - Fully configured database mock

## Debugging Failed Tests

1. Run tests with verbose output: `-v`
2. Show full traceback: `--tb=long`
3. Stop on first failure: `-x`
4. Run specific test: `pytest tests/file.py::TestClass::test_method`
5. Use print statements or `pytest.set_trace()` for debugging

## Performance Considerations

- Unit tests should run in < 1 second each
- Integration tests should run in < 5 seconds each
- Total test suite should complete in < 30 seconds
- Use mocks to avoid real database calls
- Use TestClient for HTTP testing (faster than real server)

## Maintenance

Review and update tests when:
- Adding new endpoints
- Changing existing endpoint behavior
- Modifying database schema
- Updating dependencies
- Fixing bugs (add regression tests)

The test suite is designed to catch issues early and ensure the versioned API handler remains stable and reliable.