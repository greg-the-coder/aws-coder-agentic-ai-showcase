"""QueryMarketData — Strands tool implementation."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from strands import tool

from agent.db import TABLE_MARKET, scan_table

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


@tool
def query_market_data(metro: str, metric_type: str = "", date_range: str = "") -> dict:
    """Query data center market supply/demand data by metropolitan area.

    Args:
        metro: Metropolitan area or region name (e.g., "Northern Virginia", "Dallas", "APAC")
        metric_type: Optional filter - "supply", "demand", "vacancy", "absorption", "pricing", or "construction_pipeline"
        date_range: Optional date range filter (e.g., "2024-Q1")

    Returns:
        Market data including capacity, vacancy rates, absorption, pricing, and construction pipeline.
    """
    if not metro:
        return {"error": "metro parameter is required"}

    # Scan and filter (small table, scan is acceptable)
    try:
        all_markets = scan_table(TABLE_MARKET)
    except Exception:
        logger.exception("Failed to scan market data table")
        return {"error": "Internal error querying market data"}

    matched = [m for m in all_markets if _match_market(m, metro)]

    if not matched:
        return {"error": f"No market data found for '{metro}'"}

    # Apply metric_type filter
    mt = metric_type if metric_type else None
    results = [_filter_by_metric_type(m, mt) for m in matched]

    return {
        "markets": results,
        "count": len(results),
        "query": {
            "metro": metro,
            "metric_type": metric_type or None,
            "date_range": date_range or None,
        },
    }
