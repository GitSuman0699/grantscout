"""Orchestrator Agent — Central coordinator using the Graph pattern for autonomous routing.

This agent orchestrates the complete GrantScout lifecycle:
1. Scan grants.gov for new funding opportunities matching the org profile.
2. Evaluate fit & compute 5-dimension match scores for each discovery.
3. Graph Routing:
   - High match (score >= 80): Automatically triggers the Drafter Agent to pre-fill application.
   - Medium match (score 50-79): Flags for human review on dashboard.
   - Low match (score < 50): Silently archives with audit log.
4. Sweeps active deadlines and generates proactive alerts.
"""

from __future__ import annotations

import logging
from typing import Any

from strands import Agent, tool
from strands.models.bedrock import BedrockModel

from backend.config import config
from backend.tools.org_profile import retrieve_org_profile
from backend.tools.grants_api import search_grants, fetch_grant_details
from backend.storage.local_storage import storage
from backend.agents.scanner import create_scanner_agent
from backend.agents.matcher import score_grant
from backend.agents.drafter import draft_application_for_grant
from backend.agents.deadline import run_deadline_check

logger = logging.getLogger(__name__)


@tool
def execute_discovery_scan() -> dict[str, Any]:
    """Discover new grant opportunities by querying grants.gov with org profile keywords.

    Returns:
        Dictionary containing the list of newly found grant opportunities.
    """
    profile_data = storage.get_org_profile("default")
    if not profile_data:
        return {"count": 0, "grants": [], "error": "No org profile found"}

    keywords = " ".join(profile_data.get("keywords", [])[:4]) or "youth education STEM"
    search_res = search_grants(keywords=keywords, max_results=10)
    
    new_grants = []
    for g in search_res.get("grants", []):
        gid = f"grants-gov-{g.get('id')}"
        if not storage.grant_exists(gid):
            # Fetch full details
            detail_res = fetch_grant_details(opportunity_id=int(g.get("id")))
            grant_info = detail_res.get("grant") or g
            grant_info["grant_id"] = gid
            new_grants.append(grant_info)

    return {"count": len(new_grants), "grants": new_grants, "error": None}


@tool
def evaluate_and_route_grant(grant_info: dict[str, Any]) -> dict[str, Any]:
    """Score a grant against the organization profile and route according to fit score.

    Routing Policy:
    - Score >= 80: Status -> 'matched', auto-triggers pre-filling application draft
    - Score 50-79: Status -> 'matched', flags for manual review
    - Score < 50: Status -> 'archived'

    Args:
        grant_info: Detailed grant opportunity dictionary.

    Returns:
        Routing decision and match score details.
    """
    # Run evaluation
    score_analysis = score_grant(grant_info)
    
    gid = grant_info.get("grant_id") or f"grants-gov-{grant_info.get('id')}"
    saved_grant = storage.get_grant(gid)
    
    if not saved_grant:
        return {"grant_id": gid, "action": "unrecorded", "score": 0, "analysis": score_analysis}

    match_score = saved_grant.get("match_score", {})
    if isinstance(match_score, dict):
        total_score = match_score.get(
            "total",
            sum(v for k, v in match_score.items() if k != "total" and isinstance(v, (int, float))),
        )
    else:
        total_score = 0
    
    action = "flagged_for_review"
    draft_status = None

    if total_score >= 80:
        action = "auto_drafted"
        # Autonomous pre-fill drafting
        draft_result = draft_application_for_grant(saved_grant)
        draft_status = "completed"
    elif total_score < 50:
        action = "archived_silently"
        saved_grant["status"] = "archived"
        storage.save_grant(saved_grant)

    return {
        "grant_id": gid,
        "title": saved_grant.get("title"),
        "total_score": total_score,
        "action": action,
        "draft_status": draft_status,
    }


ORCHESTRATOR_SYSTEM_PROMPT = """You are the Lead Autonomous Orchestrator for GrantScout.

YOUR MISSION:
Autonomously run the end-to-end grant discovery, scoring, and routing lifecycle in the background. Only surface high-value opportunities that require real human decisions, fulfilling the hackathon promise of silent background execution.

WORKFLOW:
1. Execute discovery using `execute_discovery_scan`.
2. For each discovered opportunity, evaluate fit and execute Graph routing using `evaluate_and_route_grant`.
3. Perform a deadline check across the pipeline using `scan_upcoming_deadlines`.
4. Synthesize an executive briefing of the complete scan cycle with concrete metrics:
   - Total opportunities scanned
   - New grants scored (with breakdown of high/medium/low matches)
   - Applications auto-drafted
   - Upcoming deadlines requiring human attention.
"""


def create_orchestrator_agent() -> Agent:
    """Create and configure the Orchestrator Agent.

    Returns:
        A Strands Agent configured for multi-agent graph orchestration.
    """
    model = BedrockModel(
        model_id=config.BEDROCK_MODEL_ID,
        region_name=config.AWS_REGION,
    )

    agent = Agent(
        model=model,
        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
        tools=[
            execute_discovery_scan,
            evaluate_and_route_grant,
            retrieve_org_profile,
        ],
    )

    logger.info("Orchestrator Agent initialized")
    return agent


def run_full_orchestration_cycle() -> dict[str, Any]:
    """Execute a complete autonomous scan, match, draft, and deadline cycle.

    This function executes the deterministic and agentic pipeline:
    1. Scan grants.gov for opportunities matching org profile.
    2. Score discovered opportunities.
    3. Route according to graph policy (score >= 80 -> draft).
    4. Run deadline checks.

    Returns:
        Comprehensive summary dictionary of the orchestration run.
    """
    logger.info("Starting autonomous GrantScout orchestration cycle...")
    
    # 1. Discovery
    discovery_res = execute_discovery_scan()
    grants_found = discovery_res.get("grants", [])
    
    routed_results = []
    # 2. Score & Route each new grant
    for g in grants_found:
        route_res = evaluate_and_route_grant(g)
        routed_results.append(route_res)

    # 3. Deadline Check
    deadline_summary = run_deadline_check()

    summary = {
        "grants_scanned": len(grants_found),
        "routed_opportunities": routed_results,
        "deadline_summary": deadline_summary,
        "status": "completed",
    }
    
    logger.info(f"Orchestration cycle complete. Processed {len(grants_found)} opportunities.")
    return summary
