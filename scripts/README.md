# Registry API Scripts

This directory contains maintenance and analysis scripts for the registry-api.

## Data Management Scripts

### `analyze_cascade_deletion_simple.py`
**Purpose**: Analyzes cascade deletion issues for user subscriptions
**Usage**: `uv run python scripts/analyze_cascade_deletion_simple.py` or `just analyze-cascade-deletion`
**What it does**:
- Identifies orphaned subscriptions (subscriptions for deleted users)
- Provides data integrity analysis
- Shows subscription count discrepancies
- Read-only analysis for monitoring

### `fix_cascade_deletion_simple.py`
**Purpose**: Fixes cascade deletion issues and provides code solution
**Usage**: `uv run python scripts/fix_cascade_deletion_simple.py` or `just fix-cascade-deletion`
**What it does**:
- Analyzes orphaned subscriptions
- Optionally cleans up orphaned data
- Provides the code fix for proper cascade deletion
- Shows implementation steps

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

### `debug-person-update-issue.py`
**Purpose**: Debug specific person update issues causing 500 errors
**Usage**: `python scripts/debug-person-update-issue.py`
**What it does**:
- Tests person GET and UPDATE operations
- Tests various data scenarios (empty fields, nulls, etc.)
- Identifies specific causes of 500 errors
- Tests with different authentication headers

### `test-project-subscription-api.py`
**Purpose**: Test project and subscription API endpoints
**Usage**: `python scripts/test-project-subscription-api.py`
**What it does**:
- Tests project CRUD operations
- Tests subscription CRUD operations
- Identifies enum handling issues
- Validates API response formats

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

## Just Tasks (Recommended)

For better integration with the development workflow, use these just tasks:

```bash
# Data management
just analyze-cascade-deletion    # Analyze subscription data integrity
just fix-cascade-deletion        # Fix cascade deletion issues
just check-subscription-integrity # Monitor data consistency

# Testing
just test-critical              # Run critical integration tests
just test-all                   # Run all tests
just test-coverage              # Run tests with coverage

# Code quality
just lint                       # Run code quality checks
just format                     # Fix code formatting
```

## Environment Variables

Some scripts may require environment variables:

- `API_URL`: Base URL for API testing (defaults to production URL)
- `AWS_PROFILE`: AWS profile for deployment scripts
- `ENVIRONMENT`: Target environment (dev/staging/prod)
- `PEOPLE_TABLE_NAME`: DynamoDB table name for people (default: PeopleTable)
- `SUBSCRIPTIONS_TABLE_NAME`: DynamoDB table name for subscriptions (default: SubscriptionsTable)

## Usage Examples

```bash
# Analyze cascade deletion issues
just analyze-cascade-deletion

# Fix cascade deletion issues
just fix-cascade-deletion

# Run compatibility test
node scripts/api-frontend-compatibility-test.js

# Apply frontend patches
node scripts/frontend-compatibility-patch.js

# Run pre-commit checks
./scripts/pre-commit-check.sh
```

## Script Dependencies

- **Python scripts**: Require Python 3.7+ and dependencies managed by uv
- **Node.js scripts**: Require Node.js 16+ (no additional dependencies)
- **Shell scripts**: Require bash and standard Unix tools
- **AWS scripts**: Require AWS credentials configured (boto3)

## Maintenance

These scripts are maintained as part of the registry-api repository. When updating:

1. Test scripts in development environment first
2. Update documentation if script behavior changes
3. Ensure scripts work with current API version
4. Update environment variable requirements if needed
5. Follow the branch-first, PR-review, CodeCatalyst-deploy workflow

## Troubleshooting

### Common Issues

1. **Permission denied**: Make shell scripts executable with `chmod +x scripts/*.sh`
2. **Module not found**: Use `uv run` for Python scripts or ensure proper virtual environment
3. **API connection errors**: Check API_URL environment variable and network connectivity
4. **Authentication errors**: Some scripts may require valid AWS credentials
5. **Import errors**: Run scripts from the registry-api root directory

### Data Management Issues

1. **Orphaned subscriptions**: Use `just analyze-cascade-deletion` to identify
2. **Subscription count discrepancies**: Check for cascade deletion issues
3. **Database connectivity**: Ensure AWS credentials and region are configured
4. **Table not found**: Verify table names in environment variables

### Getting Help

- Check script output for specific error messages
- Review the script source code for detailed comments
- Test with debug/verbose flags where available
- Ensure all dependencies are installed with `uv install`
- Check the troubleshooting documentation in registry-documentation/troubleshooting/