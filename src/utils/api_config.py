"""
API Configuration Utility

Provides a robust way to get the API URL for tests and other components.
Tries multiple sources in order of preference:
1. Environment variable
2. CloudFormation stack output
3. Default fallback
"""

import os
import subprocess
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_api_url() -> str:
    """
    Get the API URL from the most reliable source available.

    Returns:
        str: The API base URL (without trailing slash)
    """
    # 1. Try environment variable first (most reliable for tests)
    api_url = os.getenv("API_BASE_URL")
    if api_url:
        logger.info(f"Using API URL from environment variable: {api_url}")
        return api_url.rstrip("/")

    # 2. Try CloudFormation stack output
    try:
        api_url = get_api_url_from_cloudformation()
        if api_url:
            logger.info(f"Using API URL from CloudFormation: {api_url}")
            return api_url.rstrip("/")
    except Exception as e:
        logger.warning(f"Failed to get API URL from CloudFormation: {e}")

    # 3. Fall back to known production URL
    default_url = "https://2t9blvt2c1.execute-api.us-east-1.amazonaws.com/prod"
    logger.info(f"Using default API URL: {default_url}")
    return default_url


def get_api_url_from_cloudformation() -> Optional[str]:
    """
    Get API URL from CloudFormation stack output.

    Returns:
        Optional[str]: The API URL if found, None otherwise
    """
    try:
        result = subprocess.run(
            [
                "aws",
                "cloudformation",
                "describe-stacks",
                "--stack-name",
                "PeopleRegisterInfrastructureStack",
                "--query",
                "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue",
                "--output",
                "text",
                "--region",
                "us-east-1",
            ],
            capture_output=True,
            text=True,
            timeout=10,  # 10 second timeout
        )

        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        else:
            logger.warning(f"CloudFormation query failed: {result.stderr}")
            return None

    except subprocess.TimeoutExpired:
        logger.warning("CloudFormation query timed out")
        return None
    except FileNotFoundError:
        logger.warning("AWS CLI not found")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error querying CloudFormation: {e}")
        return None


def set_api_url_for_tests(url: str) -> None:
    """
    Set the API URL for testing purposes.

    Args:
        url: The API base URL to use for tests
    """
    os.environ["API_BASE_URL"] = url
    logger.info(f"Set API URL for tests: {url}")


# For backward compatibility and easy imports
API_BASE_URL = get_api_url()
