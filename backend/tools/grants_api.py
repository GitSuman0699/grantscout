"""Custom Strands tools for interacting with the grants.gov API.

These tools enable the Scanner Agent to discover and retrieve
grant opportunities from the federal grants.gov database.
The API is public and requires no authentication.
"""

from __future__ import annotations

from datetime import datetime, timezone
import html
import logging
import re
from typing import Any

import requests

from backend.config import config

logger = logging.getLogger(__name__)

GRANTS_API_BASE = config.GRANTS_API_BASE_URL
REQUEST_TIMEOUT = 10

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


def strip_html_tags(text: str) -> str:
    """Remove HTML tags and decode entities from API response text."""
    if not text:
        return ""
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', ' ', text)
    # Decode HTML entities
    clean = html.unescape(clean)
    # Collapse whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def search_grants(
    keywords: str,
    agency: str = "",
    funding_category: str = "",
    max_results: int = 25,
) -> dict[str, Any]:
    """Search grants.gov for federal funding opportunities matching the given criteria.

    Use this tool to discover new grant opportunities that may match a nonprofit's
    mission and programs. The tool queries the public grants.gov API and returns
    a list of currently posted or forecasted opportunities.

    Args:
        keywords: Search terms related to the organization's mission and programs.
                  Use specific terms like 'youth STEM education' rather than generic
                  terms like 'education'. Multiple keywords can be space-separated.
        agency: Optional. Federal agency code to filter by (e.g., 'HHS' for Health
                and Human Services, 'ED' for Department of Education, 'NSF' for
                National Science Foundation). Leave empty to search all agencies.
        funding_category: Optional. Funding category code to filter results.
                          Common codes: 'ED' (Education), 'HL' (Health),
                          'IS' (Income Security), 'AR' (Arts), 'EN' (Environment).
                          Leave empty to search all categories.
        max_results: Maximum number of results to return. Default is 25.

    Returns:
        A dictionary containing:
        - 'total_count': Total number of matching opportunities found
        - 'grants': List of grant summaries with id, title, agency, award info, and deadlines
        - 'search_params': The search parameters used
        - 'error': Error message if the search failed, None otherwise
    """
    try:
        request_body = {
            "keyword": keywords,
            "oppStatuses": "posted",
            "sortBy": "openDate|desc",
            "rows": min(max_results, 50),
            "startRecordNum": 0,
        }

        if agency:
            request_body["agencies"] = agency
        if funding_category:
            request_body["fundingCategories"] = funding_category

        logger.info(f"Searching grants.gov with keywords='{keywords}', agency='{agency}'")

        response = requests.post(
            f"{GRANTS_API_BASE}/search2",
            headers=DEFAULT_HEADERS,
            json=request_body,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        # Parse the response into a clean format
        opp_hits = data.get("data", {}).get("oppHits", [])
        total_count = data.get("data", {}).get("totalCount", 0)

        grants = []
        for opp in opp_hits:
            grant = {
                "id": opp.get("id"),
                "opportunity_number": opp.get("number", ""),
                "title": opp.get("title", "Unknown Title"),
                "agency": opp.get("agency", ""),
                "open_date": opp.get("openDate", ""),
                "close_date": opp.get("closeDate", ""),
                "award_ceiling": opp.get("awardCeiling", 0),
                "award_floor": opp.get("awardFloor", 0),
                "opportunity_status": opp.get("oppStatus", ""),
            }
            grants.append(grant)

        logger.info(f"Found {len(grants)} grants out of {total_count} total matches")

        return {
            "total_count": total_count,
            "grants": grants,
            "search_params": {
                "keywords": keywords,
                "agency": agency,
                "funding_category": funding_category,
            },
            "error": None,
        }

    except requests.exceptions.Timeout:
        logger.error("grants.gov API request timed out")
        return {
            "total_count": 0,
            "grants": [],
            "search_params": {"keywords": keywords},
            "error": "Request timed out. grants.gov may be experiencing high load.",
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"grants.gov API request failed: {e}")
        return {
            "total_count": 0,
            "grants": [],
            "search_params": {"keywords": keywords},
            "error": f"API request failed: {e!s}",
        }
    except Exception as e:
        logger.error(f"Unexpected error searching grants: {e}")
        return {
            "total_count": 0,
            "grants": [],
            "search_params": {"keywords": keywords},
            "error": f"Unexpected error: {e!s}",
        }


def fetch_grant_details(opportunity_id: int | str) -> dict[str, Any]:
    """Fetch detailed information about a specific grant opportunity from grants.gov.

    Use this tool after discovering a grant via search_grants to retrieve the full
    details including synopsis, eligibility requirements, award amounts, and deadlines.
    This provides the complete information needed for match scoring and application drafting.

    Args:
        opportunity_id: The unique grants.gov opportunity ID number.
                        This is the 'id' field from search_grants results.

    Returns:
        A dictionary containing:
        - 'grant': Full grant details including synopsis, eligibility, award info, and dates
        - 'error': Error message if the fetch failed, None otherwise
    """
    try:
        logger.info(f"Fetching grant details for opportunity_id={opportunity_id}")

        opp_id_payload = int(opportunity_id) if str(opportunity_id).isdigit() else opportunity_id
        response = requests.post(
            f"{GRANTS_API_BASE}/fetchOpportunity",
            headers=DEFAULT_HEADERS,
            json={"opportunityId": opp_id_payload},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        opp = data.get("data", {})
        synopsis = opp.get("synopsis") or opp.get("forecast") or {}

        raw_title = opp.get("opportunityTitle") or synopsis.get("opportunityTitle", "Unknown Title")
        clean_title = strip_html_tags(raw_title) if raw_title else "Unknown Title"

        raw_synopsis = synopsis.get("synopsisDesc") or synopsis.get("forecastDesc") or synopsis.get("description") or ""
        clean_synopsis = strip_html_tags(raw_synopsis) if raw_synopsis else ""

        raw_agency = synopsis.get("agencyName", "")
        clean_agency = strip_html_tags(raw_agency) if raw_agency else ""

        pkgs = opp.get("opportunityPkgs", [])
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        has_active_packages = False
        for p in pkgs:
            pkg_close = str(p.get("closingDate") or p.get("closingDateStr") or "").strip()
            if pkg_close:
                pkg_close_date = pkg_close[:10]  # YYYY-MM-DD
                if pkg_close_date >= now_iso:
                    has_active_packages = True
                    break
            else:
                has_active_packages = True
                break

        has_packages = has_active_packages if pkgs else False

        post_date = synopsis.get("postingDate") or synopsis.get("createdDate") or ""
        close_date = synopsis.get("responseDate") or synopsis.get("estApplicationResponseDate") or ""
        fiscal_year = synopsis.get("fiscalYear")

        grant_details = {
            "id": opp.get("id"),
            "opportunity_number": opp.get("opportunityNumber", ""),
            "title": clean_title,
            "agency": clean_agency,
            "agency_code": synopsis.get("agencyCode", ""),
            "synopsis_description": clean_synopsis,
            "award_ceiling": synopsis.get("awardCeiling", synopsis.get("estimatedFunding", "0")),
            "award_floor": synopsis.get("awardFloor", "0"),
            "post_date": post_date,
            "close_date": close_date,
            "original_due_date": opp.get("originalDueDate", ""),
            "fiscal_year": fiscal_year,
            "has_packages": has_packages,
            "archive_date": synopsis.get("archiveDate", ""),
            "estimated_funding": synopsis.get("estimatedFunding", ""),
            "expected_awards": synopsis.get("numberOfAwards", ""),
            "applicant_types": synopsis.get("applicantTypes", []),
            "funding_instrument_type": synopsis.get("fundingInstrumentType", ""),
            "category_of_funding": synopsis.get("categoryOfFunding", ""),
            "additional_info_url": synopsis.get("additionalInformationUrl", ""),
            "grantor_contact_info": synopsis.get("grantorContactInfo", synopsis.get("agencyContactEmail", "")),
        }

        logger.info(f"Successfully fetched details for: {grant_details['title']}")

        return {
            "grant": grant_details,
            "error": None,
        }

    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching grant {opportunity_id}")
        return {
            "grant": None,
            "error": "Request timed out. grants.gov may be experiencing high load.",
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch grant {opportunity_id}: {e}")
        return {
            "grant": None,
            "error": f"API request failed: {e!s}",
        }
    except Exception as e:
        logger.error(f"Unexpected error fetching grant {opportunity_id}: {e}")
        return {
            "grant": None,
            "error": f"Unexpected error: {e!s}",
        }
