"""
Main entry point for the People Registry API Lambda function.
"""

from mangum import Mangum
from src.handlers.people_handler import app

# Create Lambda handler using Mangum
lambda_handler = Mangum(app)

def main():
    print("People Registry API - Lambda handler ready")
    print("Available endpoints:")
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            methods = ', '.join(route.methods)
            print(f"  {methods} {route.path}")

if __name__ == "__main__":
    main()
