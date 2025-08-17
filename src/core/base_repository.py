"""
Base Repository - Foundation class for optimized repository pattern.
Provides common functionality for database operations and performance tracking.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..utils.logging_config import get_handler_logger


class BaseRepository(ABC):
    """Base repository class with common functionality for database operations."""

    def __init__(self):
        self.logger = get_handler_logger(self.__class__.__name__.lower())
        # Import here to avoid circular imports
        from .config import get_config

        config = get_config()

        # Determine table name based on repository class name
        class_name = self.__class__.__name__.lower()
        if "people" in class_name or "user" in class_name:
            self.table_name = config.get_table_name("people")
        elif "project" in class_name:
            self.table_name = config.get_table_name("projects")
        else:
            # Default fallback - this should be overridden by subclasses
            self.table_name = "people"  # Default table name

        # Performance tracking
        self.operation_stats = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "avg_response_time": 0.0,
        }

        self.logger.debug(f"Base repository initialized: {self.__class__.__name__}")

    @abstractmethod
    async def initialize(self):
        """Initialize the repository with any required setup."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the repository."""
        pass

    def get_operation_stats(self) -> Dict[str, Any]:
        """Get repository operation statistics."""
        return {
            "repository": self.__class__.__name__,
            "statistics": self.operation_stats.copy(),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _update_operation_stats(self, success: bool, response_time: float):
        """Update operation statistics."""
        self.operation_stats["total_operations"] += 1

        if success:
            self.operation_stats["successful_operations"] += 1
        else:
            self.operation_stats["failed_operations"] += 1

        # Update average response time
        current_avg = self.operation_stats["avg_response_time"]
        total_ops = self.operation_stats["total_operations"]
        self.operation_stats["avg_response_time"] = (
            current_avg * (total_ops - 1) + response_time
        ) / total_ops
