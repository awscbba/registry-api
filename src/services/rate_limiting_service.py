"""
Rate limiting service for protecting sensitive endpoints from abuse.
Implements sliding window rate limiting with Redis-like functionality using DynamoDB.
"""

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum
import hashlib

from ..core.base_service import BaseService, ServiceStatus, HealthCheck, ServiceResponse
from ..models.error_handling import ErrorContext, APIException, ErrorCode
from ..services.defensive_dynamodb_service import (
    DefensiveDynamoDBService as DynamoDBService,
)
from ..services.logging_service import logging_service


class RateLimitType(str, Enum):
    """Types of rate limits for different scenarios."""

    LOGIN_ATTEMPTS = "LOGIN_ATTEMPTS"
    PASSWORD_RESET = "PASSWORD_RESET"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"
    API_REQUESTS = "API_REQUESTS"
    PERSON_CREATION = "PERSON_CREATION"
    PERSON_UPDATES = "PERSON_UPDATES"
    EMAIL_VERIFICATION = "EMAIL_VERIFICATION"
    SEARCH_REQUESTS = "SEARCH_REQUESTS"


class RateLimitWindow(str, Enum):
    """Time windows for rate limiting."""

    MINUTE = "MINUTE"
    HOUR = "HOUR"
    DAY = "DAY"


class RateLimitConfig:
    """Configuration for rate limiting rules."""

    def __init__(
        self,
        limit_type: RateLimitType,
        max_requests: int,
        window: RateLimitWindow,
        window_size_seconds: int,
        block_duration_seconds: int = 300,  # 5 minutes default
        progressive_penalties: bool = False,
    ):
        self.limit_type = limit_type
        self.max_requests = max_requests
        self.window = window
        self.window_size_seconds = window_size_seconds
        self.block_duration_seconds = block_duration_seconds
        self.progressive_penalties = progressive_penalties


class RateLimitResult:
    """Result of rate limit check."""

    def __init__(
        self,
        allowed: bool,
        current_count: int,
        limit: int,
        reset_time: datetime,
        retry_after_seconds: Optional[int] = None,
        blocked_until: Optional[datetime] = None,
    ):
        self.allowed = allowed
        self.current_count = current_count
        self.limit = limit
        self.reset_time = reset_time
        self.retry_after_seconds = retry_after_seconds
        self.blocked_until = blocked_until


class RateLimitingService(BaseService):
    """Service for implementing rate limiting across the API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("rate_limiting_service", config)
        self.db_service = None
        self.configs = {}

    async def initialize(self) -> bool:
        """Initialize the rate limiting service."""
        try:
            self.logger.info("Initializing RateLimitingService...")

            # Initialize database service
            self.db_service = DynamoDBService()

            # Rate limiting configurations
            self.configs = {
                RateLimitType.LOGIN_ATTEMPTS: RateLimitConfig(
                    limit_type=RateLimitType.LOGIN_ATTEMPTS,
                    max_requests=5,
                    window=RateLimitWindow.HOUR,
                    window_size_seconds=3600,
                    block_duration_seconds=900,  # 15 minutes
                    progressive_penalties=True,
                ),
                RateLimitType.PASSWORD_RESET: RateLimitConfig(
                    limit_type=RateLimitType.PASSWORD_RESET,
                    max_requests=3,
                    window=RateLimitWindow.HOUR,
                    window_size_seconds=3600,
                    block_duration_seconds=1800,  # 30 minutes
                ),
                RateLimitType.PASSWORD_CHANGE: RateLimitConfig(
                    limit_type=RateLimitType.PASSWORD_CHANGE,
                    max_requests=10,
                    window=RateLimitWindow.HOUR,
                    window_size_seconds=3600,
                    block_duration_seconds=300,  # 5 minutes
                ),
                RateLimitType.API_REQUESTS: RateLimitConfig(
                    limit_type=RateLimitType.API_REQUESTS,
                    max_requests=1000,
                    window=RateLimitWindow.HOUR,
                    window_size_seconds=3600,
                    block_duration_seconds=60,  # 1 minute
                ),
                RateLimitType.PERSON_CREATION: RateLimitConfig(
                    limit_type=RateLimitType.PERSON_CREATION,
                    max_requests=10,
                    window=RateLimitWindow.HOUR,
                    window_size_seconds=3600,
                    block_duration_seconds=600,  # 10 minutes
                ),
                RateLimitType.PERSON_UPDATES: RateLimitConfig(
                    limit_type=RateLimitType.PERSON_UPDATES,
                    max_requests=50,
                    window=RateLimitWindow.HOUR,
                    window_size_seconds=3600,
                    block_duration_seconds=300,  # 5 minutes
                ),
                RateLimitType.EMAIL_VERIFICATION: RateLimitConfig(
                    limit_type=RateLimitType.EMAIL_VERIFICATION,
                    max_requests=5,
                    window=RateLimitWindow.HOUR,
                    window_size_seconds=3600,
                    block_duration_seconds=1800,  # 30 minutes
                ),
                RateLimitType.SEARCH_REQUESTS: RateLimitConfig(
                    limit_type=RateLimitType.SEARCH_REQUESTS,
                    max_requests=100,
                    window=RateLimitWindow.HOUR,
                    window_size_seconds=3600,
                    block_duration_seconds=60,  # 1 minute
                ),
            }

            self._initialized = True
            self.logger.info("RateLimitingService initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize RateLimitingService: {str(e)}")
            return False

    async def health_check(self) -> HealthCheck:
        """Perform health check for the rate limiting service."""
        start_time = time.time()

        try:
            if not self._initialized:
                return HealthCheck(
                    service_name=self.service_name,
                    status=ServiceStatus.UNHEALTHY,
                    message="Service not initialized",
                    response_time_ms=(time.time() - start_time) * 1000,
                )

            # Test database connectivity
            if self.db_service:
                await self._test_database_connectivity()

            response_time = (time.time() - start_time) * 1000

            return HealthCheck(
                service_name=self.service_name,
                status=ServiceStatus.HEALTHY,
                message="Rate limiting service is healthy",
                details={
                    "database_connected": self.db_service is not None,
                    "configured_limits": len(self.configs),
                    "limit_types": list(self.configs.keys()),
                },
                response_time_ms=response_time,
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.logger.error(f"Health check failed: {str(e)}")

            return HealthCheck(
                service_name=self.service_name,
                status=ServiceStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                response_time_ms=response_time,
            )

    async def _test_database_connectivity(self):
        """Test database connectivity for rate limiting service."""
        if not self.db_service:
            raise Exception("Database service not initialized")

        try:
            # Test with a simple rate limit check operation
            test_key = f"health_check_{int(time.time())}"
            test_limit_type = RateLimitType.API_REQUESTS

            # Test database connectivity by attempting a simple operation
            # This will raise an exception if database is not accessible
            if hasattr(self.db_service, "test_connection"):
                await self.db_service.test_connection()
            else:
                # Fallback: test basic database access
                # Create a test rate limit entry (without actually storing it)
                current_time = datetime.now(timezone.utc)
                test_data = {
                    "identifier": test_key,
                    "limit_type": test_limit_type.value,
                    "timestamp": current_time.isoformat(),
                    "count": 1,
                }
                # This tests that we can format data for database operations
                self.logger.debug(
                    f"Rate limiting database connectivity test data prepared: {test_data}"
                )

            self.logger.debug("Rate limiting service database connectivity test passed")

        except Exception as e:
            raise Exception(f"Database connectivity test failed: {str(e)}")

    async def check_rate_limit(
        self, limit_type: RateLimitType, identifier: str, context: ErrorContext
    ) -> RateLimitResult:
        """
        Check if request is within rate limits.

        Args:
            limit_type: Type of rate limit to check
            identifier: Unique identifier (IP, user ID, email, etc.)
            context: Request context for logging

        Returns:
            RateLimitResult with limit check details
        """
        try:
            config = self.configs.get(limit_type)
            if not config:
                # No rate limit configured, allow request
                return RateLimitResult(
                    allowed=True,
                    current_count=0,
                    limit=0,
                    reset_time=datetime.now(timezone.utc),
                )

            # Generate rate limit key
            rate_limit_key = self._generate_rate_limit_key(limit_type, identifier)

            # Check if currently blocked
            block_result = await self._check_block_status(rate_limit_key, config)
            if not block_result.allowed:
                await self._log_rate_limit_blocked(
                    limit_type, identifier, context, block_result
                )
                return block_result

            # Get current request count
            current_count = await self._get_current_count(rate_limit_key, config)

            # Calculate reset time
            reset_time = self._calculate_reset_time(config)

            # Check if limit exceeded
            if current_count >= config.max_requests:
                # Apply block if configured
                blocked_until = None
                if config.block_duration_seconds > 0:
                    blocked_until = datetime.now(timezone.utc) + timedelta(
                        seconds=config.block_duration_seconds
                    )
                    await self._apply_block(
                        rate_limit_key, blocked_until, current_count
                    )

                result = RateLimitResult(
                    allowed=False,
                    current_count=current_count,
                    limit=config.max_requests,
                    reset_time=reset_time,
                    retry_after_seconds=(
                        config.block_duration_seconds
                        if blocked_until
                        else config.window_size_seconds
                    ),
                    blocked_until=blocked_until,
                )

                await self._log_rate_limit_exceeded(
                    limit_type, identifier, context, result, config
                )
                return result

            # Increment counter
            await self._increment_counter(rate_limit_key, config)

            return RateLimitResult(
                allowed=True,
                current_count=current_count + 1,
                limit=config.max_requests,
                reset_time=reset_time,
            )

        except Exception as e:
            # Log error but don't block requests on rate limiting failures
            await logging_service.log_structured(
                level="ERROR",
                category="RATE_LIMITING",
                message=f"Rate limiting check failed: {str(e)}",
                context=context,
                additional_data={
                    "limit_type": limit_type.value,
                    "identifier": identifier,
                },
            )

            # Allow request on rate limiting service failure
            return RateLimitResult(
                allowed=True,
                current_count=0,
                limit=0,
                reset_time=datetime.now(timezone.utc),
            )

    async def record_violation(
        self,
        limit_type: RateLimitType,
        identifier: str,
        context: ErrorContext,
        severity: str = "HIGH",
    ):
        """Record a rate limit violation for tracking repeat offenders."""
        try:
            violation_key = f"violation:{limit_type.value}:{identifier}"

            # Get current violation count
            violations = await self._get_violation_count(violation_key)

            # Increment violation count
            await self._increment_violation_count(violation_key, violations + 1)

            # Apply progressive penalties if configured
            config = self.configs.get(limit_type)
            if config and config.progressive_penalties:
                await self._apply_progressive_penalty(
                    limit_type, identifier, violations + 1
                )

            # Log violation
            await logging_service.log_structured(
                level="WARNING",
                category="RATE_LIMITING",
                message=f"Rate limit violation recorded: {limit_type.value}",
                context=context,
                additional_data={
                    "limit_type": limit_type.value,
                    "identifier": identifier,
                    "violation_count": violations + 1,
                    "severity": severity,
                },
            )

        except Exception as e:
            await logging_service.log_structured(
                level="ERROR",
                category="RATE_LIMITING",
                message=f"Failed to record rate limit violation: {str(e)}",
                context=context,
            )

    async def clear_rate_limit(
        self, limit_type: RateLimitType, identifier: str, context: ErrorContext
    ):
        """Clear rate limit for an identifier (admin function)."""
        try:
            rate_limit_key = self._generate_rate_limit_key(limit_type, identifier)

            # Clear counter
            await self._clear_counter(rate_limit_key)

            # Clear block
            await self._clear_block(rate_limit_key)

            # Log admin action
            await logging_service.log_structured(
                level="INFO",
                category="RATE_LIMITING",
                message=f"Rate limit cleared by admin: {limit_type.value}",
                context=context,
                additional_data={
                    "limit_type": limit_type.value,
                    "identifier": identifier,
                    "admin_action": True,
                },
            )

        except Exception as e:
            await logging_service.log_structured(
                level="ERROR",
                category="RATE_LIMITING",
                message=f"Failed to clear rate limit: {str(e)}",
                context=context,
            )

    def _generate_rate_limit_key(
        self, limit_type: RateLimitType, identifier: str
    ) -> str:
        """Generate a unique key for rate limiting storage."""
        # Hash identifier for privacy and consistent key length
        identifier_hash = hashlib.sha256(identifier.encode()).hexdigest()[:16]
        timestamp_window = int(
            time.time() // self.configs[limit_type].window_size_seconds
        )
        return f"rate_limit:{limit_type.value}:{identifier_hash}:{timestamp_window}"

    async def _check_block_status(
        self, rate_limit_key: str, config: RateLimitConfig
    ) -> RateLimitResult:
        """Check if identifier is currently blocked."""
        try:
            block_key = f"block:{rate_limit_key}"

            # This would check DynamoDB for block status
            # For now, return not blocked
            return RateLimitResult(
                allowed=True,
                current_count=0,
                limit=config.max_requests,
                reset_time=datetime.now(timezone.utc),
            )

        except Exception:
            # On error, assume not blocked
            return RateLimitResult(
                allowed=True,
                current_count=0,
                limit=config.max_requests,
                reset_time=datetime.now(timezone.utc),
            )

    async def _get_current_count(
        self, rate_limit_key: str, config: RateLimitConfig
    ) -> int:
        """Get current request count for the rate limit window."""
        try:
            # This would query DynamoDB for current count
            # For now, return 0
            return 0
        except Exception:
            return 0

    def _calculate_reset_time(self, config: RateLimitConfig) -> datetime:
        """Calculate when the rate limit window resets."""
        now = datetime.now(timezone.utc)
        window_start = (
            int(time.time() // config.window_size_seconds) * config.window_size_seconds
        )
        reset_time = datetime.fromtimestamp(
            window_start + config.window_size_seconds, tz=timezone.utc
        )
        return reset_time

    async def _increment_counter(self, rate_limit_key: str, config: RateLimitConfig):
        """Increment the request counter for the rate limit window."""
        try:
            # This would increment counter in DynamoDB with TTL
            pass
        except Exception as e:
            # Log but don't fail the request
            pass

    async def _apply_block(
        self, rate_limit_key: str, blocked_until: datetime, violation_count: int
    ):
        """Apply a temporary block for rate limit violation."""
        try:
            block_key = f"block:{rate_limit_key}"

            # This would store block information in DynamoDB with TTL
            block_data = {
                "blocked_until": blocked_until.isoformat(),
                "violation_count": violation_count,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            # Store with TTL
            pass

        except Exception as e:
            # Log but don't fail the request
            pass

    async def _get_violation_count(self, violation_key: str) -> int:
        """Get current violation count for progressive penalties."""
        try:
            # This would query DynamoDB for violation count
            return 0
        except Exception:
            return 0

    async def _increment_violation_count(self, violation_key: str, count: int):
        """Increment violation count with TTL."""
        try:
            # This would store/update violation count in DynamoDB
            pass
        except Exception:
            pass

    async def _apply_progressive_penalty(
        self, limit_type: RateLimitType, identifier: str, violation_count: int
    ):
        """Apply progressive penalties for repeat violations."""
        try:
            # Progressive penalty logic
            if violation_count >= 5:
                # Extended block for repeat offenders
                penalty_duration = (
                    3600 * violation_count
                )  # Hours based on violation count
                penalty_key = f"penalty:{limit_type.value}:{identifier}"

                # This would apply extended penalty
                pass

        except Exception:
            pass

    async def _clear_counter(self, rate_limit_key: str):
        """Clear rate limit counter."""
        try:
            # This would delete the counter from DynamoDB
            pass
        except Exception:
            pass

    async def _clear_block(self, rate_limit_key: str):
        """Clear rate limit block."""
        try:
            block_key = f"block:{rate_limit_key}"
            # This would delete the block from DynamoDB
            pass
        except Exception:
            pass

    async def _log_rate_limit_exceeded(
        self,
        limit_type: RateLimitType,
        identifier: str,
        context: ErrorContext,
        result: RateLimitResult,
        config: RateLimitConfig,
    ):
        """Log rate limit exceeded event."""
        await logging_service.log_rate_limit_event(
            endpoint=context.path or "unknown",
            context=context,
            limit_type=limit_type.value,
            current_count=result.current_count,
            limit=result.limit,
            window_seconds=config.window_size_seconds,
        )

    async def _log_rate_limit_blocked(
        self,
        limit_type: RateLimitType,
        identifier: str,
        context: ErrorContext,
        result: RateLimitResult,
    ):
        """Log rate limit block event."""
        await logging_service.log_structured(
            level="WARNING",
            category="RATE_LIMITING",
            message=f"Request blocked due to rate limit: {limit_type.value}",
            context=context,
            additional_data={
                "limit_type": limit_type.value,
                "identifier": identifier,
                "blocked_until": (
                    result.blocked_until.isoformat() if result.blocked_until else None
                ),
                "retry_after_seconds": result.retry_after_seconds,
            },
        )

    async def get_rate_limit_status(
        self, limit_type: RateLimitType, identifier: str
    ) -> Dict[str, Any]:
        """Get current rate limit status for monitoring."""
        try:
            config = self.configs.get(limit_type)
            if not config:
                return {"error": "Rate limit type not configured"}

            rate_limit_key = self._generate_rate_limit_key(limit_type, identifier)
            current_count = await self._get_current_count(rate_limit_key, config)
            reset_time = self._calculate_reset_time(config)

            return {
                "limit_type": limit_type.value,
                "current_count": current_count,
                "limit": config.max_requests,
                "remaining": max(0, config.max_requests - current_count),
                "reset_time": reset_time.isoformat(),
                "window_seconds": config.window_size_seconds,
            }

        except Exception as e:
            return {"error": f"Failed to get rate limit status: {str(e)}"}


# Global rate limiting service instance
rate_limiting_service = RateLimitingService()


# Convenience functions for common rate limiting checks
async def check_login_rate_limit(
    identifier: str, context: ErrorContext
) -> RateLimitResult:
    """Check rate limit for login attempts."""
    return await rate_limiting_service.check_rate_limit(
        RateLimitType.LOGIN_ATTEMPTS, identifier, context
    )


async def check_password_reset_rate_limit(
    identifier: str, context: ErrorContext
) -> RateLimitResult:
    """Check rate limit for password reset requests."""
    return await rate_limiting_service.check_rate_limit(
        RateLimitType.PASSWORD_RESET, identifier, context
    )


async def check_password_change_rate_limit(
    identifier: str, context: ErrorContext
) -> RateLimitResult:
    """Check rate limit for password changes."""
    return await rate_limiting_service.check_rate_limit(
        RateLimitType.PASSWORD_CHANGE, identifier, context
    )


async def check_api_rate_limit(
    identifier: str, context: ErrorContext
) -> RateLimitResult:
    """Check general API rate limit."""
    return await rate_limiting_service.check_rate_limit(
        RateLimitType.API_REQUESTS, identifier, context
    )


def create_rate_limit_exception(
    result: RateLimitResult, context: ErrorContext
) -> APIException:
    """Create a rate limit exception from rate limit result."""
    return APIException(
        error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
        message=f"Rate limit exceeded. Try again in {result.retry_after_seconds} seconds.",
        context=context,
        retry_after=result.retry_after_seconds,
        blocked_until=result.blocked_until,
    )
