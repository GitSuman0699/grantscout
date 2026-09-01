"""Seed script to populate GrantScout with a demo organization profile.

Run this script to set up a sample nonprofit organization that
demonstrates GrantScout's grant matching capabilities.
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.storage.local_storage import storage


DEMO_ORG_PROFILE = {
    "org_id": "default",
    "name": "Youth Education Alliance",
    "ein": "12-3456789",
    "mission": "Providing after-school STEM education and mentorship programs to underserved youth ages 8-18 in the Metro Atlanta area, empowering them with the skills and confidence to pursue careers in science, technology, engineering, and mathematics.",
    "org_type": "501(c)(3) nonprofit",
    "founded_year": 2019,
    "annual_budget": 450000,
    "staff_count": 5,
    "service_area": "Metro Atlanta, Georgia",
    "target_population": "Underserved youth ages 8-18 from low-income families",
    "programs": [
        {
            "name": "STEM After School",
            "description": "Weekly after-school coding, robotics, and science workshops at 4 community centers across Metro Atlanta. Students learn Python programming, build robots with Arduino kits, and conduct hands-on science experiments.",
            "participants_served": 200,
            "outcomes": "85% of participants improved math grades by at least one letter grade. 92% expressed increased interest in STEM careers."
        },
        {
            "name": "Summer STEM Camp",
            "description": "Intensive 6-week summer camp providing immersive STEM education including app development, environmental science field trips, and guest speakers from local tech companies.",
            "participants_served": 80,
            "outcomes": "100% of campers completed a capstone project. 3 projects won regional science fair awards."
        },
        {
            "name": "Mentorship Connect",
            "description": "One-on-one mentorship program pairing students with STEM professionals from partner companies including Georgia Tech, Emory University, and local tech startups.",
            "participants_served": 50,
            "outcomes": "78% of mentees maintained the mentorship relationship for over 12 months. 15 mentees received college scholarships."
        }
    ],
    "past_grants": [
        {
            "funder": "National Science Foundation (NSF)",
            "amount": 25000,
            "year": 2024,
            "status": "completed",
            "outcome": "Served 150 students across 3 community centers. Purchased robotics kits and lab equipment."
        },
        {
            "funder": "Georgia Department of Education",
            "amount": 15000,
            "year": 2024,
            "status": "completed",
            "outcome": "Funded Summer STEM Camp for 60 students. All students completed the program."
        },
        {
            "funder": "Atlanta Community Foundation",
            "amount": 10000,
            "year": 2025,
            "status": "active",
            "outcome": "Supporting expansion of Mentorship Connect program to 2 additional schools."
        },
        {
            "funder": "Google.org Impact Challenge",
            "amount": 50000,
            "year": 2025,
            "status": "active",
            "outcome": "Developing a mobile app for student progress tracking and parent engagement."
        }
    ],
    "board_members": [
        "Dr. Sarah Chen (Board Chair) — Former Georgia Tech CS Professor",
        "Marcus Williams (Treasurer) — CPA, Partner at Williams & Associates",
        "Dr. Lisa Patel (Secretary) — Pediatrician, Emory Healthcare",
        "James Rodriguez — VP Engineering, Mailchimp",
        "Tamika Johnson — Principal, Westside Community Center"
    ],
    "keywords": [
        "STEM education",
        "youth development",
        "after-school programs",
        "underserved youth",
        "coding education",
        "robotics",
        "mentorship",
        "science education",
        "technology education",
        "low-income students",
        "community education",
        "workforce development"
    ]
}


def seed_org_profile():
    """Seed the demo organization profile."""
    storage.save_org_profile(DEMO_ORG_PROFILE)
    print(f"[OK] Seeded organization profile: {DEMO_ORG_PROFILE['name']}")
    print(f"   Mission: {DEMO_ORG_PROFILE['mission'][:80]}...")
    print(f"   Programs: {len(DEMO_ORG_PROFILE['programs'])}")
    print(f"   Past Grants: {len(DEMO_ORG_PROFILE['past_grants'])}")
    print(f"   Keywords: {', '.join(DEMO_ORG_PROFILE['keywords'][:5])}...")
    print(f"   Storage: {storage.base_path / 'org_profiles' / 'default.json'}")


if __name__ == "__main__":
    seed_org_profile()
