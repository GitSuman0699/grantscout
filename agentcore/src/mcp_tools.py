"""MCP Tool Proxies for AgentCore.

These are thin @tool-decorated wrappers that Strands agents can use directly.
Under the hood, each function calls the corresponding tool on the Render MCP Server
via the MCP Client session stored in the global `_mcp_session`.

This module is the bridge between the Strands Agent SDK (which expects local @tool
functions) and the remote MCP Server (which hosts the real implementations on Render).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from strands import tool

logger = logging.getLogger(__name__)

# Global MCP session and event loop
_mcp_session = None
_mcp_loop = None


def set_mcp_session(session, loop=None):
    """Set the global MCP client session for all tool proxies."""
    global _mcp_session, _mcp_loop
    _mcp_session = session
    if loop is not None:
        _mcp_loop = loop
    else:
        try:
            import asyncio
            _mcp_loop = asyncio.get_running_loop()
        except RuntimeError:
            _mcp_loop = None


async def _call_remote_tool(name: str, arguments: dict[str, Any]) -> Any:
    """Call a tool on the remote Render MCP server."""
    if _mcp_session is None:
        # Check if local fallback is available for local test environments
        try:
            from backend.tools import application, compliance, grants_api, notifications, org_profile, rag_search
            for mod in (grants_api, org_profile, rag_search, application, compliance, notifications):
                if hasattr(mod, name):
                    fn = getattr(mod, name)
                    raw_fn = getattr(fn, "_tool_func", getattr(fn, "__wrapped__", fn))
                    if callable(raw_fn):
                        return raw_fn(**arguments)
        except Exception as e:
            logger.warning(f"Local fallback execution for '{name}' failed: {e}")
        raise RuntimeError(f"MCP session not initialized and local fallback failed for '{name}'. Call set_mcp_session() first.")
    result = await _mcp_session.call_tool(name, arguments=arguments)
    # MCP returns content as a list of content blocks
    if hasattr(result, "content") and result.content:
        text = result.content[0].text if hasattr(result.content[0], "text") else str(result.content[0])
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return text
    return str(result)


def _call_remote_tool_sync(name: str, arguments: dict[str, Any]) -> Any:
    """Synchronous wrapper for calling remote MCP tools."""
    import asyncio
    global _mcp_loop
    if _mcp_session is None:
        # Check if local fallback is available for local test environments
        try:
            from backend.tools import application, compliance, grants_api, notifications, org_profile, rag_search
            for mod in (grants_api, org_profile, rag_search, application, compliance, notifications):
                if hasattr(mod, name):
                    fn = getattr(mod, name)
                    raw_fn = getattr(fn, "_tool_func", getattr(fn, "__wrapped__", fn))
                    if callable(raw_fn):
                        return raw_fn(**arguments)
        except Exception as e:
            logger.warning(f"Local fallback execution for '{name}' failed: {e}")
        raise RuntimeError(f"MCP session not initialized and local fallback failed for '{name}'. Call set_mcp_session() first.")

    if _mcp_loop is not None and _mcp_loop.is_running():
        active_loop = _mcp_loop
        try:
            current_loop = asyncio.get_running_loop()
            if current_loop is active_loop:
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(
                        lambda: asyncio.run_coroutine_threadsafe(
                            _call_remote_tool(name, arguments), active_loop
                        ).result(timeout=120)
                    ).result()
        except RuntimeError:
            pass  # Running in a worker thread (e.g. asyncio.to_thread in Strands)
        future = asyncio.run_coroutine_threadsafe(_call_remote_tool(name, arguments), active_loop)
        return future.result(timeout=120)
    else:
        return asyncio.run(_call_remote_tool(name, arguments))


# ==========================================
#  Grant API Tools
# ==========================================

@tool
def search_grants(keywords: str = "", max_results: int = 10) -> dict[str, Any]:
    """Search grants.gov for federal funding opportunities matching keywords.

    Args:
        keywords: Search terms (e.g. 'STEM education', 'robotics youth').
        max_results: Maximum opportunities to return (default: 10, max: 25).

    Returns:
        Dictionary containing matching grant opportunities.
    """
    return _call_remote_tool_sync("search_grants", {"keywords": keywords, "max_results": max_results})


@tool
def fetch_grant_details(opportunity_id: str | int) -> dict[str, Any]:
    """Fetch full details for a specific grant opportunity from grants.gov.

    Args:
        opportunity_id: The grants.gov opportunity ID.

    Returns:
        Dictionary containing full grant details.
    """
    return _call_remote_tool_sync("fetch_grant_details", {"opportunity_id": str(opportunity_id)})


# ==========================================
#  Org Profile Tools
# ==========================================

@tool
def retrieve_org_profile() -> dict[str, Any]:
    """Retrieve the nonprofit organization's profile.

    Returns:
        Dictionary containing the org profile data.
    """
    return _call_remote_tool_sync("retrieve_org_profile", {})


@tool
def check_grant_exists(grant_id: str) -> dict[str, Any]:
    """Check if a grant has already been discovered and stored.

    Args:
        grant_id: The unique ID of the grant to check.

    Returns:
        Dictionary with exists status.
    """
    return _call_remote_tool_sync("check_grant_exists", {"grant_id": grant_id})


@tool
def save_matched_grant(
    grant_id: str, title: str, agency: str, synopsis: str,
    award_ceiling: float, award_floor: float, close_date: str,
    status: str, match_score: dict, match_reasoning: str,
    opportunity_id: str | int | None = None,
    opportunity_number: str | None = None,
    application_url: str | None = None,
) -> dict[str, Any]:
    """Save a scored/matched grant to storage.

    Args:
        grant_id: Unique grant identifier.
        title: Grant title.
        agency: Funding agency.
        synopsis: Grant synopsis.
        award_ceiling: Maximum award amount.
        award_floor: Minimum award amount.
        close_date: Application deadline.
        status: Grant status (matched/archived).
        match_score: Scoring breakdown dict.
        match_reasoning: Text reasoning for the score.
        opportunity_id: Numeric Grants.gov opportunity ID.
        opportunity_number: Federal solicitation number.
        application_url: Direct URL to the opportunity.

    Returns:
        Dictionary with save confirmation.
    """
    args = {
        "grant_id": grant_id, "title": title, "agency": agency,
        "synopsis": synopsis, "award_ceiling": award_ceiling,
        "award_floor": award_floor, "close_date": close_date,
        "status": status, "match_score": match_score,
        "match_reasoning": match_reasoning,
    }
    if opportunity_id is not None:
        args["opportunity_id"] = opportunity_id
    if opportunity_number is not None:
        args["opportunity_number"] = opportunity_number
    if application_url is not None:
        args["application_url"] = application_url

    return _call_remote_tool_sync("save_matched_grant", args)


# ==========================================
#  RAG Search Tools
# ==========================================

@tool
def query_knowledge_base(query: str, top_k: int = 3) -> dict[str, Any]:
    """Search the organization's knowledge base for relevant context.

    Args:
        query: Natural language search query.
        top_k: Number of results to return.

    Returns:
        Dictionary containing matching knowledge base entries.
    """
    return _call_remote_tool_sync("query_knowledge_base", {"query": query, "top_k": top_k})


# ==========================================
#  Application Tools
# ==========================================

@tool
def generate_budget_csv(
    grant_id: str, direct_personnel: float, fringe_benefits: float,
    travel: float, supplies: float, other: float, indirect_rate_pct: float
) -> dict[str, Any]:
    """Generate a structured CSV for the SF-424 budget template.

    Args:
        grant_id: The ID of the grant.
        direct_personnel: Total personnel salaries.
        fringe_benefits: Total fringe benefits.
        travel: Total travel costs.
        supplies: Total supplies costs.
        other: Total other direct costs.
        indirect_rate_pct: Approved indirect cost rate percentage.

    Returns:
        Dictionary containing csv_data string and total_requested.
    """
    return _call_remote_tool_sync("generate_budget_csv", {
        "grant_id": grant_id, "direct_personnel": direct_personnel,
        "fringe_benefits": fringe_benefits, "travel": travel,
        "supplies": supplies, "other": other,
        "indirect_rate_pct": indirect_rate_pct,
    })


@tool
def update_draft_section(
    grant_id: str, org_id: str, grant_title: str,
    section_title: str, content: str
) -> dict[str, Any]:
    """Save or update a specific section of a grant application draft.

    Args:
        grant_id: The unique ID of the target grant opportunity.
        org_id: The organization ID applying for the grant.
        grant_title: Title of the grant opportunity.
        section_title: The specific section being updated.
        content: The full drafted text for this section.

    Returns:
        Dictionary with success status and completion percentage.
    """
    return _call_remote_tool_sync("update_draft_section", {
        "grant_id": grant_id, "org_id": org_id, "grant_title": grant_title,
        "section_title": section_title, "content": content,
    })


@tool
def save_application_draft(
    grant_id: str, org_id: str, grant_title: str,
    sections: list[Any] | None = None, submission_checklist: list[Any] | None = None,
    budget_csv_data: str | None = None
) -> dict[str, Any]:
    """Persist a complete application draft to storage.

    Args:
        grant_id: Grant identifier.
        org_id: Organization identifier.
        grant_title: Title of the grant.
        sections: List of section dictionaries.
        submission_checklist: Optional checklist items.
        budget_csv_data: Optional budget CSV string.

    Returns:
        Dictionary with draft_id and save confirmation.
    """
    return _call_remote_tool_sync("save_application_draft", {
        "grant_id": grant_id, "org_id": org_id, "grant_title": grant_title,
        "sections": sections, "submission_checklist": submission_checklist or [],
        "budget_csv_data": budget_csv_data,
    })


@tool
def get_existing_application_draft(grant_id: str) -> dict[str, Any]:
    """Retrieve an existing application draft for a grant.

    Args:
        grant_id: The grant ID to look up.

    Returns:
        Dictionary with the draft data or empty if not found.
    """
    return _call_remote_tool_sync("get_existing_application_draft", {"grant_id": grant_id})


# ==========================================
#  Compliance Tools
# ==========================================

@tool
def calculate_mtdc_compliance(
    total_direct_costs: float, excluded_costs: float = 0.0,
    indirect_rate_pct: float = 10.0
) -> dict[str, Any]:
    """Calculate Modified Total Direct Costs compliance.

    Args:
        total_direct_costs: Sum of all direct cost categories.
        excluded_costs: Costs excluded from MTDC base.
        indirect_rate_pct: Negotiated indirect cost rate.

    Returns:
        Dictionary with MTDC calculation breakdown.
    """
    return _call_remote_tool_sync("calculate_mtdc_compliance", {
        "total_direct_costs": total_direct_costs,
        "excluded_costs": excluded_costs,
        "indirect_rate_pct": indirect_rate_pct,
    })


@tool
def audit_application_compliance(grant_id: str) -> dict[str, Any]:
    """Audit a draft application for federal compliance issues.

    Args:
        grant_id: The grant ID whose application to audit.

    Returns:
        Dictionary with compliance findings.
    """
    return _call_remote_tool_sync("audit_application_compliance", {"grant_id": grant_id})


# ==========================================
#  Notification Tools
# ==========================================

@tool
def send_deadline_alert(
    grant_id: str,
    days_remaining: int = 0,
    priority: str = "normal",
    grant_title: str = "",
    deadline: str = "",
) -> dict[str, Any]:
    """Send a deadline alert for a grant opportunity.

    Args:
        grant_id: The grant to alert about.
        days_remaining: Days until the deadline.
        priority: Alert priority (critical/high/normal/low).
        grant_title: Optional title of the grant.
        deadline: Optional deadline date.

    Returns:
        Dictionary with alert confirmation.
    """
    args: dict[str, Any] = {
        "grant_id": grant_id,
        "days_remaining": days_remaining,
        "priority": priority,
    }
    if grant_title:
        args["grant_title"] = grant_title
    if deadline:
        args["deadline"] = deadline
    return _call_remote_tool_sync("send_deadline_alert", args)


@tool
def send_external_notification(channel: str, message: str) -> dict[str, Any]:
    """Send a notification to an external channel.

    Args:
        channel: The notification channel.
        message: The message content.

    Returns:
        Dictionary with notification status.
    """
    return _call_remote_tool_sync("send_external_notification", {
        "channel": channel, "message": message,
    })


@tool
def scan_upcoming_deadlines(days_ahead: int = 30) -> dict[str, Any]:
    """Scan for upcoming grant deadlines within a time window.

    Args:
        days_ahead: Number of days to look ahead.

    Returns:
        Dictionary with upcoming deadlines.
    """
    return _call_remote_tool_sync("scan_upcoming_deadlines", {"days_ahead": days_ahead})
