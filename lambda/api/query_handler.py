"""POST /v1/query — Submit natural language query to Bedrock Agent or AgentCore.

Receives ``{ "session_id": "...", "message": "..." }``, invokes either:
  1. AgentCore supervisor Lambda (Strands SDK agent) — if AGENTCORE_FUNCTION_NAME is set
  2. Bedrock Agent via ``bedrock-agent-runtime`` — if BEDROCK_AGENT_ID is set
  3. Mock fallback — keyword-based classification

Stores the conversation in the ``dcai-sessions`` table and returns the response.
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
AGENTCORE_FUNCTION_NAME: str = os.environ.get("AGENTCORE_FUNCTION_NAME", "")

_dynamodb: Any = None
_bedrock_runtime: Any = None
_lambda_client: Any = None


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


def _get_lambda_client() -> Any:
    global _lambda_client
    if _lambda_client is None:
        _lambda_client = boto3.client(
            "lambda",
            config=Config(read_timeout=95, connect_timeout=5)
        )
    return _lambda_client


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
    """Generate a mock response when neither AgentCore nor Bedrock Agent is available."""
    intent = _classify_intent(message)
    return _MOCK_RESPONSES[intent]


def _parse_sources(response_text: str, source: str) -> List[str]:
    """Extract 'Source:' lines from response text."""
    import re
    matches = re.findall(r"Source:\s*(.+)", response_text)
    if matches:
        return [f"Source: {m.strip()}" for m in matches]
    if source == "agentcore-strands":
        return ["Source: AWS Bedrock AgentCore (Strands SDK + Mistral Large)"]
    if source == "bedrock-agent":
        return ["Source: AWS Bedrock Agent"]
    return ["Source: Moody's CreditView (Mock Data)"]


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
# AgentCore invocation (Strands SDK agent via Lambda)
# ---------------------------------------------------------------------------

def _invoke_agentcore(session_id: str, message: str) -> str:
    """Invoke the AgentCore supervisor Lambda and return the response text."""
    client = _get_lambda_client()

    payload = json.dumps({
        "body": json.dumps({
            "session_id": session_id,
            "message": message,
        })
    })

    response = client.invoke(
        FunctionName=AGENTCORE_FUNCTION_NAME,
        InvocationType="RequestResponse",
        Payload=payload.encode("utf-8"),
    )

    # Parse the Lambda response
    response_payload = json.loads(response["Payload"].read().decode("utf-8"))

    if response_payload.get("statusCode") == 200:
        body = json.loads(response_payload["body"])
        return body.get("response", body.get("message", ""))
    else:
        error_body = response_payload.get("body", "{}")
        if isinstance(error_body, str):
            error_body = json.loads(error_body)
        raise RuntimeError(f"AgentCore returned error: {error_body}")


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

def _get_session_context(session_id: str) -> Optional[str]:
    """Retrieve recent conversation context for the session (memory support).
    
    Returns a summary of recent messages to provide context to the agent,
    or None if no prior conversation exists.
    """
    try:
        table = _get_dynamodb().Table(TABLE_SESSIONS)
        response = table.get_item(Key={"session_id": session_id})
        item = response.get("Item")
        if not item:
            return None

        messages = item.get("messages", [])
        if not messages:
            return None

        # Return last 6 messages as context (3 turns)
        recent = messages[-6:]
        context_lines = []
        for msg in recent:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            # Truncate long messages for context
            if len(content) > 500:
                content = content[:500] + "..."
            context_lines.append(f"{role}: {content}")

        return "\n".join(context_lines)
    except Exception:
        logger.warning("Failed to retrieve session context for %s", session_id, exc_info=True)
        return None


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
                "agent_id": AGENTCORE_FUNCTION_NAME or BEDROCK_AGENT_ID or "mock-agent",
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

    # Priority: AgentCore > Bedrock Agent > Mock
    if AGENTCORE_FUNCTION_NAME:
        try:
            response_text = _invoke_agentcore(session_id, message)
            source = "agentcore-strands"
        except Exception:
            logger.warning("AgentCore invocation failed, trying Bedrock Agent fallback", exc_info=True)
            if BEDROCK_AGENT_ID and BEDROCK_AGENT_ALIAS_ID:
                try:
                    response_text = _invoke_bedrock_agent(session_id, message)
                    source = "bedrock-agent"
                except Exception:
                    logger.warning("Bedrock Agent also failed, using mock", exc_info=True)
                    response_text = _mock_response(message)
                    source = "mock-fallback"
            else:
                response_text = _mock_response(message)
                source = "mock-fallback"
    elif BEDROCK_AGENT_ID and BEDROCK_AGENT_ALIAS_ID:
        try:
            response_text = _invoke_bedrock_agent(session_id, message)
            source = "bedrock-agent"
        except Exception:
            logger.warning("Bedrock Agent invocation failed, using mock fallback", exc_info=True)
            response_text = _mock_response(message)
            source = "mock-fallback"
    else:
        logger.info("No agent configured, using mock response")
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
