"""GrantScout Cost & Token Optimization Engine.

Provides tiered multi-provider model routing, response caching,
prompt compression, and token usage tracking to minimize inference
costs while maintaining output quality.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel

from backend.config import config

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
#  Model Tier Definitions
# ──────────────────────────────────────────────


class ModelTier(str, Enum):
    """Agent task complexity tiers mapped to cost-appropriate models."""

    FAST = "fast"        # Simple classification, keyword extraction, formatting
    STANDARD = "standard"  # Scoring, analysis, moderate reasoning
    PREMIUM = "premium"   # Complex drafting, multi-section generation, nuanced evaluation


@dataclass
class ModelConfig:
    """Configuration for a model tier."""

    tier: ModelTier
    model_id: str
    region: str
    cost_per_1k_input: float   # USD per 1K input tokens
    cost_per_1k_output: float  # USD per 1K output tokens
    max_tokens: int = 4096
    description: str = ""


# Default tiered routing configuration
MODEL_TIERS: dict[ModelTier, ModelConfig] = {
    ModelTier.FAST: ModelConfig(
        tier=ModelTier.FAST,
        model_id="us.anthropic.claude-haiku-4-20250514-v1:0",
        region=config.AWS_REGION,
        cost_per_1k_input=0.0008,
        cost_per_1k_output=0.004,
        max_tokens=2048,
        description="Fast classification, keyword extraction, deduplication checks",
    ),
    ModelTier.STANDARD: ModelConfig(
        tier=ModelTier.STANDARD,
        model_id=config.BEDROCK_MODEL_ID,  # Claude Sonnet 4
        region=config.AWS_REGION,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        max_tokens=4096,
        description="Grant scoring, fit evaluation, structured analysis",
    ),
    ModelTier.PREMIUM: ModelConfig(
        tier=ModelTier.PREMIUM,
        model_id=config.BEDROCK_MODEL_ID,  # Claude Sonnet 4 (or Opus for premium)
        region=config.AWS_REGION,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        max_tokens=8192,
        description="Multi-section proposal drafting, complex narrative generation",
    ),
}

# Agent-to-tier mapping
AGENT_TIER_MAP: dict[str, ModelTier] = {
    "scanner": ModelTier.FAST,
    "matcher": ModelTier.STANDARD,
    "drafter": ModelTier.PREMIUM,
    "deadline": ModelTier.FAST,
    "orchestrator": ModelTier.STANDARD,
}


def get_model_for_agent(agent_name: str) -> ModelConfig:
    """Get the cost-optimized model configuration for a specific agent.

    Args:
        agent_name: Name of the agent ('scanner', 'matcher', 'drafter', etc.).

    Returns:
        ModelConfig with the appropriate model tier.
    """
    tier = AGENT_TIER_MAP.get(agent_name, ModelTier.STANDARD)
    return MODEL_TIERS[tier]


# ──────────────────────────────────────────────
#  Response Cache (LRU with TTL)
# ──────────────────────────────────────────────


class ResponseCache:
    """LRU cache with time-to-live for agent responses.

    Caches deterministic tool outputs (e.g., org profiles, grant details)
    to avoid redundant LLM invocations for repeated queries.
    """

    def __init__(self, max_size: int = 256, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def _make_key(self, namespace: str, query: str) -> str:
        """Generate a deterministic cache key."""
        raw = f"{namespace}:{query}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(self, namespace: str, query: str) -> Optional[Any]:
        """Retrieve a cached response if it exists and is not expired."""
        key = self._make_key(namespace, query)
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                self._hits += 1
                # Move to end (most recently used)
                self._cache.move_to_end(key)
                return value
            else:
                # Expired — remove
                del self._cache[key]
        self._misses += 1
        return None

    def set(self, namespace: str, query: str, value: Any) -> None:
        """Store a response in the cache."""
        key = self._make_key(namespace, query)
        self._cache[key] = (value, time.time())
        self._cache.move_to_end(key)
        # Evict oldest if over capacity
        while len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

    def invalidate(self, namespace: str, query: str) -> None:
        """Remove a specific entry from the cache."""
        key = self._make_key(namespace, query)
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    @property
    def stats(self) -> dict[str, Any]:
        """Return cache performance statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_pct": round(hit_rate, 1),
            "ttl_seconds": self.ttl_seconds,
        }


# Global cache singleton
response_cache = ResponseCache(max_size=256, ttl_seconds=3600)


# ──────────────────────────────────────────────
#  Token Usage Tracker
# ──────────────────────────────────────────────


@dataclass
class TokenUsageEntry:
    """A single token usage log entry."""

    agent: str
    tier: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    timestamp: str
    cached: bool = False


class TokenTracker:
    """Tracks token usage and estimated costs across all agent invocations."""

    def __init__(self):
        self._entries: list[TokenUsageEntry] = []
        self._session_start = datetime.utcnow().isoformat()

    def log_usage(
        self,
        agent: str,
        input_tokens: int,
        output_tokens: int,
        cached: bool = False,
    ) -> TokenUsageEntry:
        """Log a token usage event and compute estimated cost.

        Args:
            agent: Agent name ('scanner', 'matcher', etc.).
            input_tokens: Number of input tokens consumed.
            output_tokens: Number of output tokens generated.
            cached: Whether the response was served from cache.

        Returns:
            The logged TokenUsageEntry.
        """
        model_config = get_model_for_agent(agent)

        if cached:
            cost = 0.0
        else:
            cost = (
                (input_tokens / 1000) * model_config.cost_per_1k_input
                + (output_tokens / 1000) * model_config.cost_per_1k_output
            )

        entry = TokenUsageEntry(
            agent=agent,
            tier=model_config.tier.value,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=round(cost, 6),
            timestamp=datetime.utcnow().isoformat(),
            cached=cached,
        )
        self._entries.append(entry)
        return entry

    @property
    def summary(self) -> dict[str, Any]:
        """Generate a summary of token usage and costs."""
        total_input = sum(e.input_tokens for e in self._entries)
        total_output = sum(e.output_tokens for e in self._entries)
        total_cost = sum(e.estimated_cost_usd for e in self._entries)
        cached_count = sum(1 for e in self._entries if e.cached)

        per_agent: dict[str, dict[str, Any]] = {}
        for e in self._entries:
            if e.agent not in per_agent:
                per_agent[e.agent] = {
                    "invocations": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                    "cached": 0,
                    "tier": e.tier,
                }
            per_agent[e.agent]["invocations"] += 1
            per_agent[e.agent]["input_tokens"] += e.input_tokens
            per_agent[e.agent]["output_tokens"] += e.output_tokens
            per_agent[e.agent]["cost_usd"] = round(
                per_agent[e.agent]["cost_usd"] + e.estimated_cost_usd, 6
            )
            if e.cached:
                per_agent[e.agent]["cached"] += 1

        return {
            "session_start": self._session_start,
            "total_invocations": len(self._entries),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "total_estimated_cost_usd": round(total_cost, 6),
            "cache_hits": cached_count,
            "savings_from_cache_pct": round(
                (cached_count / len(self._entries) * 100) if self._entries else 0, 1
            ),
            "per_agent": per_agent,
        }

    def reset(self) -> None:
        """Reset the tracker for a new session."""
        self._entries.clear()
        self._session_start = datetime.utcnow().isoformat()


# Global tracker singleton
token_tracker = TokenTracker()


# ──────────────────────────────────────────────
#  Prompt Compression Utilities
# ──────────────────────────────────────────────


def compress_grant_synopsis(synopsis: str, max_words: int = 150) -> str:
    """Compress a grant synopsis to reduce token consumption.

    Strips boilerplate phrases and truncates to essential content.

    Args:
        synopsis: Raw grant synopsis text.
        max_words: Maximum word count for the compressed version.

    Returns:
        Compressed synopsis string.
    """
    if not synopsis:
        return ""

    # Remove common boilerplate phrases
    boilerplate = [
        "The purpose of this funding opportunity announcement is to",
        "This notice invites applications for",
        "The Department of",
        "DEPARTMENT OF HEALTH AND HUMAN SERVICES",
        "NOTE:",
        "See the full announcement for",
    ]
    compressed = synopsis
    for bp in boilerplate:
        compressed = compressed.replace(bp, "")

    # Truncate to max_words
    words = compressed.split()
    if len(words) > max_words:
        compressed = " ".join(words[:max_words]) + "..."

    return compressed.strip()


def estimate_tokens(text: str) -> int:
    """Estimate token count for a string (rough approximation: ~4 chars per token).

    Args:
        text: Input text string.

    Returns:
        Estimated token count.
    """
    return max(1, len(text) // 4)
