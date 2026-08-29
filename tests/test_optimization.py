"""Test suite for Cost & Token Optimization engine and Evaluation Harness."""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.optimization import (
    ModelTier,
    ResponseCache,
    TokenTracker,
    get_model_for_agent,
    MODEL_TIERS,
    AGENT_TIER_MAP,
    compress_grant_synopsis,
    estimate_tokens,
    response_cache,
    token_tracker,
)
from tests.eval_harness import (
    run_full_evaluation,
    evaluate_rag_retrieval,
    evaluate_drafter_completeness,
    EVAL_CORPUS,
)


class TestModelTierRouting(unittest.TestCase):
    """Test tiered model routing for cost optimization."""

    def test_01_scanner_routes_to_fast_tier(self):
        """Scanner Agent should use the cheapest (FAST) model."""
        cfg = get_model_for_agent("scanner")
        self.assertEqual(cfg.tier, ModelTier.FAST)
        self.assertTrue(cfg.cost_per_1k_input < 0.002)

    def test_02_matcher_routes_to_standard_tier(self):
        """Matcher Agent should use the STANDARD model for scoring."""
        cfg = get_model_for_agent("matcher")
        self.assertEqual(cfg.tier, ModelTier.STANDARD)

    def test_03_drafter_routes_to_premium_tier(self):
        """Drafter Agent should use the PREMIUM model for complex generation."""
        cfg = get_model_for_agent("drafter")
        self.assertEqual(cfg.tier, ModelTier.PREMIUM)

    def test_04_deadline_routes_to_fast_tier(self):
        """Deadline Agent (simple scheduling) should use FAST tier."""
        cfg = get_model_for_agent("deadline")
        self.assertEqual(cfg.tier, ModelTier.FAST)

    def test_05_unknown_agent_defaults_to_standard(self):
        """Unknown agent names should default to STANDARD tier."""
        cfg = get_model_for_agent("unknown_agent")
        self.assertEqual(cfg.tier, ModelTier.STANDARD)


class TestResponseCache(unittest.TestCase):
    """Test LRU response cache with TTL."""

    def setUp(self):
        self.cache = ResponseCache(max_size=3, ttl_seconds=60)

    def test_01_cache_miss_returns_none(self):
        """Cache miss should return None."""
        result = self.cache.get("ns", "nonexistent")
        self.assertIsNone(result)

    def test_02_cache_set_and_get(self):
        """Set then get should return cached value."""
        self.cache.set("grants", "stem education", {"count": 5})
        result = self.cache.get("grants", "stem education")
        self.assertEqual(result, {"count": 5})

    def test_03_cache_eviction_on_overflow(self):
        """Oldest entries should be evicted when cache exceeds max_size."""
        self.cache.set("ns", "key1", "v1")
        self.cache.set("ns", "key2", "v2")
        self.cache.set("ns", "key3", "v3")
        self.cache.set("ns", "key4", "v4")  # Should evict key1
        self.assertIsNone(self.cache.get("ns", "key1"))
        self.assertEqual(self.cache.get("ns", "key4"), "v4")

    def test_04_cache_stats(self):
        """Stats should report hits, misses, and hit rate."""
        self.cache.set("ns", "k", "v")
        self.cache.get("ns", "k")  # hit
        self.cache.get("ns", "missing")  # miss
        stats = self.cache.stats
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["hit_rate_pct"], 50.0)

    def test_05_cache_invalidation(self):
        """Explicit invalidation should remove the entry."""
        self.cache.set("ns", "k", "v")
        self.cache.invalidate("ns", "k")
        self.assertIsNone(self.cache.get("ns", "k"))


class TestTokenTracker(unittest.TestCase):
    """Test token usage tracking and cost estimation."""

    def setUp(self):
        self.tracker = TokenTracker()

    def test_01_log_usage_entry(self):
        """Logging usage should record the entry with estimated cost."""
        entry = self.tracker.log_usage("scanner", input_tokens=500, output_tokens=200)
        self.assertEqual(entry.agent, "scanner")
        self.assertEqual(entry.tier, "fast")
        self.assertTrue(entry.estimated_cost_usd > 0)

    def test_02_cached_entry_zero_cost(self):
        """Cached responses should have zero cost."""
        entry = self.tracker.log_usage("matcher", input_tokens=1000, output_tokens=500, cached=True)
        self.assertEqual(entry.estimated_cost_usd, 0.0)
        self.assertTrue(entry.cached)

    def test_03_summary_aggregation(self):
        """Summary should aggregate across all agents."""
        self.tracker.log_usage("scanner", 100, 50)
        self.tracker.log_usage("matcher", 500, 300)
        self.tracker.log_usage("drafter", 1000, 800)
        summary = self.tracker.summary
        self.assertEqual(summary["total_invocations"], 3)
        self.assertTrue(summary["total_tokens"] > 0)
        self.assertEqual(len(summary["per_agent"]), 3)

    def test_04_reset_clears_all(self):
        """Reset should clear all entries."""
        self.tracker.log_usage("scanner", 100, 50)
        self.tracker.reset()
        self.assertEqual(self.tracker.summary["total_invocations"], 0)


class TestPromptCompression(unittest.TestCase):
    """Test prompt compression utilities."""

    def test_01_compress_synopsis(self):
        """Long synopsis should be truncated to max_words."""
        long_text = " ".join(["word"] * 500)
        compressed = compress_grant_synopsis(long_text, max_words=100)
        self.assertTrue(len(compressed.split()) <= 101)  # 100 + "..."

    def test_02_boilerplate_removal(self):
        """Common boilerplate phrases should be stripped."""
        text = "The purpose of this funding opportunity announcement is to support STEM education."
        compressed = compress_grant_synopsis(text)
        self.assertNotIn("The purpose of this funding opportunity announcement is to", compressed)
        self.assertIn("STEM education", compressed)

    def test_03_token_estimation(self):
        """Token estimation should approximate ~4 chars per token."""
        text = "Hello world, this is a test."
        tokens = estimate_tokens(text)
        self.assertTrue(5 <= tokens <= 10)


class TestEvalHarness(unittest.TestCase):
    """Test the evaluation harness produces valid results."""

    def test_01_eval_corpus_has_minimum_cases(self):
        """Eval corpus should contain at least 5 ground-truth test cases."""
        self.assertTrue(len(EVAL_CORPUS) >= 5)

    def test_02_matcher_evaluation_runs_all_cases(self):
        """Matcher evaluation should produce results for all test cases."""
        report = run_full_evaluation()
        self.assertEqual(report.total_cases, len(EVAL_CORPUS))
        self.assertTrue(report.accuracy_pct >= 0)

    def test_03_rag_retrieval_precision(self):
        """RAG retrieval should find all expected organizational facts."""
        results = evaluate_rag_retrieval()
        self.assertEqual(results["total"], 4)
        self.assertTrue(results["precision_pct"] >= 75.0)

    def test_04_drafter_completeness(self):
        """Drafter should produce 6 complete sections."""
        results = evaluate_drafter_completeness()
        self.assertTrue(results["passed"])
        self.assertEqual(results["sections_count"], 6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
