"""GET /v1/sessions/{id} — Retrieve conversation history for a session."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TABLE_SESSIONS: str = os.environ.get("TABLE_SESSIONS", "dcai-sessions")

_dynamodb: Any = None


def _get_dynamodb() -> Any:
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb")
    return _dynamodb


def _api_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
        "body": json.dumps(body, default=str),
    }


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for GET /v1/sessions/{id}."""
    logger.info("Session handler invoked")

    http_method = event.get("httpMethod", "GET")
    if http_method == "OPTIONS":
        return _api_response(200, {})

    # Extract session_id from path parameters
    path_params = event.get("pathParameters") or {}
    session_id: str = path_params.get("id", "")

    if not session_id:
        return _api_response(400, {"error": "Session ID is required in the path"})

    try:
        table = _get_dynamodb().Table(TABLE_SESSIONS)
        response = table.get_item(Key={"session_id": session_id})
        item = response.get("Item")
    except Exception:
        logger.exception("Failed to retrieve session %s", session_id)
        return _api_response(500, {"error": "Internal error retrieving session"})

    if not item:
        return _api_response(404, {"error": f"Session '{session_id}' not found"})

    return _api_response(200, {
        "session_id": item.get("session_id"),
        "user_id": item.get("user_id", ""),
        "agent_id": item.get("agent_id", ""),
        "messages": item.get("messages", []),
        "created_at": item.get("created_at", ""),
        "updated_at": item.get("updated_at", ""),
        "metadata": item.get("metadata", {}),
        "message_count": len(item.get("messages", [])),
    })
