"""
Database connection and utilities.
Simplified DynamoDB client without field mapping complexity.
"""

import boto3
import logging
from typing import Dict, Any, Optional, List
from botocore.exceptions import ClientError
from .config import config

logger = logging.getLogger(__name__)


class DatabaseClient:
    """Simplified DynamoDB client with standardized field handling."""

    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb", region_name=config.database.region)
        # Cache for table objects to avoid recreating them
        self._table_cache = {}

    def _get_table(self, table_name: str):
        """Get or create a table object with caching."""
        if table_name not in self._table_cache:
            self._table_cache[table_name] = self.dynamodb.Table(table_name)
        return self._table_cache[table_name]

    async def get_item(
        self, table_name: str, key: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Get a single item from DynamoDB."""
        try:
            table = self._get_table(table_name)
            response = table.get_item(Key=key)
            return response.get("Item")
        except ClientError as e:
            logger.error(f"Error getting item from {table_name}: {e}")
            return None

    async def put_item(self, table_name: str, item: Dict[str, Any]) -> bool:
        """Put an item into DynamoDB."""
        try:
            table = self._get_table(table_name)
            table.put_item(Item=item)
            return True
        except ClientError as e:
            logger.error(f"Error putting item to {table_name}: {e}")
            # Re-raise the error so we can see what's actually wrong
            raise e
        except Exception as e:
            logger.error(f"Unexpected error putting item to {table_name}: {e}")
            raise e

    async def update_item(
        self, table_name: str, key: Dict[str, Any], update_data: Dict[str, Any]
    ) -> bool:
        """Update an item in DynamoDB."""
        try:
            table = self._get_table(table_name)

            # Build update expression
            update_expression = "SET "
            expression_values = {}
            expression_names = {}

            for field, value in update_data.items():
                if field != "id":  # Don't update the key
                    attr_name = f"#{field}"
                    attr_value = f":{field}"
                    update_expression += f"{attr_name} = {attr_value}, "
                    expression_names[attr_name] = field
                    expression_values[attr_value] = value

            # Remove trailing comma and space
            update_expression = update_expression.rstrip(", ")

            table.update_item(
                Key=key,
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=expression_values,
            )
            return True
        except ClientError as e:
            logger.error(f"Error updating item in {table_name}: {e}")
            return False

    async def delete_item(self, table_name: str, key: Dict[str, Any]) -> bool:
        """Delete an item from DynamoDB."""
        try:
            table = self._get_table(table_name)
            table.delete_item(Key=key)
            return True
        except ClientError as e:
            logger.error(f"Error deleting item from {table_name}: {e}")
            return False

    async def scan_table(
        self, table_name: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Scan a table and return all items."""
        try:
            table = self._get_table(table_name)

            if limit:
                response = table.scan(Limit=limit)
            else:
                response = table.scan()

            return response.get("Items", [])
        except ClientError as e:
            logger.error(f"Error scanning table {table_name}: {e}")
            return []

    async def query_by_index(
        self, table_name: str, index_name: str, key_condition: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Query a table by GSI."""
        try:
            table = self._get_table(table_name)

            # Build key condition expression
            key_condition_expression = ""
            expression_values = {}

            for field, value in key_condition.items():
                key_condition_expression += f"{field} = :{field}"
                expression_values[f":{field}"] = value

            response = table.query(
                IndexName=index_name,
                KeyConditionExpression=key_condition_expression,
                ExpressionAttributeValues=expression_values,
            )

            return response.get("Items", [])
        except ClientError as e:
            logger.error(f"Error querying {table_name} by index {index_name}: {e}")
            return []


# Global database client instance
db = DatabaseClient()
