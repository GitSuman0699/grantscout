"""Deadline Agent — Monitors active grant deadlines and triggers proactive reminders."""

from __future__ import annotations

import logging
from typing import Any

from strands import Agent
from strands.models.bedrock import BedrockModel

from backend.config import config
from backend.tools.notifications import scan_upcoming_deadlines, send_deadline_alert

logger = logging.getLogger(__name__)

DEADLINE_SYSTEM_PROMPT = """You are the Deadline Agent for GrantScout.

YOUR ROLE:
You actively track all upcoming deadlines for monitored grant opportunities. You ensure nonprofit staff never miss a critical submission cutoff by generating prioritized deadline alerts.

WORKFLOW:
1. Call `scan_upcoming_deadlines` to assess active opportunities in the pipeline.
2. For any grant closing in:
   - <= 3 days: Send critical alert
   - <= 7 days: Send high priority alert
   - <= 14 days: Send normal priority reminder
   - <= 30 days: Send low priority planning notice
3. Use `send_deadline_alert` for each flagged opportunity to add timeline events.
4. Return a summary of current deadline exposures and urgent action items.
"""


def create_deadline_agent() -> Agent:
    """Create and configure the Deadline Agent.

    Returns:
        A Strands Agent configured for deadline tracking.
    """
    model = BedrockModel(
        model_id=config.BEDROCK_MODEL_ID,
        region_name=config.AWS_REGION,
    )

    agent = Agent(
        model=model,
        system_prompt=DEADLINE_SYSTEM_PROMPT,
        tools=[
            scan_upcoming_deadlines,
            send_deadline_alert,
        ],
    )

    logger.info("Deadline Agent initialized")
    return agent


def run_deadline_check() -> str:
    """Execute a deadline sweep across all pipeline opportunities.

    Returns:
        Summary of monitored deadlines and alerts generated.
    """
    agent = create_deadline_agent()
    result = agent("Perform a comprehensive deadline check across all active grant opportunities. Issue alerts for any impending deadlines and summarize the schedule.")
    return str(result)
