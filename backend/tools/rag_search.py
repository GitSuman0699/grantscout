"""Custom Strands tools for querying the RAG knowledge base."""

from __future__ import annotations

import logging
from typing import Any

from strands import tool

from backend.rag.knowledge_base import knowledge_base

logger = logging.getLogger(__name__)


@tool
def query_knowledge_base(query: str, top_k: int = 3, category: str = "") -> dict[str, Any]:
    """Search the nonprofit organization's indexed document library for verified facts and past outcomes.

    Use this tool to find specific historical data, past proposal narratives,
    IRS Form 990 financials, audited outcome metrics, and staff qualifications
    to incorporate into grant proposals and fit evaluations.

    Args:
        query: Specific search terms or question (e.g., 'past STEM student grade improvement outcomes', 'annual budget breakdown personnel costs').
        top_k: Number of relevant document passages to retrieve (default: 3).
        category: Optional category filter: 'past_proposal', 'irs_990', 'impact_report', 'bios', or leave empty for all.

    Returns:
        Dictionary containing matched document passages with relevance scores and source document names.
    """
    try:
        cat_filter = category if category else None
        results = knowledge_base.search(query=query, top_k=top_k, category=cat_filter)

        passages = []
        for r in results:
            passages.append({
                "source_document": r.doc_name,
                "category": r.category,
                "relevance_score": r.relevance_score,
                "excerpt": r.content,
            })

        logger.info(f"KnowledgeBase query '{query[:40]}...' returned {len(passages)} passages.")
        return {
            "query": query,
            "count": len(passages),
            "passages": passages,
            "error": None,
        }
    except Exception as e:
        logger.error(f"Error querying knowledge base: {e}")
        return {
            "query": query,
            "count": 0,
            "passages": [],
            "error": str(e),
        }
