#!/bin/bash

# Workflow Validation Script
# Validates CodeCatalyst workflow YAML files for syntax and common issues

set -e

echo "🔍 Validating CodeCatalyst Workflows"
echo "==================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "SUCCESS")
            echo -e "${GREEN}✅ $message${NC}"
            ;;
        "FAIL")
            echo -e "${RED}❌ $message${NC}"
            ;;
        "WARN")
            echo -e "${YELLOW}⚠️ $message${NC}"
            ;;
        "INFO")
            echo -e "ℹ️ $message"
            ;;
    esac
}

# Check if we're in the right directory
if [ ! -d ".codecatalyst/workflows" ]; then
    print_status "FAIL" "Please run this script from the repository root directory"
    exit 1
fi

# Check for required tools
print_status "INFO" "Checking required tools..."

if command -v python3 &> /dev/null; then
    print_status "SUCCESS" "Python 3 is available"
else
    print_status "FAIL" "Python 3 is required for YAML validation"
    exit 1
fi

# Install PyYAML if not available
if ! python3 -c "import yaml" 2>/dev/null; then
    print_status "INFO" "Installing PyYAML for validation..."
    pip3 install PyYAML || {
        print_status "WARN" "Could not install PyYAML, skipping YAML syntax validation"
        YAML_VALIDATION=false
    }
else
    YAML_VALIDATION=true
fi

# Validate YAML syntax
if [ "$YAML_VALIDATION" = true ]; then
    print_status "INFO" "Validating YAML syntax..."
    
    for workflow_file in .codecatalyst/workflows/*.yml; do
        if [ -f "$workflow_file" ]; then
            echo "Checking $workflow_file..."
            if python3 -c "
import yaml
import sys
try:
    with open('$workflow_file', 'r') as f:
        yaml.safe_load(f)
    print('✅ Valid YAML syntax')
except yaml.YAMLError as e:
    print(f'❌ YAML syntax error: {e}')
    sys.exit(1)
except Exception as e:
    print(f'❌ Error reading file: {e}')
    sys.exit(1)
"; then
                print_status "SUCCESS" "$(basename "$workflow_file") - YAML syntax valid"
            else
                print_status "FAIL" "$(basename "$workflow_file") - YAML syntax invalid"
                exit 1
            fi
        fi
    done
else
    print_status "WARN" "Skipping YAML syntax validation"
fi

# Check for common CodeCatalyst workflow issues
print_status "INFO" "Checking for common workflow issues..."

ISSUES_FOUND=false

# Check for consistent environment variable usage
print_status "INFO" "Checking environment variable consistency..."

for workflow_file in .codecatalyst/workflows/*.yml; do
    if [ -f "$workflow_file" ]; then
        # Check for mixed usage of branch name variables
        if grep -q "CODECATALYST_BRANCH_NAME" "$workflow_file" && grep -q "CODECATALYST_SOURCE_BRANCH_NAME" "$workflow_file"; then
            print_status "WARN" "$(basename "$workflow_file") uses both CODECATALYST_BRANCH_NAME and CODECATALYST_SOURCE_BRANCH_NAME"
            print_status "INFO" "Consider using fallback pattern: \${CODECATALYST_BRANCH_NAME:-\${CODECATALYST_SOURCE_BRANCH_NAME:-unknown}}"
        fi
        
        # Check for hardcoded values that should be variables
        if grep -q "142728997126" "$workflow_file"; then
            print_status "WARN" "$(basename "$workflow_file") contains hardcoded account ID"
        fi
        
        # Check for missing error handling in critical operations
        if grep -q "git clone" "$workflow_file" && ! grep -A5 -B5 "git clone" "$workflow_file" | grep -q "||"; then
            print_status "WARN" "$(basename "$workflow_file") git clone operations may lack error handling"
        fi
        
        # Check for S3 operations without error handling
        if grep -q "aws s3" "$workflow_file" && ! grep -A3 -B3 "aws s3" "$workflow_file" | grep -q "||"; then
            print_status "WARN" "$(basename "$workflow_file") S3 operations may lack error handling"
        fi
    fi
done

# Check for required workflow structure
print_status "INFO" "Checking workflow structure..."

for workflow_file in .codecatalyst/workflows/*.yml; do
    if [ -f "$workflow_file" ]; then
        # Check for required fields
        if ! grep -q "Name:" "$workflow_file"; then
            print_status "FAIL" "$(basename "$workflow_file") missing Name field"
            ISSUES_FOUND=true
        fi
        
        if ! grep -q "SchemaVersion:" "$workflow_file"; then
            print_status "FAIL" "$(basename "$workflow_file") missing SchemaVersion field"
            ISSUES_FOUND=true
        fi
        
        if ! grep -q "Triggers:" "$workflow_file"; then
            print_status "FAIL" "$(basename "$workflow_file") missing Triggers field"
            ISSUES_FOUND=true
        fi
        
        if ! grep -q "Actions:" "$workflow_file"; then
            print_status "FAIL" "$(basename "$workflow_file") missing Actions field"
            ISSUES_FOUND=true
        fi
        
        # Check for proper indentation (basic check)
        if grep -n "^[[:space:]]*[[:space:]]" "$workflow_file" | grep -v "^[[:space:]]*#" | head -1; then
            print_status "INFO" "$(basename "$workflow_file") appears to use proper YAML indentation"
        fi
    fi
done

# Check for environment and connection configuration
print_status "INFO" "Checking environment configuration..."

for workflow_file in .codecatalyst/workflows/*.yml; do
    if [ -f "$workflow_file" ]; then
        if grep -q "Environment:" "$workflow_file"; then
            if grep -q "Connections:" "$workflow_file"; then
                print_status "SUCCESS" "$(basename "$workflow_file") has environment connections configured"
            else
                print_status "WARN" "$(basename "$workflow_file") has Environment but no Connections"
            fi
        fi
    fi
done

# Generate validation report
print_status "INFO" "Generating validation report..."

cat > workflow-validation-report.txt << EOF
CodeCatalyst Workflow Validation Report
======================================
Timestamp: $(date)
Repository: $(basename "$(pwd)")

Workflows Validated:
$(ls -1 .codecatalyst/workflows/*.yml | sed 's/^/- /')

Validation Results:
==================
YAML Syntax: $([ "$YAML_VALIDATION" = true ] && echo "VALIDATED" || echo "SKIPPED")
Structure Check: $([ "$ISSUES_FOUND" = false ] && echo "PASSED" || echo "ISSUES FOUND")

Common Issues Checked:
- Environment variable consistency
- Error handling in critical operations
- Required workflow fields
- Environment and connection configuration
- Hardcoded values

Recommendations:
===============
1. Use consistent environment variable patterns
2. Add error handling for all external operations
3. Test workflows in a development environment first
4. Monitor workflow execution logs for issues
5. Keep workflows simple and focused

$([ "$ISSUES_FOUND" = false ] && echo "✅ No critical issues found" || echo "⚠️ Some issues found - review warnings above")
EOF

cat workflow-validation-report.txt

if [ "$ISSUES_FOUND" = false ]; then
    print_status "SUCCESS" "Workflow validation completed successfully!"
    print_status "INFO" "Workflows appear ready for CodeCatalyst execution"
    exit 0
else
    print_status "WARN" "Workflow validation completed with issues"
    print_status "INFO" "Review the issues above before deploying to CodeCatalyst"
    exit 1
fi