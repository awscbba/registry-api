#!/bin/bash
# Setup script for git hooks in registry-api
# This ensures all developers have the same pre-push validation

echo "🔧 Setting up git hooks for registry-api..."

# Get the git repository root directory
REPO_ROOT="$(git rev-parse --show-toplevel)"

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Not in registry-api root directory"
    echo "📍 Current directory: $(pwd)"
    echo "💡 Run this script from the registry-api root directory"
    exit 1
fi

# Copy the pre-push hook
echo "📋 Installing pre-push hook..."
cp .githooks/pre-push .git/hooks/pre-push

# Make sure it's executable
chmod +x .git/hooks/pre-push

echo "✅ Git hooks installed successfully!"
echo ""
echo "📝 The pre-push hook will now:"
echo "   • Run black formatter"
echo "   • Run flake8 linter" 
echo "   • Run 12 critical tests (including address field standardization tests)"
echo "   • Prevent pushes if any checks fail"
echo ""
echo "🧪 Critical tests include:"
echo "   • API service method consistency"
echo "   • Async/sync consistency validation"
echo "   • V2 response format consistency"
echo "   • Production health checks"
echo "   • Address field standardization (8 tests)"
echo ""
echo "💡 To run the critical tests manually: just test-critical-passing"
echo "🔍 To run all tests: just test-all"