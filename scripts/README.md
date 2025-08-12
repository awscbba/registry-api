# Scripts Directory

This directory contains utility scripts for managing and maintaining the People Registry API.

## Admin Management Scripts

### Core Admin Scripts

- **`create_admin_user.py`** - Creates the first admin user for the system
- **`set_initial_admin.py`** - Sets an existing user as admin by email
- **`fix_admin_user.py`** - Fixes admin user with correct credentials (admin@awsugcbba.org / awsugcbba2025)
- **`fix_admin_password_exact.py`** - Updates admin password using exact same method as deployed code

### Diagnostic Scripts

- **`diagnose_admin.py`** - Simple diagnostic script to check admin users in DynamoDB
- **`diagnose_admin_login.py`** - Comprehensive async diagnostic for admin login issues
- **`diagnose_deployed_api.py`** - Diagnoses the deployed API to understand login issues
- **`test_api_login.py`** - Tests the deployed API login endpoint directly

## Database Management Scripts

- **`create_roles_tables.py`** - Creates DynamoDB tables for the RBAC system
- **`database_health_check.py`** - Comprehensive database health check
- **`cleanup_duplicate_subscriptions.py`** - Removes duplicate subscription entries
- **`fix_cascade_deletion_simple.py`** - Fixes cascade deletion issues

## Analysis Scripts

- **`analyze_cascade_deletion_simple.py`** - Analyzes cascade deletion patterns
- **`verify_rbac_simple.py`** - Verifies Role-Based Access Control implementation

## Infrastructure Scripts

- **`request_ses_production.py`** - Requests SES production access for email functionality

## Validation Scripts

- **`validate-workflows.sh`** - Validates GitHub/CodeCatalyst workflows
- **`validate-deployment.sh`** - Validates deployment configuration
- **`pre-commit-check.sh`** - Pre-commit quality checks

## Usage Examples

### Fix Admin Login Issues
```bash
# Diagnose admin login problems
python scripts/diagnose_deployed_api.py

# Fix admin user with correct credentials
python scripts/fix_admin_user.py

# Test the API login
python scripts/test_api_login.py
```

### Create New Admin User
```bash
# Create first admin user
python scripts/create_admin_user.py

# Set existing user as admin
python scripts/set_initial_admin.py
```

### Database Maintenance
```bash
# Check database health
python scripts/database_health_check.py

# Clean up duplicates
python scripts/cleanup_duplicate_subscriptions.py
```

## Admin Credentials

The current admin user credentials are:
- **Email**: `admin@awsugcbba.org`
- **Password**: `awsugcbba2025`

## Notes

- All scripts should be run from the project root directory
- Most scripts require AWS credentials to be configured
- Scripts that modify data include safety checks and confirmations
- Diagnostic scripts are safe to run and don't modify data

## Script Organization

Scripts are organized by functionality:
- **Admin Management**: User creation, password resets, diagnostics
- **Database**: Health checks, cleanup, maintenance
- **Infrastructure**: Deployment validation, service setup
- **Analysis**: Data analysis and verification tools
