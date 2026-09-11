"""Test suite for GrantScout Model Context Protocol (MCP) Server."""

import json
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.mcp_endpoints.server import (
    get_organization_profile_resource,
    mcp_server,
)
from backend.tools.grants_api import search_grants
from backend.tools.rag_search import query_knowledge_base


class TestMCPServer(unittest.TestCase):
    """Test suite for FastMCP tool, resource, and prompt registrations and executions."""

    def test_01_mcp_server_initialization(self):
        """Verify FastMCP server is correctly named with instructions."""
        self.assertEqual(mcp_server.name, "GrantScout MCP")
        self.assertTrue("GrantScout" in (mcp_server.instructions or ""))

    def test_02_mcp_tools_registered(self):
        """Verify all 15 production GrantScout tools are declared on the server."""
        tool_names = [t.name for t in mcp_server._tool_manager.list_tools()]
        expected_tools = [
            "search_grants",
            "fetch_grant_details",
            "retrieve_org_profile",
            "check_grant_exists",
            "save_matched_grant",
            "query_knowledge_base",
            "generate_budget_csv",
            "update_draft_section",
            "save_application_draft",
            "get_existing_application_draft",
            "calculate_mtdc_compliance",
            "audit_application_compliance",
            "send_deadline_alert",
            "send_external_notification",
            "scan_upcoming_deadlines",
        ]
        for tool_name in expected_tools:
            self.assertIn(tool_name, tool_names)

    def test_03_mcp_resources_registered(self):
        """Verify URI resources are exposed."""
        resource_uris = [str(r.uri) for r in mcp_server._resource_manager.list_resources()]
        self.assertIn("grantscout://profile", resource_uris)
        self.assertIn("grantscout://pipeline", resource_uris)
        self.assertIn("grantscout://knowledge-base/documents", resource_uris)

    def test_04_mcp_prompts_registered(self):
        """Verify prompt templates are exposed."""
        prompt_names = [p.name for p in mcp_server._prompt_manager.list_prompts()]
        self.assertIn("analyze_grant_opportunity", prompt_names)
        self.assertIn("draft_grant_proposal", prompt_names)

    def test_05_execute_mcp_knowledge_base_query(self):
        """Verify query_knowledge_base tool returns valid dict matching documents."""
        data = query_knowledge_base(query="STEM math grade improvement", top_k=2)
        self.assertIn("passages", data)
        self.assertTrue(len(data["passages"]) > 0)
        self.assertTrue(any("85%" in p["excerpt"] for p in data["passages"]))

    def test_06_read_mcp_profile_resource(self):
        """Verify reading grantscout://profile resource returns valid organization JSON."""
        raw_json = get_organization_profile_resource()
        data = json.loads(raw_json)
        self.assertIn("name", data)
        self.assertEqual(data["name"], "Youth Education Alliance")
        self.assertEqual(data["org_id"], "default")

    def test_07_execute_mcp_search_grants(self):
        """Verify search_grants tool returns valid dictionary with grants list."""
        data = search_grants(keywords="STEM education", max_results=2)
        self.assertIn("grants", data)
        self.assertIsNone(data.get("error"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
