"""DynamoDB helper utilities for Data Center Investments Agent."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Table name resolution from environment variables
# ---------------------------------------------------------------------------
TABLE_OPERATORS = os.environ.get("TABLE_OPERATORS", "dcai-operators")
TABLE_METRICS = os.environ.get("TABLE_METRICS", "dcai-metrics")
TABLE_ESG = os.environ.get("TABLE_ESG", "dcai-esg-profiles")
TABLE_MARKET = os.environ.get("TABLE_MARKET", "dcai-market-data")
TABLE_SESSIONS = os.environ.get("TABLE_SESSIONS", "dcai-sessions")
TABLE_TRACES = os.environ.get("TABLE_TRACES", "dcai-traces")
TABLE_WORKATO_RUNS = os.environ.get("TABLE_WORKATO_RUNS", "dcai-workato-runs")

# ---------------------------------------------------------------------------
# Shared DynamoDB resource (lazy-initialised)
# ---------------------------------------------------------------------------
_dynamodb_resource: Any = None


def _get_resource() -> Any:
    """Return a cached boto3 DynamoDB resource."""
    global _dynamodb_resource
    if _dynamodb_resource is None:
        _dynamodb_resource = boto3.resource("dynamodb")
    return _dynamodb_resource


def _get_table(table_name: str) -> Any:
    """Return a DynamoDB Table object."""
    return _get_resource().Table(table_name)


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------

def get_item(table_name: str, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Get a single item from a DynamoDB table by primary key.

    Args:
        table_name: Name of the DynamoDB table.
        key: Dict containing partition key (and optional sort key).

    Returns:
        The item dict or ``None`` if not found.
    """
    try:
        table = _get_table(table_name)
        response = table.get_item(Key=key)
        return response.get("Item")
    except Exception:
        logger.exception("get_item failed for table=%s key=%s", table_name, key)
        raise


def put_item(table_name: str, item: Dict[str, Any]) -> Dict[str, Any]:
    """Put (upsert) an item into a DynamoDB table.

    Args:
        table_name: Name of the DynamoDB table.
        item: The complete item dict to write.

    Returns:
        The DynamoDB put_item response metadata.
    """
    try:
        table = _get_table(table_name)
        response = table.put_item(Item=item)
        logger.debug("put_item succeeded for table=%s", table_name)
        return response
    except Exception:
        logger.exception("put_item failed for table=%s", table_name)
        raise


def query_items(
    table_name: str,
    key_condition: Any,
    index_name: Optional[str] = None,
    filter_expression: Optional[Any] = None,
    limit: Optional[int] = None,
    scan_index_forward: bool = True,
) -> List[Dict[str, Any]]:
    """Query items from a DynamoDB table using a key condition expression.

    Args:
        table_name: Name of the DynamoDB table.
        key_condition: A boto3 ``Key`` condition expression.
        index_name: Optional GSI name.
        filter_expression: Optional filter expression applied after query.
        limit: Maximum items to return.
        scan_index_forward: Sort ascending (True) or descending (False).

    Returns:
        List of item dicts matching the query.
    """
    try:
        table = _get_table(table_name)
        kwargs: Dict[str, Any] = {
            "KeyConditionExpression": key_condition,
            "ScanIndexForward": scan_index_forward,
        }
        if index_name:
            kwargs["IndexName"] = index_name
        if filter_expression is not None:
            kwargs["FilterExpression"] = filter_expression
        if limit is not None:
            kwargs["Limit"] = limit

        items: List[Dict[str, Any]] = []
        while True:
            response = table.query(**kwargs)
            items.extend(response.get("Items", []))
            last_key = response.get("LastEvaluatedKey")
            if not last_key or (limit and len(items) >= limit):
                break
            kwargs["ExclusiveStartKey"] = last_key

        return items[:limit] if limit else items
    except Exception:
        logger.exception(
            "query_items failed for table=%s index=%s", table_name, index_name
        )
        raise


def scan_table(
    table_name: str,
    filter_expression: Optional[Any] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Full-table scan with optional filter.  Use sparingly.

    Args:
        table_name: Name of the DynamoDB table.
        filter_expression: Optional filter expression.
        limit: Maximum items to return.

    Returns:
        List of item dicts.
    """
    try:
        table = _get_table(table_name)
        kwargs: Dict[str, Any] = {}
        if filter_expression is not None:
            kwargs["FilterExpression"] = filter_expression
        if limit is not None:
            kwargs["Limit"] = limit

        items: List[Dict[str, Any]] = []
        while True:
            response = table.scan(**kwargs)
            items.extend(response.get("Items", []))
            last_key = response.get("LastEvaluatedKey")
            if not last_key or (limit and len(items) >= limit):
                break
            kwargs["ExclusiveStartKey"] = last_key

        return items[:limit] if limit else items
    except Exception:
        logger.exception("scan_table failed for table=%s", table_name)
        raise
