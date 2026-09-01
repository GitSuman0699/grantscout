"""Multi-Tenant Nonprofit Personas & Sector Archetypes.

Provides distinct sector configurations allowing GrantScout to dynamically
adapt its scanner keywords, matcher scoring rubric, and RAG knowledge base
to any nonprofit domain.
"""

from __future__ import annotations

from typing import Optional
from backend.api.models.schemas import NonprofitPersona, OrgProfile, Program, PastGrant

PERSONAS: list[NonprofitPersona] = [
    NonprofitPersona(
        id="youth-stem",
        name="Youth Education Alliance",
        sector="STEM Education & Youth Development",
        tagline="Empowering low-income K-12 students through hands-on robotics and coding academies.",
        annual_budget=450000,
        mission="Empower youth in underserved urban communities through hands-on STEM education, coding literacy, robotics competitions, and mentorship programs that build pathways to high-growth technology careers.",
        keywords=[
            "STEM education",
            "youth robotics",
            "coding for kids",
            "after-school STEM",
            "computer science education",
            "K-12 technology literacy",
            "underserved youth mentoring",
        ],
        target_population="K-12 students (ages 8-18) in Title I public school districts and urban communities",
        service_area="Metro Atlanta, GA and surrounding counties",
        founded_year=2019,
        icon="code",
    ),
    NonprofitPersona(
        id="food-security",
        name="Second Harvest Community Network",
        sector="Food Security & Community Nutrition",
        tagline="Ending food insecurity through community pantries, mobile nutrition, and fresh grocery rescue.",
        annual_budget=850000,
        mission="Eradicate hunger and improve health outcomes in vulnerable neighborhoods through grocery rescue, mobile food pantries, emergency meal distribution, and community nutrition education workshops.",
        keywords=[
            "food security",
            "community nutrition",
            "food bank",
            "hunger relief",
            "emergency food assistance",
            "grocery rescue",
            "SNAP outreach",
            "childhood hunger",
        ],
        target_population="Low-income families, food-insecure seniors, and unhoused individuals",
        service_area="Regional Tri-County Area",
        founded_year=2017,
        icon="utensils",
    ),
    NonprofitPersona(
        id="clean-water",
        name="Clearwater Watershed Coalition",
        sector="Clean Water & Environmental Justice",
        tagline="Protecting municipal drinking water sources and restoring community watershed ecosystems.",
        annual_budget=620000,
        mission="Protect community drinking water quality, restore degraded wetlands and urban waterways, conduct citizen science water testing, and advocate for environmental justice in frontline communities.",
        keywords=[
            "clean drinking water",
            "watershed restoration",
            "environmental justice",
            "water quality monitoring",
            "wetlands conservation",
            "pollution remediation",
            "green infrastructure",
        ],
        target_population="Frontline communities affected by water contamination and environmental pollution",
        service_area="Lower River Basin Watershed",
        founded_year=2018,
        icon="droplet",
    ),
    NonprofitPersona(
        id="veterans-health",
        name="Veterans Forward Initiative",
        sector="Veterans Health & Housing Transition",
        tagline="Supporting military veterans with transitional housing, mental health, and civilian career pathways.",
        annual_budget=780000,
        mission="Provide comprehensive supportive services to transitioning military veterans and their families, including trauma-informed mental health counseling, transitional housing assistance, and civilian workforce training.",
        keywords=[
            "veterans housing",
            "military transition",
            "veteran mental health",
            "PTSD support",
            "veteran workforce development",
            "homeless veteran assistance",
            "service member rehabilitation",
        ],
        target_population="Post-9/11 military veterans, disabled veterans, and their dependents",
        service_area="Statewide Veterans Support Corridor",
        founded_year=2016,
        icon="shield",
    ),
]


def get_persona_by_id(persona_id: str) -> Optional[NonprofitPersona]:
    """Retrieve a nonprofit persona by ID."""
    for p in PERSONAS:
        if p.id == persona_id:
            return p
    return None


def persona_to_org_profile(persona: NonprofitPersona) -> OrgProfile:
    """Convert a persona archetype into a full OrgProfile object."""
    return OrgProfile(
        org_id="default",
        name=persona.name,
        ein="58-1234567",
        mission=persona.mission,
        org_type="501(c)(3) nonprofit",
        founded_year=persona.founded_year,
        annual_budget=persona.annual_budget,
        staff_count=6 if persona.annual_budget < 600000 else 12,
        service_area=persona.service_area,
        target_population=persona.target_population,
        programs=[
            Program(
                name=f"{persona.name} Core Initiative",
                description=persona.tagline,
                participants_served=450,
                outcomes=f"Achieved 88% success rate in target metrics across {persona.service_area}.",
            )
        ],
        past_grants=[
            PastGrant(
                funder="Federal Community Development Grant",
                amount=75000.0,
                year=2024,
                status="completed",
                outcome="Successfully met all quarterly delivery milestones and financial audit standards.",
            )
        ],
        board_members=["Dr. Evelyn Reed (Board Chair)", "Marcus Vance (Treasurer)", "Sarah Lin (Secretary)"],
        keywords=persona.keywords,
    )
