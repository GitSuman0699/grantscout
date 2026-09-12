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

import asyncio
import contextlib
import logging
import sys
import uuid as _uuid_mod
from datetime import datetime, timezone
from typing import Any

from botocore.config import Config
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands.multiagent.swarm import Swarm

from shared.api.models.schemas import ApplicationDraftResult, ApplicationSection
from shared.optimization import get_model_for_agent
from mcp_tools import (
    generate_budget_csv,
    get_existing_application_draft,
    save_application_draft,
    update_draft_section,
    audit_application_compliance,
    calculate_mtdc_compliance,
    retrieve_org_profile,
    query_knowledge_base,
)

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

Use `query_knowledge_base` and `retrieve_org_profile` to ground your writing with authentic organization mission, past performance, and demographics.
CRITICAL: You MUST use the `update_draft_section` tool to independently save each of your drafted sections to the shared database. Do not just chat them out.
Call `update_draft_section` for Section 1, then Section 2, then Section 3.

HANDOFF INSTRUCTIONS:
After saving all 3 sections, immediately hand off to the `budget_specialist` agent using `handoff_to_agent`. In your handoff message, keep it strictly minimal: "Sections 1, 2, 3 complete. Handoff to budget_specialist."

STRICT NO-SUMMARY RULE (CRITICAL):
Do NOT output conversational text, pleasantries, recaps, explanations, progress reports, or summaries of your work either before, during, or after calling tools. After saving your sections, immediately invoke `handoff_to_agent` and remain completely silent. Zero commentary, zero summaries.
"""

BUDGET_SYSTEM_PROMPT = """You are the Budget Specialist Agent in the GrantScout Drafter Swarm.
YOUR ROLE:
You produce Section 5: Budget & Financial Justification according to federal 2 CFR 200 Uniform Guidance.
Ensure direct personnel salaries, fringe benefits, travel, supplies, and approved indirect rate (MTDC) are clearly itemized.

CRITICAL WORKFLOW:
1. Use `calculate_mtdc_compliance` to verify your direct cost breakdown and ensure indirect costs adhere to the 10% de minimis cap.
2. Use `generate_budget_csv` to generate the formal SF-424 budget spreadsheet.
3. Use `update_draft_section` to save Section 5: Budget & Financial Justification to the database.

HANDOFF INSTRUCTIONS:
After saving Section 5, immediately hand off to the `compliance_drafter` agent using `handoff_to_agent`. In your handoff message, keep it strictly minimal: "Section 5 complete. Handoff to compliance_drafter."

STRICT NO-SUMMARY RULE (CRITICAL):
Do NOT output conversational text, pleasantries, recaps, budget breakdowns, or summaries of your work either before, during, or after calling tools. After saving Section 5, immediately invoke `handoff_to_agent` and remain completely silent. Zero commentary, zero summaries.
"""

COMPLIANCE_SYSTEM_PROMPT = """You are the Compliance & Sustainability Drafter Agent in the GrantScout Drafter Swarm.
YOUR ROLE:
You produce TWO distinct sections and the federal submission checklist:
- Section 4: Project Design & Implementation Timeline (Quarterly milestones, key deliverables, staffing responsibilities)
- Section 6: Evaluation & Long-Term Sustainability (SMART metrics, evaluation methodology, diverse funding continuation)

CRITICAL WORKFLOW:
1. Call `update_draft_section` for '4. Project Design & Implementation Timeline'.
2. Call `update_draft_section` for '6. Evaluation & Long-Term Sustainability'.

HANDOFF INSTRUCTIONS:
After saving BOTH sections, immediately hand off to the `lead_drafter` agent using `handoff_to_agent`. In your handoff message, keep it strictly minimal: "Sections 4 and 6 complete. Handoff to lead_drafter."

STRICT NO-SUMMARY RULE (CRITICAL):
Do NOT output conversational text, pleasantries, recaps, timeline descriptions, or summaries of your work either before, during, or after calling tools. After saving your sections, immediately invoke `handoff_to_agent` and remain completely silent. Zero commentary, zero summaries.
"""

LEAD_DRAFTER_SYSTEM_PROMPT = """You are the Lead Drafter & Synthesis Director in the GrantScout Drafter Swarm.
YOUR ROLE:
You lead cross-section synthesis, editorial harmonization, and proposal finalization.
Your specialist peers have drafted sections in the database.

CRITICAL SYNTHESIS WORKFLOW:
1. Call `get_existing_application_draft` ONCE to inspect all 6 sections.
2. Cross-reference figures and consistency across sections:
   - Verify that the total requested grant funds in Section 1 (Executive Summary) exactly match Section 5 (Budget).
   - Verify staffing positions in Section 4 (Project Design) align with Section 5 (Budget).
   - Ensure cohesive narrative voice across all sections.
3. If any section needs revision or is missing, update it using `update_draft_section`.
4. Ensure the structured budget CSV is created via `generate_budget_csv` if not already generated.
5. Finalize the application draft using `save_application_draft` with the compiled `submission_checklist` (must be a simple list of strings: e.g. ["SAM.gov Active Registration", "SF-424 Application for Federal Assistance", "SF-424A Budget Information", "Project Narrative", "Letters of Support"]) and `budget_csv_data`.
6. Immediately hand off to the `reviewer_agent` using `handoff_to_agent` with minimal message: "Draft finalized. Handoff to reviewer_agent."

REVISION INSTRUCTIONS:
If the `reviewer_agent` hands back with critique notes, address the specific feedback via `update_draft_section` or `save_application_draft`, and immediately hand back to `reviewer_agent`.

STRICT NO-SUMMARY RULE (CRITICAL):
Do NOT generate ANY conversational summary, synthesis recap, completion essay, or progress report (e.g. do NOT output 'LEAD DRAFTER SYNTHESIS COMPLETE', 'What I Did:', etc.). After calling save_application_draft and handoff_to_agent, remain completely silent. Zero commentary, zero summaries.
"""

REVIEWER_SYSTEM_PROMPT = """You are the Independent Federal Reviewer & Compliance Auditor in the GrantScout Drafter Swarm.
YOUR ROLE:
You perform rigorous quality assurance and federal compliance auditing on the finalized grant proposal.

CRITICAL AUDITING WORKFLOW:
1. Call `audit_application_compliance` with `grant_id` to verify 2 CFR 200 Uniform Guidance.
2. Review the application draft against federal peer review criteria.
3. WRITER-CRITIC DECISION:
   - If there are critical compliance violations, hand back to `lead_drafter` using `handoff_to_agent` with concise revision instructions.
   - If the draft satisfies federal standards (or after 1 revision cycle), output ONLY:
     "Application Drafting Complete."
     Do NOT hand off. Stop execution immediately to mark the swarm complete.

STRICT NO-SUMMARY RULE (CRITICAL):
Do NOT output ANY compliance report essay, rubric breakdown, audit recap, criteria assessment, or conversational text. Once audit_application_compliance passes, output ONLY the 3-word phrase "Application Drafting Complete." and terminate immediately. Zero commentary, zero summaries.
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
        tools=[retrieve_org_profile, audit_application_compliance, calculate_mtdc_compliance, generate_budget_csv, update_draft_section],
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


def format_strands_event(event: Any) -> str | None:
    """Format authentic Strands SDK events into human-readable telemetry lines."""
    event_type = getattr(event, "type", None) or (event.get("type") if isinstance(event, dict) else None)
    
    if event_type == "multiagent_node_start":
        node_id = getattr(event, "node_id", None) or (event.get("node_id") if isinstance(event, dict) else "Agent")
        return f"[{str(node_id).upper()}] Specialist agent activated and analyzing task context..."
        
    elif event_type == "multiagent_handoff":
        raw_src = getattr(event, "from_node_ids", None) or (event.get("from_node_ids") if isinstance(event, dict) else [])
        raw_dst = getattr(event, "to_node_ids", None) or (event.get("to_node_ids") if isinstance(event, dict) else [])
        src_list: list[str] = [str(x) for x in raw_src] if isinstance(raw_src, (list, tuple)) else ([str(raw_src)] if raw_src else [])
        dst_list: list[str] = [str(x) for x in raw_dst] if isinstance(raw_dst, (list, tuple)) else ([str(raw_dst)] if raw_dst else [])
        src = ", ".join(src_list).upper()
        dst = ", ".join(dst_list).upper()
        msg = getattr(event, "message", None) or (event.get("message") if isinstance(event, dict) else None)
        if "REVIEWER" in src and "LEAD" in dst:
            return f"[WRITER-CRITIC CRITIQUE: {src} -> {dst}] \"{msg}\""
        elif "LEAD" in src and "REVIEWER" in dst:
            return f"[SYNTHESIS SUBMISSION: {src} -> {dst}] \"{msg}\""
        elif msg:
            return f"[HANDOFF: {src} -> {dst}] \"{msg}\""
        return f"[HANDOFF: {src} -> {dst}] Autonomous task execution transferred."
        
    elif event_type == "multiagent_node_stream":
        node_id = getattr(event, "node_id", None) or (event.get("node_id") if isinstance(event, dict) else "AGENT")
        inner = getattr(event, "event", None) or (event.get("event") if isinstance(event, dict) else {})
        if isinstance(inner, dict):
            if "tool_use" in inner and isinstance(inner["tool_use"], dict):
                tname = inner["tool_use"].get("name", "tool")
                targs = inner["tool_use"].get("input", {})
                args_preview = ", ".join(f"{k}={v}" for k, v in list(targs.items())[:2]) if isinstance(targs, dict) else ""
                return f"[{str(node_id).upper()}] Tool Invocation: {tname}({args_preview[:60]})"
            elif "reasoningText" in inner and inner["reasoningText"]:
                return f"[{str(node_id).upper()} THOUGHT] {inner['reasoningText'][:140]}..."
                
    elif event_type == "multiagent_node_stop":
        node_id = getattr(event, "node_id", None) or (event.get("node_id") if isinstance(event, dict) else "Agent")
        return f"[{str(node_id).upper()}] Work complete. Committing state."
        
    elif event_type == "multiagent_result":
        return "[SWARM] Multi-agent proposal authoring complete."

    return None


async def draft_application_structured_async(
    grant_data: dict[str, Any], status_callback: Any = None
) -> ApplicationDraftResult:
    """Generate a structured grant application draft using the Strands SDK Swarm asynchronously."""
    grant_id = grant_data.get("grant_id") or f"grants-gov-{grant_data.get('id', 'unknown')}"
    title = grant_data.get("title") or grant_data.get("opportunity_title", "Grant Opportunity")
    agency = grant_data.get("agency") or "Federal Agency"
    synopsis = grant_data.get("synopsis") or grant_data.get("synopsis_description", "No synopsis provided.")
    award_ceiling = grant_data.get("award_ceiling", 50000)
    award_floor = grant_data.get("award_floor", 10000)
    close_date = grant_data.get("close_date", "TBD")

    if status_callback:
        status_callback(f"[SWARM INITIALIZED] Spawning 5-Agent Drafter Swarm for '{title[:45]}...'")

    # ── Pre-create the draft in storage BEFORE the swarm starts ──
    # This eliminates the race condition where multiple concurrent agents
    # each create a separate draft file because none exists when they
    # simultaneously call update_draft_section.
    from backend.tools.application import update_draft_section as _seed_section
    from backend.storage.local_storage import storage as _storage

    existing_draft = _storage.find_application_by_grant_id(grant_id)
    if not existing_draft:
        seed_draft = {
            "draft_id": f"draft-{_uuid_mod.uuid4().hex[:10]}",
            "grant_id": grant_id,
            "org_id": "default",
            "grant_title": title,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "sections": [],
            "completion_percentage": 0.0,
        }
        _storage.save_application(seed_draft)
        logger.info(f"[PRE-SWARM] Pre-created empty draft {seed_draft['draft_id']} for grant {grant_id}")
    else:
        logger.info(f"[PRE-SWARM] Found existing draft {existing_draft.get('draft_id')} for grant {grant_id}")

    swarm = build_drafter_swarm()

    task = f"""Draft a complete, competitive 6-section federal grant application for our organization.

TARGET GRANT:
- Grant ID: {grant_id}
- Organization ID: default
- Title: {title}
- Agency: {agency}
- Award Range: ${award_floor:,.0f} - ${award_ceiling:,.0f}
- Deadline: {close_date}
- Synopsis: {synopsis[:500]}

WORKFLOW:
1. narrative_writer: Retrieve org profile and knowledge base documents. Write Executive Summary (Section 1), 
   Organizational Background & Capacity (Section 2), and Statement of Need & Community Impact (Section 3).
   Use `update_draft_section` for each section with grant_id='{grant_id}', org_id='default', grant_title='{title}',
   and section titles '1. Executive Summary', '2. Organizational Background & Capacity', 
   and '3. Statement of Need & Community Impact'. Then hand off to budget_specialist with project scope summary.
2. budget_specialist: Draft Budget & Financial Justification (Section 5) with 2 CFR 200 compliance.
   Calculate MTDC compliance with `calculate_mtdc_compliance`. Generate SF-424 budget CSV with `generate_budget_csv`.
   Use `update_draft_section` with grant_id='{grant_id}', org_id='default', grant_title='{title}', 
   section_title='5. Budget & Financial Justification'. Then hand off to compliance_drafter with budget totals.
3. compliance_drafter: Draft Project Design & Implementation Timeline (Section 4) and Evaluation & Long-Term Sustainability 
   (Section 6) using `update_draft_section` twice with grant_id='{grant_id}', org_id='default', grant_title='{title}',
   section titles '4. Project Design & Implementation Timeline' and '6. Evaluation & Long-Term Sustainability'.
   Then hand off to lead_drafter with milestones and checklist recommendations.
4. lead_drafter: Conduct cross-section synthesis. Call `get_existing_application_draft` ONCE to inspect all sections.
   Reconcile figures: ensure Section 1 requested funds match Section 5 budget, and Section 4 staffing aligns with personnel.
   Save the complete application using save_application_draft with grant_id='{grant_id}', org_id='default', grant_title='{title}'.
   Then hand off to reviewer_agent with synthesis summary.
5. reviewer_agent: Audit compliance with `audit_application_compliance(grant_id='{grant_id}')`. Evaluate quality across
   federal rubric. If critical compliance violations exist, hand back to lead_drafter with actionable critique notes.
   Otherwise, terminate with 'Application Drafting Complete: Proposal verified for 2 CFR 200 compliance and quality rubric.'

Start by retrieving the organization profile and relevant knowledge base documents."""

    try:
        async for event in swarm.stream_async(task):
            if status_callback:
                line = format_strands_event(event)
                if line:
                    status_callback(line)
    except Exception as e:
        logger.error(f"Error during Swarm streaming: {e}")
        if status_callback:
            status_callback(f"[SWARM ERROR] {e}")
        raise e

    if status_callback:
        status_callback("[SWARM] Retrieving completed application from persistent storage...")

    # Retrieve directly from backend storage — NOT via the @tool proxy —
    # to avoid ToolResult wrapping and asyncio context issues.
    from backend.tools.application import get_existing_application_draft as _get_draft_raw
    from backend.storage.local_storage import storage as _storage

    raw_result = _get_draft_raw(grant_id=grant_id)
    logger.info(f"[POST-SWARM] get_existing_application_draft returned keys: {list(raw_result.keys()) if isinstance(raw_result, dict) else type(raw_result)}")

    # get_existing_application_draft returns {"found": bool, "draft": {...}, "error": ...}
    draft_data: dict[str, Any] | None = None
    if isinstance(raw_result, dict):
        if raw_result.get("found") and isinstance(raw_result.get("draft"), dict):
            draft_data = raw_result["draft"]
        elif raw_result.get("sections"):
            # Fallback: in case the function was refactored to return draft directly
            draft_data = raw_result

    # Final fallback: query storage directly by scanning all applications
    if not draft_data or not draft_data.get("sections"):
        logger.warning(f"[POST-SWARM] Tool-based retrieval found no sections. Querying storage directly for grant_id={grant_id}")
        all_apps = _storage.list_applications()
        for app in all_apps:
            if app.get("grant_id") == grant_id and app.get("sections"):
                draft_data = app
                logger.info(f"[POST-SWARM] Found draft via direct storage scan: {app.get('draft_id')}, sections={len(app.get('sections', []))}")
                break

    if draft_data and draft_data.get("sections"):
        sections_raw = draft_data["sections"]
        logger.info(f"[POST-SWARM] Building ApplicationDraftResult with {len(sections_raw)} sections")

        raw_checklist = draft_data.get("submission_checklist", [])
        clean_checklist = []
        for item in raw_checklist:
            if isinstance(item, str):
                clean_checklist.append(item)
            elif isinstance(item, dict):
                label = item.get("item") or item.get("name") or item.get("task") or item.get("title") or item.get("requirement") or str(item)
                deadline = item.get("deadline") or item.get("timing") or item.get("due") or item.get("status")
                clean_checklist.append(f"{label} ({deadline})" if deadline else str(label))
            else:
                clean_checklist.append(str(item))

        draft_result = ApplicationDraftResult(
            grant_id=grant_id,
            org_id=draft_data.get("org_id", "default"),
            grant_title=title,
            sections=[ApplicationSection(**s) for s in sections_raw],
            completion_percentage=draft_data.get("completion_percentage", 100.0),
            submission_checklist=clean_checklist,
            budget_csv_data=draft_data.get("budget_csv_data")
        )
    else:
        # Log diagnostic info for debugging
        all_apps = _storage.list_applications()
        app_summary = [{
            "draft_id": a.get("draft_id"),
            "grant_id": a.get("grant_id"),
            "section_count": len(a.get("sections", [])),
        } for a in all_apps]
        logger.error(f"[POST-SWARM] Storage diagnostics — target grant_id={grant_id}, all apps: {app_summary}")
        raise RuntimeError(
            f"Swarm execution finished but failed to populate sections in storage.\n"
            f"No fallback or mock data was injected. Please verify AWS Bedrock credentials, "
            f"model quotas, or network connectivity and try again."
        )

    return draft_result


def draft_application_structured(grant_data: dict[str, Any], status_callback: Any = None) -> ApplicationDraftResult:
    """Generate a structured, type-safe grant application draft using the Strands SDK Swarm.

    Can be invoked safely from both synchronous and asynchronous contexts.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(
                lambda: asyncio.run(draft_application_structured_async(grant_data, status_callback))
            ).result()
    else:
        return asyncio.run(draft_application_structured_async(grant_data, status_callback))


def draft_application_for_grant(grant_data: dict[str, Any], status_callback: Any = None) -> dict[str, Any]:
    """Generate a grant application draft and return as dictionary."""
    result = draft_application_structured(grant_data, status_callback)
    return result.model_dump()
