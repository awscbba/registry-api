"""
Base Repository - Abstract base class for all data access repositories

This module provides the foundation for the Repository Pattern implementation,
ensuring consistent data access patterns across all domain repositories.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, TypeVar, Generic
from dataclasses import dataclass
from enum import Enum
import logging
import time
import uuid
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

# Generic type for repository entities
T = TypeVar("T")


class QueryOperator(Enum):
    """Supported query operators for repository queries"""

    EQUALS = "eq"
    NOT_EQUALS = "ne"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    BEGINS_WITH = "begins_with"
    CONTAINS = "contains"
    IN = "in"
    BETWEEN = "between"


@dataclass
class QueryFilter:
    """Query filter for repository operations"""

    field: str
    operator: QueryOperator
    value: Any
    value2: Optional[Any] = None  # For BETWEEN operations


@dataclass
class QueryOptions:
    """Query options for repository operations"""

    filters: List[QueryFilter] = None
    sort_key: Optional[str] = None
    sort_ascending: bool = True
    limit: Optional[int] = None
    start_key: Optional[Dict[str, Any]] = None
    consistent_read: bool = False
    index_name: Optional[str] = None


@dataclass
class RepositoryResult(Generic[T]):
    """Standardized repository operation result"""

    success: bool
    data: Optional[Union[T, List[T]]] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @property
    def count(self) -> int:
        """Get count of items in result"""
        if self.data is None:
            return 0
        if isinstance(self.data, list):
            return len(self.data)
        return 1


class BaseRepository(ABC, Generic[T]):
    """
    Abstract base repository class providing standardized data access patterns.

    All domain repositories should inherit from this class to ensure consistent
    data access patterns and error handling.
    """

    def __init__(self, table_name: str, region: str = "us-east-1"):
        self.table_name = table_name
        self.region = region
        self.logger = logging.getLogger(f"repository.{self.__class__.__name__}")

        # Initialize DynamoDB resources
        self.dynamodb = boto3.resource("dynamodb", region_name=region)
        self.table = self.dynamodb.Table(table_name)

        # Performance tracking
        self._operation_count = 0
        self._total_response_time = 0.0

    @abstractmethod
    def _to_entity(self, item: Dict[str, Any]) -> T:
        """Convert DynamoDB item to domain entity"""
        pass

    @abstractmethod
    def _to_item(self, entity: T) -> Dict[str, Any]:
        """Convert domain entity to DynamoDB item"""
        pass

    @abstractmethod
    def _get_primary_key(self, entity: T) -> Dict[str, Any]:
        """Get primary key from entity"""
        pass

    def _log_operation(self, operation: str, duration: float, success: bool, **kwargs):
        """Log repository operation for monitoring"""
        self._operation_count += 1
        self._total_response_time += duration

        log_data = {
            "operation": operation,
            "table": self.table_name,
            "duration_ms": round(duration * 1000, 2),
            "success": success,
            "avg_response_time_ms": round(
                (self._total_response_time / self._operation_count) * 1000, 2
            ),
            **kwargs,
        }

        if success:
            self.logger.info(f"Repository operation completed", extra=log_data)
        else:
            self.logger.error(f"Repository operation failed", extra=log_data)

    def _handle_error(self, operation: str, error: Exception) -> RepositoryResult[T]:
        """Standardized error handling for repository operations"""
        error_code = "UNKNOWN_ERROR"
        error_message = str(error)

        if isinstance(error, ClientError):
            error_code = error.response["Error"]["Code"]
            error_message = error.response["Error"]["Message"]

        self.logger.error(
            f"Repository {operation} failed: {error_message}",
            extra={"error_code": error_code, "table": self.table_name},
        )

        return RepositoryResult[T](
            success=False, error=error_message, error_code=error_code
        )

    def _build_filter_expression(self, filters: List[QueryFilter]):
        """Build DynamoDB filter expression from query filters"""
        if not filters:
            return None

        expressions = []

        for filter_item in filters:
            attr = Attr(filter_item.field)

            if filter_item.operator == QueryOperator.EQUALS:
                expressions.append(attr.eq(filter_item.value))
            elif filter_item.operator == QueryOperator.NOT_EQUALS:
                expressions.append(attr.ne(filter_item.value))
            elif filter_item.operator == QueryOperator.LESS_THAN:
                expressions.append(attr.lt(filter_item.value))
            elif filter_item.operator == QueryOperator.LESS_THAN_OR_EQUAL:
                expressions.append(attr.lte(filter_item.value))
            elif filter_item.operator == QueryOperator.GREATER_THAN:
                expressions.append(attr.gt(filter_item.value))
            elif filter_item.operator == QueryOperator.GREATER_THAN_OR_EQUAL:
                expressions.append(attr.gte(filter_item.value))
            elif filter_item.operator == QueryOperator.BEGINS_WITH:
                expressions.append(attr.begins_with(filter_item.value))
            elif filter_item.operator == QueryOperator.CONTAINS:
                expressions.append(attr.contains(filter_item.value))
            elif filter_item.operator == QueryOperator.IN:
                expressions.append(attr.is_in(filter_item.value))
            elif filter_item.operator == QueryOperator.BETWEEN:
                expressions.append(attr.between(filter_item.value, filter_item.value2))

        # Combine all expressions with AND
        result = expressions[0]
        for expr in expressions[1:]:
            result = result & expr

        return result

    async def get_by_id(self, entity_id: str) -> RepositoryResult[T]:
        """Get entity by ID"""
        start_time = time.time()

        try:
            response = self.table.get_item(Key={"id": entity_id})

            duration = time.time() - start_time

            if "Item" not in response:
                self._log_operation(
                    "get_by_id", duration, True, entity_id=entity_id, found=False
                )
                return RepositoryResult[T](success=True, data=None)

            entity = self._to_entity(response["Item"])
            self._log_operation(
                "get_by_id", duration, True, entity_id=entity_id, found=True
            )

            return RepositoryResult[T](success=True, data=entity)

        except Exception as e:
            duration = time.time() - start_time
            self._log_operation(
                "get_by_id", duration, False, entity_id=entity_id, error=str(e)
            )
            return self._handle_error("get_by_id", e)

    async def create(self, entity: T) -> RepositoryResult[T]:
        """Create new entity"""
        start_time = time.time()

        try:
            item = self._to_item(entity)

            # Add metadata
            now = datetime.now(timezone.utc).isoformat()
            item.update({"created_at": now, "updated_at": now, "version": 1})

            # Use condition to prevent overwriting existing items
            self.table.put_item(Item=item, ConditionExpression=Attr("id").not_exists())

            duration = time.time() - start_time
            self._log_operation("create", duration, True, entity_id=item.get("id"))

            # Return the created entity with metadata
            created_entity = self._to_entity(item)
            return RepositoryResult[T](success=True, data=created_entity)

        except Exception as e:
            duration = time.time() - start_time
            self._log_operation("create", duration, False, error=str(e))
            return self._handle_error("create", e)

    async def update(self, entity: T) -> RepositoryResult[T]:
        """Update existing entity"""
        start_time = time.time()

        try:
            item = self._to_item(entity)
            primary_key = self._get_primary_key(entity)

            # Build update expression
            update_expression = "SET updated_at = :updated_at, version = version + :inc"
            expression_values = {
                ":updated_at": datetime.now(timezone.utc).isoformat(),
                ":inc": 1,
            }

            # Add all non-key fields to update
            for key, value in item.items():
                if key not in primary_key and key not in [
                    "created_at",
                    "updated_at",
                    "version",
                ]:
                    update_expression += f", {key} = :{key}"
                    expression_values[f":{key}"] = value

            response = self.table.update_item(
                Key=primary_key,
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ConditionExpression=Attr("id").exists(),
                ReturnValues="ALL_NEW",
            )

            duration = time.time() - start_time
            self._log_operation(
                "update", duration, True, entity_id=primary_key.get("id")
            )

            updated_entity = self._to_entity(response["Attributes"])
            return RepositoryResult[T](success=True, data=updated_entity)

        except Exception as e:
            duration = time.time() - start_time
            self._log_operation("update", duration, False, error=str(e))
            return self._handle_error("update", e)

    async def delete(self, entity_id: str) -> RepositoryResult[bool]:
        """Delete entity by ID"""
        start_time = time.time()

        try:
            self.table.delete_item(
                Key={"id": entity_id}, ConditionExpression=Attr("id").exists()
            )

            duration = time.time() - start_time
            self._log_operation("delete", duration, True, entity_id=entity_id)

            return RepositoryResult[bool](success=True, data=True)

        except Exception as e:
            duration = time.time() - start_time
            self._log_operation(
                "delete", duration, False, entity_id=entity_id, error=str(e)
            )
            return self._handle_error("delete", e)

    async def list_all(
        self, options: Optional[QueryOptions] = None
    ) -> RepositoryResult[List[T]]:
        """List all entities with optional filtering and pagination"""
        start_time = time.time()

        try:
            scan_kwargs = {}

            if options:
                if options.filters:
                    scan_kwargs["FilterExpression"] = self._build_filter_expression(
                        options.filters
                    )

                if options.limit:
                    scan_kwargs["Limit"] = options.limit

                if options.start_key:
                    scan_kwargs["ExclusiveStartKey"] = options.start_key

                if options.consistent_read:
                    scan_kwargs["ConsistentRead"] = options.consistent_read

                if options.index_name:
                    scan_kwargs["IndexName"] = options.index_name

            response = self.table.scan(**scan_kwargs)

            entities = [self._to_entity(item) for item in response.get("Items", [])]

            # Sort if requested
            if options and options.sort_key:
                entities.sort(
                    key=lambda x: getattr(x, options.sort_key, ""),
                    reverse=not options.sort_ascending,
                )

            duration = time.time() - start_time
            self._log_operation("list_all", duration, True, count=len(entities))

            metadata = {}
            if "LastEvaluatedKey" in response:
                metadata["last_evaluated_key"] = response["LastEvaluatedKey"]
            if "Count" in response:
                metadata["count"] = response["Count"]
            if "ScannedCount" in response:
                metadata["scanned_count"] = response["ScannedCount"]

            return RepositoryResult[List[T]](
                success=True, data=entities, metadata=metadata if metadata else None
            )

        except Exception as e:
            duration = time.time() - start_time
            self._log_operation("list_all", duration, False, error=str(e))
            return self._handle_error("list_all", e)

    async def query_by_index(
        self,
        index_name: str,
        key_condition: Dict[str, Any],
        options: Optional[QueryOptions] = None,
    ) -> RepositoryResult[List[T]]:
        """Query entities using a secondary index"""
        start_time = time.time()

        try:
            # Build key condition expression
            key_conditions = []
            for field, value in key_condition.items():
                key_conditions.append(Key(field).eq(value))

            key_condition_expr = key_conditions[0]
            for condition in key_conditions[1:]:
                key_condition_expr = key_condition_expr & condition

            query_kwargs = {
                "IndexName": index_name,
                "KeyConditionExpression": key_condition_expr,
            }

            if options:
                if options.filters:
                    query_kwargs["FilterExpression"] = self._build_filter_expression(
                        options.filters
                    )

                if options.limit:
                    query_kwargs["Limit"] = options.limit

                if options.start_key:
                    query_kwargs["ExclusiveStartKey"] = options.start_key

                if options.consistent_read:
                    query_kwargs["ConsistentRead"] = options.consistent_read

                if not options.sort_ascending:
                    query_kwargs["ScanIndexForward"] = False

            response = self.table.query(**query_kwargs)

            entities = [self._to_entity(item) for item in response.get("Items", [])]

            duration = time.time() - start_time
            self._log_operation(
                "query_by_index", duration, True, index=index_name, count=len(entities)
            )

            metadata = {}
            if "LastEvaluatedKey" in response:
                metadata["last_evaluated_key"] = response["LastEvaluatedKey"]
            if "Count" in response:
                metadata["count"] = response["Count"]
            if "ScannedCount" in response:
                metadata["scanned_count"] = response["ScannedCount"]

            return RepositoryResult[List[T]](
                success=True, data=entities, metadata=metadata if metadata else None
            )

        except Exception as e:
            duration = time.time() - start_time
            self._log_operation(
                "query_by_index", duration, False, index=index_name, error=str(e)
            )
            return self._handle_error("query_by_index", e)

    async def batch_get(self, entity_ids: List[str]) -> RepositoryResult[List[T]]:
        """Get multiple entities by their IDs"""
        start_time = time.time()

        try:
            if not entity_ids:
                return RepositoryResult[List[T]](success=True, data=[])

            # DynamoDB batch_get_item has a limit of 100 items
            batch_size = 100
            all_entities = []

            for i in range(0, len(entity_ids), batch_size):
                batch_ids = entity_ids[i : i + batch_size]

                response = self.dynamodb.batch_get_item(
                    RequestItems={
                        self.table_name: {
                            "Keys": [{"id": entity_id} for entity_id in batch_ids]
                        }
                    }
                )

                items = response.get("Responses", {}).get(self.table_name, [])
                entities = [self._to_entity(item) for item in items]
                all_entities.extend(entities)

            duration = time.time() - start_time
            self._log_operation(
                "batch_get",
                duration,
                True,
                requested=len(entity_ids),
                found=len(all_entities),
            )

            return RepositoryResult[List[T]](success=True, data=all_entities)

        except Exception as e:
            duration = time.time() - start_time
            self._log_operation(
                "batch_get", duration, False, requested=len(entity_ids), error=str(e)
            )
            return self._handle_error("batch_get", e)

    async def count(
        self, options: Optional[QueryOptions] = None
    ) -> RepositoryResult[int]:
        """Count entities with optional filtering"""
        start_time = time.time()

        try:
            scan_kwargs = {"Select": "COUNT"}

            if options and options.filters:
                scan_kwargs["FilterExpression"] = self._build_filter_expression(
                    options.filters
                )

            response = self.table.scan(**scan_kwargs)
            count = response.get("Count", 0)

            duration = time.time() - start_time
            self._log_operation("count", duration, True, count=count)

            return RepositoryResult[int](success=True, data=count)

        except Exception as e:
            duration = time.time() - start_time
            self._log_operation("count", duration, False, error=str(e))
            return self._handle_error("count", e)

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get repository performance statistics"""
        return {
            "operation_count": self._operation_count,
            "total_response_time_ms": round(self._total_response_time * 1000, 2),
            "average_response_time_ms": round(
                (self._total_response_time / max(self._operation_count, 1)) * 1000, 2
            ),
            "table_name": self.table_name,
        }
