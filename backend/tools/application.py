"""Custom Strands tools for grant application drafting and document generation."""

from __future__ import annotations

import csv
import io
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from backend.storage.local_storage import storage

logger = logging.getLogger(__name__)


def generate_budget_csv(grant_id: str, direct_personnel: float, fringe_benefits: float, travel: float, supplies: float, other: float, indirect_rate_pct: float) -> dict[str, Any]:
    """Generate a structured CSV representing the SF-424 budget template for the grant application.
    
    Args:
        grant_id: The ID of the grant.
        direct_personnel: Total personnel salaries.
        fringe_benefits: Total fringe benefits.
        travel: Total travel costs.
        supplies: Total supplies costs.
        other: Total other direct costs.
        indirect_rate_pct: The approved indirect cost rate percentage (e.g. 10.0).
        
    Returns:
        Dictionary containing 'csv_data' string.
    """
    total_direct = direct_personnel + fringe_benefits + travel + supplies + other
    indirect_costs = total_direct * (indirect_rate_pct / 100.0)
    total_costs = total_direct + indirect_costs
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Category", "Amount ($)", "Notes"])
    writer.writerow(["a. Personnel", f"{direct_personnel:.2f}", "Direct Staff Salaries"])
    writer.writerow(["b. Fringe Benefits", f"{fringe_benefits:.2f}", ""])
    writer.writerow(["c. Travel", f"{travel:.2f}", ""])
    writer.writerow(["d. Supplies", f"{supplies:.2f}", ""])
    writer.writerow(["e. Other", f"{other:.2f}", ""])
    writer.writerow(["Total Direct Costs", f"{total_direct:.2f}", "Sum of a-e"])
    writer.writerow([f"Indirect Costs ({indirect_rate_pct}%)", f"{indirect_costs:.2f}", "MTDC Rate"])
    writer.writerow(["TOTAL REQUESTED", f"{total_costs:.2f}", "Total Direct + Indirect"])
    
    csv_str = output.getvalue()
    
    return {"csv_data": csv_str, "total_requested": total_costs}


def update_draft_section(
    grant_id: str,
    org_id: str,
    grant_title: str,
    section_title: str,
    content: str,
) -> dict[str, Any]:
    """Save or update a specific section of a grant application draft.
    
    Use this tool to incrementally build the application draft. Each specialized agent
    should call this tool for the sections they are responsible for writing.
    
    Args:
        grant_id: The unique ID of the target grant opportunity.
        org_id: The organization ID applying for the grant.
        grant_title: Title of the grant opportunity.
        section_title: The specific section being updated (e.g., 'Executive Summary', 'Budget & Financial Justification').
        content: The full drafted text for this section.
    
    Returns:
        A dictionary containing success status and current completion percentage.
    """
    try:
        # Use direct grant_id lookup instead of scanning all files
        # This is faster and avoids issues with corrupted files blocking the scan
        existing = storage.find_application_by_grant_id(grant_id)
        
        if existing:
            draft_data: dict[str, Any] = existing
            sections = draft_data.get("sections", [])
        else:
            draft_data: dict[str, Any] = {
                "draft_id": f"draft-{uuid.uuid4().hex[:10]}",
                "grant_id": grant_id,
                "org_id": org_id,
                "grant_title": grant_title,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "sections": []
            }
            sections = []

        # Update or add section
        section_idx = next((i for i, s in enumerate(sections) if s.get("title") == section_title), -1)
        
        word_count = len(content.split())
        new_section = {
            "title": section_title,
            "content": content,
            "is_auto_filled": True,
            "needs_review": True,
            "word_count": word_count
        }

        if section_idx >= 0:
            sections[section_idx] = new_section
        else:
            sections.append(new_section)
            
        draft_data["sections"] = sections
        draft_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Calculate completion pct
        completion_pct = round((len(sections) / 6.0) * 100, 1)
        draft_data["completion_percentage"] = completion_pct

        storage.save_application(draft_data)
        
        # Update grant status
        grant = storage.get_grant(grant_id)
        if grant:
            grant["status"] = "ready_for_review"
            grant["draft_location"] = draft_data["draft_id"]
            grant["updated_at"] = datetime.now(timezone.utc).isoformat()
            storage.save_grant(grant)
            
        return {"saved": True, "section": section_title, "completion": completion_pct}
        
    except Exception as e:
        logger.error(f"Error updating draft section {section_title}: {e}")
        return {"saved": False, "error": str(e)}


def save_application_draft(
    grant_id: str,
    org_id: str,
    grant_title: str,
    sections: list[dict[str, Any]] | None = None,
    submission_checklist: list[str] | None = None,
    budget_csv_data: str | None = None,
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
        submission_checklist: List of requirements for submission (e.g. SAM.gov, SF-424, letters).
        budget_csv_data: Comma-separated values for the SF-424 budget template.

    Returns:
        A dictionary containing the 'draft_id', 'status', and 'saved' boolean.
    """
    try:
        # Use direct grant_id lookup to preserve existing draft_id
        existing = storage.find_application_by_grant_id(grant_id)
        draft_id = existing.get("draft_id") if existing else f"draft-{uuid.uuid4().hex[:10]}"
        created_at = existing.get("created_at") if existing else datetime.now(timezone.utc).isoformat()

        # Build map of existing sections already drafted in storage
        existing_sections = existing.get("sections", []) if existing else []
        existing_map = {s.get("title", "").strip(): s for s in existing_sections if isinstance(s, dict)}

        # Helper to detect placeholder stubs like "See existing draft"
        def is_placeholder_content(text: Any) -> bool:
            if not text:
                return True
            cleaned = str(text).strip().lower()
            if cleaned in (
                "see existing draft",
                "see existing draft.",
                "existing draft",
                "existing draft.",
                "see draft",
                "as drafted",
                "as drafted in previous section",
                "drafted",
                "see previous draft",
                "refer to draft",
                "placeholder",
            ):
                return True
            if len(cleaned) < 50:
                return True
            return False

        # Merge sections defensively: NEVER overwrite rich drafted text with stubs
        final_sections: list[dict[str, Any]] = []
        if sections and isinstance(sections, list):
            for sec in sections:
                if not isinstance(sec, dict):
                    continue
                title = sec.get("title", "").strip()
                content = str(sec.get("content", ""))

                # If incoming content is a placeholder and we have an existing section with real content, preserve the existing one!
                if is_placeholder_content(content) and title in existing_map:
                    real_sec = existing_map[title]
                    logger.info(f"🛡️ Guarded rich content for section '{title}' ({len(real_sec.get('content', ''))} chars) against placeholder '{content}'")
                    final_sections.append(real_sec)
                else:
                    wc = sec.get("word_count") or len(content.split())
                    final_sections.append({
                        "title": title,
                        "content": content,
                        "is_auto_filled": True,
                        "needs_review": sec.get("needs_review", True),
                        "word_count": wc,
                    })
        else:
            # If sections was None or empty, retain all existing sections
            final_sections = existing_sections

        # If any existing section was omitted in the incoming array, preserve it
        incoming_titles = {s.get("title", "").strip() for s in final_sections}
        for title, ex_sec in existing_map.items():
            if title not in incoming_titles:
                final_sections.append(ex_sec)

        # Sort sections by standard title numbering (1., 2., 3., etc.)
        final_sections.sort(key=lambda s: s.get("title", ""))

        # Calculate true completion percentage based on substantive non-placeholder content
        valid_sections = sum(1 for s in final_sections if not is_placeholder_content(s.get("content", "")))
        completion_pct = round((valid_sections / 6.0) * 100, 1)

        # Clean submission checklist
        clean_checklist = []
        for item in (submission_checklist or []):
            if isinstance(item, str):
                clean_checklist.append(item)
            elif isinstance(item, dict):
                label = item.get("item") or item.get("name") or item.get("task") or item.get("title") or item.get("requirement") or str(item)
                deadline = item.get("deadline") or item.get("timing") or item.get("due") or item.get("status")
                clean_checklist.append(f"{label} ({deadline})" if deadline else str(label))
            else:
                clean_checklist.append(str(item))

        # Preserve existing budget CSV and checklist if not re-provided
        final_budget_csv = budget_csv_data or (existing.get("budget_csv_data") if existing else None)
        final_checklist = clean_checklist if clean_checklist else (existing.get("submission_checklist", []) if existing else [])

        draft_data = {
            "draft_id": draft_id,
            "grant_id": grant_id,
            "org_id": org_id,
            "grant_title": grant_title,
            "sections": final_sections,
            "completion_percentage": completion_pct,
            "submission_checklist": final_checklist,
            "budget_csv_data": final_budget_csv,
            "created_at": created_at,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        storage.save_application(draft_data)

        # Update grant status to ready_for_review if grant exists
        grant = storage.get_grant(grant_id)
        if grant:
            grant["status"] = "ready_for_review"
            grant["draft_location"] = draft_id
            grant["updated_at"] = datetime.now(timezone.utc).isoformat()
            storage.save_grant(grant)

        # Add activity entry
        storage.add_activity({
            "event_type": "application_drafted",
            "message": f"Pre-filled application draft for '{grant_title}' ({completion_pct}% auto-completed)",
            "details": {"grant_id": grant_id, "draft_id": draft_id},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        logger.info(f"Saved application draft {draft_id} for grant {grant_id} ({valid_sections}/6 valid sections)")
        return {
            "draft_id": draft_id,
            "saved": True,
            "completion_percentage": completion_pct,
            "valid_sections": valid_sections,
            "error": None,
        }

    except Exception as e:
        logger.error(f"Error saving application draft: {e}")
        return {"draft_id": None, "saved": False, "error": str(e)}


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
        app = storage.find_application_by_grant_id(grant_id)
        if app:
            return {"found": True, "draft": app, "error": None}
        return {"found": False, "draft": None, "error": None}
    except Exception as e:
        logger.error(f"Error finding application draft: {e}")
        return {"found": False, "draft": None, "error": str(e)}
