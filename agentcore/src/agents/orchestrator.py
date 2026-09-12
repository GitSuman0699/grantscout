"""Orchestrator Agent — Central coordinator for Cognitive AI evaluation and routing.

In GrantScout's 3-Tier Architecture:
1. Tier 1 (Presentation): React frontend triggers discovery cycles and receives real-time SSE progress.
2. Tier 2 (Application Backend): Pure Python deterministic discovery (Grants.gov API ingestion,
   query expansion, date math, RFI filtering) and deadline sweeps (<14 days).
3. Tier 3 (Cognitive AI - AgentCore): This module coordinates cognitive reasoning:
   - Matcher Node: Evaluates discovered opportunities across a 5-dimension rubric using Bedrock Claude
     and routes them into qualified (≥80), manual review (50-79), or silent archive (<50).

Autonomous execution is orchestrated with real-time SSE status streaming for the user interface.
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

from shared.optimization import get_model_for_agent

# Dynamic MCP tools injected from mcp_tools proxy module
from mcp_tools import (
    fetch_grant_details,
    save_matched_grant,
    retrieve_org_profile,
    scan_upcoming_deadlines,
)
from agents.matcher import (
    evaluate_all_discovered_grants,
    evaluate_all_discovered_grants_async,
    evaluate_grant_structured,
    evaluate_grant_structured_async,
    score_grant,
)
try:
    from backend.tools.notifications import scan_upcoming_deadlines as run_deadline_check
except ImportError:
    from mcp_tools import scan_upcoming_deadlines as run_deadline_check

try:
    from backend.discovery import execute_discovery_scan
except ImportError:
    execute_discovery_scan = None

logger = logging.getLogger(__name__)


@tool
def evaluate_and_route_grant(grant_id: str = "", grant_info: dict[str, Any] | None = None) -> dict[str, Any]:
    """Score a grant against the organization profile and route according to fit score.

    Evaluation Routing Policy:
    - Score >= 80: Status -> 'matched', Action -> 'qualified_match' (highly qualified fit)
    - Score 50-79: Status -> 'matched', Action -> 'flagged_for_review'
    - Score < 50: Status -> 'archived', Action -> 'archived_silently'

    Args:
        grant_id: Unique identifier for the grant (e.g. 'grants-gov-359157').
        grant_info: Optional detailed grant opportunity dictionary.

    Returns:
        Routing decision and match score details.
    """
    if not grant_info and grant_id:
        try:
            from backend.storage.local_storage import storage
            grant_info = storage.get_grant(grant_id)
        except Exception:
            pass

        if not grant_info:
            try:
                from mcp_tools import fetch_grant_details
                clean_num = grant_id.replace("grants-gov", "").replace("-", "").strip()
                details_res = fetch_grant_details(opportunity_id=clean_num)
                grant_info = details_res.get("grant") or {}
                if grant_info and "grant_id" not in grant_info:
                    grant_info["grant_id"] = grant_id
            except Exception as e:
                logger.warning(f"Failed to fetch details for {grant_id}: {e}")

    if not grant_info:
        logger.error(f"evaluate_and_route_grant failed: no grant details found for {grant_id}")
        return {"error": f"Grant details not found for {grant_id}"}

    # Run structured evaluation via Matcher Agent (persists via MCP tool save_matched_grant)
    evaluation = evaluate_grant_structured(grant_info, persist=True)
    gid = evaluation.grant_id
    total_score = evaluation.match_score.total

    if total_score >= 80:
        action = "qualified_match"
    elif total_score < 50:
        action = "archived_silently"
    else:
        action = "flagged_for_review"

    return {
        "grant_id": gid,
        "title": grant_info.get("title", "Grant Opportunity"),
        "total_score": total_score,
        "action": action,
    }


# ──────────────────────────────────────────────
#  Agent System Prompts
# ──────────────────────────────────────────────

MATCHER_GRAPH_PROMPT = """You are the Matcher Node in the GrantScout Graph pipeline.
YOUR MISSION:
Call `evaluate_all_discovered_grants()` to score and route all candidate grant opportunities against the organization profile across the 5-dimension rubric. Alternatively, call `evaluate_and_route_grant(grant_id=...)` for each grant ID.

STRICT NO-SUMMARY RULE (CRITICAL):
- Do NOT output conversational text, scoring tables, markdown reports, status recaps, or routing summaries.
- Never output verification sections or next-step plans.
- Once evaluation finishes, output ONLY: "Scoring complete: qualified opportunities routed." if any grant scored >= 80, else "Scoring and routing complete." and terminate immediately."""


ORCHESTRATOR_SYSTEM_PROMPT = """You are the Lead Autonomous Orchestrator for GrantScout.

YOUR MISSION:
Autonomously run the grant evaluation, scoring, and pipeline routing lifecycle in the background.

WORKFLOW:
1. For each candidate opportunity, evaluate fit across the 5-dimension rubric using `evaluate_all_discovered_grants` or `evaluate_and_route_grant`.

STRICT NO-SUMMARY RULE (CRITICAL):
- Do NOT output conversational text, markdown summaries, or status tables.
- Output ONLY: "Orchestration complete." upon completion."""



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


# ──────────────────────────────────────────────
#  Strands Graph DAG Builder
# ──────────────────────────────────────────────


def build_orchestration_graph(remote_tools: list[Any] | None = None):
    """Build the GrantScout pipeline as a real Strands SDK Graph DAG.

    Graph Topology:
        Matcher (Cognitive Reasoning Node)
    """
    matcher_tools: list[Any] = [evaluate_all_discovered_grants, evaluate_and_route_grant, retrieve_org_profile, save_matched_grant]

    if remote_tools:
        for t in remote_tools:
            name = getattr(t, "tool_name", getattr(t, "__name__", ""))
            if name in ["evaluate_and_route_grant", "save_matched_grant"]:
                matcher_tools.append(t)

    matcher_agent = Agent(
        name="matcher",
        model=_create_bedrock_model("matcher"),
        system_prompt=MATCHER_GRAPH_PROMPT,
        tools=matcher_tools,
    )

    # Build the Graph DAG using Strands SDK GraphBuilder
    builder = GraphBuilder()
    builder.set_graph_id("grantscout_pipeline")

    builder.add_node(matcher_agent, "matcher")

    # Set entry point and timeouts
    builder.set_entry_point("matcher")
    builder.set_execution_timeout(1800.0)    # 30 min total pipeline timeout
    builder.set_node_timeout(600.0)          # 10 min per individual node

    graph = builder.build()
    logger.info("GrantScout Graph DAG built: Matcher")
    return graph




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

    tools: list[Any] = [evaluate_all_discovered_grants, evaluate_and_route_grant, retrieve_org_profile]
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
        status_callback("[GRAPH INITIALIZED] Building GrantScout Evaluation Graph DAG (Matcher)...")

    graph = build_orchestration_graph(remote_tools)

    task = prompt or (
        "Run the GrantScout cognitive evaluation and routing cycle. "
        "Matcher: score and route all candidate discovered grants across the 5-dimension rubric. "
        "CRITICAL RULE: All agents must output ZERO conversational text, tables, or summaries. Minimal tool calls and one-line completion only."
    )

    completed_nodes: list[str] = []
    total_nodes = 1
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
    """Execute high-performance autonomous cycle: Tier 2 Discovery -> Tier 3 Parallel Matcher -> Deadline Sweep."""
    logger.info("Starting GrantScout high-performance discovery cycle...")
    if status_callback:
        status_callback("[PIPELINE INITIALIZED] Launching high-performance autonomous discovery cycle...")

    # Stage 1: Deterministic Backend Discovery Scan (Zero LLM token waste, sub-second API fetch)
    if status_callback:
        status_callback("[DISCOVERY] Ingesting authentic grants from Grants.gov API with expanded query variations...")

    try:
        from backend.discovery import execute_discovery_scan
        discovery_res: dict[str, Any] = execute_discovery_scan()
    except ImportError:
        discovery_res = {"count": 0, "grants": []}
    raw_grants = discovery_res.get("grants") if isinstance(discovery_res, dict) else []
    grants_found: list[dict[str, Any]] = raw_grants if isinstance(raw_grants, list) else []
    count_found = len(grants_found)

    if status_callback:
        status_callback(f"[DISCOVERY COMPLETE] Discovered {count_found} active candidate opportunities matching criteria.")

    # Stage 2: Parallel Cognitive Matcher Agent (Real LLM 5-dimension rubric scoring in parallel)
    if status_callback:
        status_callback(f"[MATCHER] Evaluating candidate opportunities concurrently via Claude Bedrock...")

    eval_res = await evaluate_all_discovered_grants_async()
    evaluated = eval_res.get("evaluated", [])

    matched_count = sum(1 for e in evaluated if e.get("action") in ("qualified_match", "auto_draft_queued"))
    review_count = sum(1 for e in evaluated if e.get("action") == "flagged_for_review")

    if status_callback:
        status_callback(
            f"[MATCH COMPLETE] Evaluated {len(evaluated)} opportunities ({matched_count} qualified matches, {review_count} flagged for review)."
        )

    # Stage 3: Deterministic Deadline & Compliance Sweep (Tier 2 Backend)
    if status_callback:
        status_callback("[DEADLINE] Scanning active pipeline opportunities for upcoming closing windows (<14 days)...")

    try:
        from backend.tools.notifications import scan_upcoming_deadlines
        deadline_summary = scan_upcoming_deadlines(auto_alert=True)
    except ImportError:
        try:
            from mcp_tools import scan_upcoming_deadlines
            deadline_summary = scan_upcoming_deadlines()
        except Exception:
            deadline_summary = {"count": 0, "deadlines": []}

    if status_callback:
        status_callback(
            f"[ORCHESTRATION COMPLETE] Discovery cycle finished. Processed {count_found} opportunities. Pipeline updated."
        )

    return {
        "status": "completed",
        "grants_scanned": count_found,
        "grants_evaluated": len(evaluated),
        "routed_opportunities": evaluated,
        "deadline_summary": deadline_summary,
    }

