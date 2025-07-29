#!/bin/bash
# Setup script to install git hooks for registry-api

echo "🔧 Setting up git hooks for registry-api..."

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Get the repository root
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to repository root
cd "$REPO_ROOT"

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

# Create .git/hooks directory if it doesn't exist
mkdir -p .git/hooks

# Install pre-push hook
if [ -f ".githooks/pre-push" ]; then
    cp .githooks/pre-push .git/hooks/pre-push
    chmod +x .git/hooks/pre-push
    echo "✅ Pre-push hook installed"
else
    echo "❌ Error: .githooks/pre-push not found"
    exit 1
fi

# Test if uv is available
if command -v uv &> /dev/null; then
    echo "✅ uv is available"
else
    echo "⚠️  Warning: uv is not installed or not in PATH"
    echo "💡 Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

echo ""
echo "🎉 Git hooks setup complete!"
echo ""
echo "📋 What happens now:"
echo "   • Before each 'git push', the pre-push hook will:"
echo "     1. Run 'black .' to format code"
echo "     2. Run 'flake8' to check linting"
echo "     3. Stop the push if there are issues"
echo ""
echo "💡 Tips:"
echo "   • If formatting changes are made, you'll need to commit them first"
echo "   • You can still run './scripts/pre-commit-check.sh' manually anytime"
echo "   • To bypass hooks (not recommended): git push --no-verify"
echo ""
echo "🔧 To uninstall hooks: rm .git/hooks/pre-push"