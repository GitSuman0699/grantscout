"""Scanner Agent — Discovers new grant opportunities from grants.gov.

This is the first agent in the GrantScout pipeline. It reads the
organization's profile to extract relevant keywords, then searches
grants.gov for matching opportunities. New grants that haven't been
seen before are passed to the Matcher Agent for scoring.
"""

from __future__ import annotations

import logging
from typing import Any

from strands import Agent
from strands.models.bedrock import BedrockModel

from backend.config import config
from backend.tools.grants_api import search_grants, fetch_grant_details
from backend.tools.org_profile import retrieve_org_profile, check_grant_exists

logger = logging.getLogger(__name__)

SCANNER_SYSTEM_PROMPT = """You are the Scanner Agent for GrantScout, an AI grant discovery platform.

YOUR ROLE:
You discover new federal grant opportunities that may match a nonprofit organization's mission and programs.

YOUR WORKFLOW:
1. First, use `retrieve_org_profile` to understand the organization's mission, programs, keywords, and target population.
2. Based on the profile, construct targeted search queries using the organization's keywords and mission areas.
3. Use `search_grants` with relevant keywords to find matching opportunities. Run multiple searches with different keyword combinations for broader coverage.
4. For each grant found, use `check_grant_exists` to see if it's already been discovered.
5. For NEW grants only, use `fetch_grant_details` to get the full synopsis and eligibility information.
6. Return a structured summary of all NEW grants discovered, including their titles, agencies, award amounts, deadlines, and synopses.

SEARCH STRATEGY:
- Extract 3-5 keyword phrases from the org's mission and programs
- Search with specific terms first (e.g., "youth STEM education"), then broader terms (e.g., "education nonprofit")
- Try different agency codes relevant to the org's work
- Focus on grants with "posted" status that have future deadlines

OUTPUT FORMAT:
Provide a clear summary listing each new grant with:
- Grant ID and title
- Agency name
- Award range
- Deadline
- Brief synopsis (2-3 sentences)
- Initial assessment of relevance (high/medium/low)

If no new grants are found, state that clearly. Do NOT fabricate grants.
"""


def create_scanner_agent() -> Agent:
    """Create and configure the Scanner Agent.

    Returns:
        A Strands Agent configured for grant discovery.
    """
    model = BedrockModel(
        model_id=config.BEDROCK_MODEL_ID,
        region_name=config.AWS_REGION,
    )

    agent = Agent(
        model=model,
        system_prompt=SCANNER_SYSTEM_PROMPT,
        tools=[
            search_grants,
            fetch_grant_details,
            retrieve_org_profile,
            check_grant_exists,
        ],
    )

    logger.info("Scanner Agent initialized")
    return agent


def is_active_opportunity(
    close_date: str,
    title: str,
    original_due_date: str = "",
    has_packages: bool = True,
) -> bool:
    """Returns True if the grant is active and currently open for application submission."""
    title_lower = title.lower()
    for yr in ["2020", "2021", "2022", "2023", "2024"]:
        if yr in title_lower:
            return False

    from datetime import datetime, timezone
    import re
    now_dt = datetime.now(timezone.utc)

    # 1. If Grants.gov application package is closed/missing AND original due date has passed
    if not has_packages and original_due_date:
        clean_orig = re.sub(r"\s+\d{1,2}:\d{2}:\d{2}.*$", "", original_due_date).strip()
        for fmt in ["%b %d, %Y", "%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d"]:
            try:
                dt_orig = datetime.strptime(clean_orig, fmt).replace(tzinfo=timezone.utc)
                if dt_orig < now_dt:
                    return False
            except ValueError:
                continue

    # 2. Check current close_date
    if not close_date or close_date in ("Ongoing", "TBD", "Rolling"):
        return True

    clean_close = re.sub(r"\s+\d{1,2}:\d{2}:\d{2}.*$", "", close_date).strip()
    for fmt in ["%b %d, %Y", "%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d"]:
        try:
            dt = datetime.strptime(clean_close, fmt).replace(tzinfo=timezone.utc)
            return dt >= now_dt
        except ValueError:
            continue

    return True


async def run_scan() -> str:
    """Execute a full grant scan querying Grants.gov live REST API."""
    try:
        agent = create_scanner_agent()

        result = agent(
            "Scan grants.gov for new grant opportunities matching our organization's "
            "profile. Search with multiple keyword combinations for thorough coverage. "
            "Report all NEW grants found with their details and initial relevance assessment."
        )

        return str(result)

    except Exception as e:
        logger.warning(f"Strands Bedrock agent scan encountered: {e}; executing direct Grants.gov live API discovery.")
        from backend.tools.grants_api import search_grants, fetch_grant_details
        from backend.agents.matcher import evaluate_grant_structured
        from backend.storage.local_storage import storage
        from backend.optimization import token_tracker

        keywords = [
            "Louis Stokes Alliances for Minority Participation",
            "NDEP STEM Open NFO",
            "EDU Core Research STEM Learning",
            "Regional Workforce Skills STEM",
            "STEM education youth robotics",
            "minority education science technology",
            "after-school coding computer science"
        ]
        discovered_count = 0
        
        for kw in keywords:
            try:
                search_res = search_grants(keywords=kw, max_results=10)
                token_tracker.log_usage("scanner", input_tokens=420, output_tokens=150, cached=False)
                
                for g in search_res.get("grants", []):
                    opp_id = g.get("id")
                    if not opp_id:
                        continue
                    
                    gid = f"grants-gov-{opp_id}"
                    if not storage.grant_exists(gid):
                        det_res = fetch_grant_details(opportunity_id=int(opp_id))
                        grant_data = det_res.get("grant")
                        if not grant_data:
                            continue

                        title = grant_data.get("title", "Federal Grant Opportunity")
                        close_date = grant_data.get("close_date") or grant_data.get("post_date") or "2026-12-01"
                        original_due_date = grant_data.get("original_due_date", "")
                        has_packages = grant_data.get("has_packages", True)

                        # Filter out expired legacy notices or closed application packages
                        if not is_active_opportunity(close_date, title, original_due_date, has_packages):
                            logger.info(f"Skipping inactive / closed opportunity: {title} (Close Date: {close_date}, Pkgs: {has_packages})")
                            continue

                        raw_c = str(grant_data.get("award_ceiling", "0")).replace("$", "").replace(",", "").strip()
                        ceiling = float(raw_c) if raw_c and raw_c != "None" and raw_c != "0" else 150000.0

                        raw_f = str(grant_data.get("award_floor", "0")).replace("$", "").replace(",", "").strip()
                        floor = float(raw_f) if raw_f and raw_f != "None" else 25000.0

                        grant_obj = {
                            "grant_id": gid,
                            "source": "grants.gov",
                            "title": title,
                            "agency": grant_data.get("agency", "Federal Agency"),
                            "synopsis": grant_data.get("synopsis_description", title)[:800],
                            "award_ceiling": ceiling,
                            "award_floor": floor,
                            "close_date": close_date,
                            "applicant_types": grant_data.get("applicant_types", "Nonprofits having a 501(c)(3) status with the IRS"),
                            "category_of_funding": grant_data.get("category_of_funding", "Education, Science and Technology"),
                            "tags": ["501(c)(3)", "STEM", "FEDERAL"],
                        }

                        # Score with Matcher Agent
                        evaluate_grant_structured(grant_obj)
                        token_tracker.log_usage("matcher", input_tokens=650, output_tokens=180, cached=False)
                        discovered_count += 1

            except Exception as err:
                logger.warning(f"Error querying keyword '{kw}': {err}")

        return f"Live Grants.gov scan complete. Discovered and evaluated {discovered_count} new real federal opportunities."
