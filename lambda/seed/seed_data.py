"""Seed all DynamoDB tables with mock data from DATA_MODEL.md.

Can be invoked as a Lambda function or run locally:
    python seed_data.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from decimal import Decimal
from typing import Any, Dict, List

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Table names
# ---------------------------------------------------------------------------
TABLE_OPERATORS: str = os.environ.get("TABLE_OPERATORS", "dcai-operators")
TABLE_METRICS: str = os.environ.get("TABLE_METRICS", "dcai-metrics")
TABLE_ESG: str = os.environ.get("TABLE_ESG", "dcai-esg-profiles")
TABLE_MARKET: str = os.environ.get("TABLE_MARKET", "dcai-market-data")
TABLE_SESSIONS: str = os.environ.get("TABLE_SESSIONS", "dcai-sessions")
TABLE_TRACES: str = os.environ.get("TABLE_TRACES", "dcai-traces")

_dynamodb: Any = None


def _get_dynamodb() -> Any:
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb")
    return _dynamodb


def _decimal(val: Any) -> Any:
    """Convert floats to Decimal for DynamoDB."""
    if isinstance(val, float):
        return Decimal(str(val))
    if isinstance(val, dict):
        return {k: _decimal(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_decimal(i) for i in val]
    return val


def _batch_write(table_name: str, items: List[Dict[str, Any]]) -> int:
    """Write items to a DynamoDB table using batch_writer."""
    table = _get_dynamodb().Table(table_name)
    count = 0
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=_decimal(item))
            count += 1
    logger.info("Seeded %d items to %s", count, table_name)
    return count


# ---------------------------------------------------------------------------
# Mock Data — Operators (Section 2.1 of DATA_MODEL.md)
# ---------------------------------------------------------------------------
OPERATORS: List[Dict[str, Any]] = [
    {"id": "op-001", "name": "Equinix Inc.",        "ticker": "EQIX", "moodys_rating": "A3",   "sector": "Data Center REIT", "hq": "US", "market_cap": 74200},
    {"id": "op-002", "name": "Digital Realty Trust", "ticker": "DLR",  "moodys_rating": "Baa2", "sector": "Data Center REIT", "hq": "US", "market_cap": 38500},
    {"id": "op-003", "name": "QTS Realty Trust",     "ticker": None,   "moodys_rating": "Ba2",  "sector": "Data Center",      "hq": "US", "market_cap": None},
    {"id": "op-004", "name": "CyrusOne LLC",         "ticker": None,   "moodys_rating": "Ba3",  "sector": "Data Center",      "hq": "US", "market_cap": None},
    {"id": "op-005", "name": "CoreSite Realty",      "ticker": "COR",  "moodys_rating": "Baa3", "sector": "Data Center REIT", "hq": "US", "market_cap": 8400},
    {"id": "op-006", "name": "Switch Inc.",          "ticker": "SWCH", "moodys_rating": "B1",   "sector": "Data Center",      "hq": "US", "market_cap": 7900},
]

# ---------------------------------------------------------------------------
# Mock Data — Markets (Section 2.2)
# ---------------------------------------------------------------------------
MARKETS: List[Dict[str, Any]] = [
    {"market_id": "mkt-nova", "region": "NA",   "market_name": "Northern Virginia", "total_capacity_mw": 2850, "absorption_rate": 410, "vacancy_rate": 0.03, "avg_price_per_kw": 120, "construction_pipeline_mw": 680, "yoy_growth": 0.18},
    {"market_id": "mkt-dfw",  "region": "NA",   "market_name": "Dallas / Ft Worth", "total_capacity_mw": 980,  "absorption_rate": 175, "vacancy_rate": 0.07, "avg_price_per_kw": 95,  "construction_pipeline_mw": 320, "yoy_growth": 0.22},
    {"market_id": "mkt-phx",  "region": "NA",   "market_name": "Phoenix",           "total_capacity_mw": 620,  "absorption_rate": 130, "vacancy_rate": 0.05, "avg_price_per_kw": 88,  "construction_pipeline_mw": 275, "yoy_growth": 0.29},
    {"market_id": "mkt-sin",  "region": "APAC", "market_name": "Singapore",         "total_capacity_mw": 410,  "absorption_rate": 55,  "vacancy_rate": 0.02, "avg_price_per_kw": 165, "construction_pipeline_mw": 80,  "yoy_growth": 0.08},
    {"market_id": "mkt-fra",  "region": "EMEA", "market_name": "Frankfurt",         "total_capacity_mw": 730,  "absorption_rate": 95,  "vacancy_rate": 0.04, "avg_price_per_kw": 140, "construction_pipeline_mw": 210, "yoy_growth": 0.14},
]

# ---------------------------------------------------------------------------
# Mock Data — Financial Metrics (Section 2.3)
# ---------------------------------------------------------------------------
FINANCIAL_METRICS: List[Dict[str, Any]] = [
    {"operator_id": "op-001", "period": "2024-Q1", "revenue": 2012, "ebitda": 952,  "ffo": 820, "debt_to_ebitda": 3.8, "interest_coverage": 5.1, "occupancy_rate": 0.92, "capex": 710, "liquidity": 4500},
    {"operator_id": "op-001", "period": "2024-Q2", "revenue": 2085, "ebitda": 991,  "ffo": 855, "debt_to_ebitda": 3.7, "interest_coverage": 5.3, "occupancy_rate": 0.93, "capex": 740, "liquidity": 4650},
    {"operator_id": "op-002", "period": "2024-Q1", "revenue": 1350, "ebitda": 685,  "ffo": 570, "debt_to_ebitda": 5.9, "interest_coverage": 3.4, "occupancy_rate": 0.85, "capex": 520, "liquidity": 2800},
    {"operator_id": "op-002", "period": "2024-Q2", "revenue": 1385, "ebitda": 710,  "ffo": 592, "debt_to_ebitda": 5.7, "interest_coverage": 3.5, "occupancy_rate": 0.86, "capex": 545, "liquidity": 2950},
    {"operator_id": "op-003", "period": "2024-Q1", "revenue": 420,  "ebitda": 195,  "ffo": 160, "debt_to_ebitda": 6.8, "interest_coverage": 2.6, "occupancy_rate": 0.88, "capex": 310, "liquidity": 900},
    {"operator_id": "op-003", "period": "2024-Q2", "revenue": 445,  "ebitda": 210,  "ffo": 172, "debt_to_ebitda": 6.5, "interest_coverage": 2.7, "occupancy_rate": 0.89, "capex": 325, "liquidity": 950},
    {"operator_id": "op-004", "period": "2024-Q1", "revenue": 380,  "ebitda": 175,  "ffo": 140, "debt_to_ebitda": 7.1, "interest_coverage": 2.3, "occupancy_rate": 0.82, "capex": 280, "liquidity": 650},
    {"operator_id": "op-004", "period": "2024-Q2", "revenue": 395,  "ebitda": 184,  "ffo": 148, "debt_to_ebitda": 6.9, "interest_coverage": 2.4, "occupancy_rate": 0.83, "capex": 295, "liquidity": 700},
    {"operator_id": "op-005", "period": "2024-Q1", "revenue": 185,  "ebitda": 102,  "ffo": 88,  "debt_to_ebitda": 4.2, "interest_coverage": 4.0, "occupancy_rate": 0.94, "capex": 95,  "liquidity": 520},
    {"operator_id": "op-005", "period": "2024-Q2", "revenue": 192,  "ebitda": 107,  "ffo": 92,  "debt_to_ebitda": 4.1, "interest_coverage": 4.1, "occupancy_rate": 0.95, "capex": 100, "liquidity": 545},
    {"operator_id": "op-006", "period": "2024-Q1", "revenue": 165,  "ebitda": 78,   "ffo": 62,  "debt_to_ebitda": 5.5, "interest_coverage": 2.9, "occupancy_rate": 0.80, "capex": 220, "liquidity": 380},
    {"operator_id": "op-006", "period": "2024-Q2", "revenue": 175,  "ebitda": 84,   "ffo": 67,  "debt_to_ebitda": 5.3, "interest_coverage": 3.0, "occupancy_rate": 0.81, "capex": 235, "liquidity": 410},
]

# ---------------------------------------------------------------------------
# Mock Data — ESG Profiles (Section 2.4)
# ---------------------------------------------------------------------------
ESG_PROFILES: List[Dict[str, Any]] = [
    {"operator_id": "op-001", "pue": 1.25, "carbon_intensity": 210, "renewable_pct": 0.96, "water_usage": 1.1, "climate_risk_score": 82, "green_bond_outstanding": 3750},
    {"operator_id": "op-002", "pue": 1.35, "carbon_intensity": 290, "renewable_pct": 0.68, "water_usage": 1.4, "climate_risk_score": 71, "green_bond_outstanding": 2100},
    {"operator_id": "op-003", "pue": 1.40, "carbon_intensity": 340, "renewable_pct": 0.52, "water_usage": 1.6, "climate_risk_score": 63, "green_bond_outstanding": 500},
    {"operator_id": "op-004", "pue": 1.38, "carbon_intensity": 310, "renewable_pct": 0.45, "water_usage": 1.5, "climate_risk_score": 58, "green_bond_outstanding": 0},
    {"operator_id": "op-005", "pue": 1.30, "carbon_intensity": 250, "renewable_pct": 0.72, "water_usage": 1.2, "climate_risk_score": 75, "green_bond_outstanding": 800},
    {"operator_id": "op-006", "pue": 1.18, "carbon_intensity": 105, "renewable_pct": 1.00, "water_usage": 0.9, "climate_risk_score": 88, "green_bond_outstanding": 1200},
]

# ---------------------------------------------------------------------------
# Mock Data — Credit Ratings (derived from operators + DATA_MODEL Section 1.2)
# ---------------------------------------------------------------------------
CREDIT_RATINGS: List[Dict[str, Any]] = [
    {
        "operator_id": "op-001",
        "rating": "A3",
        "outlook": "STA",
        "watch_status": None,
        "rating_date": "2024-03-15",
        "previous_rating": "A3",
        "analyst": "Michael Chen",
    },
    {
        "operator_id": "op-002",
        "rating": "Baa2",
        "outlook": "STA",
        "watch_status": None,
        "rating_date": "2024-02-22",
        "previous_rating": "Baa2",
        "analyst": "Sarah Williams",
    },
    {
        "operator_id": "op-003",
        "rating": "Ba2",
        "outlook": "POS",
        "watch_status": "UPG",
        "rating_date": "2024-01-18",
        "previous_rating": "Ba3",
        "analyst": "David Park",
    },
    {
        "operator_id": "op-004",
        "rating": "Ba3",
        "outlook": "NEG",
        "watch_status": "DNG",
        "rating_date": "2024-04-05",
        "previous_rating": "Ba2",
        "analyst": "Jennifer Liu",
    },
    {
        "operator_id": "op-005",
        "rating": "Baa3",
        "outlook": "STA",
        "watch_status": None,
        "rating_date": "2024-03-01",
        "previous_rating": "Baa3",
        "analyst": "Robert Martinez",
    },
    {
        "operator_id": "op-006",
        "rating": "B1",
        "outlook": "STA",
        "watch_status": None,
        "rating_date": "2024-02-10",
        "previous_rating": "B1",
        "analyst": "Emily Zhao",
    },
]


# ---------------------------------------------------------------------------
# Seeder
# ---------------------------------------------------------------------------

def seed_all() -> Dict[str, int]:
    """Seed all DynamoDB tables and return counts."""
    results: Dict[str, int] = {}

    # Operators — filter out None values for DynamoDB
    cleaned_operators = []
    for op in OPERATORS:
        cleaned = {k: v for k, v in op.items() if v is not None}
        cleaned_operators.append(cleaned)
    results["operators"] = _batch_write(TABLE_OPERATORS, cleaned_operators)

    # Markets
    results["markets"] = _batch_write(TABLE_MARKET, MARKETS)

    # Financial Metrics
    results["financial_metrics"] = _batch_write(TABLE_METRICS, FINANCIAL_METRICS)

    # ESG Profiles
    results["esg_profiles"] = _batch_write(TABLE_ESG, ESG_PROFILES)

    # Credit Ratings — stored in operators table with composite key,
    # or in a separate approach: store as attributes on operator items.
    # We'll store them as separate items in operators table with id = "cr-{operator_id}"
    credit_items = []
    for cr in CREDIT_RATINGS:
        item = {**cr, "id": f"cr-{cr['operator_id']}", "record_type": "credit_rating"}
        # Remove None watch_status for DynamoDB
        if item.get("watch_status") is None:
            del item["watch_status"]
        if item.get("previous_rating") is None:
            del item["previous_rating"]
        credit_items.append(item)
    results["credit_ratings"] = _batch_write(TABLE_OPERATORS, credit_items)

    return results


# ---------------------------------------------------------------------------
# Lambda handler
# ---------------------------------------------------------------------------

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for seeding DynamoDB tables."""
    logger.info("Seed data handler invoked")

    try:
        results = seed_all()
        total = sum(results.values())
        logger.info("Seeding complete: %d total records", total)
        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "success",
                "message": f"Seeded {total} records across all tables",
                "details": results,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }),
        }
    except Exception as exc:
        logger.exception("Seed data failed")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "status": "error",
                "error": str(exc),
            }),
        }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )

    print("Seeding DynamoDB tables with mock data...")
    print(f"  TABLE_OPERATORS = {TABLE_OPERATORS}")
    print(f"  TABLE_METRICS   = {TABLE_METRICS}")
    print(f"  TABLE_ESG       = {TABLE_ESG}")
    print(f"  TABLE_MARKET    = {TABLE_MARKET}")
    print()

    try:
        results = seed_all()
        total = sum(results.values())
        print(f"\nSeeding complete! {total} total records written:")
        for table, count in results.items():
            print(f"  {table}: {count} records")
    except Exception as exc:
        print(f"\nSeeding failed: {exc}", file=sys.stderr)
        sys.exit(1)
