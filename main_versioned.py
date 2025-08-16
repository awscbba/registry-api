"""
Main entry point for the versioned People Registry API Lambda function.
This version includes v1 (legacy) and v2 (fixed) endpoints with Service Registry architecture.
Updated to use modular_api_handler with admin endpoints.
"""

from mangum import Mangum
from src.handlers.modular_api_handler import app

# Create Lambda handler using Mangum
lambda_handler = Mangum(app)


def main():
    print("People Registry API - Service Registry with Admin Endpoints")
    print("Available versions: v1 (legacy), v2 (enhanced)")
    print("Available endpoints:")
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            methods = ", ".join(route.methods)
            print(f"  {methods} {route.path}")


if __name__ == "__main__":
    main()
