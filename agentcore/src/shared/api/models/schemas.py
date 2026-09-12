"""Pydantic data models for GrantScout."""

from typing import Any
# from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, field_validator

# ──────────────────────────────────────────────
#  Enums
# ──────────────────────────────────────────────


class GrantStatus(str, Enum):
    """Processing status of a grant in the pipeline."""

    DISCOVERED = "discovered"
    MATCHED = "matched"
    DRAFTING = "drafting"
    READY_FOR_REVIEW = "ready_for_review"
    SUBMITTED = "submitted"
    ARCHIVED = "archived"


class ActivityType(str, Enum):
    """Types of agent activity events."""

    GRANTS_FOUND = "grants_found"
    GRANT_MATCHED = "grant_matched"
    APPLICATION_DRAFTED = "application_drafted"
    DEADLINE_REMINDER = "deadline_reminder"
    GRANTS_ARCHIVED = "grants_archived"
    SCAN_COMPLETED = "scan_completed"
    ERROR = "error"


# ──────────────────────────────────────────────
#  Organization Profile
# ──────────────────────────────────────────────


class Program(BaseModel):
    """A program run by the nonprofit."""

    name: str
    description: str
    participants_served: int = 0
    outcomes: str = ""


class PastGrant(BaseModel):
    """A grant the organization has received in the past."""

    funder: str
    amount: float
    year: int
    status: str = "completed"
    outcome: str = ""


class OrgProfile(BaseModel):
    """Complete nonprofit organization profile."""

    org_id: str = Field(default="")
    name: str
    ein: str = ""
    mission: str
    org_type: str = "501(c)(3) nonprofit"
    founded_year: int = 2020
    annual_budget: float = 0
    staff_count: int = 1
    service_area: str = ""
    target_population: str = ""
    programs: list[Program] = []
    past_grants: list[PastGrant] = []
    board_members: list[str] = []
    keywords: list[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ──────────────────────────────────────────────
#  Grant Opportunity
# ──────────────────────────────────────────────


from pydantic import BaseModel, Field, computed_field


class MatchScore(BaseModel):
    """Detailed match score breakdown across 5 dimensions."""

    mission_alignment: int = Field(0, ge=0, le=30)
    eligibility_fit: int = Field(0, ge=0, le=25)
    capacity_match: int = Field(0, ge=0, le=20)
    geographic_fit: int = Field(0, ge=0, le=15)
    track_record: int = Field(0, ge=0, le=10)

    @computed_field
    @property
    def total(self) -> int:
        return (
            self.mission_alignment
            + self.eligibility_fit
            + self.capacity_match
            + self.geographic_fit
            + self.track_record
        )


class GrantOpportunity(BaseModel):
    """A grant opportunity discovered from grants.gov."""

    grant_id: str
    source: str = "grants.gov"
    title: str
    agency: str = ""
    opportunity_number: str = ""
    synopsis: str = ""
    award_ceiling: float = 0
    award_floor: float = 0
    close_date: str | None = None
    post_date: str | None = None
    applicant_types: list[str] = []
    funding_category: str = ""

    # GrantScout processing fields
    status: GrantStatus = GrantStatus.DISCOVERED
    match_score: MatchScore | None = None
    match_reasoning: str = ""
    draft_location: str = ""

    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def total_score(self) -> int:
        return self.match_score.total if self.match_score else 0

    @property
    def award_range(self) -> str:
        if self.award_ceiling and self.award_floor:
            return f"${self.award_floor:,.0f} - ${self.award_ceiling:,.0f}"
        elif self.award_ceiling:
            return f"Up to ${self.award_ceiling:,.0f}"
        return "Not specified"


# ──────────────────────────────────────────────
#  Application Draft
# ──────────────────────────────────────────────


class ApplicationSection(BaseModel):
    """A section of a grant application."""

    title: str
    content: str = ""
    is_auto_filled: bool = False
    needs_review: bool = True
    word_count: int = 0


class ApplicationDraft(BaseModel):
    """A pre-filled grant application draft."""

    draft_id: str = ""
    grant_id: str
    org_id: str
    grant_title: str = ""
    sections: list[ApplicationSection] = []
    completion_percentage: float = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ──────────────────────────────────────────────
#  Agent Structured Output Models (Type-Safe Schemas)
# ──────────────────────────────────────────────


class GrantEvaluationResult(BaseModel):
    """Structured, type-safe evaluation produced by Matcher Agent."""

    grant_id: str
    status: GrantStatus = GrantStatus.MATCHED
    match_score: MatchScore
    match_reasoning: str
    key_strengths: list[str] = Field(
        default_factory=list,
        description="Key alignment points between the grant and the nonprofit mission.",
    )
    potential_risks: list[str] = Field(
        default_factory=list,
        description="Capacity, geographic, or administrative challenges identified.",
    )
    recommended_action: str = Field(
        description="Actionable next step: 'auto_draft', 'manual_review', or 'archive_silently'.",
    )


class ApplicationDraftResult(BaseModel):
    """Structured, type-safe application output produced by Drafter Agent."""

    grant_id: str
    org_id: str = "default"
    grant_title: str = ""
    sections: list[ApplicationSection] = Field(default_factory=list)
    completion_percentage: float = 100.0
    recommended_human_actions: list[str] = Field(
        default_factory=list,
        description="Specific tasks recommended for human staff review before submission.",
    )
    submission_checklist: list[str] = Field(
        default_factory=list,
        description="Concrete checklist of requirements for submission (e.g. SAM.gov, SF-424, letters).",
    )
    budget_csv_data: str | None = Field(
        default=None,
        description="Comma-separated values for the SF-424 budget template.",
    )

    @field_validator("submission_checklist", "recommended_human_actions", mode="before")
    @classmethod
    def _coerce_checklist_items(cls, v: Any) -> list[str]:
        if not v:
            return []
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            result = []
            for item in v:
                if isinstance(item, str):
                    result.append(item)
                elif isinstance(item, dict):
                    text = item.get("item") or item.get("name") or item.get("task") or item.get("title") or item.get("requirement") or str(item)
                    deadline = item.get("deadline") or item.get("timing") or item.get("due") or item.get("status")
                    result.append(f"{text} ({deadline})" if deadline else str(text))
                else:
                    result.append(str(item))
            return result
        return []


CANONICAL_SECTION_TITLES = [
    "1. Executive Summary",
    "2. Organizational Background & Capacity",
    "3. Statement of Need & Community Impact",
    "4. Project Design & Implementation Timeline",
    "5. Budget & Financial Justification",
    "6. Evaluation & Long-Term Sustainability",
]


class StaffRole(BaseModel):
    """Staffing allocation for the proposed project."""
    title: str = Field(..., description="Role title, e.g. 'Project Director', 'Lead STEM Instructor'")
    fte: float = Field(default=1.0, description="Full-Time Equivalent allocation (e.g. 0.5 or 1.0)")
    annual_salary: float = Field(default=0.0, description="Allocated annual grant salary for this position")
    responsibilities: str = Field(default="", description="Key responsibilities under this grant project")


class QuarterlyMilestone(BaseModel):
    """Quarterly deliverable milestone."""
    quarter: str = Field(..., description="Quarter designation, e.g. 'Q1 (Months 1-3)'")
    milestone: str = Field(..., description="Key deliverable or event completed in this quarter")
    lead_role: str = Field(default="", description="Staff role primarily responsible")


class ProjectBlueprint(BaseModel):
    """Structured architectural blueprint establishing the single source of truth for a grant proposal."""
    project_title: str = Field(..., description="Compelling, descriptive title for the proposed grant project")
    target_population: str = Field(..., description="Target demographic, community, and number of participants served")
    total_requested_amount: float = Field(..., description="Total grant funding requested, strictly aligned with award ceiling/floor")
    primary_objective: str = Field(..., description="Core purpose and primary measurable goal of the project")
    key_staff: list[StaffRole] = Field(default_factory=list, description="Key staff roles needed to execute the work plan")
    quarterly_milestones: list[QuarterlyMilestone] = Field(default_factory=list, description="Q1 to Q4 sequential work plan milestones")
    major_equipment_or_supplies: list[str] = Field(default_factory=list, description="Key materials, technology kits, or supplies needed")
    primary_kpis: list[str] = Field(default_factory=list, description="SMART performance metrics measuring project success")


# ──────────────────────────────────────────────
#  Activity Feed
# ──────────────────────────────────────────────


class ActivityEvent(BaseModel):
    """An agent activity event for the dashboard feed."""

    event_id: str = ""
    event_type: ActivityType
    message: str
    details: dict = {}
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ──────────────────────────────────────────────
#  Dashboard Stats
# ──────────────────────────────────────────────


class DashboardStats(BaseModel):
    """Summary statistics for the dashboard."""

    grants_discovered: int = 0
    grants_this_week: int = 0
    high_matches: int = 0
    applications_drafted: int = 0
    next_deadline: str | None = None
    days_until_deadline: int | None = None
    agent_status: str = "active"
    last_scan: datetime | None = None


# ──────────────────────────────────────────────
#  2 CFR 200 Federal Regulatory Compliance Models
# ──────────────────────────────────────────────


class ComplianceFinding(BaseModel):
    """A specific finding from a 2 CFR 200 federal compliance audit."""

    finding_id: str
    category: str = Field(description="e.g. 'indirect_cost', 'unallowable_cost', 'cost_sharing', 'personnel_allocation', 'procurement'")
    severity: str = Field(description="'pass', 'warning', or 'violation'")
    rule_reference: str = Field(description="Federal regulation reference e.g. '2 CFR 200.414(f)'")
    description: str
    recommendation: str = ""


class ComplianceAuditResult(BaseModel):
    """Result of an automated federal 2 CFR 200 compliance audit on an application draft."""

    audit_id: str
    draft_id: str
    grant_id: str
    overall_status: str = Field(description="'compliant', 'needs_revision', or 'high_risk'")
    compliance_score: int = Field(100, ge=0, le=100)
    indirect_cost_rate_pct: float = 10.0
    indirect_cost_compliant: bool = True
    unallowable_costs_detected: list[str] = Field(default_factory=list)
    findings: list[ComplianceFinding] = Field(default_factory=list)
    audited_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ──────────────────────────────────────────────
#  Multi-Tenant Nonprofit Persona Models
# ──────────────────────────────────────────────


class NonprofitPersona(BaseModel):
    """A sector-specific nonprofit persona archetype."""

    id: str
    name: str
    sector: str
    tagline: str
    annual_budget: float
    mission: str
    keywords: list[str] = Field(default_factory=list)
    target_population: str = ""
    service_area: str = ""
    founded_year: int = 2020
    icon: str = "sparkles"


# ──────────────────────────────────────────────
#  Real-Time Agent Telemetry & Thought Models
# ──────────────────────────────────────────────


class AgentThoughtEvent(BaseModel):
    """A real-time telemetry/thought event emitted by an agent during execution."""

    agent: str
    tier: str = "standard"
    model_id: str = ""
    step: str
    thought: str
    tool_called: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

