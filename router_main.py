"""
Simple routing Lambda that forwards requests to appropriate backend Lambda functions.
This solves the API Gateway policy size limit issue by having a single integration point.
"""
import json
import boto3
import os
import logging
from typing import Dict, Any

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Lambda client
lambda_client = boto3.client('lambda')

# Get Lambda function names from environment variables
AUTH_FUNCTION_NAME = os.environ['AUTH_FUNCTION_NAME']
API_FUNCTION_NAME = os.environ['API_FUNCTION_NAME']

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Route requests to appropriate Lambda functions based on path.

    Routing rules:
    - /auth/* -> AuthFunction
    - Everything else -> PeopleApiFunction
    """

    # Add logging to debug the issue
    logger.info(f"Router received event: {json.dumps(event)}")

    # Extract path from the event
    path = event.get('path', '')
    http_method = event.get('httpMethod', 'GET')

    logger.info(f"Extracted path: {path}, method: {http_method}")

    # Determine target function based on path
    if path.startswith('/auth'):
        target_function = AUTH_FUNCTION_NAME
    else:
        target_function = API_FUNCTION_NAME

    logger.info(f"Routing to function: {target_function}")

    try:
        # Forward the request to the appropriate Lambda function
        logger.info(f"Invoking {target_function} with payload size: {len(json.dumps(event))}")
        response = lambda_client.invoke(
            FunctionName=target_function,
            InvocationType='RequestResponse',
            Payload=json.dumps(event)
        )

        logger.info(f"Lambda response status: {response['StatusCode']}")

        # Parse the response
        payload = json.loads(response['Payload'].read())

        logger.info(f"Parsed payload: {json.dumps(payload)[:200]}...")

        return payload

    except Exception as e:
        # Return error response with more details
        error_msg = f"Router error: {str(e)}"
        logger.error(error_msg)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
            },
            'body': json.dumps({
                'error': 'Router internal server error',
                'message': error_msg,
                'path': path,
                'target_function': target_function
            })
        }
