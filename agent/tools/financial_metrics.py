"""GetFinancialMetrics — Strands tool implementation."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from boto3.dynamodb.conditions import Key
from strands import tool

from agent.db import TABLE_METRICS, query_items

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


@tool
def get_financial_metrics(entity_id: str, period: str = "latest", metrics: str = "") -> dict:
    """Get financial metrics for a data center operator.

    Args:
        entity_id: Operator ID (e.g., "op-001")
        period: Time period filter - "latest", "trailing_4q", "yoy", or specific period like "Q2-2024"
        metrics: Comma-separated list of metrics to return (e.g., "debt_to_ebitda,revenue"). Empty = all.

    Returns:
        Financial metrics including debt/EBITDA, interest coverage, revenue, EBITDA, FFO, occupancy rate.
    """
    if not entity_id:
        return {"error": "entity_id parameter is required"}

    requested_metrics: Optional[List[str]] = None
    if metrics:
        requested_metrics = [m.strip() for m in metrics.split(",")]

    # Query all metrics for this operator, sorted descending by period
    try:
        items = query_items(
            TABLE_METRICS,
            Key("operator_id").eq(entity_id),
            scan_index_forward=False,
        )
    except Exception:
        logger.exception("Failed to query metrics for %s", entity_id)
        return {"error": "Internal error querying financial metrics"}

    if not items:
        return {"error": f"No financial metrics found for operator '{entity_id}'"}

    # Apply period filter
    if period == "latest":
        result = _filter_metrics(items[0], requested_metrics)
        return {"metrics": result}

    elif period == "trailing_4q":
        trailing = items[:4]
        return {
            "metrics": [_filter_metrics(item, requested_metrics) for item in trailing],
            "period_count": len(trailing),
        }

    elif period == "yoy":
        if len(items) >= 2:
            return _compute_yoy(items[0], items[-1])
        else:
            body = _filter_metrics(items[0], requested_metrics)
            body["note"] = "Insufficient data for YoY comparison"
            return body

    else:
        # Treat as specific period string
        matching = [i for i in items if i.get("period") == period]
        if matching:
            return {"metrics": _filter_metrics(matching[0], requested_metrics)}
        else:
            return {"error": f"No metrics found for period '{period}'"}
