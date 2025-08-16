"""
DateTime Utilities - Standardized timezone-aware datetime handling

This module provides standardized datetime utilities to replace deprecated
datetime.utcnow() usage and ensure consistent timezone handling across
the entire Service Registry architecture.

Addresses Python 3.12+ compatibility and timezone consistency issues.
"""

from datetime import datetime, timezone, timedelta
from typing import Union, Optional
import re


class DateTimeUtils:
    """
    Standardized datetime utilities for Service Registry pattern.

    This class provides timezone-aware datetime operations that replace
    deprecated datetime.utcnow() and ensure consistent behavior across services.
    """

    @staticmethod
    def utc_now() -> datetime:
        """
        Get current UTC datetime with timezone information.

        Replaces deprecated datetime.utcnow() with timezone-aware alternative.

        Returns:
            datetime: Current UTC datetime with timezone info
        """
        return datetime.now(timezone.utc)

    @staticmethod
    def utc_isoformat() -> str:
        """
        Get current UTC datetime as ISO format string.

        Returns:
            str: Current UTC datetime in ISO format with timezone
        """
        return DateTimeUtils.utc_now().isoformat()

    @staticmethod
    def safe_datetime_parse(dt_input: Union[str, datetime, None]) -> Optional[datetime]:
        """
        Safely parse datetime input ensuring UTC timezone.

        Handles various datetime formats and ensures timezone awareness.

        Args:
            dt_input: String, datetime object, or None

        Returns:
            datetime: Timezone-aware datetime in UTC, or None if input is None
        """
        if dt_input is None:
            return None

        if isinstance(dt_input, str):
            # Handle various ISO format strings
            try:
                # Handle 'Z' suffix (Zulu time)
                if dt_input.endswith("Z"):
                    dt_input = dt_input[:-1] + "+00:00"

                # Parse ISO format
                dt = datetime.fromisoformat(dt_input)
            except ValueError:
                # Try parsing without timezone info
                try:
                    dt = datetime.fromisoformat(dt_input)
                except ValueError:
                    # Last resort: try common formats
                    formats = [
                        "%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%d %H:%M:%S.%f",
                        "%Y-%m-%dT%H:%M:%S",
                        "%Y-%m-%dT%H:%M:%S.%f",
                    ]
                    dt = None
                    for fmt in formats:
                        try:
                            dt = datetime.strptime(dt_input, fmt)
                            break
                        except ValueError:
                            continue

                    if dt is None:
                        raise ValueError(f"Unable to parse datetime string: {dt_input}")
        else:
            dt = dt_input

        # Ensure timezone awareness
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt

    @staticmethod
    def format_for_api(dt: datetime) -> str:
        """
        Format datetime for API responses.

        Ensures consistent datetime formatting across all API responses.

        Args:
            dt: Datetime object

        Returns:
            str: Formatted datetime string for API responses
        """
        if dt is None:
            return None

        # Ensure timezone awareness
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.isoformat()

    @staticmethod
    def format_for_database(dt: datetime) -> str:
        """
        Format datetime for database storage.

        Args:
            dt: Datetime object

        Returns:
            str: Formatted datetime string for database storage
        """
        return DateTimeUtils.format_for_api(dt)

    @staticmethod
    def days_ago(days: int) -> datetime:
        """
        Get datetime N days ago from now.

        Args:
            days: Number of days ago

        Returns:
            datetime: UTC datetime N days ago
        """
        return DateTimeUtils.utc_now() - timedelta(days=days)

    @staticmethod
    def hours_ago(hours: int) -> datetime:
        """
        Get datetime N hours ago from now.

        Args:
            hours: Number of hours ago

        Returns:
            datetime: UTC datetime N hours ago
        """
        return DateTimeUtils.utc_now() - timedelta(hours=hours)

    @staticmethod
    def minutes_ago(minutes: int) -> datetime:
        """
        Get datetime N minutes ago from now.

        Args:
            minutes: Number of minutes ago

        Returns:
            datetime: UTC datetime N minutes ago
        """
        return DateTimeUtils.utc_now() - timedelta(minutes=minutes)

    @staticmethod
    def add_hours(dt: datetime, hours: int) -> datetime:
        """
        Add hours to a datetime.

        Args:
            dt: Base datetime
            hours: Number of hours to add

        Returns:
            datetime: Datetime with hours added
        """
        return dt + timedelta(hours=hours)

    @staticmethod
    def add_days(dt: datetime, days: int) -> datetime:
        """
        Add days to a datetime.

        Args:
            dt: Base datetime
            days: Number of days to add

        Returns:
            datetime: Datetime with days added
        """
        return dt + timedelta(days=days)

    @staticmethod
    def is_expired(dt: datetime, expiry_hours: int = 24) -> bool:
        """
        Check if a datetime is expired based on expiry hours.

        Args:
            dt: Datetime to check
            expiry_hours: Number of hours after which it's considered expired

        Returns:
            bool: True if expired, False otherwise
        """
        if dt is None:
            return True

        # Ensure timezone awareness
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        expiry_time = dt + timedelta(hours=expiry_hours)
        return DateTimeUtils.utc_now() > expiry_time

    @staticmethod
    def time_until_expiry(dt: datetime, expiry_hours: int = 24) -> Optional[timedelta]:
        """
        Get time remaining until expiry.

        Args:
            dt: Base datetime
            expiry_hours: Number of hours until expiry

        Returns:
            timedelta: Time remaining, or None if already expired
        """
        if dt is None:
            return None

        # Ensure timezone awareness
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        expiry_time = dt + timedelta(hours=expiry_hours)
        remaining = expiry_time - DateTimeUtils.utc_now()

        return remaining if remaining.total_seconds() > 0 else None


# Convenience functions for backward compatibility and ease of use


def utc_now() -> datetime:
    """
    Get current UTC datetime.

    Convenience function that wraps DateTimeUtils.utc_now().
    Replaces deprecated datetime.utcnow().

    Returns:
        datetime: Current UTC datetime with timezone info
    """
    return DateTimeUtils.utc_now()


def utc_isoformat() -> str:
    """
    Get current UTC datetime as ISO format string.

    Convenience function that wraps DateTimeUtils.utc_isoformat().

    Returns:
        str: Current UTC datetime in ISO format
    """
    return DateTimeUtils.utc_isoformat()


def safe_isoformat(dt: Union[datetime, None]) -> Optional[str]:
    """
    Safely format datetime to ISO string.

    Args:
        dt: Datetime object or None

    Returns:
        str: ISO formatted datetime string, or None if input is None
    """
    if dt is None:
        return None
    return DateTimeUtils.format_for_api(dt)


def parse_datetime(dt_input: Union[str, datetime, None]) -> Optional[datetime]:
    """
    Parse datetime from various input formats.

    Convenience function that wraps DateTimeUtils.safe_datetime_parse().

    Args:
        dt_input: String, datetime object, or None

    Returns:
        datetime: Parsed datetime with timezone info, or None
    """
    return DateTimeUtils.safe_datetime_parse(dt_input)


# Migration helpers for replacing deprecated datetime.utcnow()


def replace_utcnow_in_code(code_content: str) -> str:
    """
    Helper function to replace datetime.utcnow() calls in code.

    This can be used in migration scripts to automatically update code.

    Args:
        code_content: String containing Python code

    Returns:
        str: Updated code with datetime.utcnow() replaced
    """
    # Replace datetime.utcnow() with utc_now()
    patterns = [
        (r"datetime\.utcnow\(\)", "utc_now()"),
        (r"datetime\.utcnow\(\)\.isoformat\(\)", "utc_isoformat()"),
        (
            r"datetime\.now\(\)(?!\.)",
            "utc_now()",
        ),  # Replace datetime.now() but not datetime.now().something
        (r"datetime\.now\(\)\.isoformat\(\)", "utc_isoformat()"),
    ]

    updated_content = code_content
    for pattern, replacement in patterns:
        updated_content = re.sub(pattern, replacement, updated_content)

    return updated_content


# Example usage patterns for Service Registry

"""
USAGE EXAMPLES:

1. Replace datetime.utcnow():
   # OLD: datetime.utcnow()
   # NEW: utc_now()
   current_time = utc_now()

2. Replace datetime.utcnow().isoformat():
   # OLD: datetime.utcnow().isoformat()
   # NEW: utc_isoformat()
   timestamp = utc_isoformat()

3. Safe datetime parsing:
   parsed_dt = parse_datetime(user_input)

4. Format for API responses:
   api_timestamp = DateTimeUtils.format_for_api(some_datetime)

5. Check expiry:
   if DateTimeUtils.is_expired(token_created_at, expiry_hours=1):
       # Token expired

6. Time calculations:
   one_hour_ago = DateTimeUtils.hours_ago(1)
   tomorrow = DateTimeUtils.add_days(utc_now(), 1)

MIGRATION PATTERN:
# Before (deprecated):
from datetime import datetime
timestamp = datetime.utcnow().isoformat()

# After (recommended):
from ..utils.datetime_utils import utc_isoformat
timestamp = utc_isoformat()
"""
