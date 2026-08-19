"""Comprehensive integration tests for GrantScout multi-agent pipeline."""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.storage.local_storage import storage
from backend.tools.grants_api import search_grants, fetch_grant_details
from backend.tools.org_profile import retrieve_org_profile, save_matched_grant
from backend.tools.application import save_application_draft
from backend.tools.notifications import scan_upcoming_deadlines


class TestGrantScoutPipeline(unittest.TestCase):
    """Test suite for GrantScout tools, storage, and agent operations."""

    def test_01_org_profile_retrieval(self):
        """Verify organization profile is loaded with correct data."""
        res = retrieve_org_profile("default")
        self.assertIsNone(res.get("error"))
        self.assertIsNotNone(res.get("profile"))
        self.assertEqual(res["profile"]["name"], "Youth Education Alliance")
        self.assertTrue(len(res["profile"]["keywords"]) > 0)

    def test_02_grants_gov_live_search(self):
        """Verify live querying to grants.gov public search API."""
        res = search_grants(keywords="STEM education", max_results=3)
        self.assertIsNone(res.get("error"))
        self.assertIn("grants", res)
        self.assertTrue(len(res["grants"]) > 0)
        self.assertIn("title", res["grants"][0])

    def test_03_save_matched_grant(self):
        """Verify saving and retrieving scored grant opportunities."""
        test_gid = "test-grant-101"
        score_breakdown = {
            "mission_alignment": 28,
            "eligibility_fit": 24,
            "capacity_match": 18,
            "geographic_fit": 14,
            "track_record": 9,
        }
        res = save_matched_grant(
            grant_id=test_gid,
            title="National Youth STEM Innovation Grant",
            agency="Department of Education",
            synopsis="Funding for community-based robotics and coding programs for low-income youth.",
            award_ceiling=50000.0,
            award_floor=15000.0,
            close_date="2026-11-30",
            status="matched",
            match_score=score_breakdown,
            match_reasoning="Outstanding mission alignment with Youth Education Alliance after-school coding programs.",
        )
        self.assertTrue(res.get("saved"))

        # Verify saved in storage
        retrieved = storage.get_grant(test_gid)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["title"], "National Youth STEM Innovation Grant")
        self.assertEqual(sum(retrieved["match_score"].values()), 93)

    def test_04_save_and_retrieve_draft(self):
        """Verify multi-section grant application draft persistence."""
        sections = [
            {
                "title": "Executive Summary",
                "content": "Youth Education Alliance requests $50,000 to expand STEM workshops.",
                "is_auto_filled": True,
                "needs_review": False,
                "word_count": 11,
            },
            {
                "title": "Organizational Background",
                "content": "Founded in 2019, YEA has served over 200 students annually across Atlanta.",
                "is_auto_filled": True,
                "needs_review": False,
                "word_count": 12,
            },
            {
                "title": "Project Design",
                "content": "Weekly hands-on coding and robotics sessions with Arduino hardware.",
                "is_auto_filled": False,
                "needs_review": True,
                "word_count": 10,
            },
        ]
        res = save_application_draft(
            grant_id="test-grant-101",
            org_id="default",
            grant_title="National Youth STEM Innovation Grant",
            sections=sections,
        )
        self.assertTrue(res.get("saved"))
        self.assertIsNotNone(res.get("draft_id"))

    def test_05_deadline_scan(self):
        """Verify deadline scanner detects active deadlines."""
        res = scan_upcoming_deadlines()
        self.assertIsNone(res.get("error"))
        self.assertIn("deadlines", res)


if __name__ == "__main__":
    unittest.main(verbosity=2)
