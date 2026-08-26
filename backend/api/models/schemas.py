"""Pydantic data models for GrantScout."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


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
    close_date: Optional[str] = None
    post_date: Optional[str] = None
    applicant_types: list[str] = []
    funding_category: str = ""

    # GrantScout processing fields
    status: GrantStatus = GrantStatus.DISCOVERED
    match_score: Optional[MatchScore] = None
    match_reasoning: str = ""
    draft_location: str = ""

    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


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
    org_id: str
    grant_title: str
    sections: list[ApplicationSection]
    completion_percentage: float
    recommended_human_actions: list[str] = Field(
        default_factory=list,
        description="Specific tasks recommended for human staff review before submission.",
    )


# ──────────────────────────────────────────────
#  Activity Feed
# ──────────────────────────────────────────────


class ActivityEvent(BaseModel):
    """An agent activity event for the dashboard feed."""

    event_id: str = ""
    event_type: ActivityType
    message: str
    details: dict = {}
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ──────────────────────────────────────────────
#  Dashboard Stats
# ──────────────────────────────────────────────


class DashboardStats(BaseModel):
    """Summary statistics for the dashboard."""

    grants_discovered: int = 0
    grants_this_week: int = 0
    high_matches: int = 0
    applications_drafted: int = 0
    next_deadline: Optional[str] = None
    days_until_deadline: Optional[int] = None
    agent_status: str = "active"
    last_scan: Optional[datetime] = None
