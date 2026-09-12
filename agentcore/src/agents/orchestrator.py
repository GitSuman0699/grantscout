"""Orchestrator Agent — Central coordinator using the Strands SDK Graph pattern for autonomous routing.

This agent orchestrates the complete GrantScout lifecycle as a real Strands SDK Graph DAG:
1. Scanner Node: Scans grants.gov for new funding opportunities matching the org profile.
2. Matcher Node: Evaluates fit & computes 5-dimension match scores for each discovery.
3. Drafter Node (Conditional): Auto-triggered only when high-scoring grants (≥80) are found.
4. Deadline Node: Sweeps active deadlines and generates proactive alerts.

The Graph uses conditional edges to implement intelligent routing:
- Scanner → Matcher (always)
- Matcher → Drafter (conditional: only if high-score grants exist)
- Matcher → Deadline (always)
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

from botocore.config import Config
from strands import Agent, tool
from strands.models.bedrock import BedrockModel
from strands.multiagent.graph import GraphBuilder

# Dynamic MCP tools injected from mcp_tools proxy module
from mcp_tools import (
    search_grants,
    fetch_grant_details,
    save_matched_grant,
    retrieve_org_profile,
    check_grant_exists,
    scan_upcoming_deadlines,
    save_application_draft,
    get_existing_application_draft,
    update_draft_section,
    generate_budget_csv,
    send_deadline_alert,
)
from agents.scanner import is_active_opportunity
from agents.matcher import evaluate_grant_structured, score_grant
from agents.deadline import run_deadline_check

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
    profile_res = retrieve_org_profile()
    profile_data = profile_res.get("profile") if isinstance(profile_res, dict) and "profile" in profile_res else profile_res
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
        try:
            exists_res = check_grant_exists(grant_id=gid)
            if exists_res.get("exists"):
                continue
        except Exception as e:
            logger.warning(f"Check exists failed for {gid}: {e}")

        # Fetch full opportunity details
        try:
            detail_res = fetch_grant_details(opportunity_id=str(g.get("id")))
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

    Graph Routing Policy (implemented via Strands Graph conditional edges):
    - Score >= 80: Status -> 'matched', auto-triggers pre-filling application draft
    - Score 50-79: Status -> 'matched', flags for manual review
    - Score < 50: Status -> 'archived'

    Args:
        grant_info: Detailed grant opportunity dictionary.

    Returns:
        Routing decision and match score details.
    """
    # Run structured evaluation via Matcher Agent (persists via MCP tool save_matched_grant)
    evaluation = evaluate_grant_structured(grant_info, persist=True)
    gid = evaluation.grant_id
    total_score = evaluation.match_score.total

    action = "flagged_for_review"
    draft_status = None

    if total_score >= 80:
        action = "auto_draft_queued"
        draft_status = "queued"
    elif total_score < 50:
        action = "archived_silently"
    else:
        action = "flagged_for_review"

    return {
        "grant_id": gid,
        "title": grant_info.get("title", "Grant Opportunity"),
        "total_score": total_score,
        "action": action,
        "draft_status": draft_status,
    }


# ──────────────────────────────────────────────
#  Agent System Prompts
# ──────────────────────────────────────────────

SCANNER_GRAPH_PROMPT = """You are the Scanner Node in the GrantScout Graph pipeline.
Execute a discovery scan using `execute_discovery_scan` to find new federal grant opportunities
matching the organization's profile and keywords. Report the number of new grants discovered."""

MATCHER_GRAPH_PROMPT = """You are the Matcher Node in the GrantScout Graph pipeline.
For each new grant opportunity found by the Scanner, use `evaluate_and_route_grant` to:
1. Score it against the organization profile (5-dimension rubric)
2. Route it based on score: ≥80 auto-draft, 50-79 review, <50 archive
Report the routing decisions for all evaluated grants."""

DRAFTER_GRAPH_PROMPT = """You are the Drafter Node in the GrantScout Graph pipeline.
You are only activated when high-scoring grants (≥80) have been queued for drafting.
YOUR MISSION:
Identify any grants queued for drafting or with fit score ≥80.
For each high-scoring opportunity, invoke `execute_swarm_proposal_drafting(grant_id=...)` to trigger the authentic 5-Agent Collaborative Drafter Swarm to author the complete 6-section proposal.
Report completion for all drafted opportunities."""

DEADLINE_GRAPH_PROMPT = """You are the Deadline Monitor Node in the GrantScout Graph pipeline.
Sweep all active grant opportunities and check for upcoming deadlines.
Generate proactive alerts for any grants closing within the next 14 days."""

ORCHESTRATOR_SYSTEM_PROMPT = """You are the Lead Autonomous Orchestrator for GrantScout.

YOUR MISSION:
Autonomously run the end-to-end grant discovery, scoring, and routing lifecycle in the background. Only surface high-value opportunities that require real human decisions, fulfilling the hackathon promise of silent background execution.

WORKFLOW:
1. Execute discovery using `execute_discovery_scan`.
2. For each discovered opportunity, evaluate fit and execute Graph routing using `evaluate_and_route_grant`.
3. Perform a deadline check across the pipeline using `scan_upcoming_deadlines`.
"""


# ──────────────────────────────────────────────
#  Strands Graph DAG Builder
# ──────────────────────────────────────────────


from shared.optimization import get_model_for_agent
from mcp_tools import scan_upcoming_deadlines


@tool
def execute_swarm_proposal_drafting(grant_id: str) -> dict[str, Any]:
    """Execute the authentic 5-Agent Collaborative Drafter Swarm to author a full 6-section proposal for a qualified grant.
    
    Args:
        grant_id: The ID of the grant opportunity to author a proposal for.
        
    Returns:
        Summary of the drafted proposal sections and completion status.
    """
    grant = None
    try:
        from backend.storage.local_storage import storage
        grant = storage.get_grant(grant_id)
        if not grant:
            clean_num = grant_id.replace("grants-gov-", "")
            for g in storage.list_grants():
                if str(g.get("id")) == clean_num or g.get("grant_id") == grant_id:
                    grant = g
                    break
    except Exception:
        pass

    if not grant:
        # Fallback via MCP tool fetch_grant_details
        try:
            from mcp_tools import fetch_grant_details
            clean_num = grant_id.replace("grants-gov-", "")
            details_res = fetch_grant_details(opportunity_id=clean_num)
            grant = details_res.get("grant") if isinstance(details_res, dict) else None
            if grant and "grant_id" not in grant:
                grant["grant_id"] = grant_id
        except Exception as e:
            logger.warning(f"Failed to fetch details via MCP for grant {grant_id}: {e}")

    if not grant:
        grant = {"grant_id": grant_id, "title": f"Opportunity {grant_id}"}
        
    from agents.drafter import draft_application_structured
    draft_result = draft_application_structured(grant)
    return {
        "success": True,
        "grant_id": grant_id,
        "sections_count": len(draft_result.sections),
        "completion_percentage": draft_result.completion_percentage,
        "status": "completed",
    }


def _create_bedrock_model(agent_name: str) -> BedrockModel:
    """Create a BedrockModel configured for the given agent tier."""
    model_cfg = get_model_for_agent(agent_name)
    return BedrockModel(
        model_id=model_cfg.model_id,
        region_name=model_cfg.region,
        boto_client_config=Config(
            read_timeout=3600,
            connect_timeout=900,
            retries={'max_attempts': 3, 'mode': 'standard'}
        ),
    )


def _has_high_score_grants(state: Any) -> bool:
    """Graph edge condition: only route to Drafter node if high-scoring grants (≥80) are queued.
    
    Evaluates both:
    1. Structured Matcher Node result in GraphState (checking for action='auto_draft_queued')
    2. Persistent storage for any grant with match_score >= 80 or status='queued'
    """
    # 1. Check matcher node results in state if available
    try:
        results = getattr(state, "results", {})
        if isinstance(results, dict) and "matcher" in results:
            matcher_res = results["matcher"]
            res_obj = getattr(matcher_res, "result", None)
            if hasattr(res_obj, "message") and isinstance(res_obj.message, dict):
                content = str(res_obj.message.get("content", []))
                if "auto_draft_queued" in content:
                    return True
    except Exception as e:
        logger.debug(f"Error inspecting matcher state results: {e}")

    # 2. Check persistent storage for high-scoring queued opportunities
    try:
        from backend.storage.local_storage import storage
        all_grants = storage.list_grants()
        for g in all_grants:
            score = g.get("match_score", {}).get("total", 0) if isinstance(g.get("match_score"), dict) else (g.get("fit_score") or 0)
            if score >= 80 and g.get("status") in ("queued", "ready_for_review", "matched"):
                draft = storage.find_application_by_grant_id(g.get("grant_id", ""))
                if not draft or draft.get("completion_percentage", 0) < 100:
                    return True
    except Exception as e:
        logger.debug(f"Error checking storage in edge condition: {e}")

    return False


def build_orchestration_graph(remote_tools: list[Any] | None = None):
    """Build the GrantScout pipeline as a real Strands SDK Graph DAG.

    Graph Topology:
        Scanner → Matcher → Drafter (conditional: high-scoring grants exist)
                          → Deadline (always)
    """
    scanner_tools: list[Any] = [execute_discovery_scan, retrieve_org_profile, search_grants, fetch_grant_details]
    matcher_tools: list[Any] = [evaluate_and_route_grant, retrieve_org_profile, save_matched_grant]
    drafter_tools: list[Any] = [execute_swarm_proposal_drafting, retrieve_org_profile, save_application_draft, get_existing_application_draft, update_draft_section, generate_budget_csv]
    deadline_tools: list[Any] = [scan_upcoming_deadlines, send_deadline_alert]

    if remote_tools:
        for t in remote_tools:
            name = getattr(t, "tool_name", getattr(t, "__name__", ""))
            if name in ["execute_discovery_scan", "search_grants"]:
                scanner_tools.append(t)
            elif name in ["evaluate_and_route_grant", "save_matched_grant"]:
                matcher_tools.append(t)
            elif name in ["save_application_draft", "update_draft_section"]:
                drafter_tools.append(t)
            elif name in ["scan_upcoming_deadlines"]:
                deadline_tools.append(t)

    scanner_agent = Agent(
        name="scanner",
        model=_create_bedrock_model("scanner"),
        system_prompt=SCANNER_GRAPH_PROMPT,
        tools=scanner_tools,
    )

    matcher_agent = Agent(
        name="matcher",
        model=_create_bedrock_model("matcher"),
        system_prompt=MATCHER_GRAPH_PROMPT,
        tools=matcher_tools,
    )

    drafter_agent = Agent(
        name="drafter",
        model=_create_bedrock_model("drafter"),
        system_prompt=DRAFTER_GRAPH_PROMPT,
        tools=drafter_tools,
    )

    deadline_agent = Agent(
        name="deadline",
        model=_create_bedrock_model("deadline"),
        system_prompt=DEADLINE_GRAPH_PROMPT,
        tools=deadline_tools,
    )

    # Build the Graph DAG using Strands SDK GraphBuilder
    builder = GraphBuilder()
    builder.set_graph_id("grantscout_pipeline")

    # Add nodes
    builder.add_node(scanner_agent, "scanner")
    builder.add_node(matcher_agent, "matcher")
    builder.add_node(drafter_agent, "drafter")
    builder.add_node(deadline_agent, "deadline")

    # Define edges — the core of the Graph Routing Pattern
    builder.add_edge("scanner", "matcher")                                    # Always: scan results flow to scoring
    builder.add_edge("matcher", "drafter", condition=_has_high_score_grants)   # Conditional: only if ≥80 scoring grants queued
    builder.add_edge("matcher", "deadline")                                   # Always: deadline sweep after scoring

    # Set entry point and timeouts
    builder.set_entry_point("scanner")
    builder.set_execution_timeout(1800.0)    # 30 min total pipeline timeout
    builder.set_node_timeout(600.0)          # 10 min per individual node

    graph = builder.build()
    logger.info("GrantScout Graph DAG built: Scanner → Matcher → [Drafter (conditional)] + Deadline")
    return graph


# Drafter tools are now dynamically injected via MCP


def create_orchestrator_agent(remote_tools: list[Any] | None = None) -> Agent:
    """Create and configure the Orchestrator Agent (legacy single-agent mode).

    This is maintained for backward compatibility with the /api/agent/scan endpoint.
    The Graph-based execution (run_full_orchestration_cycle) is the primary path.

    Returns:
        A Strands Agent configured for multi-agent orchestration.
    """
    model_cfg = get_model_for_agent("orchestrator")
    model = BedrockModel(
        model_id=model_cfg.model_id,
        region_name=model_cfg.region,
        boto_client_config=Config(read_timeout=3600, connect_timeout=900, retries={'max_attempts': 3, 'mode': 'standard'})
    )

    tools: list[Any] = [execute_discovery_scan, evaluate_and_route_grant, retrieve_org_profile]
    if remote_tools:
        tools.extend(remote_tools)

    agent = Agent(
        model=model,
        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
        tools=tools,
    )

    logger.info("Orchestrator Agent initialized")
    return agent


def format_graph_event(event: Any) -> str | None:
    """Format authentic Strands SDK Graph DAG events into human-readable telemetry lines."""
    event_type = getattr(event, "type", None) or (event.get("type") if isinstance(event, dict) else None)
    
    if event_type == "multiagent_node_start":
        node_id = getattr(event, "node_id", None) or (event.get("node_id") if isinstance(event, dict) else "Node")
        return f"[{str(node_id).upper()}] Node activated in GrantScout Discovery Graph DAG."
        
    elif event_type == "multiagent_handoff":
        raw_src = getattr(event, "from_node_ids", None) or (event.get("from_node_ids") if isinstance(event, dict) else [])
        raw_dst = getattr(event, "to_node_ids", None) or (event.get("to_node_ids") if isinstance(event, dict) else [])
        src_list: list[str] = [str(x) for x in raw_src] if isinstance(raw_src, (list, tuple)) else ([str(raw_src)] if raw_src else [])
        dst_list: list[str] = [str(x) for x in raw_dst] if isinstance(raw_dst, (list, tuple)) else ([str(raw_dst)] if raw_dst else [])
        src = ", ".join(src_list).upper()
        dst = ", ".join(dst_list).upper()
        msg = getattr(event, "message", None) or (event.get("message") if isinstance(event, dict) else None)
        if msg:
            return f"[GRAPH ROUTING: {src} -> {dst}] \"{msg}\""
        return f"[GRAPH ROUTING: {src} -> {dst}] Evaluated edge condition. Advancing pipeline stage."
        
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
        node_id = getattr(event, "node_id", None) or (event.get("node_id") if isinstance(event, dict) else "Node")
        return f"[{str(node_id).upper()}] Node processing complete."
        
    elif event_type == "multiagent_result":
        return "[GRAPH] Discovery Graph DAG orchestration complete."

    return None


async def run_orchestrator(remote_tools: list[Any] | None = None, status_callback: Any | None = None) -> str:
    """Run the Orchestrator to perform discovery and routing autonomously via the Strands Graph DAG."""
    summary = await run_full_orchestration_cycle(remote_tools=remote_tools, status_callback=status_callback)
    return f"ORCHESTRATION COMPLETE: {summary}"


async def run_graph_orchestration_cycle(
    prompt: str = "",
    remote_tools: list[Any] | None = None,
    status_callback: Any | None = None,
) -> dict[str, Any]:
    """Execute the complete GrantScout pipeline as a Strands SDK Graph DAG with live event streaming."""
    logger.info("Starting GrantScout Graph DAG orchestration cycle...")
    if status_callback:
        status_callback("[GRAPH INITIALIZED] Building GrantScout Discovery Graph DAG (Scanner -> Matcher -> Drafter / Deadline)...")

    graph = build_orchestration_graph(remote_tools)

    task = prompt or (
        "Run the complete GrantScout discovery cycle. "
        "Scanner: scan for new federal grants matching the org profile. "
        "Matcher: score each discovered grant and route based on fit score. "
        "Drafter: if any high-scoring grants are queued, begin pre-filling proposals. "
        "Deadline: check all active grants for upcoming deadlines."
    )

    completed_nodes: list[str] = []
    total_nodes = 4
    status = "completed"

    try:
        async for event in graph.stream_async(task):
            event_type = getattr(event, "type", None) or (event.get("type") if isinstance(event, dict) else None)
            if event_type == "multiagent_node_stop":
                nid = getattr(event, "node_id", None) or (event.get("node_id") if isinstance(event, dict) else None)
                if nid and nid not in completed_nodes:
                    completed_nodes.append(str(nid))
            elif event_type == "multiagent_result":
                res_status = getattr(event, "status", None) or (event.get("status") if isinstance(event, dict) else None)
                if res_status:
                    status = str(res_status)

            if status_callback:
                line = format_graph_event(event)
                if line:
                    status_callback(line)
    except Exception as e:
        logger.error(f"Error during Graph DAG streaming: {e}")
        if status_callback:
            status_callback(f"[GRAPH ERROR] {e}")
        raise e

    summary = {
        "status": status,
        "completed_nodes": completed_nodes,
        "total_nodes": total_nodes,
    }
    logger.info(f"Graph DAG cycle complete. Nodes: {len(completed_nodes)}/{total_nodes}, Status: {status}")
    return summary


async def run_full_orchestration_cycle(
    prompt: str = "",
    remote_tools: list[Any] | None = None,
    status_callback: Any | None = None,
) -> dict[str, Any]:
    """Execute a complete autonomous scan, match, draft, and deadline cycle via Graph DAG."""
    try:
        return await run_graph_orchestration_cycle(prompt, remote_tools, status_callback)
    except Exception as e:
        logger.error(f"Graph DAG execution failed: {e}")
        raise e


def _run_sequential_fallback() -> dict[str, Any]:
    """Fallback: sequential execution without Graph DAG (used if Graph execution fails)."""
    logger.info("Running sequential fallback orchestration cycle...")

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

    logger.info(f"Sequential fallback cycle complete. Processed {len(grants_found)} opportunities.")
    return summary
