"""Custom Strands tools for grant application drafting and document generation."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from strands import tool

from backend.storage.local_storage import storage

logger = logging.getLogger(__name__)


@tool
def save_application_draft(
    grant_id: str,
    org_id: str,
    grant_title: str,
    sections: list[dict[str, Any]],
) -> dict[str, Any]:
    """Save a generated grant application draft to storage.

    Use this tool to persist a multi-section application draft after it has been
    drafted and reviewed by specialist agents.

    Args:
        grant_id: The unique ID of the target grant opportunity.
        org_id: The organization ID applying for the grant.
        grant_title: Title of the grant opportunity.
        sections: List of section dictionaries. Each section should have:
                  - 'title': str (e.g. 'Executive Summary', 'Project Narrative', 'Budget & Justification')
                  - 'content': str (the full generated text for this section)
                  - 'is_auto_filled': bool (True if pre-filled from org data)
                  - 'needs_review': bool (True if human review is recommended)
                  - 'word_count': int (number of words in content)

    Returns:
        A dictionary containing the 'draft_id', 'status', and 'saved' boolean.
    """
    try:
        draft_id = f"draft-{uuid.uuid4().hex[:10]}"
        
        # Calculate completion and section counts
        total_sections = len(sections)
        auto_filled_count = sum(1 for s in sections if s.get("is_auto_filled", False))
        completion_pct = round((auto_filled_count / total_sections * 100), 1) if total_sections > 0 else 0.0

        for sec in sections:
            if "word_count" not in sec or not sec["word_count"]:
                sec["word_count"] = len(sec.get("content", "").split())

        draft_data = {
            "draft_id": draft_id,
            "grant_id": grant_id,
            "org_id": org_id,
            "grant_title": grant_title,
            "sections": sections,
            "completion_percentage": completion_pct,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        storage.save_application(draft_data)

        # Update grant status to ready_for_review if grant exists
        grant = storage.get_grant(grant_id)
        if grant:
            grant["status"] = "ready_for_review"
            grant["draft_location"] = draft_id
            grant["updated_at"] = datetime.utcnow().isoformat()
            storage.save_grant(grant)

        # Add activity entry
        storage.add_activity({
            "event_type": "application_drafted",
            "message": f"Pre-filled application draft for '{grant_title}' ({completion_pct}% auto-completed)",
            "details": {"grant_id": grant_id, "draft_id": draft_id},
            "timestamp": datetime.utcnow().isoformat(),
        })

        logger.info(f"Saved application draft {draft_id} for grant {grant_id}")
        return {
            "draft_id": draft_id,
            "saved": True,
            "completion_percentage": completion_pct,
            "error": None,
        }

    except Exception as e:
        logger.error(f"Error saving application draft: {e}")
        return {"draft_id": None, "saved": False, "error": str(e)}


@tool
def get_existing_application_draft(grant_id: str) -> dict[str, Any]:
    """Retrieve an existing application draft for a given grant ID.

    Use this tool to check if an application has already been drafted or to
    read previous draft content for refinement.

    Args:
        grant_id: Unique grant ID to look up.

    Returns:
        Dictionary with 'found' boolean and 'draft' data if present.
    """
    try:
        apps = storage.list_applications()
        for app in apps:
            if app.get("grant_id") == grant_id:
                return {"found": True, "draft": app, "error": None}
        return {"found": False, "draft": None, "error": None}
    except Exception as e:
        logger.error(f"Error finding application draft: {e}")
        return {"found": False, "draft": None, "error": str(e)}
