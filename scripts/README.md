# Registry API Scripts

This directory contains maintenance and analysis scripts for the registry-api.

## Production Analysis Scripts

### `fix-critical-api-issues.py`
**Purpose**: Addresses critical compatibility issues between API and frontend
**Usage**: `python scripts/fix-critical-api-issues.py`
**What it does**:
- Checks for data leakage in API responses
- Creates backward compatibility endpoints
- Generates frontend update guides

### `api-frontend-compatibility-test.js`
**Purpose**: Tests compatibility between updated API and existing frontend
**Usage**: `node scripts/api-frontend-compatibility-test.js`
**What it does**:
- Tests all CRUD operations
- Validates response formats
- Checks field naming consistency
- Identifies breaking changes

### `debug-api-responses.js`
**Purpose**: Debug actual API responses to understand compatibility issues
**Usage**: `node scripts/debug-api-responses.js`
**What it does**:
- Makes test requests to API endpoints
- Shows detailed response information
- Helps identify response format issues

## Frontend Compatibility Scripts

### `frontend-compatibility-patch.js`
**Purpose**: Applies immediate fixes to frontend for better API compatibility
**Usage**: `node scripts/frontend-compatibility-patch.js`
**What it does**:
- Patches API service to handle new response formats
- Adds authentication error handling
- Creates authentication stub for development

### `verify-frontend-patches.js`
**Purpose**: Verifies that frontend patches were applied correctly
**Usage**: `node scripts/verify-frontend-patches.js`
**What it does**:
- Checks if patches were applied successfully
- Tests patched logic
- Provides next steps for deployment

## Development Scripts

### `pre-commit-check.sh`
**Purpose**: Runs code quality checks before commits
**Usage**: `./scripts/pre-commit-check.sh`
**What it does**:
- Runs black formatting
- Runs flake8 linting
- Optionally runs tests

### `set_initial_admin.py`
**Purpose**: Sets up initial admin user for the system
**Usage**: `python scripts/set_initial_admin.py`
**What it does**:
- Creates initial admin user
- Sets up proper permissions

### `validate-deployment.sh`
**Purpose**: Validates deployment configuration
**Usage**: `./scripts/validate-deployment.sh`
**What it does**:
- Checks deployment configuration
- Validates environment variables
- Tests basic connectivity

### `validate-workflows.sh`
**Purpose**: Validates CI/CD workflow configuration
**Usage**: `./scripts/validate-workflows.sh`
**What it does**:
- Checks workflow syntax
- Validates pipeline configuration
- Tests workflow steps

## Environment Variables

Some scripts may require environment variables:

- `API_URL`: Base URL for API testing (defaults to production URL)
- `AWS_PROFILE`: AWS profile for deployment scripts
- `ENVIRONMENT`: Target environment (dev/staging/prod)

## Usage Examples

```bash
# Run compatibility test
node scripts/api-frontend-compatibility-test.js

# Apply frontend patches
node scripts/frontend-compatibility-patch.js

# Verify patches were applied
node scripts/verify-frontend-patches.js

# Run pre-commit checks
./scripts/pre-commit-check.sh

# Debug API responses
node scripts/debug-api-responses.js
```

## Script Dependencies

- **Python scripts**: Require Python 3.7+ and dependencies from requirements.txt
- **Node.js scripts**: Require Node.js 16+ (no additional dependencies)
- **Shell scripts**: Require bash and standard Unix tools

## Maintenance

These scripts are maintained as part of the registry-api repository. When updating:

1. Test scripts in development environment first
2. Update documentation if script behavior changes
3. Ensure scripts work with current API version
4. Update environment variable requirements if needed

## Troubleshooting

### Common Issues

1. **Permission denied**: Make shell scripts executable with `chmod +x scripts/*.sh`
2. **Module not found**: Ensure you're running Python scripts from the registry-api root directory
3. **API connection errors**: Check API_URL environment variable and network connectivity
4. **Authentication errors**: Some scripts may require valid API credentials

### Getting Help

- Check script output for specific error messages
- Review the script source code for detailed comments
- Test with debug/verbose flags where available
- Ensure all dependencies are installed