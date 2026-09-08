"""Drafter Agent — Collaborative multi-agent application generator using the Strands SDK Swarm pattern.

This module implements a real Strands SDK Swarm with autonomous agent handoffs:
1. NarrativeAgent: Drafts mission alignment, organization background, and statement of need using RAG.
2. BudgetAgent: Builds 2 CFR 200 compliant budget justifications matching award parameters.
3. ComplianceDrafterAgent: Generates implementation timelines, milestones, and sustainability frameworks.
4. LeadDrafterAgent: Synthesizes all contributions into the final 6-section ApplicationDraftResult.

The Swarm uses the strands.multiagent.swarm.Swarm class with:
- Autonomous handoffs via the SDK's built-in `handoff_to_agent` tool
- Entry point at the NarrativeAgent
- Max 12 handoffs and 16 iterations for bounded execution
"""

from __future__ import annotations

import sys
import contextlib
import asyncio
import logging
from typing import Any

from strands import Agent
from strands.models.bedrock import BedrockModel
from strands.multiagent.swarm import Swarm
from botocore.config import Config

from backend.config import config
from backend.optimization import get_model_for_agent
from backend.tools.org_profile import retrieve_org_profile
from backend.tools.application import save_application_draft, get_existing_application_draft, update_draft_section, generate_budget_csv
from backend.tools.rag_search import query_knowledge_base
from backend.tools.compliance import audit_application_compliance, calculate_mtdc_compliance
from backend.api.models.schemas import ApplicationDraftResult, ApplicationSection

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  Sub-Agent System Prompts
# ──────────────────────────────────────────────

NARRATIVE_SYSTEM_PROMPT = """You are the Narrative Writer Agent in the GrantScout Drafter Swarm.
YOUR ROLE:
You specialize in writing compelling, evidence-backed narrative sections for nonprofit grant proposals.
You produce Sections 1, 2, and 3:
1. Executive Summary
2. Organizational Background & Capacity
3. Statement of Need & Community Impact

Use `query_knowledge_base` and `retrieve_org_profile` to ground your writing.
CRITICAL: You MUST use the `update_draft_section` tool to independently save each of your drafted sections to the shared database. Do not just chat them out.
Call `update_draft_section` for Section 1, then for Section 2, then for Section 3.

HANDOFF INSTRUCTIONS:
After saving your sections, hand off to the `budget_specialist` agent.
"""

BUDGET_SYSTEM_PROMPT = """You are the Budget Specialist Agent in the GrantScout Drafter Swarm.
YOUR ROLE:
You produce Section 5: Budget & Financial Justification.
Ensure direct personnel allocations and indirect rate (MTDC) are clearly itemized.

CRITICAL: You MUST use the `calculate_mtdc_compliance` tool to deterministically verify your indirect cost math before finalizing the budget.
CRITICAL: You MUST use the `update_draft_section` tool to save your Section 5 draft to the shared database. Do not just chat it out.

HANDOFF INSTRUCTIONS:
After saving Section 5, hand off to the `compliance_drafter` agent.
"""

COMPLIANCE_SYSTEM_PROMPT = """You are the Compliance & Sustainability Drafter Agent in the GrantScout Drafter Swarm.
YOUR ROLE:
You produce TWO distinct sections:
- Section 4: Project Design & Timeline
- Section 6: Evaluation & Sustainability

CRITICAL: You MUST use `update_draft_section` TWICE. Once for 'Project Design & Timeline' and once for 'Evaluation & Sustainability'. Do not combine them. Do not skip either of them.

HANDOFF INSTRUCTIONS:
After saving BOTH sections, hand off to the `lead_drafter` agent.
"""

LEAD_DRAFTER_SYSTEM_PROMPT = """You are the Lead Drafter Coordinator in the GrantScout Drafter Swarm.
YOUR ROLE:
You coordinate the swarm. Your peers have already saved their sections to the shared database using `update_draft_section`.
Use `get_existing_application_draft` to verify that all 6 sections are present and populated.
If any are missing, write them yourself and save them using `update_draft_section`.

You must also use `generate_budget_csv` to create a structured budget CSV based on the Section 5 budget narrative.
You must compile a concrete `submission_checklist` (e.g. SAM.gov registration, SF-424 forms, specific attachments required).

Once the draft is 100% complete with 6 sections, use `save_application_draft` and provide your submission_checklist and the budget_csv_data. DO NOT pass the sections argument, it will automatically pull the sections from the database.
After successfully calling save_application_draft, hand off to the `reviewer_agent`.
"""

REVIEWER_SYSTEM_PROMPT = """You are the Quality Reviewer Agent in the GrantScout Drafter Swarm.
YOUR ROLE:
You evaluate the final draft for completeness.
Use `get_existing_application_draft` to read the completed application. Check if all 6 sections are present.
If you find catastrophic issues (e.g., a section is entirely missing), you may use the built-in `handoff_to_agent` tool to hand control back to the `lead_drafter` to fix it.
CRITICAL: You are generally very lenient. To prevent infinite loops, if all 6 sections are present and reasonably populated, you MUST output a final summary stating 'Application Drafting Complete' and terminate. Do NOT hand off.
"""


# ──────────────────────────────────────────────
#  Strands Agent Factories
# ──────────────────────────────────────────────


def _create_bedrock_model(agent_name: str = "drafter") -> BedrockModel:
    """Create a BedrockModel configured for the given agent tier."""
    model_cfg = get_model_for_agent(agent_name)
    return BedrockModel(
        model_id=model_cfg.model_id,
        region_name=model_cfg.region,
        boto_client_config=Config(
            read_timeout=3600,
            connect_timeout=900,
            retries={'max_attempts': 3, 'mode': 'standard'},
        ),
    )


def create_narrative_agent() -> Agent:
    """Create the specialized Narrative Writer Strands Agent."""
    return Agent(
        name="narrative_writer",
        model=_create_bedrock_model(),
        system_prompt=NARRATIVE_SYSTEM_PROMPT,
        tools=[retrieve_org_profile, query_knowledge_base, update_draft_section],
    )


def create_budget_agent() -> Agent:
    """Create the specialized Budget Specialist Strands Agent."""
    return Agent(
        name="budget_specialist",
        model=_create_bedrock_model(),
        system_prompt=BUDGET_SYSTEM_PROMPT,
        tools=[retrieve_org_profile, audit_application_compliance, calculate_mtdc_compliance, update_draft_section],
    )


def create_compliance_drafter_agent() -> Agent:
    """Create the specialized Compliance & Sustainability Strands Agent."""
    return Agent(
        name="compliance_drafter",
        model=_create_bedrock_model(),
        system_prompt=COMPLIANCE_SYSTEM_PROMPT,
        tools=[query_knowledge_base, audit_application_compliance, update_draft_section],
    )


def create_drafter_agent() -> Agent:
    """Create and configure the Lead Drafter Coordinator Agent.

    Returns:
        A Strands Agent configured as the final synthesis node in the Drafter Swarm.
    """
    return Agent(
        name="lead_drafter",
        model=_create_bedrock_model(),
        system_prompt=LEAD_DRAFTER_SYSTEM_PROMPT,
        tools=[
            retrieve_org_profile,
            query_knowledge_base,
            save_application_draft,
            get_existing_application_draft,
            update_draft_section,
            audit_application_compliance,
            generate_budget_csv,
        ],
    )

def create_reviewer_agent() -> Agent:
    """Create the Quality Reviewer Agent to enforce the non-linear swarm loop."""
    return Agent(
        name="reviewer_agent",
        model=_create_bedrock_model(),
        system_prompt=REVIEWER_SYSTEM_PROMPT,
        tools=[get_existing_application_draft, audit_application_compliance],
    )


# ──────────────────────────────────────────────
#  Strands SDK Swarm — Real Multi-Agent Orchestration
# ──────────────────────────────────────────────


def build_drafter_swarm() -> Swarm:
    """Build the GrantScout Drafter Swarm using the Strands SDK Swarm class.

    The Swarm enables autonomous agent handoffs via the SDK's built-in
    `handoff_to_agent` tool. Each agent can autonomously decide when to
    hand off to the next specialist.

    Swarm topology:
        narrative_writer → budget_specialist → compliance_drafter → lead_drafter

    Returns:
        A configured Strands Swarm instance.
    """
    narrative_agent = create_narrative_agent()
    budget_agent = create_budget_agent()
    compliance_agent = create_compliance_drafter_agent()
    lead_agent = create_drafter_agent()
    reviewer_agent = create_reviewer_agent()

    swarm = Swarm(
        nodes=[narrative_agent, budget_agent, compliance_agent, lead_agent, reviewer_agent],
        entry_point=narrative_agent,
        max_handoffs=15,
        max_iterations=20,
        execution_timeout=900.0,    # 15 min total swarm timeout
        node_timeout=300.0,         # 5 min per agent
        id="grantscout_drafter_swarm",
    )

    logger.info(
        "GrantScout Drafter Swarm built: "
        "narrative_writer ↔ budget_specialist ↔ compliance_drafter ↔ lead_drafter ↔ reviewer_agent"
    )
    return swarm


def get_text_from_result(result) -> str:
    """Extract text from a Strands AgentResult."""
    try:
        if hasattr(result, "message") and isinstance(result.message, dict):
            return "".join(block.get("text", "") for block in result.message.get("content", []) if isinstance(block, dict))
    except Exception as e:
        logger.warning(f"Error extracting text from result: {e}")
    return str(result)


class StdoutInterceptor:
    """Intercepts stdout to stream raw agent thoughts back via callback."""
    def __init__(self, callback):
        self.callback = callback
        self.original_stdout = sys.stdout
        self.buffer = ""

    def write(self, s):
        self.original_stdout.write(s)
        self.buffer += s
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            line = line.strip()
            # Pass clean lines to the UI (truncate overly long ones)
            if line and "DEBUG" not in line:
                self.callback(line[:150])

    def flush(self):
        self.original_stdout.flush()


def draft_application_structured(grant_data: dict[str, Any], status_callback: Any = None) -> ApplicationDraftResult:
    """Generate a structured, type-safe grant application draft using the Strands SDK Swarm.

    The Swarm orchestrates 4 specialized agents with autonomous handoffs:
    1. NarrativeAgent writes sections 1-3 (grounded in RAG knowledge base)
    2. BudgetAgent writes section 5 (2 CFR 200 compliant)
    3. ComplianceDrafterAgent writes sections 4 & 6
    4. LeadDrafterAgent synthesizes and saves the final application

    Args:
        grant_data: Dictionary containing grant opportunity details.
        status_callback: Optional callback for real-time status updates.

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

    if status_callback:
        status_callback("Initializing Strands Drafter Swarm with 4 specialized agents...")

    # Build the Swarm
    swarm = build_drafter_swarm()

    # Construct the task prompt for the Swarm
    task = f"""Draft a complete, competitive 6-section federal grant application for our organization.

TARGET GRANT:
- Grant ID: {grant_id}
- Title: {title}
- Agency: {agency}
- Award Range: ${award_floor:,.0f} - ${award_ceiling:,.0f}
- Deadline: {close_date}
- Synopsis: {synopsis[:500]}

WORKFLOW:
1. narrative_writer: Retrieve org profile and knowledge base documents. Write Executive Summary, 
   Organizational Background, and Statement of Need (Sections 1-3). Then hand off to budget_specialist.
2. budget_specialist: Draft Budget & Financial Justification (Section 5) with 2 CFR 200 compliance.
   Then hand off to compliance_drafter.
3. compliance_drafter: Draft Project Design & Timeline (Section 4) and Evaluation & Sustainability 
   (Section 6) using `update_draft_section` twice. Then hand off to lead_drafter.
4. lead_drafter: Synthesize sections. Verify all 6 are present. Generate the budget CSV. Formulate the submission checklist. 
   Save the complete application using save_application_draft with grant_id='{grant_id}'.
   Then hand off to reviewer_agent.
5. reviewer_agent: Evaluate the draft. If perfect, terminate with 'Application Drafting Complete'.

Start by retrieving the organization profile and relevant knowledge base documents."""

    if status_callback:
        status_callback("Swarm started — narrative_writer agent is working...")
        interceptor = StdoutInterceptor(status_callback)
    else:
        interceptor = sys.stdout

    # Run the Swarm asynchronously with intercepted stdout
    try:
        with contextlib.redirect_stdout(interceptor): # type: ignore
            swarm_result = asyncio.run(swarm.invoke_async(task))
            
        logger.info(
            f"Drafter Swarm completed. Status: {swarm_result.status}, "
            f"Executions: {swarm_result.execution_count}, "
            f"Time: {swarm_result.execution_time:.1f}s"
        )
    except RuntimeError:
        # Already in an async context — run in a new thread
        loop = asyncio.new_event_loop()
        try:
            with contextlib.redirect_stdout(interceptor): # type: ignore
                swarm_result = loop.run_until_complete(swarm.invoke_async(task))
        finally:
            loop.close()

    if status_callback:
        status_callback("Swarm completed — retrieving populated native sections...")

    # The Swarm has natively hydrated the shared state via `update_draft_section`.
    # No need for an expensive, brittle extractor agent. We just fetch the completed draft from the DB.
    from backend.storage.local_storage import storage
    apps = storage.list_applications()
    saved_app = next((a for a in apps if a.get("grant_id") == grant_id), None)
    
    if saved_app and saved_app.get("sections"):
        draft_result = ApplicationDraftResult(
            grant_id=grant_id,
            org_id=saved_app.get("org_id", "default"),
            grant_title=title,
            sections=[ApplicationSection(**s) for s in saved_app["sections"]],
            completion_percentage=saved_app.get("completion_percentage", 100.0),
            submission_checklist=saved_app.get("submission_checklist", []),
            budget_csv_data=saved_app.get("budget_csv_data")
        )
    else:
        raise ValueError("Swarm failed to populate sections natively using the shared state.")

    # Ensure the draft is persisted one final time just in case
    save_result = save_application_draft(
        grant_id=draft_result.grant_id,
        org_id=draft_result.org_id,
        grant_title=draft_result.grant_title,
        sections=[s.model_dump() for s in draft_result.sections],
        submission_checklist=draft_result.submission_checklist,
        budget_csv_data=draft_result.budget_csv_data,
    )
    logger.info(f"Persisted application draft {save_result.get('draft_id')} for {draft_result.grant_id}")

    return draft_result


def draft_application_for_grant(grant_data: dict[str, Any], status_callback: Any = None) -> dict[str, Any]:
    """Generate a grant application draft and return as dictionary."""
    result = draft_application_structured(grant_data, status_callback)
    return result.model_dump()
