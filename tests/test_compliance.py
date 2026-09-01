"""Unit tests for 2 CFR 200 Federal Regulatory Compliance Engine."""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.tools.compliance import audit_application_compliance, parse_indirect_rate


class TestComplianceEngine(unittest.TestCase):
    """Test suite for 2 CFR 200 compliance audits."""

    def test_01_compliant_budget_audit(self):
        """Verify compliant budget with 10% indirect rate passes with high score."""
        budget_text = """
        ### Budget Justification
        - Personnel: Program Director ($35,000, 0.5 FTE)
        - Supplies: Educational robotics kits ($10,000)
        - Indirect Costs: 10.0% Modified Total Direct Costs ($4,500)
        """
        project_text = "Sustainable partnership with local community schools and corporate sponsors."

        res = audit_application_compliance(
            grant_id="test-grant-comp-01",
            budget_narrative=budget_text,
            project_design=project_text,
        )

        self.assertEqual(res["overall_status"], "compliant")
        self.assertGreaterEqual(res["compliance_score"], 85)
        self.assertTrue(res["indirect_cost_compliant"])
        self.assertEqual(len(res["unallowable_costs_detected"]), 0)

    def test_02_unallowable_costs_detection(self):
        """Verify unallowable costs like alcohol and lobbying trigger violations."""
        budget_text = """
        ### Budget Justification
        - Staff Wages: $25,000
        - Banquet & Wine: $5,000 for donor gala dinner
        - Legislative Advocacy & Lobbying: $8,000
        """

        res = audit_application_compliance(
            grant_id="test-grant-comp-02",
            budget_narrative=budget_text,
        )

        self.assertIn("Alcoholic Beverages", res["unallowable_costs_detected"])
        self.assertIn("Lobbying & Political Activity", res["unallowable_costs_detected"])
        self.assertLess(res["compliance_score"], 70)
        self.assertNotEqual(res["overall_status"], "compliant")

    def test_03_indirect_cost_rate_cap_violation(self):
        """Verify indirect rate exceeding 10% de minimis is flagged."""
        budget_text = """
        - Salaries: $30,000
        - Indirect Cost Rate: 28.5% administrative overhead ($8,550)
        """

        rate, is_compliant = parse_indirect_rate(budget_text)
        self.assertEqual(rate, 28.5)
        self.assertFalse(is_compliant)

        res = audit_application_compliance(
            grant_id="test-grant-comp-03",
            budget_narrative=budget_text,
        )
        self.assertFalse(res["indirect_cost_compliant"])
        self.assertLess(res["compliance_score"], 80)


if __name__ == "__main__":
    unittest.main(verbosity=2)
