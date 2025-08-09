"""
X-Ray tracing configuration for the People Registry API.
This module sets up AWS X-Ray tracing for comprehensive observability.
"""

import os
import logging
from typing import Optional

# Configure logging
logger = logging.getLogger(__name__)

# X-Ray SDK imports with error handling
try:
    from aws_xray_sdk.core import xray_recorder, patch_all
    from aws_xray_sdk.core.context import Context
    from aws_xray_sdk.core.models import http
    XRAY_AVAILABLE = True
except ImportError as e:
    logger.warning(f"X-Ray SDK not available: {e}")
    XRAY_AVAILABLE = False


def configure_xray() -> bool:
    """
    Configure X-Ray tracing for the Lambda function.
    
    Returns:
        bool: True if X-Ray was successfully configured, False otherwise
    """
    if not XRAY_AVAILABLE:
        logger.warning("X-Ray SDK not available, tracing disabled")
        return False
    
    try:
        # Check if we're running in Lambda environment
        if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
            logger.info("Configuring X-Ray for Lambda environment")
            
            # Configure X-Ray recorder
            xray_recorder.configure(
                context_missing='LOG_ERROR',  # Log errors instead of raising exceptions
                plugins=('EC2Plugin', 'ECSPlugin'),  # Add AWS plugins
                daemon_address=os.environ.get('_X_AMZN_TRACE_ID', '127.0.0.1:2000'),
                use_ssl=False
            )
            
            # Patch AWS SDK calls, HTTP requests, and other libraries
            patch_all()
            
            logger.info("X-Ray tracing configured successfully")
            return True
        else:
            logger.info("Not running in Lambda, X-Ray tracing disabled")
            return False
            
    except Exception as e:
        logger.error(f"Failed to configure X-Ray: {e}")
        return False


def create_subsegment(name: str, metadata: Optional[dict] = None):
    """
    Create a custom X-Ray subsegment for detailed tracing.
    
    Args:
        name: Name of the subsegment
        metadata: Optional metadata to attach to the subsegment
    
    Returns:
        X-Ray subsegment context manager or None if X-Ray is not available
    """
    from contextlib import nullcontext
    
    if not XRAY_AVAILABLE or not XRAY_ENABLED:
        # Return a no-op context manager
        return nullcontext()
    
    try:
        subsegment = xray_recorder.begin_subsegment(name)
        if metadata:
            subsegment.put_metadata('custom', metadata)
        return subsegment
    except Exception as e:
        logger.error(f"Failed to create X-Ray subsegment '{name}': {e}")
        return nullcontext()


def add_annotation(key: str, value: str) -> None:
    """
    Add an annotation to the current X-Ray segment.
    Annotations are indexed and can be used for filtering traces.
    
    Args:
        key: Annotation key
        value: Annotation value
    """
    if not XRAY_AVAILABLE or not XRAY_ENABLED:
        return
    
    try:
        xray_recorder.put_annotation(key, value)
    except Exception as e:
        logger.error(f"Failed to add X-Ray annotation '{key}': {e}")


def add_metadata(namespace: str, key: str, value: any) -> None:
    """
    Add metadata to the current X-Ray segment.
    Metadata is not indexed but provides detailed information.
    
    Args:
        namespace: Metadata namespace
        key: Metadata key
        value: Metadata value
    """
    if not XRAY_AVAILABLE or not XRAY_ENABLED:
        return
    
    try:
        xray_recorder.put_metadata(key, value, namespace)
    except Exception as e:
        logger.error(f"Failed to add X-Ray metadata '{namespace}.{key}': {e}")


def trace_http_request(url: str, method: str = 'GET'):
    """
    Trace an HTTP request with X-Ray.
    
    Args:
        url: Request URL
        method: HTTP method
    
    Returns:
        HTTP subsegment context manager
    """
    from contextlib import nullcontext
    
    if not XRAY_AVAILABLE or not XRAY_ENABLED:
        return nullcontext()
    
    try:
        return xray_recorder.in_subsegment_async(
            name=f'{method} {url}',
            namespace='remote'
        )
    except Exception as e:
        logger.error(f"Failed to trace HTTP request to '{url}': {e}")
        return nullcontext()


# Initialize X-Ray when module is imported
XRAY_ENABLED = configure_xray()

# Export key functions and status
__all__ = [
    'XRAY_ENABLED',
    'configure_xray',
    'create_subsegment',
    'add_annotation',
    'add_metadata',
    'trace_http_request'
]
