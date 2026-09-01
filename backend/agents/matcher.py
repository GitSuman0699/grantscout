"""Matcher Agent — Evaluates grant-to-organization fit.

This agent receives grant opportunities discovered by the Scanner
and scores them against the organization's profile across 5 dimensions.
Grants scoring ≥80 are routed to drafting, 50-79 are flagged for review,
and <50 are archived silently.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from strands import Agent
from strands.models.bedrock import BedrockModel
from botocore.config import Config

from backend.config import config
from backend.tools.org_profile import retrieve_org_profile, save_matched_grant
from backend.tools.rag_search import query_knowledge_base
from backend.api.models.schemas import GrantEvaluationResult, MatchScore, GrantStatus

logger = logging.getLogger(__name__)

MATCHER_SYSTEM_PROMPT = """You are the Matcher Agent for GrantScout, an AI grant discovery platform.

YOUR ROLE:
You evaluate how well a grant opportunity matches a nonprofit organization's profile.
You produce a detailed match score and reasoning using a strict structured output schema.
You have access to `query_knowledge_base` to check the organization's past grant awards, financials, and verified metrics.

SCORING DIMENSIONS (total = 100):

1. MISSION ALIGNMENT (0-30 points):
   - How closely does the grant's purpose align with the org's stated mission?
   - Does the grant target the same population the org serves?
   - Are the grant's goals compatible with the org's existing programs?

2. ELIGIBILITY FIT (0-25 points):
   - Does the org's type match the grant's eligible applicant types?
   - Does the org meet any stated minimum requirements?
   - Disqualifying factors receive 0.

3. CAPACITY MATCH (0-20 points):
   - Is the award amount realistic for the org's current budget?
   - Does the org have the staff capacity to execute the proposed work?

4. GEOGRAPHIC FIT (0-15 points):
   - Does the grant target the org's service area or is it national?

5. TRACK RECORD (0-10 points):
   - Has the org done similar work before with measurable outcomes?

ROUTING CRITERIA:
- Score ≥ 80: Status = 'matched', Recommended Action = 'auto_draft'
- Score 50-79: Status = 'matched', Recommended Action = 'manual_review'
- Score < 50: Status = 'archived', Recommended Action = 'archive_silently'
"""


from backend.optimization import get_model_for_agent

def create_matcher_agent() -> Agent:
    """Create and configure the Matcher Agent.

    Returns:
        A Strands Agent configured for grant matching and scoring.
    """
    model_cfg = get_model_for_agent("matcher")
    model = BedrockModel(
        model_id=model_cfg.model_id,
        region_name=model_cfg.region,
        boto_client_config=Config(read_timeout=3600, connect_timeout=900, retries={'max_attempts': 3, 'mode': 'standard'})
    )

    agent = Agent(
        model=model,
        system_prompt=MATCHER_SYSTEM_PROMPT,
        tools=[
            retrieve_org_profile,
            query_knowledge_base,
            save_matched_grant,
        ],
    )

    logger.info("Matcher Agent initialized")
    return agent


def evaluate_grant_structured(grant_details: dict[str, Any], persist: bool = True) -> GrantEvaluationResult:
    """Evaluate a grant against the org profile with structured Pydantic output.

    Args:
        grant_details: Dictionary containing grant opportunity fields.
        persist: Whether to save the scored grant to persistent storage. Default True.

    Returns:
        Validated GrantEvaluationResult Pydantic model instance.
    """
    gid = grant_details.get("grant_id") or f"grants-gov-{grant_details.get('id', 'unknown')}"
    title = grant_details.get("title", "Grant Opportunity")
    agency = grant_details.get("agency", "Federal Agency")
    synopsis = grant_details.get("synopsis_description", grant_details.get("synopsis", ""))
    award_ceiling = grant_details.get("award_ceiling", 0)
    close_date = grant_details.get("close_date", "TBD")
    applicant_types = grant_details.get("applicant_types", "")

    prompt = f"""Evaluate this federal grant opportunity against our organization profile:

TARGET OPPORTUNITY:
- ID: {gid}
- Title: {title}
- Agency: {agency}
- Award Ceiling: ${award_ceiling}
- Deadline: {close_date}
- Eligible Applicants: {applicant_types}
- Synopsis: {synopsis}

Retrieve our org profile and return a fully formulated GrantEvaluationResult.
"""

    agent = create_matcher_agent()

    try:
        # Modern Strands SDK structured output invocation
        agent_result = agent(prompt, structured_output_model=GrantEvaluationResult)
        if isinstance(agent_result.structured_output, GrantEvaluationResult):
            evaluation = agent_result.structured_output
        else:
            raise ValueError("Empty or invalid structured output returned by agent")
    except Exception as e:
        logger.error(f"Live Bedrock structured_output invocation unavailable ({e}); failing evaluation.")
        raise ValueError(f"Matcher evaluation failed due to an error: {e}")

    # Persist the evaluated result only if persist is True
    if persist:
        synopsis_val = str(grant_details.get("synopsis_description") or grant_details.get("synopsis") or "")
        save_matched_grant(
            grant_id=evaluation.grant_id,
            title=grant_details.get("title", "Grant Opportunity"),
            agency=grant_details.get("agency", "Federal Agency"),
            synopsis=synopsis_val,
            award_ceiling=float(grant_details.get("award_ceiling") or 0),
            award_floor=float(grant_details.get("award_floor") or 0),
            close_date=grant_details.get("close_date", "TBD"),
            status=evaluation.status.value,
            match_score=evaluation.match_score.model_dump(),
            match_reasoning=evaluation.match_reasoning,
        )

    return evaluation


def score_grant(grant_details: dict) -> str:
    """Score a single grant against the org profile with structured output enforcement.

    Args:
        grant_details: Full grant details from the Scanner Agent.

    Returns:
        Formatted summary string of the structured evaluation.
    """
    evaluation = evaluate_grant_structured(grant_details)
    return (
        f"Grant: {evaluation.grant_id}\n"
        f"Score: {evaluation.match_score.total}/100\n"
        f"Status: {evaluation.status.value.upper()}\n"
        f"Action: {evaluation.recommended_action}\n"
        f"Reasoning: {evaluation.match_reasoning}\n"
        f"Key Strengths: {', '.join(evaluation.key_strengths)}"
    )
