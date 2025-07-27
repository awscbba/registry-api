# CodeCatalyst Workflow Reference

This document provides reference information for the CodeCatalyst workflows in this repository.

## Workflow Syntax Reference

### Basic Structure
```yaml
Name: Workflow_Name
SchemaVersion: "1.0"

Triggers:
  - Type: PUSH | PULLREQUEST | MANUAL
    Branches: [branch-list]
    Events: [event-list]  # For PULLREQUEST only

Actions:
  ActionName:
    Identifier: aws/build@v1
    DependsOn: [dependency-list]  # Optional
    Compute:
      Type: EC2 | Lambda
    Environment:
      Connections:
        - Role: IAM-Role-Name
          Name: "AWS-Account-ID"
      Name: Environment-Name
    Inputs:
      Sources: [WorkflowSource]
      Artifacts: [artifact-list]  # Optional
    Configuration:
      Steps:
        - Run: |
            # Shell commands here
    Outputs:
      Artifacts:  # Optional
        - Name: artifact-name
          Files: [file-patterns]
```

### Trigger Types

#### PUSH Trigger
```yaml
Triggers:
  - Type: PUSH
    Branches:
      - main
      - develop
      - feature/*
```

#### PULLREQUEST Trigger
```yaml
Triggers:
  - Type: PULLREQUEST
    Branches:
      - main
    Events:
      - OPEN
      - REVISION
      - CLOSED
```

#### MANUAL Trigger
```yaml
Triggers:
  - Type: MANUAL
```

### Environment Variables

#### Built-in Variables
- `CODECATALYST_BRANCH_NAME`: Current branch name
- `CODECATALYST_SOURCE_BRANCH_NAME`: Source branch name
- `CODECATALYST_SOURCE_BRANCH_REF`: Source commit hash
- `CODECATALYST_TARGET_BRANCH_NAME`: Target branch name (for PRs)

#### Custom Environment Variables
```yaml
Environment:
  Variables:
    CUSTOM_VAR: "value"
    ANOTHER_VAR: "another-value"
```

### Artifact Management

#### Producing Artifacts
```yaml
Outputs:
  Artifacts:
    - Name: build-artifacts
      Files:
        - "dist/**/*"
        - "reports/*.json"
```

#### Consuming Artifacts
```yaml
Inputs:
  Artifacts:
    - build-artifacts
    - test-reports
```

### Conditional Execution

#### Branch-based Conditions
```bash
if [ "$CODECATALYST_BRANCH_NAME" = "main" ]; then
    echo "Running on main branch"
fi
```

#### Event-based Conditions
```bash
if [ "$CODECATALYST_EVENT_TYPE" = "PULLREQUEST" ]; then
    echo "Running on pull request"
fi
```

## Best Practices

### 1. Error Handling
```bash
set -e  # Exit on any error

# Or handle errors explicitly
command || {
    echo "Command failed"
    exit 1
}
```

### 2. Logging
```bash
echo "🚀 Starting deployment"
echo "📦 Installing dependencies"
echo "✅ Task completed successfully"
echo "❌ Task failed"
```

### 3. Tool Installation
```bash
# Install tools at the beginning of each action
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.cargo/bin:$PATH"
```

### 4. Artifact Organization
```yaml
Outputs:
  Artifacts:
    - Name: test-results
      Files:
        - "test-reports/**/*"
        - "coverage/**/*"
    - Name: security-reports
      Files:
        - "*-security-report.json"
```

### 5. Dependency Management
```bash
# Use specific versions for reproducibility
uv pip install package==1.2.3

# Or use requirements files
uv pip install -r requirements.txt
```

## Common Patterns

### Python Setup
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.cargo/bin:$PATH"

# Create virtual environment
uv venv --python=python3.13 --clear --prompt=venv
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt
```

### Test Execution
```bash
# Add src to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Run tests with coverage
python -m pytest tests/ \
  --verbose \
  --cov=src \
  --cov-report=html:htmlcov \
  --cov-report=xml:coverage.xml \
  --html=test-report.html \
  --json-report-file=test-results.json
```

### Security Scanning
```bash
# Install security tools
uv pip install bandit safety pip-audit

# Run scans
bandit -r src/ -f json -o bandit-report.json
safety check --json --output safety-report.json
pip-audit --format=json --output=pip-audit-report.json
```

### Code Quality
```bash
# Install quality tools
uv pip install black isort flake8 mypy

# Run checks
black --check --diff src/ tests/
isort --check-only --diff src/ tests/
flake8 src/ tests/ --max-line-length=88
mypy src/ --ignore-missing-imports
```

### Cross-Repository Operations
```bash
# Clone another repository
git clone https://git.us-west-2.codecatalyst.aws/v1/AWSCocha/people-registry-03/registry-infrastructure ../registry-infrastructure

# Configure git
git config --global user.name "CodeCatalyst Automation"
git config --global user.email "codecatalyst@aws.com"

# Create and push branch
git checkout -b "automated-sync-$(date +%Y%m%d-%H%M%S)"
# ... make changes ...
git add .
git commit -m "Automated sync from registry-api"
git push origin HEAD
```

## Troubleshooting

### Common Issues

#### 1. Permission Errors
```bash
# Make scripts executable
chmod +x script.sh

# Use sudo for system operations
sudo command
```

#### 2. Path Issues
```bash
# Add to PATH
export PATH="$HOME/.local/bin:$PATH"

# Use absolute paths
/usr/local/bin/command
```

#### 3. Environment Variables
```bash
# Check if variable is set
if [ -z "$VARIABLE" ]; then
    echo "Variable not set"
    exit 1
fi
```

#### 4. Artifact Issues
```bash
# Ensure artifacts exist
if [ ! -f "report.json" ]; then
    echo '{}' > report.json
fi

# Create directory structure
mkdir -p reports/coverage
```

### Debugging Tips

#### 1. Verbose Output
```bash
set -x  # Enable debug mode
command -v tool  # Check if tool exists
which python  # Find tool location
```

#### 2. Environment Information
```bash
echo "Environment Information:"
echo "Node version: $(node --version)"
echo "Python version: $(python --version)"
echo "Current directory: $(pwd)"
echo "PATH: $PATH"
```

#### 3. File System Checks
```bash
echo "Current directory contents:"
ls -la

echo "Checking for required files:"
[ -f "requirements.txt" ] && echo "✅ requirements.txt exists" || echo "❌ requirements.txt missing"
```

## Performance Optimization

### 1. Parallel Execution
```bash
# Run tests in parallel
python -m pytest -n auto

# Background processes
command1 &
command2 &
wait  # Wait for all background processes
```

### 2. Caching
```bash
# Cache dependencies (conceptual - CodeCatalyst doesn't have built-in caching)
if [ -d ".cache" ]; then
    echo "Using cached dependencies"
else
    echo "Installing fresh dependencies"
    mkdir .cache
fi
```

### 3. Minimal Installs
```bash
# Install only what's needed
uv pip install --no-deps package

# Use slim base images
# (This is handled by CodeCatalyst container selection)
```

## Security Considerations

### 1. Secrets Management
```bash
# Never log secrets
echo "Token: [REDACTED]"

# Use environment variables for sensitive data
if [ -z "$API_TOKEN" ]; then
    echo "API_TOKEN not provided"
    exit 1
fi
```

### 2. Input Validation
```bash
# Validate inputs
if [[ ! "$BRANCH_NAME" =~ ^[a-zA-Z0-9/_-]+$ ]]; then
    echo "Invalid branch name"
    exit 1
fi
```

### 3. Secure Defaults
```bash
# Set secure permissions
umask 077

# Use HTTPS for downloads
curl -fsSL https://example.com/script.sh | sh
```