#!/bin/bash
# Setup Git Hooks for Branch Protection

echo "🔧 Setting up Git hooks for branch protection..."

# Function to setup hooks for a repository
setup_hooks() {
    local repo_path=$1
    local repo_name=$(basename "$repo_path")
    
    echo "Setting up hooks for $repo_name..."
    
    # Pre-push hook
    cat > "$repo_path/.git/hooks/pre-push" << 'EOF'
#!/bin/sh
# Pre-push hook to prevent direct pushes to main

protected_branch='main'
current_branch=$(git symbolic-ref HEAD | sed -e 's,.*/\(.*\),\1,')

if [ "$protected_branch" = "$current_branch" ]; then
    echo "🚫 BLOCKED: Direct push to main branch is not allowed!"
    echo "Please create a feature branch and submit a pull request."
    echo "Current branch: $current_branch"
    echo ""
    echo "To create a feature branch:"
    echo "  git checkout -b feature/your-feature-name"
    echo "  git push origin feature/your-feature-name"
    exit 1
fi

echo "✅ Push to $current_branch allowed"
EOF

    # Pre-commit hook
    cat > "$repo_path/.git/hooks/pre-commit" << 'EOF'
#!/bin/sh
# Pre-commit hook to prevent direct commits to main

current_branch=$(git symbolic-ref HEAD | sed -e 's,.*/\(.*\),\1,')

if [ "$current_branch" = "main" ]; then
    echo "🚫 BLOCKED: Direct commits to main branch are not allowed!"
    echo "Please switch to a feature branch first:"
    echo "  git checkout -b feature/your-feature-name"
    exit 1
fi

echo "✅ Commit to $current_branch allowed"
EOF

    # Make hooks executable
    chmod +x "$repo_path/.git/hooks/pre-push"
    chmod +x "$repo_path/.git/hooks/pre-commit"
    
    echo "✅ Hooks installed for $repo_name"
}

# Setup hooks for all repositories
setup_hooks "/Users/sergio.rodriguez/Projects/Community/AWS/UserGroupCbba/CodeCatalyst/people-registry-03/registry-api"
setup_hooks "/Users/sergio.rodriguez/Projects/Community/AWS/UserGroupCbba/CodeCatalyst/people-registry-03/registry-infrastructure"
setup_hooks "/Users/sergio.rodriguez/Projects/Community/AWS/UserGroupCbba/CodeCatalyst/people-registry-03/registry-frontend"

echo ""
echo "🎉 Git hooks setup complete!"
echo ""
echo "These hooks will now prevent:"
echo "  - Direct commits to main branch"
echo "  - Direct pushes to main branch"
echo ""
echo "To bypass hooks in emergency (USE WITH EXTREME CAUTION):"
echo "  git push --no-verify"
echo "  git commit --no-verify"
