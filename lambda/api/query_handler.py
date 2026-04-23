"""POST /v1/query — Submit natural language query to Bedrock Agent.

Receives ``{ "session_id": "...", "message": "..." }``, invokes the Bedrock
Agent via ``bedrock-agent-runtime``, streams the response, stores the
conversation in the ``dcai-sessions`` table, and falls back to a mock
response if the Bedrock Agent is not yet deployed.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

import boto3

from botocore.config import Config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TABLE_SESSIONS: str = os.environ.get("TABLE_SESSIONS", "dcai-sessions")
BEDROCK_AGENT_ID: str = os.environ.get("BEDROCK_AGENT_ID", "")
BEDROCK_AGENT_ALIAS_ID: str = os.environ.get("BEDROCK_AGENT_ALIAS_ID", "")

_dynamodb: Any = None
_bedrock_runtime: Any = None


def _get_dynamodb() -> Any:
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb")
    return _dynamodb


def _get_bedrock_runtime() -> Any:
    global _bedrock_runtime
    if _bedrock_runtime is None:
        _bedrock_runtime = boto3.client(
            "bedrock-agent-runtime",
            config=Config(read_timeout=25, connect_timeout=5)
        )
    return _bedrock_runtime


def _api_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
        "body": json.dumps(body, default=str),
    }


# ---------------------------------------------------------------------------
# Mock response fallback
# ---------------------------------------------------------------------------

_MOCK_RESPONSES: Dict[str, str] = {
    "credit": (
        "Based on Moody's latest assessment, Equinix Inc. (EQIX) maintains an A3 issuer rating "
        "with a Stable outlook. The company demonstrates strong credit fundamentals with a "
        "debt-to-EBITDA of 3.7x and interest coverage of 5.3x as of Q2 2024. The probability "
        "of default stands at 0.18%, reflecting investment-grade credit quality."
    ),
    "market": (
        "Northern Virginia remains the largest data center market globally with 2,850 MW of "
        "total capacity and a tight 3.0% vacancy rate. The construction pipeline of 680 MW "
        "signals continued expansion, with 18% year-over-year growth. Average pricing is "
        "$120/kW/month, reflecting strong demand from hyperscale cloud providers."
    ),
    "esg": (
        "Switch Inc. leads the sustainability profile with a best-in-class PUE of 1.18 and "
        "100% renewable energy sourcing. Their carbon intensity of 105 kg CO₂e/MWh is the "
        "lowest in our coverage universe. Despite speculative-grade credit (B1), the strong "
        "ESG narrative supports $1.2B in outstanding green bonds."
    ),
    "default": (
        "I can help you with data center investment analysis across three domains:\n\n"
        "1. **Credit Risk** — Moody's ratings, PD/LGD estimates, financial metrics\n"
        "2. **Market Analytics** — Supply/demand, vacancy rates, pricing trends\n"
        "3. **ESG Risk** — PUE, carbon intensity, renewable energy, climate risk\n\n"
        "What would you like to explore?"
    ),
}


def _classify_intent(message: str) -> str:
    """Simple keyword-based intent classification for mock fallback."""
    msg = message.lower()
    if any(w in msg for w in ("credit", "rating", "moody", "default", "leverage", "debt")):
        return "credit"
    if any(w in msg for w in ("market", "supply", "demand", "vacancy", "pricing", "virginia", "dallas")):
        return "market"
    if any(w in msg for w in ("esg", "pue", "carbon", "renewable", "water", "climate", "sustainability")):
        return "esg"
    return "default"


def _mock_response(message: str) -> str:
    """Generate a mock response when Bedrock Agent is not available."""
    intent = _classify_intent(message)
    return _MOCK_RESPONSES[intent]


def _parse_sources(response_text: str, source: str) -> List[str]:
    """Extract 'Source:' lines from *response_text*.

    Falls back to a sensible default based on *source* when the response
    text contains no explicit source annotations.
    """
    import re
    matches = re.findall(r"Source:\s*(.+)", response_text)
    if matches:
        return [f"Source: {m.strip()}" for m in matches]
    if source == "mock" or source == "mock-fallback":
        return ["Source: Moody's CreditView (Mock Data)"]
    return ["Source: AWS Bedrock Agent"]


_SUGGESTIONS: Dict[str, List[str]] = {
    "credit": [
        "What is the market outlook for Northern Virginia?",
        "Show ESG profile for Switch",
        "Compare leverage for EQIX and DLR",
    ],
    "market": [
        "Show credit rating for Equinix",
        "What is the ESG risk for CyrusOne?",
        "Compare vacancy rates in Dallas vs Phoenix",
    ],
    "esg": [
        "What is the credit rating for Switch?",
        "Compare PUE across top 5 operators",
        "Show market supply in Northern Virginia",
    ],
    "default": [
        "Show credit rating for Equinix",
        "What is the market outlook for Northern Virginia?",
        "Show ESG profile for Switch",
    ],
}


def _generate_suggestions(message: str) -> List[str]:
    """Return 3 contextual follow-up suggestions based on intent."""
    intent = _classify_intent(message)
    return _SUGGESTIONS.get(intent, _SUGGESTIONS["default"])


def _generate_trace_id() -> str:
    """Return a trace ID of the form ``tr-<12-char hex>``."""
    return f"tr-{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# Bedrock Agent invocation
# ---------------------------------------------------------------------------

def _invoke_bedrock_agent(session_id: str, message: str) -> str:
    """Invoke Bedrock Agent and collect the streamed response."""
    client = _get_bedrock_runtime()
    response = client.invoke_agent(
        agentId=BEDROCK_AGENT_ID,
        agentAliasId=BEDROCK_AGENT_ALIAS_ID,
        sessionId=session_id,
        inputText=message,
    )

    # Collect streamed response chunks
    completion = ""
    event_stream = response.get("completion", [])
    for event in event_stream:
        chunk = event.get("chunk", {})
        if "bytes" in chunk:
            completion += chunk["bytes"].decode("utf-8")

    return completion


# ---------------------------------------------------------------------------
# Session persistence
# ---------------------------------------------------------------------------

def _store_conversation(
    session_id: str,
    user_message: str,
    assistant_response: str,
) -> None:
    """Append user+assistant messages to the session in DynamoDB."""
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    try:
        table = _get_dynamodb().Table(TABLE_SESSIONS)

        # Try to update existing session
        table.update_item(
            Key={"session_id": session_id},
            UpdateExpression=(
                "SET messages = list_append(if_not_exists(messages, :empty), :msgs), "
                "updated_at = :ts"
            ),
            ExpressionAttributeValues={
                ":msgs": [
                    {"role": "user", "content": user_message, "ts": ts},
                    {"role": "assistant", "content": assistant_response, "ts": ts},
                ],
                ":empty": [],
                ":ts": ts,
            },
        )
    except Exception:
        # If update fails, create new session
        try:
            table.put_item(Item={
                "session_id": session_id,
                "user_id": "anonymous",
                "agent_id": BEDROCK_AGENT_ID or "mock-agent",
                "messages": [
                    {"role": "user", "content": user_message, "ts": ts},
                    {"role": "assistant", "content": assistant_response, "ts": ts},
                ],
                "created_at": ts,
                "updated_at": ts,
                "metadata": {},
            })
        except Exception:
            logger.exception("Failed to store conversation for session %s", session_id)


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for POST /v1/query."""
    logger.info("Query handler invoked")

    # Handle CORS preflight
    http_method = event.get("httpMethod", "POST")
    if http_method == "OPTIONS":
        return _api_response(200, {})

    # Parse body
    raw_body = event.get("body", "{}")
    try:
        body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
    except json.JSONDecodeError:
        return _api_response(400, {"error": "Invalid JSON body"})

    session_id: str = body.get("session_id", str(uuid.uuid4()))
    message: str = body.get("message", "").strip()

    if not message:
        return _api_response(400, {"error": "message field is required"})

    start_time = time.time()

    # Try Bedrock Agent, fall back to mock
    if BEDROCK_AGENT_ID and BEDROCK_AGENT_ALIAS_ID:
        try:
            response_text = _invoke_bedrock_agent(session_id, message)
            source = "bedrock-agent"
        except Exception:
            logger.warning("Bedrock Agent invocation failed, using mock fallback", exc_info=True)
            response_text = _mock_response(message)
            source = "mock-fallback"
    else:
        logger.info("Bedrock Agent not configured, using mock response")
        response_text = _mock_response(message)
        source = "mock"

    latency_ms = (time.time() - start_time) * 1000

    # Store conversation
    _store_conversation(session_id, message, response_text)

    return _api_response(200, {
        "session_id": session_id,
        "response": response_text,
        "message": response_text,
        "source": source,
        "sources": _parse_sources(response_text, source),
        "suggestions": _generate_suggestions(message),
        "trace_id": _generate_trace_id(),
        "latency_ms": round(latency_ms, 1),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
