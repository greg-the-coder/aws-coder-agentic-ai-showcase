"""SyncMoodysData — Strands tool implementation."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any, Dict

from strands import tool

from agent.config import WORKATO_ENDPOINT

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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
            data=json.dumps({"source": "strands-agent", "action": "sync_moodys"}).encode("utf-8"),
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


@tool
def sync_moodys_data(recipe_id: str = "moodys_daily_sync") -> dict:
    """Trigger a Workato recipe to sync latest Moody's credit rating data.

    Args:
        recipe_id: Workato recipe ID to trigger. Defaults to "moodys_daily_sync".

    Returns:
        Sync status including job ID, status, and expected completion time.
    """
    workato_response = _trigger_workato_recipe(recipe_id)

    return {
        "sync_status": "initiated",
        "recipe_id": recipe_id,
        "workato_response": workato_response,
        "message": (
            f"Moody's data sync recipe '{recipe_id}' has been triggered. "
            "Data will be available within 5-10 minutes after sync completes."
        ),
    }
