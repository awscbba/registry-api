"""
Main FastAPI application with clean, modular router architecture.
No field mapping complexity - consistent camelCase throughout.
"""

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from .core.config import config
from .middleware.enterprise_middleware import (
    EnterpriseMiddleware,
    SecurityHeadersMiddleware,
    RateLimitingMiddleware,
)
from .middleware.authentication_middleware import AuthenticationMiddleware
from .middleware.authorization_middleware import (
    AuthorizationMiddleware,
    InputValidationMiddleware,
)
from .routers import (
    people_router,
    projects_router,
    subscriptions_router,
    auth_router,
    admin_router,
    public_router,
    form_submissions_router,
    image_upload_router,
)
from .utils.responses import create_success_response, create_error_response
from .exceptions.base_exceptions import BaseApplicationException
from .exceptions.error_handler import error_handler


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

    # Add enterprise middleware (order matters!)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitingMiddleware, requests_per_minute=100)
    app.add_middleware(EnterpriseMiddleware)

    # Add security middleware
    app.add_middleware(InputValidationMiddleware)
    app.add_middleware(AuthorizationMiddleware)
    app.add_middleware(AuthenticationMiddleware)

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
    app.include_router(public_router.router)
    app.include_router(form_submissions_router.router)
    app.include_router(image_upload_router.router)

    # Add enterprise exception handlers
    app.add_exception_handler(
        BaseApplicationException, error_handler.handle_application_exception
    )

    app.add_exception_handler(HTTPException, error_handler.handle_http_exception)

    app.add_exception_handler(Exception, error_handler.handle_generic_exception)

    # Add validation error handler for debugging 422 errors
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """Handle validation errors with detailed logging."""
        from .services.logging_service import logging_service, LogLevel, LogCategory

        # Log validation error details
        logging_service.log_structured(
            level=LogLevel.WARNING,
            category=LogCategory.API_ACCESS,
            message=f"Validation error on {request.method} {request.url.path}",
            additional_data={
                "method": request.method,
                "path": request.url.path,
                "errors": exc.errors(),
                "body": await request.body() if hasattr(request, "body") else None,
            },
        )

        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "message": "Request validation failed",
                "detail": exc.errors(),
                "details": exc.errors(),
                "version": "v2",
            },
        )

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


# Note: Exception handlers are now managed by the enterprise error handler
# which provides structured logging, monitoring, and consistent error responses
