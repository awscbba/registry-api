"""
Main entry point for the versioned People Registry API Lambda function.
This version includes v1 (legacy) and v2 (fixed) endpoints.
"""

from mangum import Mangum
from src.handlers.versioned_api_handler import app

# Create Lambda handler using Mangum
lambda_handler = Mangum(app)


def main():
    print("People Registry API - Versioned Lambda handler ready")
    print("Available versions: v1 (legacy), v2 (fixed)")
    print("Available endpoints:")
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            methods = ", ".join(route.methods)
            print(f"  {methods} {route.path}")


if __name__ == "__main__":
    main()