"""GrantScout RAG (Retrieval-Augmented Generation) Knowledge Base.

Enables agents to index and search nonprofit organizational documents
(e.g., past winning grant proposals, IRS Form 990 filings, annual impact reports,
and staff bios). Supports Amazon Bedrock Titan Text Embeddings with semantic
vector fallback for offline/development environments.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import boto3
from pydantic import BaseModel, Field

from backend.config import config

logger = logging.getLogger(__name__)


class DocumentChunk(BaseModel):
    """A searchable chunk of an organizational document."""

    chunk_id: str
    doc_name: str
    category: str = "general"
    content: str
    token_estimate: int = 0
    embedding: list[float] = Field(default_factory=list)


class SearchResult(BaseModel):
    """A scored search result returned from the knowledge base."""

    doc_name: str
    category: str
    content: str
    relevance_score: float


class KnowledgeBase:
    """Vector knowledge base for nonprofit organizational context."""

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = Path(storage_dir or (Path(config.LOCAL_STORAGE_PATH) / "knowledge_base"))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.storage_dir / "vector_index.json"
        self.chunks: list[DocumentChunk] = []
        self._load_index()

    def _load_index(self) -> None:
        """Load persisted index from disk."""
        if self.index_file.exists():
            try:
                data = json.loads(self.index_file.read_text(encoding="utf-8"))
                self.chunks = [DocumentChunk(**item) for item in data]
                logger.info(f"Loaded {len(self.chunks)} document chunks into KnowledgeBase.")
            except Exception as e:
                logger.warning(f"Failed to load knowledge base index: {e}")
                self.chunks = []

    def _save_index(self) -> None:
        """Persist index to disk."""
        try:
            data = [chunk.model_dump() for chunk in self.chunks]
            self.index_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save knowledge base index: {e}")

    def _chunk_text(self, text: str, chunk_size: int = 600, overlap: int = 80) -> list[str]:
        """Split document text into overlapping paragraph chunks."""
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        chunks = []
        current_chunk = []
        current_len = 0

        for p in paragraphs:
            p_words = len(p.split())
            if current_len + p_words > chunk_size and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                # retain last paragraph for overlap
                current_chunk = [current_chunk[-1], p] if len(current_chunk) > 1 else [p]
                current_len = sum(len(x.split()) for x in current_chunk)
            else:
                current_chunk.append(p)
                current_len += p_words

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks if chunks else [text]

    def _compute_embedding(self, text: str) -> list[float]:
        """Generate embedding vector using Bedrock Titan or local semantic hashing."""
        try:
            # Try Amazon Bedrock Titan Text Embeddings
            bedrock = boto3.client("bedrock-runtime", region_name=config.AWS_REGION)
            body = json.dumps({"inputText": text[:2000]})
            response = bedrock.invoke_model(
                modelId="amazon.titan-embed-text-v2:0",
                contentType="application/json",
                accept="application/json",
                body=body,
            )
            result = json.loads(response["body"].read())
            return result.get("embedding", [])
        except Exception:
            # Offline semantic frequency hashing (dense 64-dimensional bag of words)
            return self._compute_local_embedding(text)

    def _compute_local_embedding(self, text: str, dim: int = 64) -> list[float]:
        """Deterministic, normalized term-frequency hashing vector for offline dev."""
        words = re.findall(r"\w+", text.lower())
        if not words:
            return [0.0] * dim

        vec = [0.0] * dim
        for w in words:
            # Hash word into one of the buckets
            h = hash(w) % dim
            vec[h] += 1.0

        # L2 Normalize
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    def _cosine_similarity(self, vec_a: list[float], vec_b: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def add_document(self, doc_name: str, text: str, category: str = "general") -> int:
        """Ingest, chunk, embed, and index a document.

        Args:
            doc_name: Filename or title of the document.
            text: Full text content of the document.
            category: Category e.g. 'past_proposal', 'irs_990', 'impact_report', 'bios'.

        Returns:
            Number of chunks indexed.
        """
        # Remove existing chunks for this document if re-indexing
        self.chunks = [c for c in self.chunks if c.doc_name != doc_name]

        text_chunks = self._chunk_text(text)
        new_chunks = []

        for i, chunk_text in enumerate(text_chunks):
            embedding = self._compute_embedding(chunk_text)
            chunk = DocumentChunk(
                chunk_id=f"{doc_name}-chunk-{i+1}",
                doc_name=doc_name,
                category=category,
                content=chunk_text,
                token_estimate=len(chunk_text.split()),
                embedding=embedding,
            )
            new_chunks.append(chunk)

        self.chunks.extend(new_chunks)
        self._save_index()
        logger.info(f"Indexed document '{doc_name}' into {len(new_chunks)} chunks (category: {category}).")
        return len(new_chunks)

    def search(self, query: str, top_k: int = 3, category: Optional[str] = None) -> list[SearchResult]:
        """Perform semantic similarity search against indexed document chunks.

        Args:
            query: Natural language query (e.g., 'math improvement outcomes 2025').
            top_k: Maximum number of relevant chunks to return.
            category: Optional category filter.

        Returns:
            List of SearchResult objects sorted by descending relevance.
        """
        if not self.chunks:
            return []

        query_vec = self._compute_embedding(query)
        scored_results: list[tuple[float, DocumentChunk]] = []

        for chunk in self.chunks:
            if category and chunk.category != category:
                continue

            score = self._cosine_similarity(query_vec, chunk.embedding)

            # Keyword lexical bonus for exact term matches
            query_terms = set(re.findall(r"\w+", query.lower()))
            chunk_terms = set(re.findall(r"\w+", chunk.content.lower()))
            common = query_terms.intersection(chunk_terms)
            if query_terms:
                lexical_ratio = len(common) / len(query_terms)
                score = (score * 0.7) + (lexical_ratio * 0.3)

            scored_results.append((score, chunk))

        # Sort descending by relevance score
        scored_results.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, chunk in scored_results[:top_k]:
            results.append(
                SearchResult(
                    doc_name=chunk.doc_name,
                    category=chunk.category,
                    content=chunk.content,
                    relevance_score=round(score, 4),
                )
            )

        return results

    def list_documents(self) -> list[dict[str, Any]]:
        """List all indexed documents with chunk and word counts."""
        doc_stats: dict[str, dict[str, Any]] = {}
        for c in self.chunks:
            if c.doc_name not in doc_stats:
                doc_stats[c.doc_name] = {
                    "doc_name": c.doc_name,
                    "category": c.category,
                    "chunk_count": 0,
                    "total_words": 0,
                }
            doc_stats[c.doc_name]["chunk_count"] += 1
            doc_stats[c.doc_name]["total_words"] += c.token_estimate

        return list(doc_stats.values())


# Global singleton instance
knowledge_base = KnowledgeBase()
