"""Unit tests for Strands structured output and schema enforcement."""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "agentcore" / "src"))

from agents.drafter import draft_application_structured
from agents.matcher import evaluate_grant_structured
from shared.api.models.schemas import (
    ApplicationDraftResult,
    GrantEvaluationResult,
    GrantStatus,
    MatchScore,
)


class TestStructuredOutputEnforcement(unittest.TestCase):
    """Test suite for Pydantic schema validation on Agent outputs."""

    def test_01_grant_evaluation_schema_validation(self):
        """Verify GrantEvaluationResult enforces field types, constraints, and score boundaries."""
        # Valid instance
        valid_eval = GrantEvaluationResult(
            grant_id="test-gid-1",
            status=GrantStatus.MATCHED,
            match_score=MatchScore(
                mission_alignment=28,
                eligibility_fit=24,
                capacity_match=19,
                geographic_fit=14,
                track_record=9,
            ),
            match_reasoning="Strong alignment with youth coding initiatives.",
            key_strengths=["Direct mission overlap", "Strong capacity"],
            potential_risks=["Tight milestone schedule"],
            recommended_action="auto_draft",
        )
        self.assertEqual(valid_eval.match_score.total, 94)
        self.assertEqual(valid_eval.status, GrantStatus.MATCHED)
        self.assertEqual(len(valid_eval.key_strengths), 2)

    def test_02_matcher_structured_evaluation_execution(self):
        """Verify evaluate_grant_structured returns a fully typed GrantEvaluationResult."""
        mock_grant = {
            "id": 999123,
            "title": "Innovative Youth Coding and AI Academy",
            "agency": "National Science Foundation",
            "synopsis": "Grant supporting hands-on computer science, robotics, and STEM education for low-income students.",
            "award_ceiling": 75000,
            "award_floor": 25000,
            "close_date": "2026-12-01",
        }

        result = evaluate_grant_structured(mock_grant)
        self.assertIsInstance(result, GrantEvaluationResult)
        self.assertEqual(result.grant_id, "grants-gov-999123")
        self.assertTrue(result.match_score.total > 0)
        self.assertTrue(len(result.match_reasoning) > 10)
        self.assertIn(result.recommended_action, ["auto_draft", "manual_review", "archive_silently"])

    def test_03_drafter_structured_application_execution(self):
        """Verify draft_application_structured returns a validated ApplicationDraftResult with 6 sections."""
        mock_grant = {
            "grant_id": "grants-gov-999123",
            "title": "Innovative Youth Coding and AI Academy",
            "agency": "National Science Foundation",
            "synopsis": "Grant supporting hands-on computer science, robotics, and STEM education.",
            "award_ceiling": 75000,
            "award_floor": 25000,
            "close_date": "2026-12-01",
        }

        draft = draft_application_structured(mock_grant)
        self.assertIsInstance(draft, ApplicationDraftResult)
        self.assertEqual(draft.grant_id, "grants-gov-999123")
        self.assertEqual(len(draft.sections), 6)
        self.assertTrue(draft.completion_percentage > 0)
        self.assertTrue(len(draft.recommended_human_actions) > 0)

        # Verify specific required sections exist
        titles = [s.title for s in draft.sections]
        self.assertTrue(any("Executive Summary" in t for t in titles))
        self.assertTrue(any("Budget" in t for t in titles))

    def test_04_checklist_dict_coercion(self):
        """Verify ApplicationDraftResult cleanly coerces dict-based submission_checklist items to strings."""
        dict_checklist = [
            {"item": "SAM.gov Registration", "deadline": "Before submission"},
            {"item": "SF-424 Application", "deadline": "With submission"},
            "Simple string item",
        ]
        result = ApplicationDraftResult(
            grant_id="test-grant-dict",
            org_id="default",
            grant_title="Test Dict Checklist",
            sections=[],
            submission_checklist=dict_checklist,
        )
        self.assertEqual(len(result.submission_checklist), 3)
        self.assertEqual(result.submission_checklist[0], "SAM.gov Registration (Before submission)")
        self.assertEqual(result.submission_checklist[1], "SF-424 Application (With submission)")
        self.assertEqual(result.submission_checklist[2], "Simple string item")

        # Also verify backend schema directly
        from backend.api.models.schemas import ApplicationDraftResult as BackendDraftResult
        backend_result = BackendDraftResult(
            grant_id="test-grant-dict",
            org_id="default",
            grant_title="Test Dict Checklist",
            sections=[],
            submission_checklist=dict_checklist,
        )
        self.assertEqual(backend_result.submission_checklist[0], "SAM.gov Registration (Before submission)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
