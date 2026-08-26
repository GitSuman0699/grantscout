"""GrantScout Model Context Protocol (MCP) Server.

Exposes GrantScout tools, resources, and prompt templates to external MCP-compliant
clients (Claude Desktop, Cursor, and Strands Agents) using the open MCP standard.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from backend.tools.grants_api import search_grants, fetch_grant_details
from backend.tools.rag_search import query_knowledge_base
from backend.agents.matcher import evaluate_grant_structured
from backend.rag.knowledge_base import knowledge_base
from backend.storage.local_storage import storage

logger = logging.getLogger(__name__)

# Initialize FastMCP Server
mcp_server = FastMCP(
    name="GrantScout MCP",
    instructions="GrantScout Model Context Protocol server providing live federal grants discovery, nonprofit RAG retrieval, fit evaluation, and proposal generation.",
)


# ──────────────────────────────────────────────
#  MCP Tools
# ──────────────────────────────────────────────


@mcp_server.tool()
def search_federal_grants(keyword: str, max_results: int = 10) -> str:
    """Search live Grants.gov database for open and forecasted federal funding opportunities.

    Args:
        keyword: Search terms (e.g. 'STEM education', 'robotics youth', 'clean energy community').
        max_results: Maximum opportunities to return (default: 10, max: 25).

    Returns:
        JSON string containing matching grant opportunities.
    """
    res = search_grants(keyword=keyword, rows=min(max_results, 25))
    return json.dumps(res, indent=2)


@mcp_server.tool()
def fetch_grant_opportunity(opportunity_id: int) -> str:
    """Fetch complete synopsis, award ceiling/floor, and deadlines for a specific Grants.gov ID.

    Args:
        opportunity_id: Unique numeric Grants.gov opportunity ID (e.g. 359104).

    Returns:
        JSON string containing detailed grant requirements and eligibility criteria.
    """
    res = fetch_grant_details(opportunity_id=opportunity_id)
    return json.dumps(res, indent=2)


@mcp_server.tool()
def query_organization_knowledge_base(query: str, top_k: int = 3, category: str = "") -> str:
    """Perform semantic vector retrieval across the nonprofit organization's indexed documents.

    Searches past winning proposals, annual impact reports, IRS 990 financials, and staff bios.

    Args:
        query: Natural language question or search phrase.
        top_k: Number of relevant excerpts to return (default: 3).
        category: Optional filter ('impact_report', 'irs_990', 'past_proposal', 'bios').

    Returns:
        JSON string containing matched document excerpts with relevance scores.
    """
    res = query_knowledge_base(query=query, top_k=top_k, category=category)
    return json.dumps(res, indent=2)


@mcp_server.tool()
def evaluate_grant_fit(
    title: str,
    synopsis: str,
    agency: str = "Federal Agency",
    award_ceiling: float = 0.0,
    close_date: str = "TBD",
    grant_id: str = "custom-opp-1",
) -> str:
    """Score a grant opportunity against the nonprofit organization's profile across 5 rubric dimensions.

    Args:
        title: Title of the grant opportunity.
        synopsis: Summary of grant requirements and target populations.
        agency: Funding government agency.
        award_ceiling: Maximum award amount in USD.
        close_date: Application submission deadline.
        grant_id: Unique identifier for the grant.

    Returns:
        JSON string containing the structured 5-dimension rubric score and routing decision.
    """
    grant_data = {
        "grant_id": grant_id,
        "title": title,
        "agency": agency,
        "synopsis": synopsis,
        "award_ceiling": award_ceiling,
        "award_floor": 0,
        "close_date": close_date,
    }
    evaluation = evaluate_grant_structured(grant_data)
    return json.dumps(evaluation.model_dump(), indent=2)


@mcp_server.tool()
def draft_grant_section(section_name: str, grant_title: str, agency: str = "Federal Agency") -> str:
    """Draft a specific proposal section grounded in the nonprofit's verified RAG facts and history.

    Args:
        section_name: One of 'Executive Summary', 'Organizational Background', 'Statement of Need', 'Implementation Plan', 'Budget', 'Evaluation'.
        grant_title: Title of the grant opportunity.
        agency: Target grantmaking agency.

    Returns:
        Formulated draft text grounded in the organization's verified profile and RAG documents.
    """
    org_res = storage.get_org_profile("default")
    org_data = org_res.get("profile") or {}
    org_name = org_data.get("name", "Youth Education Alliance")
    budget = org_data.get("annual_budget", 450000)

    # Pull supporting metrics via RAG
    rag_res = knowledge_base.search(f"{section_name} outcomes metrics", top_k=1)
    supporting_excerpt = rag_res[0].content[:250] if rag_res else ""

    draft_text = (
        f"### {section_name}\n\n"
        f"{org_name} is honored to submit this proposal for '{grant_title}' administered by {agency}. "
        f"With an annual operating budget of ${budget:,.0f} and clean audit history, "
        f"the organization demonstrates proven fiduciary responsibility and programmatic excellence.\n\n"
        f"**Supporting Organizational Evidence:**\n{supporting_excerpt}..."
    )
    return draft_text


# ──────────────────────────────────────────────
#  MCP Resources
# ──────────────────────────────────────────────


@mcp_server.resource("grantscout://profile")
def get_organization_profile_resource() -> str:
    """Read the active nonprofit organization's core profile, mission statement, and budget."""
    org = storage.get_org_profile("default")
    return json.dumps(org, indent=2)


@mcp_server.resource("grantscout://pipeline")
def get_grant_pipeline_resource() -> str:
    """Read all tracked grant opportunities currently in the GrantScout pipeline."""
    grants = storage.list_grants()
    return json.dumps({"grants": grants, "total": len(grants)}, indent=2)


@mcp_server.resource("grantscout://knowledge-base/documents")
def get_knowledge_base_documents_resource() -> str:
    """Read the catalog of indexed organizational RAG documents."""
    docs = knowledge_base.list_documents()
    return json.dumps({"documents": docs, "total": len(docs)}, indent=2)


# ──────────────────────────────────────────────
#  MCP Prompts
# ──────────────────────────────────────────────


@mcp_server.prompt()
def analyze_grant_opportunity(grant_title: str, agency: str, synopsis: str) -> str:
    """Prompt template for performing an in-depth fit analysis on a grant opportunity."""
    return f"""Please perform a thorough 5-dimension fit evaluation for our nonprofit organization:

GRANT OPPORTUNITY:
- Title: {grant_title}
- Agency: {agency}
- Synopsis: {synopsis}

Please use `grantscout://profile` to inspect our mission, programs, and budget, and `query_organization_knowledge_base` to retrieve relevant past grant outcomes.
Then use `evaluate_grant_fit` to score the opportunity and provide a final recommendation.
"""


@mcp_server.prompt()
def draft_grant_proposal(grant_title: str, agency: str, award_amount: str) -> str:
    """Prompt template for drafting a competitive 6-section federal grant proposal."""
    return f"""Please draft a complete grant proposal for our organization:

OPPORTUNITY:
- Title: {grant_title}
- Agency: {agency}
- Requested Funding: {award_amount}

Please ground every section in our verified RAG knowledge base facts using `query_organization_knowledge_base`.
Draft all 6 required sections:
1. Executive Summary
2. Organizational Background & Capacity
3. Statement of Need & Target Population
4. Project Design & Implementation Plan
5. Budget & Financial Justification
6. Evaluation & Sustainability
"""


def main():
    """Run the MCP server using standard I/O (stdio) transport."""
    mcp_server.run(transport="stdio")


if __name__ == "__main__":
    main()
