#!/bin/bash
# Pre-commit check script for registry-api
# Run this before committing to ensure code quality

echo "🔍 Running pre-commit checks..."

# Change to the registry-api directory
cd "$(dirname "$0")/.."

# Run black formatter
echo "📝 Running black formatter..."
uv run black .
if [ $? -ne 0 ]; then
    echo "❌ Black formatting failed"
    exit 1
fi

# Run flake8 linter
echo "🔍 Running flake8 linter..."
uv run flake8
if [ $? -ne 0 ]; then
    echo "❌ Flake8 linting failed"
    exit 1
fi

# Run tests (optional - can be commented out for faster commits)
# echo "🧪 Running tests..."
# uv run pytest
# if [ $? -ne 0 ]; then
#     echo "❌ Tests failed"
#     exit 1
# fi

echo "✅ All pre-commit checks passed!"
echo "💡 Tip: Add any changed files and commit your changes"