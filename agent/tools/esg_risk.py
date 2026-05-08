"""AssessESGRisk — Strands tool implementation."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from strands import tool

from agent.db import TABLE_ESG, get_item

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


@tool
def assess_esg_risk(facility_id: str, dimensions: str = "") -> dict:
    """Assess ESG risk profile for a data center operator.

    Args:
        facility_id: Operator ID (e.g., "op-001")
        dimensions: Comma-separated ESG dimensions to assess - "pue", "carbon", "water", "climate_physical", "climate_transition". Empty = all.

    Returns:
        ESG profile including PUE, carbon intensity, renewable percentage, water usage, climate risk score, and qualitative assessments.
    """
    if not facility_id:
        return {"error": "facility_id (operator_id) parameter is required"}

    # Parse dimensions
    requested_dimensions: Optional[List[str]] = None
    if dimensions:
        requested_dimensions = [d.strip() for d in dimensions.split(",")]

    # Query ESG profile
    try:
        profile = get_item(TABLE_ESG, {"operator_id": facility_id})
    except Exception:
        logger.exception("Failed to get ESG profile for %s", facility_id)
        return {"error": "Internal error querying ESG data"}

    if not profile:
        return {"error": f"No ESG profile found for operator '{facility_id}'"}

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

    return {
        "esg_profile": esg_data,
        "dimensions_requested": requested_dimensions or "all",
    }
