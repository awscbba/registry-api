# Registry API

Backend API service for the People Registry application using FastAPI and Service Registry pattern.

## 📚 Documentation

All documentation has been consolidated in the **[registry-documentation](../registry-documentation/)** repository:

- **[Architecture Overview](../registry-documentation/architecture/)**
- **[API Documentation](../registry-documentation/api/)**
- **[Development Guide](../registry-documentation/api/development.md)**
- **[Service Registry Implementation](../registry-documentation/architecture/service-registry-implementation.md)**

## 🛠️ Scripts & Tools

The **[scripts/](./scripts/)** directory contains utility scripts for:
- **Admin Management**: User creation, password resets, diagnostics
- **Database Maintenance**: Health checks, cleanup, data migration
- **Infrastructure**: Deployment validation, service setup
- **Analysis**: Data verification and troubleshooting tools

See **[scripts/README.md](./scripts/README.md)** for detailed documentation.

## 🚀 Quick Start

```bash
# Install dependencies
uv sync

# Run tests
just test

# Start development server
just dev
```

For detailed setup instructions, see the [API Development Guide](../registry-documentation/api/development.md).
