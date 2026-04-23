"""GetFinancialMetrics — Bedrock Agent Action Group handler.

Queries the ``dcai-metrics`` table by operator_id and period.  Supports
metric filtering and period modes: latest, trailing_4q, yoy.
"""

from __future__ import annotations

import json
import logging
import os
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional

from boto3.dynamodb.conditions import Key

from shared.arize_trace import trace_span
from shared.db import TABLE_METRICS, query_items
from shared.response import format_agent_response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Supported metric fields
SUPPORTED_METRICS = {
    "debt_to_ebitda",
    "interest_coverage",
    "occupancy_rate",
    "ffo",
    "revenue",
    "ebitda",
    "capex",
    "liquidity",
}


def _decimal_default(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return int(obj) if obj == int(obj) else float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _filter_metrics(item: Dict[str, Any], requested: Optional[List[str]]) -> Dict[str, Any]:
    """Return only the requested metric fields from a metrics item."""
    if not requested:
        return item
    result: Dict[str, Any] = {
        "operator_id": item["operator_id"],
        "period": item["period"],
    }
    for m in requested:
        key = m.strip().lower()
        if key in item:
            result[key] = item[key]
    return result


def _compute_yoy(current: Dict[str, Any], previous: Dict[str, Any]) -> Dict[str, Any]:
    """Compute year-over-year change between two periods."""
    yoy: Dict[str, Any] = {
        "operator_id": current["operator_id"],
        "current_period": current["period"],
        "comparison_period": previous["period"],
        "changes": {},
    }
    for key in SUPPORTED_METRICS:
        cur_val = current.get(key)
        prev_val = previous.get(key)
        if cur_val is not None and prev_val is not None:
            cur_f = float(cur_val)
            prev_f = float(prev_val)
            if prev_f != 0:
                change_pct = round((cur_f - prev_f) / prev_f * 100, 2)
            else:
                change_pct = 0.0
            yoy["changes"][key] = {
                "current": cur_f,
                "previous": prev_f,
                "change_pct": change_pct,
            }
    return yoy


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Bedrock Agent Action Group handler for GetFinancialMetrics."""
    start_time = time.time()
    logger.info("GetFinancialMetrics invoked: %s", json.dumps(event, default=str))

    action_group: str = event.get("actionGroup", "")
    api_path: str = event.get("apiPath", "/financial-metrics")
    http_method: str = event.get("httpMethod", "GET")

    # Extract parameters
    parameters: Dict[str, str] = {
        p["name"]: p["value"] for p in event.get("parameters", [])
    }
    entity_id: str = parameters.get("entity_id", "")
    period_filter: str = parameters.get("period", "latest")
    metrics_param: str = parameters.get("metrics", "")

    if not entity_id:
        return format_agent_response(
            action_group, api_path, http_method, 400,
            {"error": "entity_id parameter is required"},
        )

    requested_metrics: Optional[List[str]] = None
    if metrics_param:
        requested_metrics = [m.strip() for m in metrics_param.split(",")]

    # Query all metrics for this operator, sorted descending by period
    try:
        items = query_items(
            TABLE_METRICS,
            Key("operator_id").eq(entity_id),
            scan_index_forward=False,
        )
    except Exception:
        logger.exception("Failed to query metrics for %s", entity_id)
        return format_agent_response(
            action_group, api_path, http_method, 500,
            {"error": "Internal error querying financial metrics"},
        )

    if not items:
        return format_agent_response(
            action_group, api_path, http_method, 404,
            {"error": f"No financial metrics found for operator '{entity_id}'"},
        )

    # Apply period filter
    if period_filter == "latest":
        # Return most recent period only
        result = _filter_metrics(items[0], requested_metrics)
        body: Any = {"metrics": result}

    elif period_filter == "trailing_4q":
        # Return up to 4 most recent quarters
        trailing = items[:4]
        body = {
            "metrics": [_filter_metrics(item, requested_metrics) for item in trailing],
            "period_count": len(trailing),
        }

    elif period_filter == "yoy":
        # Compare latest vs same quarter prior year (or earliest available)
        if len(items) >= 2:
            body = _compute_yoy(items[0], items[-1])
        else:
            body = _filter_metrics(items[0], requested_metrics)
            body["note"] = "Insufficient data for YoY comparison"

    else:
        # Treat as specific period string
        matching = [i for i in items if i.get("period") == period_filter]
        if matching:
            body = {"metrics": _filter_metrics(matching[0], requested_metrics)}
        else:
            return format_agent_response(
                action_group, api_path, http_method, 404,
                {"error": f"No metrics found for period '{period_filter}'"},
            )

    # Record trace
    latency_ms = (time.time() - start_time) * 1000
    try:
        trace_span(
            agent_name="credit-risk-agent",
            action="GetFinancialMetrics",
            input_data={"entity_id": entity_id, "period": period_filter},
            output_data={"record_count": len(items)},
            latency_ms=latency_ms,
            token_count=120,
        )
    except Exception:
        logger.warning("Failed to record Arize trace", exc_info=True)

    return format_agent_response(action_group, api_path, http_method, 200, body)
