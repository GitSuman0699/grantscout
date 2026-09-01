"""Custom Strands tools for managing organization profiles.

These tools allow agents to read and update the nonprofit's
profile data, which is essential for grant matching and
application drafting.
"""

from __future__ import annotations

import logging
from typing import Any

from strands import tool

from backend.storage.local_storage import storage

logger = logging.getLogger(__name__)


@tool
def retrieve_org_profile(org_id: str = "default") -> dict[str, Any]:
    """Retrieve the nonprofit organization's profile including mission, programs, and past grants.

    Use this tool to get the organization's complete profile data, which is needed
    for evaluating grant fit and drafting applications. The profile includes the
    organization's mission, programs, financials, past grants, and target keywords.

    Args:
        org_id: The organization ID to retrieve. Defaults to 'default' for
                single-org installations.

    Returns:
        A dictionary containing the full org profile, or an error message
        if no profile exists.
    """
    try:
        profile = storage.get_org_profile(org_id)
        if profile:
            logger.info(f"Retrieved org profile: {profile.get('name', 'Unknown')}")
            return {"profile": profile, "error": None}
        else:
            return {
                "profile": None,
                "error": "No organization profile found. Please set up your profile first.",
            }
    except Exception as e:
        logger.error(f"Error retrieving org profile: {e}")
        return {"profile": None, "error": f"Failed to retrieve profile: {str(e)}"}


@tool
def save_matched_grant(
    grant_id: str,
    title: str,
    agency: str,
    synopsis: str,
    award_ceiling: float,
    award_floor: float,
    close_date: str,
    status: str,
    match_score: dict,
    match_reasoning: str,
) -> dict[str, Any]:
    """Save a grant opportunity with its match score to the database.

    Use this tool after evaluating a grant's fit against the org profile.
    This persists the grant with its match analysis for the dashboard and
    pipeline tracking.

    Args:
        grant_id: Unique identifier for the grant (e.g., 'grants-gov-289999').
        title: The official title of the grant opportunity.
        agency: The federal agency offering the grant.
        synopsis: Brief description of the grant's purpose and requirements.
        award_ceiling: Maximum award amount in dollars.
        award_floor: Minimum award amount in dollars.
        close_date: Application deadline date string.
        status: Pipeline status - one of: 'discovered', 'matched', 'drafting',
                'ready_for_review', 'submitted', 'archived'.
        match_score: Dictionary with scoring dimensions: mission_alignment (0-30),
                     eligibility_fit (0-25), capacity_match (0-20),
                     geographic_fit (0-15), track_record (0-10).
        match_reasoning: Explanation of why the grant received this score.

    Returns:
        Confirmation of save with the grant_id, or error message.
    """
    try:
        from datetime import datetime

        grant_data = {
            "grant_id": grant_id,
            "source": "grants.gov",
            "title": title,
            "agency": agency,
            "synopsis": synopsis,
            "award_ceiling": award_ceiling,
            "award_floor": award_floor,
            "close_date": close_date,
            "status": status,
            "match_score": match_score,
            "match_reasoning": match_reasoning,
            "discovered_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        storage.save_grant(grant_data)

        # Log activity
        if isinstance(match_score, dict) and "total" in match_score:
            total_score = int(match_score["total"])
        elif isinstance(match_score, dict):
            total_score = sum(int(v) for k, v in match_score.items() if isinstance(v, (int, float)))
        else:
            total_score = 0
        storage.add_activity({
            "event_type": "grant_matched",
            "message": f"Scored '{title}' — {total_score}% match",
            "details": {"grant_id": grant_id, "score": total_score},
            "timestamp": datetime.utcnow().isoformat(),
        })

        logger.info(f"Saved matched grant: {grant_id} with score {total_score}")
        return {"grant_id": grant_id, "saved": True, "error": None}

    except Exception as e:
        logger.error(f"Error saving grant: {e}")
        return {"grant_id": grant_id, "saved": False, "error": str(e)}


@tool
def check_grant_exists(grant_id: str) -> dict[str, Any]:
    """Check if a grant already exists in the database to avoid duplicate processing.

    Use this tool before processing a newly discovered grant to see if it
    has already been discovered and scored in a previous scan.

    Args:
        grant_id: The unique identifier of the grant to check.

    Returns:
        Dictionary with 'exists' boolean and existing grant data if found.
    """
    try:
        exists = storage.grant_exists(grant_id)
        if exists:
            grant = storage.get_grant(grant_id)
            return {"exists": True, "grant": grant, "error": None}
        return {"exists": False, "grant": None, "error": None}
    except Exception as e:
        logger.error(f"Error checking grant existence: {e}")
        return {"exists": False, "grant": None, "error": str(e)}
