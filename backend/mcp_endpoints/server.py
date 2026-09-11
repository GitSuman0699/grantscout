"""GrantScout Model Context Protocol (MCP) Server.

Exposes GrantScout execution tools, resources, and prompt templates to external MCP-compliant
clients (AWS AgentCore, Claude Desktop, Cursor, and Strands Agents) using the open MCP standard.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from backend.rag.knowledge_base import knowledge_base
from backend.storage.local_storage import storage
from backend.tools.grants_api import fetch_grant_details, search_grants
from backend.tools.org_profile import check_grant_exists, retrieve_org_profile, save_matched_grant
from backend.tools.rag_search import query_knowledge_base
from backend.tools.application import (
    generate_budget_csv,
    get_existing_application_draft,
    save_application_draft,
    update_draft_section,
)
from backend.tools.compliance import audit_application_compliance, calculate_mtdc_compliance
from backend.tools.notifications import (
    scan_upcoming_deadlines,
    send_deadline_alert,
    send_external_notification,
)

logger = logging.getLogger(__name__)

# Initialize FastMCP Server
mcp_server = FastMCP(
    name="GrantScout MCP",
    instructions="GrantScout Model Context Protocol server providing live federal grants discovery, nonprofit RAG retrieval, application drafting, and deadline monitoring.",
)

# ──────────────────────────────────────────────
#  Register All 15 Production Tools
# ──────────────────────────────────────────────

_TOOLS_TO_REGISTER = [
    search_grants,
    fetch_grant_details,
    retrieve_org_profile,
    check_grant_exists,
    save_matched_grant,
    query_knowledge_base,
    generate_budget_csv,
    update_draft_section,
    save_application_draft,
    get_existing_application_draft,
    calculate_mtdc_compliance,
    audit_application_compliance,
    send_deadline_alert,
    send_external_notification,
    scan_upcoming_deadlines,
]

for _tool in _TOOLS_TO_REGISTER:
    _fn = getattr(_tool, "_tool_func", getattr(_tool, "__wrapped__", _tool))
    _name = getattr(_tool, "tool_name", getattr(_fn, "__name__", None))
    mcp_server.add_tool(_fn, name=_name)

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

Please use `grantscout://profile` to inspect our mission, programs, and budget, and `query_knowledge_base` to retrieve relevant past grant outcomes.
Then score the opportunity and provide a final recommendation.
"""


@mcp_server.prompt()
def draft_grant_proposal(grant_title: str, agency: str, award_amount: str) -> str:
    """Prompt template for drafting a competitive 6-section federal grant proposal."""
    return f"""Please draft a complete grant proposal for our organization:

OPPORTUNITY:
- Title: {grant_title}
- Agency: {agency}
- Requested Funding: {award_amount}

Please ground every section in our verified RAG knowledge base facts using `query_knowledge_base`.
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
