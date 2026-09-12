"""GrantScout Discovery Engine (Tier 2 - Application Backend).

Deterministic grant discovery, query expansion, Grants.gov API ingestion,
date/deadline validation, and duplicate prevention.
Executes with zero LLM tokens during discovery search.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from backend.storage.local_storage import storage
from backend.tools.grants_api import fetch_grant_details, search_grants
from backend.tools.org_profile import save_matched_grant

logger = logging.getLogger(__name__)


def is_active_opportunity(
    close_date: str,
    title: str,
    original_due_date: str = "",
    fiscal_year: int | None = None,
    post_date: str = "",
    has_packages: bool = True,
) -> bool:
    """Returns True if the grant is active, open, and has an active application package on Grants.gov."""
    now_dt = datetime.now(timezone.utc)

    if not has_packages:
        return False

    if fiscal_year is not None:
        try:
            if fiscal_year < 2026:
                return False
        except (ValueError, TypeError):
            pass

    title_lower = title.lower()
    for yr in ["2019", "2020", "2021", "2022", "2023", "2024"]:
        if yr in title_lower:
            return False

    if close_date in ("Ongoing", "TBD", "Rolling"):
        return True

    if not close_date:
        return False

    clean_close = re.sub(r"\s+\d{1,2}:\d{2}:\d{2}.*$", "", close_date).strip()
    for fmt in ["%b %d, %Y", "%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d"]:
        try:
            dt = datetime.strptime(clean_close, fmt).replace(tzinfo=timezone.utc)
            # Grant must be open and have at least 7 days remaining for proposal preparation
            return (dt - now_dt).total_seconds() >= 7 * 86400
        except ValueError:
            continue

    return False


def is_domain_relevant(grant_info: dict[str, Any], profile_data: dict[str, Any]) -> tuple[bool, str]:
    """Pre-filter opportunities to avoid evaluating grants completely outside the nonprofit's scope."""
    title = (grant_info.get("title") or "").lower()
    synopsis = (grant_info.get("synopsis_description") or grant_info.get("synopsis") or "").lower()
    full_text = f"{title} {synopsis}"

    # 1. Skip RFIs (Requests for Information) and non-grant notices
    if title.startswith("request for information") or "rfi" in title.split():
        return False, "Skipped: Request for Information (RFI), not a grant opportunity"

    # 2. Check for exact phrase matches from profile keywords
    keywords = profile_data.get("keywords", [])
    for kw in keywords:
        clean_kw = kw.strip().strip('"').lower()
        if clean_kw and clean_kw in full_text:
            return True, f"Direct keyword phrase match: '{clean_kw}'"

    # 3. Check for substantive domain keyword matches (words > 3 chars)
    domain_terms = set()
    for kw in keywords:
        for word in re.findall(r"[a-zA-Z0-9\-]+", kw.lower()):
            if len(word) > 3 and word not in {"with", "from", "that", "this", "have", "more", "into", "their"}:
                domain_terms.add(word)

    matches = [w for w in domain_terms if w in full_text]
    # If 2 or more domain terms match anywhere in full text, or 1 in the title
    if len(matches) >= 2:
        return True, f"Domain terms matched: {matches[:3]}"
    elif len(matches) == 1 and any(w in title for w in matches):
        return True, f"Domain term matched in title: {matches[0]}"

    return False, "No substantive domain keyword alignment with organization profile"


def _safe_float(val: Any) -> float:
    """Safely convert award amounts to float, handling 'none', 'N/A', strings, and None."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    try:
        clean = str(val).strip().replace("$", "").replace(",", "").lower()
        if clean in ("none", "n/a", "null", ""):
            return 0.0
        return float(clean)
    except (ValueError, TypeError):
        return 0.0


def execute_discovery_scan(max_candidates: int = 6) -> dict[str, Any]:
    """Discover authentic grant opportunities by querying Grants.gov with targeted org profile keywords.

    Uses high-precision quoted search queries and pre-filters opportunities against the
    nonprofit's domain and active window to avoid wasting resources on irrelevant grants.
    Saves newly discovered candidate grants to persistent storage with status='discovered'.

    Returns:
        Dictionary containing the list of newly found grant opportunities.
    """
    profile_data = storage.get_org_profile("default") or {}
    if not profile_data:
        return {"count": 0, "grants": [], "error": "No org profile found"}

    raw_keywords = profile_data.get("keywords", [])
    # Dynamic Query Expansion: combine primary exact phrases with unquoted and mission variations
    search_queries = []
    for kw in raw_keywords[:4]:
        kw_clean = kw.strip().strip('"')
        if kw_clean:
            search_queries.append(f'"{kw_clean}"')
            if " " in kw_clean:
                search_queries.append(kw_clean)

    mission_text = (profile_data.get("mission") or "").lower()
    if "stem" in mission_text and '"STEM education"' not in search_queries:
        search_queries.append('"STEM education"')
    if "robotics" in mission_text and '"robotics"' not in search_queries:
        search_queries.append('"robotics"')
    if "youth" in mission_text or "education" in mission_text:
        search_queries.append("youth development")

    if not search_queries:
        search_queries = ['"STEM education"', "robotics", '"after-school"', "youth education"]

    # Deduplicate while preserving order, cap at 6 distinct queries
    dedup_queries = []
    for q in search_queries:
        if q not in dedup_queries:
            dedup_queries.append(q)
    search_queries = dedup_queries[:6]

    logger.info(f"[Tier 2 Discovery] Searching Grants.gov across {len(search_queries)} queries: {search_queries}")

    seen_ids = set()
    candidate_grants = []
    for query in search_queries:
        try:
            search_res = search_grants(keywords=query, max_results=6)
            for g in search_res.get("grants", []):
                gid_num = g.get("id")
                if gid_num and gid_num not in seen_ids:
                    seen_ids.add(gid_num)
                    candidate_grants.append(g)
        except Exception as e:
            logger.warning(f"Search query '{query}' failed: {e}")

    new_grants = []
    for g in candidate_grants:
        gid = f"grants-gov-{g.get('id')}"
        existing = storage.get_grant(gid)
        if existing:
            # If already evaluated or archived, skip
            if existing.get("status") in ("matched", "archived", "ready_for_review", "in_progress"):
                continue

        # Fetch full opportunity details
        try:
            opp_id_str = str(g.get("id") or "").strip()
            opp_id_val: int | str = int(opp_id_str) if opp_id_str.isdigit() else opp_id_str
            detail_res = fetch_grant_details(opportunity_id=opp_id_val)
            grant_info = detail_res.get("grant") or g
            grant_info["grant_id"] = gid
            if opp_id_str:
                grant_info["id"] = opp_id_str
                grant_info["application_url"] = f"https://www.grants.gov/search-results-detail/{opp_id_str}"
                grant_info["url"] = grant_info["application_url"]
            if g.get("opportunity_number"):
                grant_info["opportunity_number"] = g.get("opportunity_number")
        except Exception as e:
            logger.warning(f"Failed to fetch details for grant {gid}: {e}")
            continue

        # 1. Filter out closed/inactive opportunities
        if not is_active_opportunity(
            close_date=grant_info.get("close_date", ""),
            title=grant_info.get("title", ""),
            original_due_date=grant_info.get("original_due_date", ""),
            fiscal_year=grant_info.get("fiscal_year"),
            has_packages=grant_info.get("has_packages", True),
        ):
            logger.info(f"Filtered out inactive/closed opportunity: {gid} - {grant_info.get('title')}")
            continue

        # 2. Pre-filter by domain relevance to avoid scanning unnecessary grants
        relevant, reason = is_domain_relevant(grant_info, profile_data)
        if not relevant:
            logger.info(f"Pre-filtered unrelated opportunity: {gid} ('{grant_info.get('title')}') - {reason}")
            continue

        logger.info(f"Discovered authentic candidate grant: {gid} ('{grant_info.get('title')}') - {reason}")
        new_grants.append(grant_info)

        # Persist candidate grant with status='discovered' to pipeline storage
        try:
            save_matched_grant(
                grant_id=gid,
                title=grant_info.get("title", "Grant Opportunity"),
                agency=grant_info.get("agency", "Federal Agency"),
                synopsis=str(grant_info.get("synopsis_description") or grant_info.get("synopsis") or ""),
                award_ceiling=_safe_float(grant_info.get("award_ceiling")),
                award_floor=_safe_float(grant_info.get("award_floor")),
                close_date=str(grant_info.get("close_date") or "TBD"),
                status="discovered",
                match_score={"mission_alignment": 0, "eligibility_fit": 0, "capacity_match": 0, "geographic_fit": 0, "track_record": 0, "total": 0},
                match_reasoning="Discovered candidate awaiting fit evaluation",
                opportunity_id=opp_id_str,
                opportunity_number=grant_info.get("opportunity_number"),
                application_url=grant_info.get("application_url"),
            )
            logger.info(f"Persisted candidate grant {gid} to pipeline storage.")
        except Exception as e:
            logger.warning(f"Failed to persist candidate grant {gid}: {e}")

        if len(new_grants) >= max_candidates:
            break

    return {"count": len(new_grants), "grants": new_grants, "error": None}
