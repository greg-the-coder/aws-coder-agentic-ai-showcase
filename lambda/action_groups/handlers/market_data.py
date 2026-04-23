"""QueryMarketData — Bedrock Agent Action Group handler.

Queries the ``dcai-market-data`` table by metro or region.  Returns supply,
demand, vacancy, absorption, pricing, and construction pipeline data.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from boto3.dynamodb.conditions import Attr, Key

from shared.arize_trace import trace_span
from shared.db import TABLE_MARKET, scan_table
from shared.response import format_agent_response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Supported metric type filters
METRIC_TYPE_FIELDS: Dict[str, List[str]] = {
    "supply": ["total_capacity_mw", "construction_pipeline_mw", "yoy_growth"],
    "demand": ["absorption_rate", "yoy_growth"],
    "vacancy": ["vacancy_rate"],
    "absorption": ["absorption_rate"],
    "pricing": ["avg_price_per_kw"],
    "construction_pipeline": ["construction_pipeline_mw"],
}


def _match_market(item: Dict[str, Any], search: str) -> bool:
    """Check if a market record matches the search term (metro or region)."""
    s = search.strip().lower()
    name = item.get("market_name", "").lower()
    market_id = item.get("market_id", "").lower()
    region = item.get("region", "").lower()
    return s in name or s == market_id or s == region or s in market_id


def _filter_by_metric_type(
    item: Dict[str, Any], metric_type: Optional[str]
) -> Dict[str, Any]:
    """Return only fields relevant to the requested metric_type."""
    if not metric_type or metric_type not in METRIC_TYPE_FIELDS:
        return item

    fields = METRIC_TYPE_FIELDS[metric_type]
    result: Dict[str, Any] = {
        "market_id": item["market_id"],
        "market_name": item.get("market_name", ""),
        "region": item.get("region", ""),
    }
    for f in fields:
        if f in item:
            result[f] = item[f]
    return result


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Bedrock Agent Action Group handler for QueryMarketData."""
    start_time = time.time()
    logger.info("QueryMarketData invoked: %s", json.dumps(event, default=str))

    action_group: str = event.get("actionGroup", "")
    api_path: str = event.get("apiPath", "/market-data")
    http_method: str = event.get("httpMethod", "GET")

    # Extract parameters
    parameters: Dict[str, str] = {
        p["name"]: p["value"] for p in event.get("parameters", [])
    }
    metro: str = parameters.get("metro", "")
    metric_type: Optional[str] = parameters.get("metric_type")
    date_range: Optional[str] = parameters.get("date_range")

    if not metro:
        return format_agent_response(
            action_group, api_path, http_method, 400,
            {"error": "metro parameter is required"},
        )

    # Scan and filter (small table, scan is acceptable)
    try:
        all_markets = scan_table(TABLE_MARKET)
    except Exception:
        logger.exception("Failed to scan market data table")
        return format_agent_response(
            action_group, api_path, http_method, 500,
            {"error": "Internal error querying market data"},
        )

    matched = [m for m in all_markets if _match_market(m, metro)]

    if not matched:
        return format_agent_response(
            action_group, api_path, http_method, 404,
            {"error": f"No market data found for '{metro}'"},
        )

    # Apply metric_type filter
    results = [_filter_by_metric_type(m, metric_type) for m in matched]

    body: Dict[str, Any] = {
        "markets": results,
        "count": len(results),
        "query": {
            "metro": metro,
            "metric_type": metric_type,
            "date_range": date_range,
        },
    }

    # Record trace
    latency_ms = (time.time() - start_time) * 1000
    try:
        trace_span(
            agent_name="market-analytics-agent",
            action="QueryMarketData",
            input_data={"metro": metro, "metric_type": metric_type},
            output_data={"result_count": len(results)},
            latency_ms=latency_ms,
            token_count=95,
        )
    except Exception:
        logger.warning("Failed to record Arize trace", exc_info=True)

    return format_agent_response(action_group, api_path, http_method, 200, body)
