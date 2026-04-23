"""Bedrock Agent Action Group response formatter.

Returns the response envelope expected by Amazon Bedrock Agents
when invoking Lambda-backed action groups.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Union


def format_agent_response(
    action_group: str,
    api_path: str,
    http_method: str,
    status_code: int,
    body: Union[Dict[str, Any], str],
) -> Dict[str, Any]:
    """Build the Bedrock Action Group Lambda response envelope.

    Args:
        action_group: Name of the action group (from event ``actionGroup``).
        api_path: API path for the action (from event ``apiPath``).
        http_method: HTTP method (GET, POST, etc.).
        status_code: HTTP status code to return.
        body: Response payload — dict will be JSON-serialised.

    Returns:
        A dict conforming to the Bedrock Agent Action Group response schema.
    """
    body_str = json.dumps(body) if isinstance(body, dict) else str(body)

    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": action_group,
            "apiPath": api_path,
            "httpMethod": http_method,
            "httpStatusCode": status_code,
            "responseBody": {
                "application/json": {
                    "body": body_str,
                }
            },
        },
    }
