#!/bin/bash

# Registry API Deployment Validation Script
# This script runs the same validation checks as the CodeCatalyst pipeline locally

set -e

echo "🚀 Registry API Deployment Validation"
echo "====================================="

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
if [ ! -f "main.py" ] || [ ! -d "src" ]; then
    print_status "FAIL" "Please run this script from the registry-api root directory"
    exit 1
fi

# Check for required tools
print_status "INFO" "Checking required tools..."

if ! command -v uv &> /dev/null; then
    print_status "FAIL" "uv is not installed. Please install uv first."
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    print_status "FAIL" "Python 3 is not installed."
    exit 1
fi

print_status "SUCCESS" "Required tools are available"

# Set up Python environment
print_status "INFO" "Setting up Python environment..."
if [ -d ".venv" ]; then
    rm -rf .venv
fi

uv venv --python=python3.13 --clear --prompt=venv
source .venv/bin/activate

# Install dependencies
print_status "INFO" "Installing dependencies..."
uv pip install -r requirements.txt
uv pip install flake8 black isort mypy bandit safety pip-audit pytest-cov pytest-html pytest-json-report

# Code quality checks
print_status "INFO" "Running code quality checks..."

# Format check
print_status "INFO" "Checking code formatting with black..."
if black --check --diff src/ tests/; then
    print_status "SUCCESS" "Code formatting is correct"
else
    print_status "FAIL" "Code formatting issues found. Run 'black src/ tests/' to fix."
    exit 1
fi

# Import sorting check
print_status "INFO" "Checking import sorting with isort..."
if isort --check-only --diff src/ tests/; then
    print_status "SUCCESS" "Import sorting is correct"
else
    print_status "FAIL" "Import sorting issues found. Run 'isort src/ tests/' to fix."
    exit 1
fi

# Linting
print_status "INFO" "Running flake8 linting..."
if flake8 src/ tests/ --max-line-length=88 --extend-ignore=E203,W503; then
    print_status "SUCCESS" "Linting passed"
else
    print_status "FAIL" "Linting issues found"
    exit 1
fi

# Type checking
print_status "INFO" "Running mypy type checking..."
if mypy src/ --ignore-missing-imports; then
    print_status "SUCCESS" "Type checking passed"
else
    print_status "WARN" "Type checking issues found (non-blocking)"
fi

# Security scanning
print_status "INFO" "Running security scans..."

# Bandit security scan
print_status "INFO" "Running Bandit security scan..."
if bandit -r src/ -f json -o bandit-report.json; then
    print_status "SUCCESS" "Bandit scan completed"
else
    print_status "WARN" "Bandit found potential security issues"
    if [ -f "bandit-report.json" ]; then
        echo "Check bandit-report.json for details"
    fi
fi

# Safety dependency vulnerability check
print_status "INFO" "Running Safety dependency vulnerability check..."
if safety check --json --output safety-report.json; then
    print_status "SUCCESS" "Safety scan completed"
else
    print_status "WARN" "Safety found vulnerable dependencies"
    if [ -f "safety-report.json" ]; then
        echo "Check safety-report.json for details"
    fi
fi

# pip-audit for additional vulnerability scanning
print_status "INFO" "Running pip-audit vulnerability scan..."
if pip-audit --format=json --output=pip-audit-report.json; then
    print_status "SUCCESS" "pip-audit scan completed"
else
    print_status "WARN" "pip-audit found vulnerable dependencies"
    if [ -f "pip-audit-report.json" ]; then
        echo "Check pip-audit-report.json for details"
    fi
fi

# Run tests
print_status "INFO" "Running comprehensive test suite..."

# Add src to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Run tests with coverage
if python -m pytest tests/ \
    --verbose \
    --cov=src \
    --cov-report=html:htmlcov \
    --cov-report=xml:coverage.xml \
    --cov-report=term-missing \
    --html=test-report.html \
    --self-contained-html \
    --json-report \
    --json-report-file=test-results.json \
    --tb=short; then
    print_status "SUCCESS" "All tests passed"
else
    print_status "FAIL" "Some tests failed"
    exit 1
fi

# Check coverage threshold
print_status "INFO" "Checking test coverage..."
COVERAGE=$(python -c "
import xml.etree.ElementTree as ET
try:
    tree = ET.parse('coverage.xml')
    root = tree.getroot()
    coverage = float(root.attrib['line-rate']) * 100
    print(f'{coverage:.1f}')
except:
    print('0')
")

echo "Coverage: ${COVERAGE}%"
if (( $(echo "$COVERAGE < 80" | bc -l) )); then
    print_status "FAIL" "Coverage ${COVERAGE}% is below 80% threshold"
    exit 1
else
    print_status "SUCCESS" "Coverage ${COVERAGE}% meets 80% threshold"
fi

# Generate validation summary
print_status "INFO" "Generating validation summary..."
cat > validation-summary.txt << EOF
Local Deployment Validation Summary
==================================
Timestamp: $(date)
Python Version: $(python --version)
uv Version: $(uv --version)

Validation Results:
==================
✅ Code Formatting: PASSED
✅ Import Sorting: PASSED
✅ Linting: PASSED
$([ -f "bandit-report.json" ] && echo "⚠️ Security Scan: COMPLETED (check reports)" || echo "✅ Security Scan: PASSED")
✅ Tests: PASSED
✅ Coverage: ${COVERAGE}% (≥80%)

Files Generated:
===============
- htmlcov/ (coverage report)
- coverage.xml
- test-report.html
- test-results.json
- bandit-report.json (if issues found)
- safety-report.json (if issues found)
- pip-audit-report.json (if issues found)

Status: READY FOR DEPLOYMENT
EOF

cat validation-summary.txt

print_status "SUCCESS" "Local validation completed successfully!"
print_status "INFO" "Your code is ready for deployment to main branch"

echo ""
echo "📊 Summary:"
echo "- Code quality: ✅ PASSED"
echo "- Security: ✅ SCANNED"
echo "- Tests: ✅ PASSED"
echo "- Coverage: ✅ ${COVERAGE}%"
echo ""
echo "🚀 Ready to push to main branch for deployment!"