"""Test suite for RAG Knowledge Base and Vector Semantic Retrieval."""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.rag.knowledge_base import knowledge_base
from backend.tools.rag_search import query_knowledge_base


class TestRAGKnowledgeBase(unittest.TestCase):
    """Test suite for document ingestion, chunking, and vector semantic search."""

    @classmethod
    def setUpClass(cls):
        # Ingest a dedicated test document
        cls.test_doc_name = "STEM_Evaluation_Metrics_2025.md"
        cls.test_content = """# 2025 STEM Academic Benchmarks

## Math and Science Outcomes
Across our 4 partner community hubs in Atlanta, 85% of regular youth participants achieved at least one full letter grade improvement in math.
Furthermore, 92% of students surveyed reported increased enthusiasm for computer science and robotics careers.

## Financial Efficiency
Youth Education Alliance maintained an 88.7% program expenditure efficiency ratio, spending only 7.8% on administrative overhead.
"""
        knowledge_base.add_document(cls.test_doc_name, cls.test_content, category="test_metrics")

    def test_01_document_indexing(self):
        """Verify document is parsed into chunks and appears in document catalog."""
        docs = knowledge_base.list_documents()
        doc_names = [d["doc_name"] for d in docs]
        self.assertIn(self.test_doc_name, doc_names)

    def test_02_semantic_search_retrieves_math_outcomes(self):
        """Verify semantic query for math improvements retrieves the relevant excerpt."""
        results = knowledge_base.search("math grade improvement percentage", top_k=2)
        self.assertTrue(len(results) > 0)
        top_match = results[0]
        self.assertIn("85%", top_match.content)
        self.assertTrue(top_match.relevance_score > 0.3)

    def test_03_semantic_search_category_filtering(self):
        """Verify category filter isolates results to the designated document category."""
        results = knowledge_base.search("administrative overhead", top_k=3, category="test_metrics")
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0].category, "test_metrics")
        self.assertIn("7.8%", results[0].content)

    def test_04_strands_tool_query_knowledge_base(self):
        """Verify Strands @tool query_knowledge_base executes cleanly and returns passage dictionaries."""
        res = query_knowledge_base(query="What percentage of students improved math grades?", top_k=2)
        self.assertIsNone(res.get("error"))
        self.assertTrue(res.get("count", 0) > 0)
        self.assertTrue(any("85%" in p["excerpt"] for p in res["passages"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
