"""Matcher Agent — Evaluates grant-to-organization fit.

This agent receives grant opportunities discovered by the Scanner
and scores them against the organization's profile across 5 dimensions.
Grants scoring ≥80 are routed to drafting, 50-79 are flagged for review,
and <50 are archived silently.
"""

from __future__ import annotations

import logging

from strands import Agent
from strands.models.bedrock import BedrockModel

from backend.config import config
from backend.tools.org_profile import retrieve_org_profile, save_matched_grant

logger = logging.getLogger(__name__)

MATCHER_SYSTEM_PROMPT = """You are the Matcher Agent for GrantScout, an AI grant discovery platform.

YOUR ROLE:
You evaluate how well a grant opportunity matches a nonprofit organization's profile.
You produce a detailed match score and reasoning.

SCORING DIMENSIONS (total = 100):

1. MISSION ALIGNMENT (0-30 points):
   - How closely does the grant's purpose align with the org's stated mission?
   - Does the grant target the same population the org serves?
   - Are the grant's goals compatible with the org's existing programs?
   - 25-30: Near-perfect alignment
   - 15-24: Strong alignment with minor gaps
   - 5-14: Partial alignment
   - 0-4: Poor or no alignment

2. ELIGIBILITY FIT (0-25 points):
   - Does the org's type match the grant's eligible applicant types?
   - Does the org meet any stated minimum requirements?
   - Are there disqualifying factors? (If so, score 0)
   - 20-25: Clearly eligible with strong fit
   - 10-19: Likely eligible, minor uncertainties
   - 1-9: Eligibility uncertain
   - 0: Clearly ineligible

3. CAPACITY MATCH (0-20 points):
   - Is the award amount realistic for the org's current budget?
   - Does the org have the staff capacity to execute the proposed work?
   - Has the org managed grants of similar size before?
   - 16-20: Award and capacity well-matched
   - 8-15: Manageable stretch
   - 1-7: Significant capacity gap
   - 0: Completely beyond capacity

4. GEOGRAPHIC FIT (0-15 points):
   - Does the grant target the org's service area?
   - Is it a national grant (any location)?
   - Does it specify regions the org doesn't serve?
   - 12-15: Perfect geographic match or national
   - 6-11: Overlapping service areas
   - 1-5: Limited geographic overlap
   - 0: Completely different geography

5. TRACK RECORD (0-10 points):
   - Has the org done similar work before?
   - Does the org have past grants from the same agency?
   - Can the org demonstrate relevant outcomes?
   - 8-10: Strong relevant track record
   - 4-7: Some relevant experience
   - 1-3: Limited relevant experience
   - 0: No relevant track record

YOUR WORKFLOW:
1. Use `retrieve_org_profile` to get the organization's complete profile.
2. Carefully analyze each scoring dimension.
3. Assign scores with clear justification for each dimension.
4. Determine the routing decision:
   - Score ≥ 80: Set status to "matched" (route to application drafting)
   - Score 50-79: Set status to "matched" (flag for user review)
   - Score < 50: Set status to "archived" (archive silently)
5. Use `save_matched_grant` to persist the scored grant.

OUTPUT FORMAT:
Provide the score breakdown, total score, routing decision, and a 2-3 sentence 
explanation of why this grant is or isn't a good fit. Be specific and reference 
concrete details from both the grant and the org profile.

IMPORTANT:
- Be honest and precise in scoring. Do NOT inflate scores.
- If a grant is clearly ineligible, score eligibility as 0 and the total will reflect that.
- Consider the org's realistic capacity — a $1M grant for a $50K budget org is a mismatch.
"""


def create_matcher_agent() -> Agent:
    """Create and configure the Matcher Agent.

    Returns:
        A Strands Agent configured for grant matching and scoring.
    """
    model = BedrockModel(
        model_id=config.BEDROCK_MODEL_ID,
        region_name=config.AWS_REGION,
    )

    agent = Agent(
        model=model,
        system_prompt=MATCHER_SYSTEM_PROMPT,
        tools=[
            retrieve_org_profile,
            save_matched_grant,
        ],
    )

    logger.info("Matcher Agent initialized")
    return agent


def score_grant(grant_details: dict) -> str:
    """Score a single grant against the org profile.

    Args:
        grant_details: Full grant details from the Scanner Agent.

    Returns:
        Match analysis as a string.
    """
    agent = create_matcher_agent()

    prompt = f"""Evaluate this grant opportunity against our organization's profile:

GRANT DETAILS:
- Title: {grant_details.get('title', 'Unknown')}
- Agency: {grant_details.get('agency', 'Unknown')}
- Grant ID: {grant_details.get('id', 'Unknown')}
- Synopsis: {grant_details.get('synopsis_description', grant_details.get('synopsis', 'Not available'))}
- Award Ceiling: ${grant_details.get('award_ceiling', 0)}
- Award Floor: ${grant_details.get('award_floor', 0)}
- Deadline: {grant_details.get('close_date', 'Not specified')}
- Eligible Applicants: {grant_details.get('applicant_types', 'Not specified')}
- Funding Category: {grant_details.get('category_of_funding', 'Not specified')}

Score this grant across all 5 dimensions, explain your reasoning, 
determine the routing decision, and save the result using save_matched_grant.
Use grant_id format: 'grants-gov-{grant_details.get("id", "unknown")}'.
"""

    result = agent(prompt)
    return str(result)
