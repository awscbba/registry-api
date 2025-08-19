"""
Repository Layer - Data Access Pattern Implementation

This module provides the repository pattern implementation for clean data access
separation following the Service Registry architecture.
"""

# Import only the base repository to avoid circular import issues
from .base_repository import BaseRepository

# Other repositories should be imported directly when needed
# This prevents circular import issues in Lambda environments

__all__ = [
    "BaseRepository",
]
