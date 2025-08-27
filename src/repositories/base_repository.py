"""
Base repository interface following clean architecture principles.
Provides common CRUD operations with proper abstraction.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, TypeVar, Generic, Any

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Base repository interface for all data access operations."""

    @abstractmethod
    async def create(self, item_data: Dict[str, Any]) -> T:
        """Create a new item in the repository."""
        pass

    @abstractmethod
    async def get_by_id(self, item_id: str) -> Optional[T]:
        """Get an item by its ID."""
        pass

    @abstractmethod
    async def update(self, item_id: str, updates: Dict[str, Any]) -> Optional[T]:
        """Update an existing item."""
        pass

    @abstractmethod
    async def delete(self, item_id: str) -> bool:
        """Delete an item by its ID."""
        pass

    @abstractmethod
    async def list_all(self, limit: Optional[int] = None) -> List[T]:
        """List all items with optional limit."""
        pass

    @abstractmethod
    async def exists(self, item_id: str) -> bool:
        """Check if an item exists."""
        pass
