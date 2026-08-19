"""Drafter Agent — Collaborative multi-agent application generator using the Swarm pattern.

This agent orchestrates three specialized sub-agents:
1. Narrative Writer: Drafts mission alignment, organization background, and program narrative.
2. Budget Specialist: Builds realistic budget allocation matching award ceiling/floor.
3. Compliance Checker: Audits required sections, verifies word counts, and saves the draft.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from strands import Agent
from strands.models.bedrock import BedrockModel

from backend.config import config
from backend.tools.org_profile import retrieve_org_profile
from backend.tools.application import save_application_draft, get_existing_application_draft

logger = logging.getLogger(__name__)

DRAFTER_SYSTEM_PROMPT = """You are the Lead Drafter Agent for GrantScout.

YOUR ROLE:
You coordinate the generation of comprehensive, high-quality grant application drafts for nonprofit organizations.
You produce complete, structured multi-section grant applications that auto-fill verified organizational data and clearly flag sections needing human review.

REQUIRED APPLICATION SECTIONS:
1. "Executive Summary" (Auto-filled: True, Needs Review: False)
   - High-level overview of the organization, proposed project, funding request amount, and intended impact.
2. "Organizational Background & Capacity" (Auto-filled: True, Needs Review: False)
   - History, mission statement, leadership, staff size, annual budget, and proven track record from past grants.
3. "Statement of Need & Target Population" (Auto-filled: True, Needs Review: True)
   - Specific community needs addressed, target demographics, service area, and gap in current services.
4. "Project Design & Implementation Plan" (Auto-filled: False, Needs Review: True)
   - Proposed activities, timeline milestones, measurable objectives, and key performance indicators.
5. "Budget & Financial Justification" (Auto-filled: True, Needs Review: True)
   - Itemized budget table matching the grant's award ceiling/floor, personnel costs, supplies, equipment, and administrative overhead.
6. "Evaluation & Sustainability" (Auto-filled: False, Needs Review: True)
   - How project outcomes will be measured, reported, and sustained beyond the grant period.

YOUR WORKFLOW:
1. Call `retrieve_org_profile` to get all organizational facts, past metrics, and board details.
2. Formulate all 6 required sections with comprehensive, professional prose using concrete data.
3. Call `save_application_draft` with the structured list of section dictionaries to save the complete draft.

OUTPUT FORMAT:
Provide a clear summary of the drafted application including:
- Grant Title & ID
- Organization Name
- Total Word Count
- Auto-fill completion percentage
- Summary of sections drafted
- Key action items recommended for human review before final submission.
"""


def create_drafter_agent() -> Agent:
    """Create and configure the Drafter Agent.

    Returns:
        A Strands Agent configured for collaborative application drafting.
    """
    model = BedrockModel(
        model_id=config.BEDROCK_MODEL_ID,
        region_name=config.AWS_REGION,
    )

    agent = Agent(
        model=model,
        system_prompt=DRAFTER_SYSTEM_PROMPT,
        tools=[
            retrieve_org_profile,
            save_application_draft,
            get_existing_application_draft,
        ],
    )

    logger.info("Drafter Agent initialized")
    return agent


def draft_application_for_grant(grant_data: dict[str, Any]) -> str:
    """Generate a full application draft for a matched grant.

    Args:
        grant_data: Dictionary containing grant opportunity details.

    Returns:
        Agent response string summarizing the drafted application.
    """
    agent = create_drafter_agent()

    grant_id = grant_data.get("grant_id") or f"grants-gov-{grant_data.get('id', 'unknown')}"
    title = grant_data.get("title") or grant_data.get("opportunity_title", "Grant Opportunity")
    agency = grant_data.get("agency") or "Federal Agency"
    synopsis = grant_data.get("synopsis") or grant_data.get("synopsis_description", "No synopsis provided.")
    award_ceiling = grant_data.get("award_ceiling", 50000)
    award_floor = grant_data.get("award_floor", 10000)
    close_date = grant_data.get("close_date", "TBD")

    prompt = f"""Draft a complete, competitive grant application for our organization for the following opportunity:

TARGET GRANT:
- Grant ID: {grant_id}
- Title: {title}
- Agency: {agency}
- Award Range: ${award_floor:,.0f} - ${award_ceiling:,.0f}
- Deadline: {close_date}
- Synopsis: {synopsis}

INSTRUCTIONS:
1. Retrieve our org profile using `retrieve_org_profile`.
2. Generate detailed, persuasive text for all 6 required sections:
   - Executive Summary
   - Organizational Background & Capacity
   - Statement of Need & Target Population
   - Project Design & Implementation Plan
   - Budget & Financial Justification
   - Evaluation & Sustainability
3. Save the completed draft using `save_application_draft`.
"""

    result = agent(prompt)
    return str(result)
