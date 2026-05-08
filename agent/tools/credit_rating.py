"""LookupCreditRating — Strands tool implementation."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from strands import tool

from agent.db import TABLE_OPERATORS, scan_table

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Mock PD/LGD mapping by rating grade
# ---------------------------------------------------------------------------
_PD_LGD_MAP: Dict[str, Dict[str, Optional[float]]] = {
    "Aaa": {"pd": 0.0001, "lgd": 0.35},
    "Aa1": {"pd": 0.0002, "lgd": 0.35},
    "Aa2": {"pd": 0.0003, "lgd": 0.35},
    "Aa3": {"pd": 0.0005, "lgd": 0.35},
    "A1":  {"pd": 0.0008, "lgd": 0.40},
    "A2":  {"pd": 0.0012, "lgd": 0.40},
    "A3":  {"pd": 0.0018, "lgd": 0.40},
    "Baa1": {"pd": 0.0035, "lgd": 0.45},
    "Baa2": {"pd": 0.0055, "lgd": 0.45},
    "Baa3": {"pd": 0.0090, "lgd": 0.45},
    "Ba1":  {"pd": 0.0160, "lgd": 0.50},
    "Ba2":  {"pd": 0.0250, "lgd": 0.50},
    "Ba3":  {"pd": 0.0400, "lgd": 0.50},
    "B1":   {"pd": 0.0650, "lgd": 0.55},
    "B2":   {"pd": 0.0980, "lgd": 0.55},
    "B3":   {"pd": 0.1400, "lgd": 0.55},
    "Caa1": {"pd": 0.1900, "lgd": 0.60},
    "Caa2": {"pd": 0.2500, "lgd": 0.60},
    "Caa3": {"pd": 0.3500, "lgd": 0.65},
    "Ca":   {"pd": 0.5000, "lgd": 0.70},
    "C":    {"pd": 0.7500, "lgd": 0.80},
    "WR":   {"pd": None, "lgd": None},
    "NR":   {"pd": None, "lgd": None},
}

# Mock outlook mapping per operator
_OUTLOOK_MAP: Dict[str, str] = {
    "op-001": "STA",
    "op-002": "STA",
    "op-003": "POS",
    "op-004": "NEG",
    "op-005": "STA",
    "op-006": "STA",
}

# Mock last action dates
_ACTION_DATE_MAP: Dict[str, str] = {
    "op-001": "2024-03-15",
    "op-002": "2024-02-22",
    "op-003": "2024-01-18",
    "op-004": "2024-04-05",
    "op-005": "2024-03-01",
    "op-006": "2024-02-10",
}


def _find_operator(entity_name: str) -> Optional[Dict[str, Any]]:
    """Find an operator by name or ticker (case-insensitive scan)."""
    search = entity_name.strip().lower()
    operators = scan_table(TABLE_OPERATORS)
    for op in operators:
        if op.get("name", "").lower() == search:
            return op
        if op.get("ticker") and op["ticker"].lower() == search:
            return op
        # Partial match
        if search in op.get("name", "").lower():
            return op
    return None


@tool
def lookup_credit_rating(entity_name: str, rating_type: str = "issuer") -> dict:
    """Retrieve Moody's credit rating for a data center operator.

    Args:
        entity_name: Name or ticker of the data center operator (e.g., "Equinix", "EQIX")
        rating_type: Type of rating to look up - "issuer" or "facility". Defaults to "issuer".

    Returns:
        Credit rating details including Moody's rating, outlook, probability of default, and loss given default.
    """
    if not entity_name:
        return {"error": "entity_name parameter is required"}

    operator = _find_operator(entity_name)

    if not operator:
        return {"error": f"No operator found matching '{entity_name}'"}

    rating = operator.get("moodys_rating", "NR")
    pd_lgd = _PD_LGD_MAP.get(rating, {"pd": None, "lgd": None})
    op_id = operator["id"]

    return {
        "entity": operator["name"],
        "operator_id": op_id,
        "ticker": operator.get("ticker"),
        "rating": rating,
        "rating_type": rating_type,
        "outlook": _OUTLOOK_MAP.get(op_id, "STA"),
        "last_action_date": _ACTION_DATE_MAP.get(op_id, "2024-01-01"),
        "probability_of_default": pd_lgd["pd"],
        "loss_given_default": pd_lgd["lgd"],
        "sector": operator.get("sector", ""),
    }
