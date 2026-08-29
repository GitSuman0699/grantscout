"""GrantScout Evaluation Harness — Empirical benchmarking for agent accuracy.

Measures scoring precision, tool-calling correctness, routing decision accuracy,
and RAG retrieval relevance across a curated test corpus of grant opportunities
with known ground-truth labels.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.agents.matcher import evaluate_grant_structured
from backend.agents.drafter import draft_application_structured
from backend.tools.rag_search import query_knowledge_base
from backend.api.models.schemas import GrantEvaluationResult, GrantStatus

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
#  Ground-Truth Test Corpus
# ──────────────────────────────────────────────

EVAL_CORPUS = [
    {
        "test_id": "eval-001",
        "grant": {
            "id": 900001,
            "title": "Youth STEM Innovation Labs for Underserved Communities",
            "agency": "National Science Foundation",
            "synopsis": "Funding for 501(c)(3) nonprofits to deliver hands-on robotics, coding, and science workshops to low-income students ages 8-18 in urban settings.",
            "award_ceiling": 75000,
            "award_floor": 25000,
            "close_date": "2027-03-15",
            "applicant_types": "Nonprofits having a 501(c)(3) status",
            "category_of_funding": "Education",
        },
        "expected": {
            "min_total_score": 78,
            "expected_action": "auto_draft",
            "expected_status": "matched",
            "key_strength_keywords": ["STEM", "youth", "mission"],
        },
        "description": "Near-perfect match: same population, same mission, same agency as past NSF award.",
    },
    {
        "test_id": "eval-002",
        "grant": {
            "id": 900002,
            "title": "Agricultural Water Conservation Research Initiative",
            "agency": "USDA",
            "synopsis": "Multi-year research grant for universities and agricultural research institutions to develop precision irrigation systems for Midwest farmland.",
            "award_ceiling": 500000,
            "award_floor": 200000,
            "close_date": "2027-06-01",
            "applicant_types": "Public and State controlled institutions of higher education",
            "category_of_funding": "Natural Resources",
        },
        "expected": {
            "max_total_score": 35,
            "expected_action": "archive_silently",
            "expected_status": "archived",
            "key_strength_keywords": [],
        },
        "description": "Clear mismatch: agriculture research for universities, not youth STEM nonprofits.",
    },
    {
        "test_id": "eval-003",
        "grant": {
            "id": 900003,
            "title": "Community Digital Literacy and Workforce Readiness",
            "agency": "Department of Labor",
            "synopsis": "Grants for community-based organizations to provide computer literacy training and workforce development programs for disadvantaged populations.",
            "award_ceiling": 100000,
            "award_floor": 30000,
            "close_date": "2027-04-30",
            "applicant_types": "Nonprofits (other than institutions of higher education)",
            "category_of_funding": "Employment, Labor, and Training",
        },
        "expected": {
            "min_total_score": 50,
            "max_total_score": 79,
            "expected_action": "manual_review",
            "expected_status": "matched",
            "key_strength_keywords": ["digital", "workforce"],
        },
        "description": "Partial match: aligned on tech education for disadvantaged populations, but workforce focus differs from pure STEM.",
    },
    {
        "test_id": "eval-004",
        "grant": {
            "id": 900004,
            "title": "After-School Coding Academies for K-12 Students",
            "agency": "Department of Education",
            "synopsis": "Competitive grants to support after-school coding and computer science programs for elementary and secondary school students from Title I schools.",
            "award_ceiling": 50000,
            "award_floor": 15000,
            "close_date": "2027-02-28",
            "applicant_types": "Nonprofits having a 501(c)(3) status",
            "category_of_funding": "Education",
        },
        "expected": {
            "min_total_score": 80,
            "expected_action": "auto_draft",
            "expected_status": "matched",
            "key_strength_keywords": ["coding", "after-school", "K-12"],
        },
        "description": "Strong match: identical program model to YEA's existing after-school STEM workshops.",
    },
    {
        "test_id": "eval-005",
        "grant": {
            "id": 900005,
            "title": "National Defense Advanced Research in Quantum Computing",
            "agency": "DARPA",
            "synopsis": "Research contracts for defense-affiliated laboratories and cleared research institutions to advance quantum error correction methodologies.",
            "award_ceiling": 5000000,
            "award_floor": 1000000,
            "close_date": "2027-12-31",
            "applicant_types": "Others (Federally Funded Research and Development Centers)",
            "category_of_funding": "Science and Technology",
        },
        "expected": {
            "max_total_score": 20,
            "expected_action": "archive_silently",
            "expected_status": "archived",
            "key_strength_keywords": [],
        },
        "description": "Extreme mismatch: defense quantum computing labs, completely outside org capability and eligibility.",
    },
]


# ──────────────────────────────────────────────
#  Evaluation Result Models
# ──────────────────────────────────────────────


@dataclass
class TestCaseResult:
    """Result of evaluating a single test case."""

    test_id: str
    description: str
    passed: bool
    score_actual: int = 0
    score_expected_range: str = ""
    action_actual: str = ""
    action_expected: str = ""
    status_actual: str = ""
    status_expected: str = ""
    strength_keywords_found: list[str] = field(default_factory=list)
    latency_ms: float = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class EvalReport:
    """Aggregate evaluation report."""

    timestamp: str = ""
    total_cases: int = 0
    passed: int = 0
    failed: int = 0
    accuracy_pct: float = 0.0
    avg_latency_ms: float = 0.0
    score_precision_pct: float = 0.0
    routing_accuracy_pct: float = 0.0
    results: list[TestCaseResult] = field(default_factory=list)


# ──────────────────────────────────────────────
#  Evaluation Engine
# ──────────────────────────────────────────────


def evaluate_single_case(test_case: dict) -> TestCaseResult:
    """Run a single evaluation test case against the Matcher Agent."""
    test_id = test_case["test_id"]
    grant = test_case["grant"]
    expected = test_case["expected"]

    result = TestCaseResult(
        test_id=test_id,
        description=test_case["description"],
        passed=True,
    )

    start = time.perf_counter()
    try:
        evaluation: GrantEvaluationResult = evaluate_grant_structured(grant)
        result.latency_ms = (time.perf_counter() - start) * 1000

        actual_score = evaluation.match_score.total
        result.score_actual = actual_score
        result.action_actual = evaluation.recommended_action
        result.status_actual = evaluation.status.value

        # Check score within expected range
        min_score = expected.get("min_total_score", 0)
        max_score = expected.get("max_total_score", 100)
        result.score_expected_range = f"{min_score}-{max_score}"

        if actual_score < min_score or actual_score > max_score:
            result.passed = False
            result.errors.append(
                f"Score {actual_score} outside expected range [{min_score}, {max_score}]"
            )

        # Check routing action
        result.action_expected = expected["expected_action"]
        if evaluation.recommended_action != expected["expected_action"]:
            result.passed = False
            result.errors.append(
                f"Action '{evaluation.recommended_action}' != expected '{expected['expected_action']}'"
            )

        # Check status
        result.status_expected = expected["expected_status"]
        if evaluation.status.value != expected["expected_status"]:
            result.passed = False
            result.errors.append(
                f"Status '{evaluation.status.value}' != expected '{expected['expected_status']}'"
            )

        # Check strength keywords
        if expected.get("key_strength_keywords"):
            all_strengths = " ".join(evaluation.key_strengths).lower()
            for kw in expected["key_strength_keywords"]:
                if kw.lower() in all_strengths:
                    result.strength_keywords_found.append(kw)

    except Exception as e:
        result.latency_ms = (time.perf_counter() - start) * 1000
        result.passed = False
        result.errors.append(f"Exception: {str(e)}")

    return result


def evaluate_rag_retrieval() -> dict[str, Any]:
    """Evaluate RAG retrieval precision on known organizational facts."""
    rag_tests = [
        {
            "query": "What percentage of students improved math grades?",
            "expected_fact": "85%",
            "category": None,
        },
        {
            "query": "annual operating budget and program expenditure ratio",
            "expected_fact": "88.7%",
            "category": "irs_990",
        },
        {
            "query": "NSF past grant award amount robotics",
            "expected_fact": "25,000",
            "category": "past_proposal",
        },
        {
            "query": "executive director qualifications PhD",
            "expected_fact": "Georgia Institute of Technology",
            "category": "bios",
        },
    ]

    results = []
    hits = 0
    for test in rag_tests:
        res = query_knowledge_base(
            query=test["query"],
            top_k=2,
            category=test.get("category") or "",
        )
        passages = res.get("passages", [])
        found = any(test["expected_fact"] in p.get("excerpt", "") for p in passages)
        if found:
            hits += 1
        results.append({
            "query": test["query"],
            "expected_fact": test["expected_fact"],
            "found": found,
            "top_score": passages[0]["relevance_score"] if passages else 0,
        })

    return {
        "total": len(rag_tests),
        "hits": hits,
        "precision_pct": round((hits / len(rag_tests)) * 100, 1),
        "results": results,
    }


def evaluate_drafter_completeness() -> dict[str, Any]:
    """Evaluate Drafter Agent for section completeness and structure adherence."""
    test_grant = {
        "grant_id": "eval-draft-001",
        "title": "Youth Coding Academy Expansion",
        "agency": "Department of Education",
        "synopsis": "Funding after-school coding programs for underserved K-12 students.",
        "award_ceiling": 60000,
        "award_floor": 20000,
        "close_date": "2027-05-01",
    }

    start = time.perf_counter()
    try:
        draft = draft_application_structured(test_grant)
        latency = (time.perf_counter() - start) * 1000

        section_titles = [s.title for s in draft.sections]
        has_executive = any("Executive" in t for t in section_titles)
        has_budget = any("Budget" in t for t in section_titles)
        has_evaluation = any("Evaluation" in t or "Sustainability" in t for t in section_titles)
        total_words = sum(s.word_count for s in draft.sections)

        return {
            "passed": len(draft.sections) >= 6 and has_executive and has_budget,
            "sections_count": len(draft.sections),
            "has_executive_summary": has_executive,
            "has_budget": has_budget,
            "has_evaluation": has_evaluation,
            "total_words": total_words,
            "completion_pct": draft.completion_percentage,
            "human_actions": len(draft.recommended_human_actions),
            "latency_ms": round(latency, 1),
        }
    except Exception as e:
        return {"passed": False, "error": str(e)}


def run_full_evaluation() -> EvalReport:
    """Run the complete evaluation harness and produce an aggregate report."""
    report = EvalReport(timestamp=datetime.utcnow().isoformat())

    # 1. Matcher scoring evaluation
    case_results = []
    for test_case in EVAL_CORPUS:
        result = evaluate_single_case(test_case)
        case_results.append(result)

    report.results = case_results
    report.total_cases = len(case_results)
    report.passed = sum(1 for r in case_results if r.passed)
    report.failed = report.total_cases - report.passed
    report.accuracy_pct = round((report.passed / report.total_cases) * 100, 1) if report.total_cases else 0

    latencies = [r.latency_ms for r in case_results if r.latency_ms > 0]
    report.avg_latency_ms = round(sum(latencies) / len(latencies), 1) if latencies else 0

    # Score precision: cases where score fell in expected range
    score_correct = sum(1 for r in case_results if not any("Score" in e for e in r.errors))
    report.score_precision_pct = round((score_correct / report.total_cases) * 100, 1) if report.total_cases else 0

    # Routing accuracy: cases where action matched expected
    route_correct = sum(1 for r in case_results if r.action_actual == r.action_expected)
    report.routing_accuracy_pct = round((route_correct / report.total_cases) * 100, 1) if report.total_cases else 0

    return report


def print_report(report: EvalReport, rag_results: dict, drafter_results: dict):
    """Pretty-print the evaluation report to stdout."""
    print("\n" + "=" * 70)
    print("  GRANTSCOUT EVALUATION HARNESS — BENCHMARK REPORT")
    print("=" * 70)
    print(f"  Timestamp: {report.timestamp}")
    print(f"  Test Cases: {report.total_cases}")
    print()

    print("─── MATCHER AGENT SCORING ───")
    print(f"  Overall Accuracy:     {report.accuracy_pct}% ({report.passed}/{report.total_cases} passed)")
    print(f"  Score Precision:      {report.score_precision_pct}%")
    print(f"  Routing Accuracy:     {report.routing_accuracy_pct}%")
    print(f"  Avg Latency:          {report.avg_latency_ms:.0f}ms")
    print()

    for r in report.results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        print(f"  [{r.test_id}] {status}  Score: {r.score_actual}/100 (expected: {r.score_expected_range})")
        print(f"           Action: {r.action_actual} (expected: {r.action_expected})")
        if r.errors:
            for e in r.errors:
                print(f"           ⚠ {e}")
    print()

    print("─── RAG RETRIEVAL PRECISION ───")
    print(f"  Precision:  {rag_results['precision_pct']}% ({rag_results['hits']}/{rag_results['total']})")
    for rr in rag_results["results"]:
        icon = "✅" if rr["found"] else "❌"
        print(f"  {icon} Query: '{rr['query'][:50]}...' → Expected '{rr['expected_fact']}' (score: {rr['top_score']})")
    print()

    print("─── DRAFTER AGENT COMPLETENESS ───")
    if drafter_results.get("passed"):
        print(f"  ✅ PASS — {drafter_results['sections_count']} sections, {drafter_results['total_words']} words")
        print(f"     Completion: {drafter_results['completion_pct']}%  |  Human Actions: {drafter_results['human_actions']}")
        print(f"     Latency: {drafter_results['latency_ms']:.0f}ms")
    else:
        print(f"  ❌ FAIL — {drafter_results.get('error', 'Incomplete sections')}")

    print()
    print("=" * 70)

    # Overall verdict
    all_pass = (
        report.accuracy_pct == 100.0
        and rag_results["precision_pct"] == 100.0
        and drafter_results.get("passed", False)
    )
    verdict = "🏆 ALL BENCHMARKS PASSED" if all_pass else "⚠️  SOME BENCHMARKS NEED ATTENTION"
    print(f"  VERDICT: {verdict}")
    print("=" * 70 + "\n")


def main():
    """Run the complete evaluation harness."""
    print("\n🧪 Running GrantScout Evaluation Harness...\n")

    report = run_full_evaluation()
    rag_results = evaluate_rag_retrieval()
    drafter_results = evaluate_drafter_completeness()

    print_report(report, rag_results, drafter_results)

    # Save report as JSON artifact
    output_dir = Path(__file__).parent.parent / "data" / "evals"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"eval_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

    report_data = {
        "timestamp": report.timestamp,
        "matcher": {
            "total_cases": report.total_cases,
            "passed": report.passed,
            "failed": report.failed,
            "accuracy_pct": report.accuracy_pct,
            "score_precision_pct": report.score_precision_pct,
            "routing_accuracy_pct": report.routing_accuracy_pct,
            "avg_latency_ms": report.avg_latency_ms,
        },
        "rag": rag_results,
        "drafter": drafter_results,
    }
    report_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
    print(f"📄 Report saved to: {report_path}\n")


if __name__ == "__main__":
    main()
