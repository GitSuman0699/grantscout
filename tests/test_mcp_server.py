"""Test suite for GrantScout Model Context Protocol (MCP) Server."""

import json
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.mcp.server import (
    mcp_server,
    search_federal_grants,
    query_organization_knowledge_base,
    evaluate_grant_fit,
    draft_grant_section,
    get_organization_profile_resource,
    get_grant_pipeline_resource,
    get_knowledge_base_documents_resource,
)


class TestMCPServer(unittest.TestCase):
    """Test suite for FastMCP tool, resource, and prompt registrations and executions."""

    def test_01_mcp_server_initialization(self):
        """Verify FastMCP server is correctly named with instructions."""
        self.assertEqual(mcp_server.name, "GrantScout MCP")
        self.assertTrue("GrantScout" in (mcp_server.instructions or ""))

    def test_02_mcp_tools_registered(self):
        """Verify all essential GrantScout tools are declared on the server."""
        # FastMCP stores tools in its tool manager
        tool_names = [t.name for t in mcp_server._tool_manager.list_tools()]
        expected_tools = [
            "search_federal_grants",
            "fetch_grant_opportunity",
            "query_organization_knowledge_base",
            "evaluate_grant_fit",
            "draft_grant_section",
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
        """Verify query_organization_knowledge_base tool returns valid JSON matching documents."""
        raw_json = query_organization_knowledge_base(query="STEM math grade improvement", top_k=2)
        data = json.loads(raw_json)
        self.assertIn("passages", data)
        self.assertTrue(len(data["passages"]) > 0)
        self.assertTrue(any("85%" in p["excerpt"] for p in data["passages"]))

    def test_06_execute_mcp_evaluate_grant_fit(self):
        """Verify evaluate_grant_fit tool produces valid structured evaluation JSON."""
        raw_json = evaluate_grant_fit(
            title="Youth Technology and AI Mentorship",
            synopsis="Community grant for hands-on youth STEM and coding instruction in Atlanta.",
            agency="NSF",
            award_ceiling=50000,
        )
        data = json.loads(raw_json)
        self.assertIn("match_score", data)
        self.assertIn("recommended_action", data)
        self.assertTrue(data["match_score"]["total"] >= 50)

    def test_07_execute_mcp_draft_grant_section(self):
        """Verify draft_grant_section tool produces grounded prose text."""
        text = draft_grant_section(
            section_name="Statement of Need",
            grant_title="Youth STEM Academy",
            agency="Dept of Education",
        )
        self.assertIn("Youth Education Alliance", text)
        self.assertIn("Statement of Need", text)
        self.assertTrue(len(text) > 100)

    def test_08_read_mcp_profile_resource(self):
        """Verify reading grantscout://profile resource returns valid organization JSON."""
        raw_json = get_organization_profile_resource()
        data = json.loads(raw_json)
        self.assertIn("name", data)
        self.assertEqual(data["name"], "Youth Education Alliance")
        self.assertEqual(data["org_id"], "default")


    def test_09_execute_mcp_search_federal_grants(self):
        """Verify search_federal_grants tool forwards correct parameters to search_grants."""
        raw_json = search_federal_grants(keyword="STEM education", max_results=2)
        data = json.loads(raw_json)
        self.assertIn("grants", data)
        self.assertIsNone(data.get("error"))

        # Test keywords alias
        raw_json_alias = search_federal_grants(keywords="STEM education", max_results=2)
        data_alias = json.loads(raw_json_alias)
        self.assertIn("grants", data_alias)


if __name__ == "__main__":
    unittest.main(verbosity=2)
