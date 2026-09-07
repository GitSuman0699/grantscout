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
from botocore.config import Config

from backend.config import config
from backend.tools.org_profile import retrieve_org_profile
from backend.tools.grants_api import search_grants, fetch_grant_details
from backend.storage.local_storage import storage
from backend.agents.scanner import create_scanner_agent, is_active_opportunity
from backend.agents.matcher import score_grant
from backend.agents.drafter import draft_application_for_grant
from backend.agents.deadline import run_deadline_check

logger = logging.getLogger(__name__)


def is_domain_relevant(grant_info: dict[str, Any], profile_data: dict[str, Any]) -> tuple[bool, str]:
    """Pre-filter opportunities to avoid evaluating grants completely outside the nonprofit's scope."""
    import re

    title = (grant_info.get("title") or "").lower()
    synopsis = (grant_info.get("synopsis_description") or grant_info.get("synopsis") or "").lower()
    full_text = f"{title} {synopsis}"

    # 1. Skip RFIs (Requests for Information) and non-grant notices
    if title.startswith("request for information") or "rfi" in title.split():
        return False, "Skipped: Request for Information (RFI), not a grant opportunity"

    # 2. Check for exact phrase matches from profile keywords
    keywords = profile_data.get("keywords", [])
    for kw in keywords:
        clean_kw = kw.strip().strip('"').lower()
        if clean_kw and clean_kw in full_text:
            return True, f"Direct keyword phrase match: '{clean_kw}'"

    # 3. Check for substantive domain keyword matches (words > 3 chars)
    domain_terms = set()
    for kw in keywords:
        for word in re.findall(r"[a-zA-Z0-9\-]+", kw.lower()):
            if len(word) > 3 and word not in {"with", "from", "that", "this", "have", "more", "into", "their"}:
                domain_terms.add(word)

    matches = [w for w in domain_terms if w in full_text]
    # If 2 or more domain terms match anywhere in full text, or 1 in the title
    if len(matches) >= 2:
        return True, f"Domain terms matched: {matches[:3]}"
    elif len(matches) == 1 and any(w in title for w in matches):
        return True, f"Domain term matched in title: {matches[0]}"

    return False, "No substantive domain keyword alignment with organization profile"


@tool
def execute_discovery_scan() -> dict[str, Any]:
    """Discover authentic grant opportunities by querying grants.gov with targeted org profile keywords.

    Uses high-precision quoted search queries and pre-filters opportunities against the
    nonprofit's domain and active window to avoid wasting resources on irrelevant grants.

    Returns:
        Dictionary containing the list of newly found grant opportunities.
    """
    profile_data = storage.get_org_profile("default")
    if not profile_data:
        return {"count": 0, "grants": [], "error": "No org profile found"}

    raw_keywords = profile_data.get("keywords", [])
    # Build list of distinct targeted search queries (exact phrases)
    search_queries = []
    for kw in raw_keywords[:5]:
        kw_clean = kw.strip()
        if not kw_clean.startswith('"') and not kw_clean.endswith('"'):
            search_queries.append(f'"{kw_clean}"')
        else:
            search_queries.append(kw_clean)

    if not search_queries:
        search_queries = ['"STEM education"', '"robotics"', '"computer science education"', '"after-school"']

    logger.info(f"Executing discovery scan across {len(search_queries)} targeted search queries: {search_queries}")

    seen_ids = set()
    candidate_grants = []
    for query in search_queries:
        try:
            search_res = search_grants(keywords=query, max_results=6)
            for g in search_res.get("grants", []):
                gid_num = g.get("id")
                if gid_num and gid_num not in seen_ids:
                    seen_ids.add(gid_num)
                    candidate_grants.append(g)
        except Exception as e:
            logger.warning(f"Search query '{query}' failed: {e}")

    new_grants = []
    for g in candidate_grants:
        gid = f"grants-gov-{g.get('id')}"
        if storage.grant_exists(gid):
            continue

        # Fetch full opportunity details
        try:
            detail_res = fetch_grant_details(opportunity_id=int(g.get("id")))
            grant_info = detail_res.get("grant") or g
            grant_info["grant_id"] = gid
        except Exception as e:
            logger.warning(f"Failed to fetch details for grant {gid}: {e}")
            continue

        # 1. Filter out closed/inactive opportunities
        if not is_active_opportunity(
            close_date=grant_info.get("close_date", ""),
            title=grant_info.get("title", ""),
            original_due_date=grant_info.get("original_due_date", ""),
            fiscal_year=grant_info.get("fiscal_year"),
            has_packages=grant_info.get("has_packages", True),
        ):
            logger.info(f"Filtered out inactive/closed opportunity: {gid} - {grant_info.get('title')}")
            continue

        # 2. Pre-filter by domain relevance to avoid scanning unnecessary grants
        relevant, reason = is_domain_relevant(grant_info, profile_data)
        if not relevant:
            logger.info(f"Pre-filtered unrelated opportunity: {gid} ('{grant_info.get('title')}') - {reason}")
            continue

        logger.info(f"Discovered authentic candidate grant: {gid} ('{grant_info.get('title')}') - {reason}")
        new_grants.append(grant_info)

        # Cap at 6 authentic candidates per cycle for fast response
        if len(new_grants) >= 6:
            break

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
        action = "auto_draft_queued"
        # Mark grant for asynchronous autonomous drafting without blocking discovery
        saved_grant["status"] = "drafting"
        saved_grant["is_drafting"] = True
        storage.save_grant(saved_grant)
        draft_status = "queued"
    elif total_score < 50:
        action = "archived_silently"
        saved_grant["status"] = "archived"
        storage.save_grant(saved_grant)
    else:
        action = "flagged_for_review"
        saved_grant["status"] = "matched"
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


from backend.optimization import get_model_for_agent

def create_orchestrator_agent() -> Agent:
    """Create and configure the Orchestrator Agent.

    Returns:
        A Strands Agent configured for multi-agent graph orchestration.
    """
    model_cfg = get_model_for_agent("orchestrator")
    model = BedrockModel(
        model_id=model_cfg.model_id,
        region_name=model_cfg.region,
        boto_client_config=Config(read_timeout=3600, connect_timeout=900, retries={'max_attempts': 3, 'mode': 'standard'})
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


async def run_orchestrator() -> str:
    """Run the Orchestrator Agent to perform discovery and routing autonomously."""
    import asyncio
    
    agent = create_orchestrator_agent()
    
    def _run():
        return agent("Execute a complete autonomous scan using execute_discovery_scan. Then, for EVERY new grant opportunity found, use evaluate_and_route_grant to score and route it. Finally, summarize the results.")

    result = await asyncio.to_thread(_run)
    return str(result)


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
