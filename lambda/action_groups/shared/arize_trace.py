"""Mock Arize trace helper for Data Center Investments Agent.

Sends trace spans to the mock Arize endpoint or writes directly to
the DynamoDB traces table.  Publishes CloudWatch custom metrics for
latency and token usage.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from typing import Any, Dict, Optional

import boto3

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ARIZE_ENDPOINT: str = os.environ.get("ARIZE_ENDPOINT", "")
TABLE_TRACES: str = os.environ.get("TABLE_TRACES", "dcai-traces")
METRIC_NAMESPACE: str = "DCInvestAgent"

# ---------------------------------------------------------------------------
# Shared clients (lazy)
# ---------------------------------------------------------------------------
_dynamodb: Any = None
_cloudwatch: Any = None
_http_client: Any = None


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


# ---------------------------------------------------------------------------
# ID generators
# ---------------------------------------------------------------------------

def _generate_trace_id() -> str:
    return f"trace-{uuid.uuid4().hex[:16]}"


def _generate_correlation_id() -> str:
    return f"corr-{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# CloudWatch metric publishing
# ---------------------------------------------------------------------------

def _publish_metrics(latency_ms: float, token_count: int) -> None:
    """Publish custom CloudWatch metrics for trace latency and token count."""
    try:
        cw = _get_cloudwatch()
        cw.put_metric_data(
            Namespace=METRIC_NAMESPACE,
            MetricData=[
                {
                    "MetricName": "TraceLatency",
                    "Value": latency_ms,
                    "Unit": "Milliseconds",
                },
                {
                    "MetricName": "TokenCount",
                    "Value": float(token_count),
                    "Unit": "Count",
                },
            ],
        )
    except Exception:
        logger.exception("Failed to publish CloudWatch metrics")


# ---------------------------------------------------------------------------
# Trace span recording
# ---------------------------------------------------------------------------

def trace_span(
    agent_name: str,
    action: str,
    input_data: Dict[str, Any],
    output_data: Dict[str, Any],
    latency_ms: float,
    token_count: int,
    session_id: Optional[str] = None,
) -> Dict[str, str]:
    """Record a trace span to mock Arize endpoint or DynamoDB.

    Args:
        agent_name: Name of the agent producing the trace.
        action: The action/operation being traced.
        input_data: Input payload for the span.
        output_data: Output payload for the span.
        latency_ms: Duration of the operation in milliseconds.
        token_count: Number of tokens consumed.
        session_id: Optional conversation session ID.

    Returns:
        Dict with ``trace_id`` and ``correlation_id``.
    """
    trace_id = _generate_trace_id()
    correlation_id = _generate_correlation_id()
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Estimate cost (rough: $0.003 per 1K input tokens for Mistral Large 2)
    cost_usd = round(token_count * 0.000003, 6)

    trace_record: Dict[str, Any] = {
        "trace_id": trace_id,
        "correlation_id": correlation_id,
        "session_id": session_id or "",
        "agent_name": agent_name,
        "action": action,
        "input": json.dumps(input_data) if isinstance(input_data, dict) else str(input_data),
        "output": json.dumps(output_data) if isinstance(output_data, dict) else str(output_data),
        "latency_ms": int(latency_ms),
        "token_count": token_count,
        "cost_usd": str(cost_usd),
        "timestamp": timestamp,
    }

    # Try mock Arize endpoint first, fall back to direct DynamoDB write
    if ARIZE_ENDPOINT:
        try:
            import urllib.request
            import urllib.error

            req = urllib.request.Request(
                f"{ARIZE_ENDPOINT}/mock/arize/traces",
                data=json.dumps(trace_record).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                logger.debug("Arize trace submitted: %s status=%d", trace_id, resp.status)
        except Exception:
            logger.warning("Failed to send trace to Arize endpoint, falling back to DynamoDB")
            _write_trace_to_dynamodb(trace_record)
    else:
        _write_trace_to_dynamodb(trace_record)

    # Publish CloudWatch metrics regardless of storage backend
    _publish_metrics(latency_ms, token_count)

    return {"trace_id": trace_id, "correlation_id": correlation_id}


def _write_trace_to_dynamodb(trace_record: Dict[str, Any]) -> None:
    """Write trace record directly to DynamoDB traces table."""
    try:
        table = _get_dynamodb().Table(TABLE_TRACES)
        table.put_item(Item=trace_record)
        logger.debug("Trace written to DynamoDB: %s", trace_record["trace_id"])
    except Exception:
        logger.exception("Failed to write trace to DynamoDB")


# ---------------------------------------------------------------------------
# Feedback recording
# ---------------------------------------------------------------------------

def record_feedback(
    trace_id: str,
    feedback: str,
) -> Dict[str, Any]:
    """Record thumbs-up / thumbs-down feedback for a trace.

    Args:
        trace_id: The trace ID to annotate.
        feedback: One of ``"thumbs_up"`` or ``"thumbs_down"``.

    Returns:
        Confirmation dict with trace_id and feedback value.
    """
    if feedback not in ("thumbs_up", "thumbs_down"):
        raise ValueError(f"Invalid feedback value: {feedback}. Must be 'thumbs_up' or 'thumbs_down'.")

    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    try:
        table = _get_dynamodb().Table(TABLE_TRACES)
        table.update_item(
            Key={"trace_id": trace_id},
            UpdateExpression="SET feedback = :fb, feedback_ts = :ts",
            ExpressionAttributeValues={
                ":fb": feedback,
                ":ts": timestamp,
            },
        )
        logger.info("Feedback recorded for trace=%s feedback=%s", trace_id, feedback)
    except Exception:
        logger.exception("Failed to record feedback for trace=%s", trace_id)
        raise

    return {"trace_id": trace_id, "feedback": feedback, "recorded_at": timestamp}
