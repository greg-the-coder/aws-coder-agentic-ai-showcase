"""Lambda/AgentCore handler for the DC Investments Supervisor Agent."""

import json
import logging
import os
import time
import uuid
from typing import Any, Dict

import boto3

from agent.supervisor import create_supervisor_agent
from agent.config import TABLE_SESSIONS

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Lazy-init agent (reuse across invocations)
_agent = None
_dynamodb = None


def _get_agent():
    global _agent
    if _agent is None:
        _agent = create_supervisor_agent()
    return _agent


def _get_dynamodb():
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb")
    return _dynamodb


def _store_conversation(session_id: str, user_message: str, assistant_response: str) -> None:
    """Append conversation turn to DynamoDB sessions table."""
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        table = _get_dynamodb().Table(TABLE_SESSIONS)
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
        try:
            table = _get_dynamodb().Table(TABLE_SESSIONS)
            table.put_item(Item={
                "session_id": session_id,
                "user_id": "anonymous",
                "agent_id": "agentcore-supervisor",
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


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle a query request — compatible with Lambda or AgentCore runtime."""
    logger.info("AgentCore handler invoked")

    # Parse input
    if isinstance(event.get("body"), str):
        body = json.loads(event["body"])
    elif isinstance(event.get("body"), dict):
        body = event["body"]
    else:
        body = event

    session_id = body.get("session_id", str(uuid.uuid4()))
    message = body.get("message", "").strip()

    if not message:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "message field is required"}),
        }

    start_time = time.time()

    # Invoke the Strands agent
    try:
        agent = _get_agent()
        result = agent(message)
        response_text = str(result)
        source = "agentcore-strands"
    except Exception:
        logger.exception("Agent invocation failed")
        response_text = "I encountered an error processing your request. Please try again."
        source = "error"

    latency_ms = (time.time() - start_time) * 1000

    # Store conversation
    _store_conversation(session_id, message, response_text)

    trace_id = f"tr-{uuid.uuid4().hex[:12]}"

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
        "body": json.dumps({
            "session_id": session_id,
            "response": response_text,
            "message": response_text,
            "source": source,
            "sources": ["Source: AWS Bedrock AgentCore (Strands SDK)"],
            "suggestions": [],
            "trace_id": trace_id,
            "latency_ms": round(latency_ms, 1),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }, default=str),
    }
