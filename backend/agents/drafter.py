"""Drafter Agent — Collaborative multi-agent application generator using the Swarm pattern.

This module implements a true multi-agent swarm with specialized sub-agents:
1. NarrativeAgent (Strands Agent): Drafts mission alignment, organization background, and statement of need using RAG.
2. BudgetAgent (Strands Agent): Builds 2 CFR 200 compliant budget justifications matching award parameters.
3. ComplianceDrafterAgent (Strands Agent): Generates implementation timelines, milestones, and sustainability frameworks.
4. LeadDrafterAgent (Strands Agent): Coordinates sequential handoffs between sub-agents and synthesizes the complete 6-section application.
"""

from __future__ import annotations

import logging
from typing import Any

from strands import Agent
from strands.models.bedrock import BedrockModel
from botocore.config import Config

from backend.config import config
from backend.optimization import get_model_for_agent
from backend.tools.org_profile import retrieve_org_profile
from backend.tools.application import save_application_draft, get_existing_application_draft
from backend.tools.rag_search import query_knowledge_base
from backend.tools.compliance import audit_application_compliance
from backend.api.models.schemas import ApplicationDraftResult, ApplicationSection

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  Sub-Agent System Prompts
# ──────────────────────────────────────────────

NARRATIVE_SYSTEM_PROMPT = """You are the Narrative Writer Agent for GrantScout.
YOUR ROLE:
You specialize in writing compelling, evidence-backed narrative sections for nonprofit grant proposals.
You produce Sections 1, 2, and 3:
1. Executive Summary
2. Organizational Background & Capacity
3. Statement of Need & Community Impact

Use `query_knowledge_base` and `retrieve_org_profile` to ground your writing in verified historical outcomes, Form 990 financials, and staff leadership bios.
"""

BUDGET_SYSTEM_PROMPT = """You are the Budget Specialist Agent for GrantScout.
YOUR ROLE:
You specialize in drafting rigorous, formulaic financial proposals and budget justifications compliant with federal 2 CFR 200 Uniform Guidance standards.
You produce Section 5: Budget & Financial Justification.

Ensure direct personnel allocations (FTEs, wages), supplies, equipment caps, and the standard 10% de minimis Modified Total Direct Cost (MTDC) indirect rate are clearly itemized.
"""

COMPLIANCE_SYSTEM_PROMPT = """You are the Compliance & Sustainability Drafter Agent for GrantScout.
YOUR ROLE:
You specialize in project timelines, measurable evaluation metrics, and long-term sustainability frameworks.
You produce Section 4 (Project Design & Timeline) and Section 6 (Evaluation & Sustainability).

Ensure clear quarterly milestones, participant KPIs, and diversified non-federal funding models are documented.
"""

LEAD_DRAFTER_SYSTEM_PROMPT = """You are the Lead Drafter Coordinator Agent for GrantScout.
YOUR ROLE:
You coordinate the multi-agent Swarm of specialized grant drafting agents (Narrative Writer, Budget Specialist, Compliance Drafter).
You synthesize all contributions into a unified, high-impact 6-section grant application conforming to the ApplicationDraftResult schema.
"""


# ──────────────────────────────────────────────
#  Strands Agent Factories
# ──────────────────────────────────────────────


def create_narrative_agent() -> Agent:
    """Create the specialized Narrative Writer Strands Agent."""
    model_cfg = get_model_for_agent("drafter")
    model = BedrockModel(model_id=model_cfg.model_id, region_name=model_cfg.region, boto_client_config=Config(read_timeout=3600, connect_timeout=900, retries={'max_attempts': 3, 'mode': 'standard'}))
    return Agent(
        model=model,
        system_prompt=NARRATIVE_SYSTEM_PROMPT,
        tools=[retrieve_org_profile, query_knowledge_base],
    )


def create_budget_agent() -> Agent:
    """Create the specialized Budget Specialist Strands Agent."""
    model_cfg = get_model_for_agent("drafter")
    model = BedrockModel(model_id=model_cfg.model_id, region_name=model_cfg.region, boto_client_config=Config(read_timeout=3600, connect_timeout=900, retries={'max_attempts': 3, 'mode': 'standard'}))
    return Agent(
        model=model,
        system_prompt=BUDGET_SYSTEM_PROMPT,
        tools=[retrieve_org_profile, audit_application_compliance],
    )


def create_compliance_drafter_agent() -> Agent:
    """Create the specialized Compliance & Sustainability Strands Agent."""
    model_cfg = get_model_for_agent("drafter")
    model = BedrockModel(model_id=model_cfg.model_id, region_name=model_cfg.region, boto_client_config=Config(read_timeout=3600, connect_timeout=900, retries={'max_attempts': 3, 'mode': 'standard'}))
    return Agent(
        model=model,
        system_prompt=COMPLIANCE_SYSTEM_PROMPT,
        tools=[query_knowledge_base, audit_application_compliance],
    )


def create_drafter_agent() -> Agent:
    """Create and configure the Lead Drafter Coordinator Agent.

    Returns:
        A Strands Agent configured for multi-agent swarm drafting.
    """
    model_cfg = get_model_for_agent("drafter")
    model = BedrockModel(
        model_id=model_cfg.model_id,
        region_name=model_cfg.region,
        boto_client_config=Config(read_timeout=3600, connect_timeout=900, retries={'max_attempts': 3, 'mode': 'standard'}),
    )

    agent = Agent(
        model=model,
        system_prompt=LEAD_DRAFTER_SYSTEM_PROMPT,
        tools=[
            retrieve_org_profile,
            query_knowledge_base,
            save_application_draft,
            get_existing_application_draft,
            audit_application_compliance,
        ],
    )

    logger.info("Lead Drafter Agent initialized with Multi-Agent Swarm tools")
    return agent


# ──────────────────────────────────────────────
#  Multi-Agent Swarm Orchestration & Execution
# ──────────────────────────────────────────────


def get_text_from_result(result) -> str:
    """Extract text from a Strands AgentResult."""
    try:
        if hasattr(result, "message") and isinstance(result.message, dict):
            return "".join(block.get("text", "") for block in result.message.get("content", []) if isinstance(block, dict))
    except Exception as e:
        logger.warning(f"Error extracting text from result: {e}")
    return str(result)


def draft_application_structured(grant_data: dict[str, Any], status_callback: Any = None) -> ApplicationDraftResult:
    """Generate a structured, type-safe grant application draft using the Multi-Agent Drafter Swarm.

    Args:
        grant_data: Dictionary containing grant opportunity details.

    Returns:
        Validated ApplicationDraftResult Pydantic model instance.
    """
    grant_id = grant_data.get("grant_id") or f"grants-gov-{grant_data.get('id', 'unknown')}"
    title = grant_data.get("title") or grant_data.get("opportunity_title", "Grant Opportunity")
    agency = grant_data.get("agency") or "Federal Agency"
    synopsis = grant_data.get("synopsis") or grant_data.get("synopsis_description", "No synopsis provided.")
    award_ceiling = grant_data.get("award_ceiling", 50000)
    award_floor = grant_data.get("award_floor", 10000)
    close_date = grant_data.get("close_date", "TBD")

    if status_callback: status_callback("Working, gathered information from [Narrative Writer]...")
    narrative_agent = create_narrative_agent()
    narr_prompt = f"Identify the mission alignment and organizational capacity for grant {title} based on our profile. Keep it under 100 words."
    narr_result = narrative_agent(narr_prompt)

    if status_callback: status_callback("Handed off to next agent [Budget Specialist]...")
    budget_agent = create_budget_agent()
    bud_prompt = f"Identify budget constraints for a request of ${award_ceiling} for grant {title}. Keep it under 100 words."
    bud_result = budget_agent(bud_prompt)

    if status_callback: status_callback("Handed off to next agent [Compliance Drafter]...")
    comp_agent = create_compliance_drafter_agent()
    comp_prompt = f"Identify evaluation metrics and timeline for grant {title}. Keep it under 100 words."
    comp_result = comp_agent(comp_prompt)

    if status_callback: status_callback("Handed off to [Lead Drafter] for final synthesis...")
    lead_agent = create_drafter_agent()

    prompt = f"""Draft a complete, competitive grant application for our organization:

TARGET GRANT:
- Grant ID: {grant_id}
- Title: {title}
- Agency: {agency}
- Award Range: ${award_floor:,.0f} - ${award_ceiling:,.0f}
- Deadline: {close_date}
- Synopsis: {synopsis}

[Narrative Agent Input]: {get_text_from_result(narr_result)}
[Budget Agent Input]: {get_text_from_result(bud_result)}
[Compliance Agent Input]: {get_text_from_result(comp_result)}

Coordinate with the Narrative Writer, Budget Specialist, and Compliance Drafter sub-agents.
Retrieve our org profile and return a fully formulated ApplicationDraftResult with all 6 structured sections.
"""

    try:
        # Modern Strands SDK structured output invocation
        agent_result = lead_agent(prompt, structured_output_model=ApplicationDraftResult)
        if isinstance(agent_result.structured_output, ApplicationDraftResult):
            draft_result = agent_result.structured_output
        else:
            raise ValueError("Empty or invalid structured output returned by drafter agent")
    except Exception as e:
        logger.error(f"Live Bedrock structured_output invocation unavailable ({e}); failing drafting.")
        raise ValueError(f"Drafting failed due to an error: {e}")

    # Persist the generated application draft to storage
    save_result = save_application_draft(
        grant_id=draft_result.grant_id,
        org_id=draft_result.org_id,
        grant_title=draft_result.grant_title,
        sections=[s.model_dump() for s in draft_result.sections],
    )
    logger.info(f"Persisted application draft {save_result.get('draft_id')} for {draft_result.grant_id}")

    return draft_result


def draft_application_for_grant(grant_data: dict[str, Any], status_callback: Any = None) -> dict[str, Any]:
    """Generate a grant application draft and return as dictionary."""
    result = draft_application_structured(grant_data, status_callback)
    if hasattr(result, "model_dump"):
        return result.model_dump()
    return result

