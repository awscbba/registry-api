# Registry API Documentation

This directory contains comprehensive documentation for the registry-api repository, including deployment workflows, testing strategies, and implementation guides.

## 📁 Documentation Structure

```
docs/
├── README.md                           # This file - Documentation overview
├── workflows/
│   ├── README.md                      # Deployment workflows overview
│   ├── api-deployment.md              # Main API deployment pipeline
│   ├── comprehensive-testing.md       # Testing pipeline documentation
│   ├── rollback-procedures.md         # Emergency rollback procedures
│   └── validation.md                  # Workflow validation guide
├── implementation/
│   ├── crud-operations.md             # Person CRUD implementation
│   ├── testing-strategy.md            # Testing approach and coverage
│   ├── security-implementation.md     # Security features and scanning
│   └── performance-optimization.md    # Performance considerations
├── deployment/
│   ├── cross-repository-sync.md       # Cross-repository coordination
│   ├── health-checks.md               # Post-deployment verification
│   └── monitoring.md                  # Monitoring and observability
└── templates/
    └── pr-template.md                  # Pull request template
```

## 🎯 Quick Start

1. **New to the project?** Start with [workflows/README.md](workflows/README.md)
2. **Implementing features?** See [implementation/crud-operations.md](implementation/crud-operations.md)
3. **Running tests?** Check [implementation/testing-strategy.md](implementation/testing-strategy.md)
4. **Deploying changes?** See [deployment/cross-repository-sync.md](deployment/cross-repository-sync.md)
5. **Creating a PR?** Use [templates/pr-template.md](templates/pr-template.md)

## 🔗 Related Documentation

- **Registry-Infrastructure**: `../registry-infrastructure/docs/` - Infrastructure and coordination
- **Registry-Frontend**: `../registry-frontend/docs/` - Frontend integration
- **Specifications**: `../.kiro/specs/person-crud-completion/` - Feature specifications

## 📊 Documentation Maintenance

This documentation is maintained alongside the codebase. When making changes:

1. Update relevant documentation files
2. Verify all links and references
3. Update the last modified date
4. Test any code examples or procedures

**Last Updated**: July 24, 2025