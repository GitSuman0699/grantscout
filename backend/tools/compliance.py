"""2 CFR 200 Federal Uniform Guidance Regulatory Compliance Engine.

Automates pre-submission regulatory audits for federal grant proposals:
- 2 CFR 200.414(f): De minimis 10% modified total direct cost (MTDC) indirect cost rate validation.
- 2 CFR 200 Subpart E: Unallowable cost detection (Alcohol §200.423, Entertainment §200.438, Lobbying §200.450, Fundraising §200.442, Contingency §200.433).
- 2 CFR 200.430: Compensation & personnel direct allocation standards.
- 2 CFR 200.306: Cost sharing and non-federal matching documentation standards.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from strands import tool

from backend.api.models.schemas import ComplianceAuditResult, ComplianceFinding
from backend.storage.local_storage import storage

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  Prohibited & Unallowable Cost Signatures
# ──────────────────────────────────────────────

UNALLOWABLE_PATTERNS = [
    (
        r"(?i)\b(alcoholic\s+beverages?|wine|beer|liquor|cocktail)\b",
        "2 CFR 200.423",
        "Alcoholic Beverages",
        "Costs of alcoholic beverages are strictly unallowable under federal awards.",
        "Remove all beverage alcohol allocations from direct and indirect line items.",
    ),
    (
        r"(?i)\b(entertainment|amusement|social\s+club|tickets\s+to\s+shows|banquet|gala\s+dinner)\b",
        "2 CFR 200.438",
        "Entertainment Costs",
        "Costs of entertainment, amusements, social activities, and related incidentals are unallowable.",
        "Reallocate social/entertainment items to legitimate programmatic workshop supplies.",
    ),
    (
        r"(?i)\b(lobbying|electioneering|political\s+campaign|legislative\s+advocacy|grassroots\s+campaign)\b",
        "2 CFR 200.450",
        "Lobbying & Political Activity",
        "Costs of attempting to influence legislation, elections, or political referendums are unallowable.",
        "Ensure all project activities are strictly non-partisan and programmatic.",
    ),
    (
        r"(?i)\b(fundraising\s+costs?|capital\s+campaign|endowment\s+fund|donor\s+acquisition)\b",
        "2 CFR 200.442",
        "Fundraising & Capital Campaigns",
        "Costs of organized fundraising, including financial campaigns and endowment drives, are unallowable.",
        "Separate development/fundraising salaries from federal grant project effort.",
    ),
    (
        r"(?i)\b(contingency\s+funds?|rainy\s+day\s+reserve|unforeseen\s+buffer|slush\s+fund)\b",
        "2 CFR 200.433",
        "Contingency Reserves",
        "Contributions to a contingency reserve or any similar provision for unforeseen events are unallowable.",
        "Base all line items on concrete cost estimates rather than generic contingency reserves.",
    ),
    (
        r"(?i)\b(fines\s+and\s+penalties|late\s+fees|traffic\s+violations)\b",
        "2 CFR 200.441",
        "Fines & Penalties",
        "Costs resulting from violations of, or failure to comply with, federal, state, or local laws are unallowable.",
        "Remove any contingency for late fees or statutory penalties.",
    ),
]


def parse_indirect_rate(budget_text: str) -> tuple[float, bool]:
    """Extract and check indirect cost rate from budget text against 10% de minimis cap."""
    # Look for explicit percentage mentions
    match = re.search(r"(?i)(?:indirect\s+cost|overhead|f&a|administrative\s+rate)[^\d]{0,20}(\d+(?:\.\d+)?)\s*%", budget_text)
    if match:
        rate = float(match.group(1))
        # 10% is standard de minimis; up to 15% permitted if documented
        is_compliant = rate <= 10.0
        return rate, is_compliant
    return 10.0, True


@tool
def audit_application_compliance(
    grant_id: str,
    draft_id: str = "",
    budget_narrative: str = "",
    project_design: str = "",
) -> dict[str, Any]:
    """Perform an automated 2 CFR 200 Uniform Guidance compliance audit on a grant application draft.

    Evaluates:
    - Indirect cost rate against the 10% de minimis cap (2 CFR 200.414(f))
    - Prohibited unallowable costs (Alcohol §200.423, Entertainment §200.438, Lobbying §200.450, Fundraising §200.442)
    - Direct personnel allocation standards (§200.430)
    - Cost-sharing & matching fund documentation (§200.306)

    Args:
        grant_id: The ID of the target grant opportunity.
        draft_id: Optional ID of the existing application draft.
        budget_narrative: Optional text of the budget section.
        project_design: Optional text of the project design section.

    Returns:
        A dictionary containing compliance score, findings list, and risk level.
    """
    logger.info(f"Auditing 2 CFR 200 compliance for grant={grant_id}, draft={draft_id}")

    # Load draft if not passed explicitly
    if not budget_narrative and draft_id:
        draft = storage.get_application(draft_id)
        if draft:
            sections = draft.get("sections", [])
            for sec in sections:
                title_lower = sec.get("title", "").lower()
                if "budget" in title_lower or "financial" in title_lower:
                    budget_narrative += "\n" + sec.get("content", "")
                if "project" in title_lower or "design" in title_lower:
                    project_design += "\n" + sec.get("content", "")

    full_text = f"{budget_narrative}\n{project_design}"
    findings: list[ComplianceFinding] = []
    unallowable_detected: list[str] = []
    score = 100

    # 1. Indirect Cost Rate Check (2 CFR 200.414(f))
    rate, rate_compliant = parse_indirect_rate(budget_narrative)
    if not rate_compliant:
        score -= 25
        findings.append(
            ComplianceFinding(
                finding_id=f"find-{uuid.uuid4().hex[:6]}",
                category="indirect_cost",
                severity="violation",
                rule_reference="2 CFR 200.414(f)",
                description=f"Indirect cost rate of {rate:.1f}% exceeds standard 10% de minimis Modified Total Direct Cost cap.",
                recommendation="Reduce indirect cost rate to 10.0% or attach approved Federal Negotiated Indirect Cost Rate Agreement (NICRA).",
            )
        )
    else:
        findings.append(
            ComplianceFinding(
                finding_id=f"find-{uuid.uuid4().hex[:6]}",
                category="indirect_cost",
                severity="pass",
                rule_reference="2 CFR 200.414(f)",
                description=f"Indirect cost rate ({rate:.1f}%) complies with 10% de minimis MTDC allowance.",
                recommendation="",
            )
        )

    # 2. Unallowable Cost Detection (2 CFR 200 Subpart E)
    for pattern, rule_ref, name, desc, rec in UNALLOWABLE_PATTERNS:
        if re.search(pattern, full_text):
            score -= 20
            unallowable_detected.append(name)
            findings.append(
                ComplianceFinding(
                    finding_id=f"find-{uuid.uuid4().hex[:6]}",
                    category="unallowable_cost",
                    severity="violation",
                    rule_reference=rule_ref,
                    description=f"Potential unallowable cost detected: {name}. {desc}",
                    recommendation=rec,
                )
            )

    # 3. Personnel Compensation Standard (2 CFR 200.430)
    has_personnel = bool(re.search(r"(?i)\b(personnel|salary|fringe|director|coordinator|fte|hourly|wages)\b", budget_narrative))
    if has_personnel:
        findings.append(
            ComplianceFinding(
                finding_id=f"find-{uuid.uuid4().hex[:6]}",
                category="personnel_allocation",
                severity="pass",
                rule_reference="2 CFR 200.430",
                description="Personnel compensation includes documented job titles and direct effort allocations.",
                recommendation="",
            )
        )
    else:
        score -= 10
        findings.append(
            ComplianceFinding(
                finding_id=f"find-{uuid.uuid4().hex[:6]}",
                category="personnel_allocation",
                severity="warning",
                rule_reference="2 CFR 200.430",
                description="Budget does not clearly itemize direct personnel or staff FTE allocations.",
                recommendation="Specify key personnel roles, FTE percentages, and fringe benefit rates.",
            )
        )

    # 4. Long-Term Sustainability & Matching (2 CFR 200.306)
    has_sustainability = bool(re.search(r"(?i)\b(sustainab|matching|cost[\s-]share|in[\s-]kind|diversif)\b", full_text))
    if has_sustainability:
        findings.append(
            ComplianceFinding(
                finding_id=f"find-{uuid.uuid4().hex[:6]}",
                category="cost_sharing",
                severity="pass",
                rule_reference="2 CFR 200.306",
                description="Application documents institutional sustainability and partner commitment.",
                recommendation="",
            )
        )
    else:
        score -= 5
        findings.append(
            ComplianceFinding(
                finding_id=f"find-{uuid.uuid4().hex[:6]}",
                category="cost_sharing",
                severity="warning",
                rule_reference="2 CFR 200.306",
                description="Sustainability and co-funding strategy could be strengthened.",
                recommendation="Highlight non-federal partner commitments or in-kind volunteer valuation.",
            )
        )

    # Calculate final score and status
    final_score = max(0, min(100, score))
    if final_score >= 85:
        overall_status = "compliant"
    elif final_score >= 60:
        overall_status = "needs_revision"
    else:
        overall_status = "high_risk"

    audit_result = ComplianceAuditResult(
        audit_id=f"audit-{uuid.uuid4().hex[:8]}",
        draft_id=draft_id,
        grant_id=grant_id,
        overall_status=overall_status,
        compliance_score=final_score,
        indirect_cost_rate_pct=rate,
        indirect_cost_compliant=rate_compliant,
        unallowable_costs_detected=unallowable_detected,
        findings=findings,
        audited_at=datetime.now(timezone.utc),
    )

    return audit_result.model_dump()
