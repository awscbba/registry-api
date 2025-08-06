# Registry API Scripts

This directory contains essential maintenance and analysis scripts for the registry-api.

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

### `cleanup_duplicate_subscriptions.py`
**Purpose**: Cleans up duplicate subscription records
**Usage**: `uv run python scripts/cleanup_duplicate_subscriptions.py`
**What it does**:
- Identifies duplicate subscription records
- Provides cleanup options for data integrity
- Maintains referential integrity during cleanup

### `database_health_check.py`
**Purpose**: Performs comprehensive database health checks
**Usage**: `uv run python scripts/database_health_check.py`
**What it does**:
- Checks database connectivity and performance
- Validates data integrity across tables
- Identifies potential issues before they become problems
- Provides health metrics and recommendations

## System Administration Scripts

### `set_initial_admin.py`
**Purpose**: Sets up initial admin user for the system
**Usage**: `uv run python scripts/set_initial_admin.py <email>`
**What it does**:
- Creates initial admin user by email
- Sets up proper admin permissions
- Required for system bootstrap

## Development & Deployment Scripts

### `pre-commit-check.sh`
**Purpose**: Runs code quality checks before commits (used by git hooks)
**Usage**: `./scripts/pre-commit-check.sh`
**What it does**:
- Runs black formatting
- Runs flake8 linting
- Runs critical tests
- Prevents commits that would fail CI/CD

### `validate-deployment.sh`
**Purpose**: Validates deployment configuration
**Usage**: `./scripts/validate-deployment.sh`
**What it does**:
- Checks deployment configuration
- Validates environment variables
- Tests basic connectivity
- Ensures deployment readiness

### `validate-workflows.sh`
**Purpose**: Validates CI/CD workflow configuration
**Usage**: `./scripts/validate-workflows.sh`
**What it does**:
- Checks workflow syntax
- Validates pipeline configuration
- Tests workflow steps
- Ensures CI/CD pipeline health

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

Scripts may require these environment variables:

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

# Set up initial admin user
uv run python scripts/set_initial_admin.py admin@example.com

# Run pre-commit checks manually
./scripts/pre-commit-check.sh

# Validate deployment configuration
./scripts/validate-deployment.sh
```

## Script Categories

### **Data Management** 🗃️
Scripts for maintaining data integrity and consistency:
- Cascade deletion analysis and fixes
- Data cleanup and validation

### **System Administration** ⚙️
Scripts for system setup and configuration:
- Initial admin user setup
- System bootstrap operations

### **Development & Deployment** 🚀
Scripts for development workflow and deployment:
- Code quality checks (git hooks)
- Deployment validation
- CI/CD workflow validation

## Script Dependencies

- **Python scripts**: Require Python 3.7+ and dependencies managed by uv
- **Shell scripts**: Require bash and standard Unix tools
- **AWS scripts**: Require AWS credentials configured (boto3)

## Development Workflow Integration

These scripts are integrated with the development workflow:

1. **Git Hooks**: `pre-commit-check.sh` runs automatically on push
2. **Just Tasks**: All scripts have corresponding just tasks for easy access
3. **CI/CD**: Validation scripts ensure deployment readiness
4. **Data Management**: Cascade deletion tools maintain data integrity

## Maintenance

Scripts are maintained following these principles:

1. **Simplicity**: Each script has a single, clear purpose
2. **Integration**: Scripts work with existing development tools (uv, just, git)
3. **Documentation**: Each script is well-documented with clear usage
4. **Testing**: Scripts are tested and validated before deployment
5. **Cleanup**: Outdated scripts are removed to avoid confusion

## Troubleshooting

### Common Issues

1. **Permission denied**: Make shell scripts executable with `chmod +x scripts/*.sh`
2. **Module not found**: Use `uv run` for Python scripts
3. **AWS credentials**: Ensure AWS credentials are configured for AWS-dependent scripts
4. **Environment variables**: Check required environment variables are set

### Data Management Issues

1. **Orphaned subscriptions**: Use `just analyze-cascade-deletion` to identify
2. **Subscription count discrepancies**: Check for cascade deletion issues
3. **Database connectivity**: Ensure AWS credentials and region are configured

### Getting Help

- Check script output for specific error messages
- Review script source code for detailed comments
- Use `just --list` to see available tasks
- Check troubleshooting documentation in `registry-documentation/troubleshooting/`

## Removed Scripts

The following scripts have been removed as they are no longer needed:

- **Frontend compatibility scripts**: Moved to registry-frontend repo
- **Debug scripts for specific issues**: Issues have been resolved
- **API compatibility test scripts**: Replaced by comprehensive test suite
- **Critical fix scripts**: Fixes have been applied and integrated

This cleanup ensures the scripts directory contains only current, essential tools.
