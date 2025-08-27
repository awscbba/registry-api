"""
Main entry point for the People Registry API.
Lambda-compatible entry point using Mangum.
"""

from mangum import Mangum
from src.app import app

# Lambda handler
handler = Mangum(app)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
