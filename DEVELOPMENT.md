# Development Guide

## Code Quality Standards

This project maintains high code quality standards using automated tools.

### Pre-Commit Checklist

Before committing any changes, **always** run:

```bash
# Quick pre-commit check (recommended)
./scripts/pre-commit-check.sh

# Or manually run each step:
uv run black .          # Format code
uv run flake8           # Check linting
uv run pytest          # Run tests (optional)
```

### Code Formatting

- **Black**: Automatic code formatting
- **Flake8**: Linting and style checking
- **Configuration**: See `.flake8` file for project-specific rules

### Linting Configuration

The project uses `.flake8` configuration with:
- Max line length: 200 characters
- Ignores common issues: F401, F811, E251, E302, E305, E402, F541, F841, E712, W503
- Excludes: .venv, __pycache__, .git, .pytest_cache, *.egg-info

### Development Workflow

1. Make your changes
2. Run `./scripts/pre-commit-check.sh`
3. Fix any issues reported
4. Add and commit your changes
5. Push to your branch

### API Versioning

This project uses API versioning:
- **v1**: Legacy endpoints (backward compatibility)
- **v2**: Enhanced endpoints with latest fixes
- **Legacy**: Unversioned endpoints redirect to v1

### Testing

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_versioned_api.py

# Run with coverage
uv run pytest --cov=src
```

### Deployment

The API uses container-based deployment:
- Docker containers for Lambda functions
- ECR for container registry
- CodeCatalyst for CI/CD pipeline

## Common Issues

### Linting Failures
- Run `uv run black .` to fix formatting
- Check `.flake8` for ignored rules
- Use `# noqa` comments sparingly for unavoidable issues

### Import Errors
- Ensure all imports are at the top of files
- Use relative imports within the src/ package
- Check for circular imports

### Container Deployment
- Ensure Dockerfile.lambda is up to date
- Test locally with Docker before deploying
- Check ECR permissions for push/pull

## Getting Help

- Check existing tests for examples
- Review API documentation in OpenAPI format
- Use the test scripts in the scripts/ directory