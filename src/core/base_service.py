"""
Base Service Interface for Service Registry Pattern

This module defines the base interface that all services must implement,
ensuring consistency across the entire application.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import logging
import time
import uuid


class ServiceStatus(Enum):
    """Service health status enumeration"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceResponse:
    """Standardized service response format"""

    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    error_code: Optional[str] = None
    errors: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary for JSON serialization"""
        result = {
            "success": self.success,
            "timestamp": time.time(),
            "request_id": str(uuid.uuid4()),
        }

        if self.data is not None:
            result["data"] = self.data
        if self.message:
            result["message"] = self.message
        if self.error_code:
            result["error_code"] = self.error_code
        if self.errors:
            result["errors"] = self.errors
        if self.metadata:
            result["metadata"] = self.metadata

        return result


@dataclass
class HealthCheck:
    """Service health check result"""

    service_name: str
    status: ServiceStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    response_time_ms: Optional[float] = None


class BaseService(ABC):
    """
    Base service class that all services must inherit from.

    Provides common functionality:
    - Logging
    - Health checks
    - Error handling
    - Configuration management
    """

    def __init__(self, service_name: str, config: Optional[Dict[str, Any]] = None):
        self.service_name = service_name
        self.config = config or {}
        self.logger = self._setup_logger()
        self._initialized = False

    def _setup_logger(self) -> logging.Logger:
        """Setup service-specific logger"""
        logger = logging.getLogger(f"service.{self.service_name}")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f"[{self.service_name}] %(asctime)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the service.
        Must be implemented by each service.

        Returns:
            bool: True if initialization successful, False otherwise
        """
        pass

    @abstractmethod
    async def health_check(self) -> HealthCheck:
        """
        Perform health check for the service.
        Must be implemented by each service.

        Returns:
            HealthCheck: Current health status of the service
        """
        pass

    async def shutdown(self) -> bool:
        """
        Gracefully shutdown the service.
        Can be overridden by services that need cleanup.

        Returns:
            bool: True if shutdown successful, False otherwise
        """
        self.logger.info(f"Shutting down {self.service_name}")
        self._initialized = False
        return True

    def is_initialized(self) -> bool:
        """Check if service is initialized"""
        return self._initialized

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)

    def success_response(
        self,
        data: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ServiceResponse:
        """Create a successful service response"""
        return ServiceResponse(
            success=True, data=data, message=message, metadata=metadata
        )

    def error_response(
        self,
        message: str,
        error_code: Optional[str] = None,
        errors: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ServiceResponse:
        """Create an error service response"""
        self.logger.error(f"Error in {self.service_name}: {message}")
        return ServiceResponse(
            success=False,
            message=message,
            error_code=error_code,
            errors=errors,
            metadata=metadata,
        )

    def log_info(self, message: str, **kwargs):
        """Log info message with service context"""
        self.logger.info(message, extra=kwargs)

    def log_warning(self, message: str, **kwargs):
        """Log warning message with service context"""
        self.logger.warning(message, extra=kwargs)

    def log_error(self, message: str, **kwargs):
        """Log error message with service context"""
        self.logger.error(message, extra=kwargs)

    def log_debug(self, message: str, **kwargs):
        """Log debug message with service context"""
        self.logger.debug(message, extra=kwargs)
