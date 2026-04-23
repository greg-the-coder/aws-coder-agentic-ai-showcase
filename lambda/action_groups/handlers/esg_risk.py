"""AssessESGRisk — Bedrock Agent Action Group handler.

Queries the ``dcai-esg-profiles`` table by operator_id and returns
PUE, carbon intensity, renewable %, water usage, climate risk score,
and green-bond data.  Supports dimension filtering.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from shared.arize_trace import trace_span
from shared.db import TABLE_ESG, get_item
from shared.response import format_agent_response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Dimension → ESGProfile fields mapping
DIMENSION_FIELDS: Dict[str, List[str]] = {
    "pue": ["pue"],
    "carbon": ["carbon_intensity"],
    "water": ["water_usage"],
    "climate_physical": ["climate_risk_score"],
    "climate_transition": ["renewable_pct", "green_bond_outstanding"],
}

# Benchmark thresholds for qualitative assessment
_BENCHMARKS: Dict[str, Dict[str, Any]] = {
    "pue": {"excellent": 1.2, "good": 1.4, "fair": 1.6, "poor": 2.0},
    "carbon_intensity": {"excellent": 150, "good": 250, "fair": 350, "poor": 500},
    "renewable_pct": {"excellent": 0.90, "good": 0.70, "fair": 0.50, "poor": 0.30},
    "water_usage": {"excellent": 1.0, "good": 1.3, "fair": 1.6, "poor": 2.0},
    "climate_risk_score": {"excellent": 80, "good": 70, "fair": 60, "poor": 50},
}


def _assess_level(metric_name: str, value: float) -> str:
    """Return a qualitative assessment level for a metric value."""
    thresholds = _BENCHMARKS.get(metric_name)
    if not thresholds:
        return "N/A"

    # For metrics where lower is better (PUE, carbon, water)
    lower_is_better = metric_name in ("pue", "carbon_intensity", "water_usage")

    if lower_is_better:
        if value <= thresholds["excellent"]:
            return "excellent"
        elif value <= thresholds["good"]:
            return "good"
        elif value <= thresholds["fair"]:
            return "fair"
        else:
            return "poor"
    else:
        # Higher is better (renewable_pct, climate_risk_score)
        if value >= thresholds["excellent"]:
            return "excellent"
        elif value >= thresholds["good"]:
            return "good"
        elif value >= thresholds["fair"]:
            return "fair"
        else:
            return "poor"


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Bedrock Agent Action Group handler for AssessESGRisk."""
    start_time = time.time()
    logger.info("AssessESGRisk invoked: %s", json.dumps(event, default=str))

    action_group: str = event.get("actionGroup", "")
    api_path: str = event.get("apiPath", "/esg-risk")
    http_method: str = event.get("httpMethod", "POST")

    # Extract parameters — may come from requestBody or parameters
    parameters: Dict[str, str] = {
        p["name"]: p["value"] for p in event.get("parameters", [])
    }

    # Also check requestBody for POST payloads
    request_body: Dict[str, Any] = {}
    raw_body = event.get("requestBody", {})
    if isinstance(raw_body, dict):
        content = raw_body.get("content", {})
        json_content = content.get("application/json", {})
        if isinstance(json_content, dict):
            props = json_content.get("properties", [])
            if isinstance(props, list):
                for prop in props:
                    request_body[prop.get("name", "")] = prop.get("value", "")

    facility_id: str = parameters.get("facility_id", "") or request_body.get("facility_id", "")
    dimensions_raw: str = parameters.get("dimensions", "") or request_body.get("dimensions", "")

    if not facility_id:
        return format_agent_response(
            action_group, api_path, http_method, 400,
            {"error": "facility_id (operator_id) parameter is required"},
        )

    # Parse dimensions
    requested_dimensions: Optional[List[str]] = None
    if dimensions_raw:
        if isinstance(dimensions_raw, str):
            requested_dimensions = [d.strip() for d in dimensions_raw.split(",")]
        elif isinstance(dimensions_raw, list):
            requested_dimensions = dimensions_raw

    # Query ESG profile
    try:
        profile = get_item(TABLE_ESG, {"operator_id": facility_id})
    except Exception:
        logger.exception("Failed to get ESG profile for %s", facility_id)
        return format_agent_response(
            action_group, api_path, http_method, 500,
            {"error": "Internal error querying ESG data"},
        )

    if not profile:
        return format_agent_response(
            action_group, api_path, http_method, 404,
            {"error": f"No ESG profile found for operator '{facility_id}'"},
        )

    # Build response with dimension filtering
    esg_data: Dict[str, Any] = {"operator_id": facility_id}

    if requested_dimensions:
        for dim in requested_dimensions:
            fields = DIMENSION_FIELDS.get(dim, [])
            for f in fields:
                val = profile.get(f)
                if val is not None:
                    esg_data[f] = float(val)
                    esg_data[f"{f}_assessment"] = _assess_level(f, float(val))
    else:
        # Return all ESG fields
        for key in ("pue", "carbon_intensity", "renewable_pct", "water_usage",
                     "climate_risk_score", "green_bond_outstanding"):
            val = profile.get(key)
            if val is not None:
                esg_data[key] = float(val)
                if key in _BENCHMARKS:
                    esg_data[f"{key}_assessment"] = _assess_level(key, float(val))

    body: Dict[str, Any] = {
        "esg_profile": esg_data,
        "dimensions_requested": requested_dimensions or "all",
    }

    # Record trace
    latency_ms = (time.time() - start_time) * 1000
    try:
        trace_span(
            agent_name="esg-risk-agent",
            action="AssessESGRisk",
            input_data={"facility_id": facility_id, "dimensions": requested_dimensions},
            output_data={"fields_returned": list(esg_data.keys())},
            latency_ms=latency_ms,
            token_count=70,
        )
    except Exception:
        logger.warning("Failed to record Arize trace", exc_info=True)

    return format_agent_response(action_group, api_path, http_method, 200, body)
