"""GET /v1/health — Service health check.

Returns operational status of the agent and connectivity to mock services.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TABLE_OPERATORS: str = os.environ.get("TABLE_OPERATORS", "dcai-operators")
ARIZE_ENDPOINT: str = os.environ.get("ARIZE_ENDPOINT", "")
WORKATO_ENDPOINT: str = os.environ.get("WORKATO_ENDPOINT", "")
BEDROCK_AGENT_ID: str = os.environ.get("BEDROCK_AGENT_ID", "")

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


def _check_dynamodb() -> Dict[str, Any]:
    """Check DynamoDB connectivity by describing the operators table."""
    try:
        table = _get_dynamodb().Table(TABLE_OPERATORS)
        table.table_status  # Forces metadata fetch
        return {"status": "healthy", "table": TABLE_OPERATORS}
    except Exception as exc:
        return {"status": "unhealthy", "error": str(exc)}


def _check_endpoint(name: str, url: str) -> Dict[str, Any]:
    """Check an HTTP endpoint."""
    if not url:
        return {"status": "not_configured", "endpoint": name}

    try:
        import urllib.request
        import urllib.error

        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return {"status": "healthy", "endpoint": name, "http_status": resp.status}
    except Exception as exc:
        return {"status": "unhealthy", "endpoint": name, "error": str(exc)}


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for GET /v1/health."""
    logger.info("Health check invoked")

    http_method = event.get("httpMethod", "GET")
    if http_method == "OPTIONS":
        return _api_response(200, {})

    checks: Dict[str, Any] = {}

    # DynamoDB
    checks["dynamodb"] = _check_dynamodb()

    # Bedrock Agent
    if BEDROCK_AGENT_ID:
        checks["bedrock_agent"] = {"status": "configured", "agent_id": BEDROCK_AGENT_ID}
    else:
        checks["bedrock_agent"] = {"status": "not_configured", "note": "Using mock fallback"}

    # Mock Arize
    arize_health_url = f"{ARIZE_ENDPOINT}/mock/arize/metrics" if ARIZE_ENDPOINT else ""
    checks["arize"] = _check_endpoint("arize", arize_health_url)

    # Mock Workato
    workato_health_url = f"{WORKATO_ENDPOINT}/mock/workato/connections" if WORKATO_ENDPOINT else ""
    checks["workato"] = _check_endpoint("workato", workato_health_url)

    # Overall status
    all_healthy = all(
        c.get("status") in ("healthy", "configured", "not_configured")
        for c in checks.values()
    )

    return _api_response(200, {
        "service": "dc-invest-agent",
        "status": "healthy" if all_healthy else "degraded",
        "version": "1.0.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "checks": checks,
    })
