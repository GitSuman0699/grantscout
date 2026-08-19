"""Seed script to populate realistic grant opportunities into GrantScout."""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.storage.local_storage import storage
from backend.tools.application import save_application_draft


SAMPLE_GRANTS = [
    {
        "grant_id": "grants-gov-359104",
        "source": "grants.gov",
        "title": "Louis Stokes Alliances for Minority Participation (LSAMP)",
        "agency": "National Science Foundation",
        "opportunity_number": "NSF-26-504",
        "synopsis": "The Louis Stokes Alliances for Minority Participation (LSAMP) program assists universities and community organizations in diversifying the STEM workforce by increasing the number of STEM degrees awarded to populations historically underrepresented in STEM disciplines. Supports robotics, community coding hubs, and structured pre-college mentoring.",
        "award_ceiling": 75000.0,
        "award_floor": 25000.0,
        "close_date": "2026-11-20",
        "post_date": "2026-08-01",
        "applicant_types": ["nonprofits", "educational_institutions", "community_alliances"],
        "funding_category": "Science and Technology",
        "status": "ready_for_review",
        "match_score": {
            "mission_alignment": 29,
            "eligibility_fit": 25,
            "capacity_match": 19,
            "geographic_fit": 14,
            "track_record": 9
        },
        "match_reasoning": "Exceptional fit with Youth Education Alliance mission. Focuses explicitly on after-school STEM mentoring and robotics for underserved youth with established community outcomes.",
        "draft_location": "draft-lsamp-2026",
        "discovered_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    },
    {
        "grant_id": "grants-gov-345938",
        "source": "grants.gov",
        "title": "NDEP STEM Open National Funding Opportunity",
        "agency": "Department of Defense - STEM",
        "opportunity_number": "NDEP-STEM-2026-01",
        "synopsis": "Supports innovative manufacturing, computer science, and engineering youth programs that enhance STEM literacy and technical workforce pipelines in underserved urban communities.",
        "award_ceiling": 50000.0,
        "award_floor": 10000.0,
        "close_date": "2026-10-15",
        "post_date": "2026-07-15",
        "applicant_types": ["nonprofits", "501c3"],
        "funding_category": "Education",
        "status": "matched",
        "match_score": {
            "mission_alignment": 27,
            "eligibility_fit": 23,
            "capacity_match": 18,
            "geographic_fit": 13,
            "track_record": 8
        },
        "match_reasoning": "Strong match for YEA coding and robotics curriculum. Award ceiling of $50,000 fits perfectly within annual organizational capacity.",
        "draft_location": "",
        "discovered_at": (datetime.utcnow() - timedelta(hours=6)).isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    },
    {
        "grant_id": "grants-gov-362422",
        "source": "grants.gov",
        "title": "EDU Core Research: STEM Learning Ecosystems",
        "agency": "National Science Foundation",
        "opportunity_number": "ECR-2026-88",
        "synopsis": "Fundamental research and implementation grants for informal STEM learning environments, community centers, and summer science learning labs.",
        "award_ceiling": 100000.0,
        "award_floor": 35000.0,
        "close_date": "2026-10-01",
        "post_date": "2026-08-10",
        "applicant_types": ["nonprofits", "universities"],
        "funding_category": "Education",
        "status": "drafting",
        "match_score": {
            "mission_alignment": 26,
            "eligibility_fit": 22,
            "capacity_match": 16,
            "geographic_fit": 13,
            "track_record": 8
        },
        "match_reasoning": "High alignment with Summer STEM Camp programs and hands-on coding initiatives across community center partners.",
        "draft_location": "",
        "discovered_at": (datetime.utcnow() - timedelta(hours=18)).isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    },
    {
        "grant_id": "grants-gov-363347",
        "source": "grants.gov",
        "title": "Regional Workforce Skills & STEM Innovation Hubs",
        "agency": "Department of Commerce",
        "opportunity_number": "DOC-EDA-2026-04",
        "synopsis": "Public diplomacy and community workforce readiness grant for advancing technical literacy and student career pathway coaching.",
        "award_ceiling": 20000.0,
        "award_floor": 10000.0,
        "close_date": "2026-08-27",
        "post_date": "2026-08-01",
        "applicant_types": ["nonprofits"],
        "funding_category": "Community Development",
        "status": "discovered",
        "match_score": {
            "mission_alignment": 21,
            "eligibility_fit": 20,
            "capacity_match": 17,
            "geographic_fit": 9,
            "track_record": 6
        },
        "match_reasoning": "Moderate geographic stretch; targets workforce readiness. Good candidate for smaller program expansion.",
        "draft_location": "",
        "discovered_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
]

SAMPLE_APPLICATION_SECTIONS = [
    {
        "title": "1. Executive Summary",
        "content": "Youth Education Alliance (YEA), a 501(c)(3) nonprofit based in Atlanta, GA, respectfully requests $75,000 from the National Science Foundation LSAMP Program. This funding will support the expansion of our 'STEM After School' and 'Mentorship Connect' programs to 200 additional underserved middle and high school students across Metro Atlanta. By providing weekly Python coding instruction, hands-on robotics workshops, and dedicated industry mentorship from local STEM professionals, this project directly addresses the systemic underrepresentation of minority students in STEM education and careers.",
        "is_auto_filled": True,
        "needs_review": False,
        "word_count": 87
    },
    {
        "title": "2. Organizational Background & Capacity",
        "content": "Founded in 2019, Youth Education Alliance has established an exceptional 7-year track record of delivering high-impact informal STEM education to youth ages 8-18. With an annual operating budget of $450,000 and 5 dedicated staff members, YEA has successfully managed federal and institutional awards including past grants from the NSF ($25,000, 2024), Georgia Department of Education ($15,000, 2024), Google.org ($50,000, 2025), and the Atlanta Community Foundation ($10,000, 2025). Our board comprises distinguished leadership including former Georgia Tech faculty, CPAs, and community leaders.",
        "is_auto_filled": True,
        "needs_review": False,
        "word_count": 85
    },
    {
        "title": "3. Statement of Need & Community Impact",
        "content": "Across Metro Atlanta public schools, fewer than 32% of underserved students in our target ZIP codes achieve proficiency in standardized math and science benchmarks, compared to 68% statewide. Traditional schools lack hardware labs for hands-on robotics and coding practice. YEA fills this critical gap by operating accessible after-school centers with 100% free enrollment, transportation subsidies, and dedicated device lending libraries.",
        "is_auto_filled": True,
        "needs_review": True,
        "word_count": 64
    },
    {
        "title": "4. Project Design & Implementation Timeline",
        "content": "Phase 1 (Months 1-3): Curriculum Refinement & Cohort Enrollment across 4 partner community centers.\nPhase 2 (Months 4-9): 28 weeks of hands-on robotics & Python workshops (2 hours/week) led by certified instructors.\nPhase 3 (Months 10-12): Capstone Project Science Fair & Regional Robotics Competition. 100% of participants will build and present an original hardware project.",
        "is_auto_filled": False,
        "needs_review": True,
        "word_count": 58
    },
    {
        "title": "5. Budget & Financial Justification",
        "content": "Personnel ($42,000): Lead STEM Instructors (2 x $18,000) + Program Coordinator ($6,000).\nEquipment & Supplies ($20,000): 40 Arduino/Raspberry Pi Robotics Kits ($8,000), 25 Chromebooks ($7,500), Lab Consumables ($4,500).\nStudent Transportation & Meals ($8,000): Weekly weekend workshop transit passes & healthy snacks.\nAdministrative & Indirect ($5,000): Program evaluation software and background checks.\nTOTAL REQUEST: $75,000.",
        "is_auto_filled": True,
        "needs_review": True,
        "word_count": 57
    },
    {
        "title": "6. Evaluation & Long-Term Sustainability",
        "content": "Program efficacy will be evaluated using pre- and post-program STEM interest surveys, school grade tracking, and project completion rubrics. Historically, 85% of YEA students improved math grades by at least one full letter grade. Long-term sustainability is anchored by recurring corporate partnerships with Atlanta tech firms and multi-year philanthropic commitments.",
        "is_auto_filled": False,
        "needs_review": True,
        "word_count": 54
    }
]


def seed_sample_data():
    """Seed sample grants and an application draft."""
    for g in SAMPLE_GRANTS:
        storage.save_grant(g)
        score_tot = sum(g["match_score"].values())
        storage.add_activity({
            "event_type": "grant_matched",
            "message": f"Autonomous Evaluator scored '{g['title']}' — {score_tot}% fit",
            "details": {"grant_id": g["grant_id"], "score": score_tot},
            "timestamp": g["discovered_at"],
        })

    # Save a comprehensive application draft
    save_application_draft(
        grant_id="grants-gov-359104",
        org_id="default",
        grant_title="Louis Stokes Alliances for Minority Participation (LSAMP)",
        sections=SAMPLE_APPLICATION_SECTIONS,
    )

    print(f"✅ Seeded {len(SAMPLE_GRANTS)} grant opportunities into GrantScout pipeline.")
    print("✅ Seeded multi-section pre-filled application draft for NSF LSAMP.")


if __name__ == "__main__":
    seed_sample_data()
