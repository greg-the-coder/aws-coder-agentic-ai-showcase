"""Data Center Investments Supervisor Agent — Strands Agents SDK implementation."""

import os
import sys

from strands import Agent
from strands.models.bedrock import BedrockModel

from agent.config import BEDROCK_MODEL_ID, AWS_REGION
from agent.tools.credit_rating import lookup_credit_rating
from agent.tools.financial_metrics import get_financial_metrics
from agent.tools.market_data import query_market_data
from agent.tools.esg_risk import assess_esg_risk
from agent.tools.generate_report import generate_report
from agent.tools.sync_moodys import sync_moodys_data

# Load system prompt
_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")
_SYSTEM_PROMPT_PATH = os.path.join(_PROMPT_DIR, "supervisor_system.txt")


def _load_system_prompt() -> str:
    with open(_SYSTEM_PROMPT_PATH, "r") as f:
        return f.read()


def create_supervisor_agent() -> Agent:
    """Create and return the configured Supervisor Agent."""
    model = BedrockModel(
        model_id=BEDROCK_MODEL_ID,
        region_name=AWS_REGION,
        streaming=False,
    )

    system_prompt = _load_system_prompt()

    agent = Agent(
        model=model,
        system_prompt=system_prompt,
        tools=[
            lookup_credit_rating,
            get_financial_metrics,
            query_market_data,
            assess_esg_risk,
            generate_report,
            sync_moodys_data,
        ],
    )

    return agent
