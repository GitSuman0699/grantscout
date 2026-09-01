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
from botocore.config import Config

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


from backend.optimization import get_model_for_agent

def create_scanner_agent() -> Agent:
    """Create and configure the Scanner Agent.

    Returns:
        A Strands Agent configured for grant discovery.
    """
    model_cfg = get_model_for_agent("scanner")
    model = BedrockModel(
        model_id=model_cfg.model_id,
        region_name=model_cfg.region,
        boto_client_config=Config(read_timeout=3600, connect_timeout=900, retries={'max_attempts': 3, 'mode': 'standard'})
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
    fiscal_year: int | None = None,
    post_date: str = "",
    has_packages: bool = True,
) -> bool:
    """Returns True if the grant is active, open, and has an active application package on Grants.gov."""
    import re
    from datetime import datetime, timezone
    now_dt = datetime.now(timezone.utc)

    # 1. Require active workspace application packages (so Apply button is enabled on Grants.gov)
    if not has_packages:
        return False

    # 2. Fiscal Year check
    if fiscal_year is not None:
        try:
            if int(fiscal_year) < 2026:
                return False
        except (ValueError, TypeError):
            pass

    # 3. Legacy years in title
    title_lower = title.lower()
    for yr in ["2019", "2020", "2021", "2022", "2023", "2024"]:
        if yr in title_lower:
            return False

    # 4. Check close date
    if close_date in ("Ongoing", "TBD", "Rolling"):
        return True

    if not close_date:
        return False

    clean_close = re.sub(r"\s+\d{1,2}:\d{2}:\d{2}.*$", "", close_date).strip()
    for fmt in ["%b %d, %Y", "%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d"]:
        try:
            dt = datetime.strptime(clean_close, fmt).replace(tzinfo=timezone.utc)
            return dt >= now_dt
        except ValueError:
            continue

    return False


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
        logger.error(f"Strands Bedrock agent scan encountered: {e}")
        raise ValueError(f"Scan failed due to an error: {e}")
