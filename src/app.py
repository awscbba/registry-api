"""
Main FastAPI application with clean, modular router architecture.
No field mapping complexity - consistent camelCase throughout.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import config
from .routers import (
    people_router,
    projects_router,
    subscriptions_router,
    auth_router,
    admin_router,
)
from .utils.responses import create_success_response, create_error_response


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="People Registry API",
        description="""
        # People Registry API v2.0

        Clean, modular API with standardized camelCase fields throughout.

        ## Key Features
        - **No Field Mapping**: Consistent camelCase from database to API
        - **Modular Architecture**: Domain-specific routers
        - **V2 Only**: Single version, no legacy complexity
        - **Standardized Responses**: Consistent response format

        ## Architecture
        - **Database**: DynamoDB with camelCase fields
        - **Models**: Pydantic v2 with direct field mapping
        - **Routers**: Domain-driven design
        - **Responses**: Standardized success/error format
        """,
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(people_router.router)
    app.include_router(projects_router.router)
    app.include_router(subscriptions_router.router)
    app.include_router(auth_router.router)
    app.include_router(admin_router.router)

    return app


# Create the application instance
app = create_app()


@app.get("/", response_model=dict)
async def root():
    """Root endpoint with API information."""
    return create_success_response(
        {
            "name": "People Registry API",
            "version": "2.0.0",
            "description": "Clean, modular API with standardized camelCase fields",
            "features": [
                "No field mapping complexity",
                "Modular router architecture",
                "V2 only (no legacy support)",
                "Standardized responses",
                "camelCase consistency",
            ],
            "endpoints": {
                "people": "/v2/people",
                "projects": "/v2/projects",
                "subscriptions": "/v2/subscriptions",
                "auth": "/auth",
                "admin": "/v2/admin",
                "docs": "/docs",
                "health": "/health",
            },
        }
    )


@app.get("/health", response_model=dict)
async def health_check():
    """Health check endpoint."""
    return create_success_response(
        {
            "status": "healthy",
            "version": "2.0.0",
            "environment": config.environment.value,
            "timestamp": "2025-01-27T00:00:00Z",
        }
    )


@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors with standardized response."""
    return JSONResponse(
        status_code=404,
        content=create_error_response("Endpoint not found", "NOT_FOUND"),
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle 500 errors with standardized response."""
    return JSONResponse(
        status_code=500,
        content=create_error_response("Internal server error", "INTERNAL_ERROR"),
    )
