"""SyncMoodysData — Bedrock Agent Action Group handler.

Calls the mock Workato endpoint to trigger a Moody's data sync recipe
and returns the sync status.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict

from shared.arize_trace import trace_span
from shared.response import format_agent_response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

WORKATO_ENDPOINT: str = os.environ.get("WORKATO_ENDPOINT", "")
RECIPE_ID: str = "moodys_daily_sync"


def _trigger_workato_recipe(recipe_id: str) -> Dict[str, Any]:
    """Invoke the mock Workato recipe trigger endpoint.

    Returns the Workato response payload or a fallback mock response
    if the endpoint is unavailable.
    """
    if not WORKATO_ENDPOINT:
        logger.info("WORKATO_ENDPOINT not configured; returning mock response")
        return {
            "data": {
                "job_id": f"job-mock-{int(time.time())}",
                "status": "running",
                "recipe_id": recipe_id,
            },
            "metadata": {
                "request_id": f"req-mock-{int(time.time())}",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        }

    url = f"{WORKATO_ENDPOINT}/mock/workato/recipes/{recipe_id}/trigger"
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps({"source": "bedrock-agent", "action": "sync_moodys"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        logger.warning("Workato trigger failed: %s — returning mock fallback", exc)
        return {
            "data": {
                "job_id": f"job-fallback-{int(time.time())}",
                "status": "running",
                "recipe_id": recipe_id,
            },
            "metadata": {
                "request_id": f"req-fallback-{int(time.time())}",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "note": "Workato endpoint unavailable; mock fallback used.",
            },
        }


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Bedrock Agent Action Group handler for SyncMoodysData."""
    start_time = time.time()
    logger.info("SyncMoodysData invoked: %s", json.dumps(event, default=str))

    action_group: str = event.get("actionGroup", "")
    api_path: str = event.get("apiPath", "/sync-moodys")
    http_method: str = event.get("httpMethod", "POST")

    parameters: Dict[str, str] = {
        p["name"]: p["value"] for p in event.get("parameters", [])
    }
    recipe_id: str = parameters.get("recipe_id", RECIPE_ID)

    # Trigger the Workato recipe
    workato_response = _trigger_workato_recipe(recipe_id)

    body: Dict[str, Any] = {
        "sync_status": "initiated",
        "recipe_id": recipe_id,
        "workato_response": workato_response,
        "message": (
            f"Moody's data sync recipe '{recipe_id}' has been triggered. "
            "Data will be available within 5–10 minutes after sync completes."
        ),
    }

    # Record trace
    latency_ms = (time.time() - start_time) * 1000
    try:
        trace_span(
            agent_name="credit-risk-agent",
            action="SyncMoodysData",
            input_data={"recipe_id": recipe_id},
            output_data={"status": "initiated"},
            latency_ms=latency_ms,
            token_count=45,
        )
    except Exception:
        logger.warning("Failed to record Arize trace", exc_info=True)

    return format_agent_response(action_group, api_path, http_method, 200, body)
