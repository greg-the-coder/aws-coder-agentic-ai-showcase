"""Mock Arize service — single Lambda handling all Arize mock routes.

Routes:
    POST /mock/arize/traces            — Accept trace span, store to DynamoDB
    GET  /mock/arize/traces/{trace_id} — Return trace details
    GET  /mock/arize/evaluations       — Return mock evaluation results
    GET  /mock/arize/metrics           — Return aggregated metrics
    GET  /mock/arize/dashboard         — Return dashboard summary
"""

from __future__ import annotations

import json
import logging
import math
import os
import random
import re
import time
import uuid
from typing import Any, Dict, List, Optional

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TABLE_TRACES: str = os.environ.get("TABLE_TRACES", "dcai-traces")
METRIC_NAMESPACE: str = "DCInvestAgent"

_dynamodb: Any = None
_cloudwatch: Any = None


def _get_dynamodb() -> Any:
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb")
    return _dynamodb


def _get_cloudwatch() -> Any:
    global _cloudwatch
    if _cloudwatch is None:
        _cloudwatch = boto3.client("cloudwatch")
    return _cloudwatch


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _request_id() -> str:
    return f"arize-{uuid.uuid4().hex[:12]}"


def _api_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "X-Arize-Request-Id": _request_id(),
        },
        "body": json.dumps(body, default=str),
    }


# ---------------------------------------------------------------------------
# POST /mock/arize/traces
# ---------------------------------------------------------------------------

def _handle_post_trace(body: Dict[str, Any]) -> Dict[str, Any]:
    trace_id = body.get("trace_id", f"trace-{uuid.uuid4().hex[:16]}")
    body["trace_id"] = trace_id
    body.setdefault("timestamp", _ts())

    # Store to DynamoDB
    try:
        table = _get_dynamodb().Table(TABLE_TRACES)
        table.put_item(Item=body)
        logger.info("Trace stored: %s", trace_id)
    except Exception:
        logger.exception("Failed to store trace %s", trace_id)
        return _api_response(500, {"error": "Failed to store trace"})

    # Publish CloudWatch metrics
    try:
        latency = float(body.get("latency_ms", 0))
        tokens = int(body.get("token_count", 0))
        cw = _get_cloudwatch()
        cw.put_metric_data(
            Namespace=METRIC_NAMESPACE,
            MetricData=[
                {"MetricName": "TraceLatency", "Value": latency, "Unit": "Milliseconds"},
                {"MetricName": "TokenCount", "Value": float(tokens), "Unit": "Count"},
            ],
        )
    except Exception:
        logger.warning("Failed to publish CW metrics", exc_info=True)

    return _api_response(200, {
        "trace_id": trace_id,
        "status": "accepted",
        "timestamp": body["timestamp"],
    })


# ---------------------------------------------------------------------------
# GET /mock/arize/traces/{trace_id}
# ---------------------------------------------------------------------------

def _handle_get_trace(trace_id: str) -> Dict[str, Any]:
    try:
        table = _get_dynamodb().Table(TABLE_TRACES)
        resp = table.get_item(Key={"trace_id": trace_id})
        item = resp.get("Item")
    except Exception:
        logger.exception("Failed to get trace %s", trace_id)
        return _api_response(500, {"error": "Internal error"})

    if not item:
        return _api_response(404, {"error": f"Trace '{trace_id}' not found"})

    return _api_response(200, {
        "trace": item,
        "metadata": {"request_id": _request_id(), "timestamp": _ts()},
    })


# ---------------------------------------------------------------------------
# GET /mock/arize/evaluations
# ---------------------------------------------------------------------------

def _handle_evaluations() -> Dict[str, Any]:
    evaluations = {
        "relevance": {
            "score": round(random.uniform(0.75, 0.95), 3),
            "threshold": 0.7,
            "status": "passing",
            "model": "mistral-small-2402",
            "samples_evaluated": 150,
            "last_evaluated": _ts(),
        },
        "faithfulness": {
            "score": round(random.uniform(0.85, 0.98), 3),
            "threshold": 0.85,
            "status": "passing",
            "model": "mistral-large-2407",
            "samples_evaluated": 150,
            "last_evaluated": _ts(),
        },
        "toxicity": {
            "violations": 0,
            "threshold": 0,
            "status": "passing",
            "model": "bedrock-guardrails",
            "samples_evaluated": 150,
            "last_evaluated": _ts(),
        },
        "latency_p95": {
            "value_ms": round(random.uniform(3500, 8500), 0),
            "threshold_ms": 10000,
            "status": "passing",
            "last_evaluated": _ts(),
        },
    }
    return _api_response(200, {
        "evaluations": evaluations,
        "summary": {
            "total_evals": 4,
            "passing": 4,
            "failing": 0,
            "evaluation_window": "rolling_1h",
        },
        "metadata": {"request_id": _request_id(), "timestamp": _ts()},
    })


# ---------------------------------------------------------------------------
# GET /mock/arize/metrics
# ---------------------------------------------------------------------------

def _handle_metrics() -> Dict[str, Any]:
    metrics = {
        "latency": {
            "p50_ms": round(random.uniform(1200, 2500), 0),
            "p95_ms": round(random.uniform(4000, 7500), 0),
            "p99_ms": round(random.uniform(8000, 12000), 0),
            "mean_ms": round(random.uniform(2000, 3500), 0),
        },
        "token_usage": {
            "avg_input_tokens": random.randint(80, 200),
            "avg_output_tokens": random.randint(150, 400),
            "total_tokens_24h": random.randint(50000, 200000),
        },
        "throughput": {
            "total_traces_24h": random.randint(200, 800),
            "traces_per_minute": round(random.uniform(0.5, 5.0), 2),
        },
        "quality": {
            "accuracy_score": round(random.uniform(0.88, 0.96), 3),
            "hallucination_rate": round(random.uniform(0.01, 0.05), 3),
        },
        "cost": {
            "estimated_cost_24h_usd": round(random.uniform(2.50, 15.00), 2),
            "avg_cost_per_query_usd": round(random.uniform(0.003, 0.015), 4),
        },
    }
    return _api_response(200, {
        "metrics": metrics,
        "period": "last_24h",
        "metadata": {"request_id": _request_id(), "timestamp": _ts()},
    })


# ---------------------------------------------------------------------------
# GET /mock/arize/dashboard
# ---------------------------------------------------------------------------

def _handle_dashboard() -> Dict[str, Any]:
    # Traces over time (last 6 hours, hourly buckets)
    traces_over_time: List[Dict[str, Any]] = []
    base_time = int(time.time()) - 6 * 3600
    for i in range(6):
        hour_ts = time.strftime(
            "%Y-%m-%dT%H:00:00Z", time.gmtime(base_time + i * 3600)
        )
        traces_over_time.append({
            "timestamp": hour_ts,
            "trace_count": random.randint(20, 120),
            "avg_latency_ms": round(random.uniform(1500, 4000), 0),
            "error_count": random.randint(0, 3),
        })

    dashboard = {
        "traces_over_time": traces_over_time,
        "model_performance": {
            "mistral-large-2407": {
                "total_invocations": random.randint(300, 600),
                "avg_latency_ms": round(random.uniform(2500, 5000), 0),
                "error_rate": round(random.uniform(0.001, 0.02), 4),
            },
            "mistral-small-2402": {
                "total_invocations": random.randint(100, 250),
                "avg_latency_ms": round(random.uniform(800, 2000), 0),
                "error_rate": round(random.uniform(0.001, 0.015), 4),
            },
        },
        "alerts": {
            "active": 0,
            "resolved_24h": random.randint(0, 3),
            "rules_configured": 3,
            "rules": [
                {"name": "embedding_drift", "status": "ok", "threshold": "cosine > 0.15"},
                {"name": "eval_regression", "status": "ok", "threshold": "faithfulness < 0.80"},
                {"name": "error_rate", "status": "ok", "threshold": "5xx > 2% over 5min"},
            ],
        },
        "embedding_drift": {
            "status": "stable",
            "current_distance": round(random.uniform(0.02, 0.10), 3),
            "threshold": 0.15,
            "baseline_date": "2024-06-01",
            "last_checked": _ts(),
        },
    }
    return _api_response(200, {
        "dashboard": dashboard,
        "metadata": {"request_id": _request_id(), "timestamp": _ts()},
    })


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

def _parse_route(raw_path: str, method: str) -> tuple[str, Optional[str]]:
    """Determine route and extract path parameters."""
    path = raw_path.rstrip("/")

    if method == "POST" and path.endswith("/traces"):
        return "post_trace", None

    m = re.match(r".*/traces/([^/]+)$", path)
    if m and method == "GET":
        return "get_trace", m.group(1)

    if path.endswith("/evaluations"):
        return "evaluations", None

    if path.endswith("/metrics"):
        return "metrics", None

    if path.endswith("/dashboard"):
        return "dashboard", None

    return "unknown", None


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for Mock Arize service."""
    logger.info("Mock Arize invoked: %s", json.dumps(event, default=str))

    http_method: str = event.get("httpMethod", event.get("requestContext", {}).get("http", {}).get("method", "GET"))
    raw_path: str = event.get("path", event.get("rawPath", ""))

    body: Dict[str, Any] = {}
    raw_body = event.get("body", "")
    if raw_body:
        try:
            body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
        except json.JSONDecodeError:
            body = {}

    route, param = _parse_route(raw_path, http_method)

    if route == "post_trace":
        return _handle_post_trace(body)
    elif route == "get_trace" and param:
        return _handle_get_trace(param)
    elif route == "evaluations":
        return _handle_evaluations()
    elif route == "metrics":
        return _handle_metrics()
    elif route == "dashboard":
        return _handle_dashboard()
    else:
        return _api_response(404, {
            "error": "Route not found",
            "path": raw_path,
            "method": http_method,
        })
