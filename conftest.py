"""
Global pytest configuration and fixtures.
Sets up Python path for all tests to import from src directory.
"""

import sys
import os
from pathlib import Path

# Add the project root and src directory to Python path
project_root = Path(__file__).parent
src_dir = project_root / "src"

# Add both paths to ensure imports work
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(src_dir))

# Also add the src directory as a module path
if str(src_dir) not in sys.path:
    sys.path.append(str(src_dir))

# Set up environment for tests
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("DYNAMODB_TABLE_NAME", "test-table")
os.environ.setdefault("AUTH_FUNCTION_NAME", "test-auth-function")
os.environ.setdefault("API_FUNCTION_NAME", "test-api-function")
