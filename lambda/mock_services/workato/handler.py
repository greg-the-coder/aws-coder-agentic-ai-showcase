"""Mock Workato service — single Lambda handling all Workato mock routes.

Routes:
    POST /mock/workato/recipes/{recipe_id}/trigger  — Trigger a recipe
    GET  /mock/workato/recipes/{recipe_id}/status   — Recipe run status
    POST /mock/workato/webhooks/moodys-rating-action — Simulate incoming Moody's webhook
    GET  /mock/workato/connections                   — List mock connections
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from typing import Any, Dict, Optional

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TABLE_WORKATO_RUNS: str = os.environ.get("TABLE_WORKATO_RUNS", "dcai-workato-runs")

_dynamodb: Any = None


def _get_dynamodb() -> Any:
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb")
    return _dynamodb


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _request_id() -> str:
    return f"wreq-{uuid.uuid4().hex[:12]}"


def _wrap_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Return an API Gateway-compatible response dict."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "X-Workato-Request-Id": _request_id(),
        },
        "body": json.dumps(body, default=str),
    }


def _workato_envelope(data: Dict[str, Any]) -> Dict[str, Any]:
    """Wrap data in realistic Workato API response format."""
    return {
        "data": data,
        "metadata": {
            "request_id": _request_id(),
            "timestamp": _ts(),
        },
    }


# ---------------------------------------------------------------------------
# Route: POST /mock/workato/recipes/{recipe_id}/trigger
# ---------------------------------------------------------------------------

def _handle_trigger(recipe_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    job_id = f"wjob-{uuid.uuid4().hex[:12]}"
    record = {
        "job_id": job_id,
        "recipe_id": recipe_id,
        "status": "running",
        "triggered_at": _ts(),
        "triggered_by": body.get("source", "api"),
        "records_processed": 0,
    }

    try:
        table = _get_dynamodb().Table(TABLE_WORKATO_RUNS)
        table.put_item(Item=record)
    except Exception:
        logger.warning("Failed to store Workato run record", exc_info=True)

    return _wrap_response(200, _workato_envelope({
        "job_id": job_id,
        "status": "running",
        "recipe_id": recipe_id,
    }))


# ---------------------------------------------------------------------------
# Route: GET /mock/workato/recipes/{recipe_id}/status
# ---------------------------------------------------------------------------

def _handle_status(recipe_id: str) -> Dict[str, Any]:
    # Return a mock "succeeded" status
    return _wrap_response(200, _workato_envelope({
        "recipe_id": recipe_id,
        "status": "succeeded",
        "last_run": _ts(),
        "records_processed": 6,
        "duration_seconds": 12.4,
        "steps_executed": 4,
        "errors": [],
    }))


# ---------------------------------------------------------------------------
# Route: POST /mock/workato/webhooks/moodys-rating-action
# ---------------------------------------------------------------------------

def _handle_moodys_webhook(body: Dict[str, Any]) -> Dict[str, Any]:
    event_id = f"wevt-{uuid.uuid4().hex[:12]}"

    # Simulate writing a Moody's rating-action event to DynamoDB
    record = {
        "job_id": event_id,
        "recipe_id": "moodys_webhook_listener",
        "status": "processed",
        "triggered_at": _ts(),
        "triggered_by": "webhook",
        "event_type": "moodys-rating-action",
        "payload": json.dumps(body, default=str),
        "records_processed": 1,
    }

    try:
        table = _get_dynamodb().Table(TABLE_WORKATO_RUNS)
        table.put_item(Item=record)
        logger.info("Moody's webhook event stored: %s", event_id)
    except Exception:
        logger.warning("Failed to store Moody's webhook event", exc_info=True)

    return _wrap_response(200, _workato_envelope({
        "event_id": event_id,
        "status": "processed",
        "message": "Moody's rating action event received and stored.",
    }))


# ---------------------------------------------------------------------------
# Route: GET /mock/workato/connections
# ---------------------------------------------------------------------------

def _handle_connections() -> Dict[str, Any]:
    connections = [
        {
            "id": "conn-001",
            "name": "Moody's CreditView",
            "provider": "moodys_creditview",
            "status": "active",
            "last_tested": "2024-06-15T10:30:00Z",
            "auth_type": "oauth2",
        },
        {
            "id": "conn-002",
            "name": "AWS S3 — dc-invest-docs",
            "provider": "aws_s3",
            "status": "active",
            "last_tested": "2024-06-15T10:31:00Z",
            "auth_type": "iam_role",
        },
        {
            "id": "conn-003",
            "name": "Salesforce — DC Investments",
            "provider": "salesforce",
            "status": "active",
            "last_tested": "2024-06-15T10:32:00Z",
            "auth_type": "oauth2",
        },
        {
            "id": "conn-004",
            "name": "Slack — #dc-credit-alerts",
            "provider": "slack",
            "status": "active",
            "last_tested": "2024-06-15T10:33:00Z",
            "auth_type": "bot_token",
        },
    ]
    return _wrap_response(200, _workato_envelope({
        "connections": connections,
        "total": len(connections),
    }))


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

def _parse_path(raw_path: str) -> tuple[str, Optional[str]]:
    """Parse API Gateway path to determine route and extract recipe_id.

    Returns:
        (route_key, recipe_id_or_none)
    """
    path = raw_path.rstrip("/")

    # POST /mock/workato/recipes/{recipe_id}/trigger
    m = re.match(r".*/recipes/([^/]+)/trigger$", path)
    if m:
        return "trigger", m.group(1)

    # GET /mock/workato/recipes/{recipe_id}/status
    m = re.match(r".*/recipes/([^/]+)/status$", path)
    if m:
        return "status", m.group(1)

    # POST /mock/workato/webhooks/moodys-rating-action
    if "webhooks/moodys-rating-action" in path:
        return "webhook", None

    # GET /mock/workato/connections
    if path.endswith("/connections"):
        return "connections", None

    return "unknown", None


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for Mock Workato service."""
    logger.info("Mock Workato invoked: %s", json.dumps(event, default=str))

    http_method: str = event.get("httpMethod", event.get("requestContext", {}).get("http", {}).get("method", "GET"))
    raw_path: str = event.get("path", event.get("rawPath", ""))

    # Parse body
    body: Dict[str, Any] = {}
    raw_body = event.get("body", "")
    if raw_body:
        try:
            body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
        except json.JSONDecodeError:
            body = {}

    route_key, recipe_id = _parse_path(raw_path)

    if route_key == "trigger" and recipe_id:
        return _handle_trigger(recipe_id, body)
    elif route_key == "status" and recipe_id:
        return _handle_status(recipe_id)
    elif route_key == "webhook":
        return _handle_moodys_webhook(body)
    elif route_key == "connections":
        return _handle_connections()
    else:
        return _wrap_response(404, _workato_envelope({
            "error": "Route not found",
            "path": raw_path,
            "method": http_method,
        }))
