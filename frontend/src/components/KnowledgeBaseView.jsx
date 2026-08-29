import React, { useState } from 'react';
import { Database, Search, FileText, CheckCircle, Sparkles, Layers, ArrowRight } from 'lucide-react';

export default function KnowledgeBaseView() {
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState(null);
  const [isSearching, setIsSearching] = useState(false);

  const indexedDocs = [
    {
      title: "IRS Form 990 (Filing Year 2024)",
      category: "irs_990",
      chunks: 14,
      embedding: "Titan Text Embeddings V2 (1024-dim)",
      facts: ["$450,000 Annual Operating Budget", "88.7% Direct Program Expenditure Ratio", "501(c)(3) Active Standing"]
    },
    {
      title: "2025 Annual Impact & Outcomes Report",
      category: "impact_report",
      chunks: 22,
      embedding: "Titan Text Embeddings V2 (1024-dim)",
      facts: ["1,200 Underrepresented Students Served", "85% Math & Science Grade Improvement", "94% Attendance Rate"]
    },
    {
      title: "NSF STEM Award #EDU-2023-4412 (Past Proposal)",
      category: "past_proposal",
      chunks: 18,
      embedding: "Titan Text Embeddings V2 (1024-dim)",
      facts: ["$25,000 NSF Award Closed with 100% Compliance", "Published Curriculum Framework", "4 Academic Partner Schools"]
    },
    {
      title: "Executive Director & Pedagogical Team Bios",
      category: "bios",
      chunks: 8,
      embedding: "Titan Text Embeddings V2 (1024-dim)",
      facts: ["Dr. Marcus Vance (PhD, Georgia Tech)", "14 Certified STEM Instructors", "5 Master Curriculum Designers"]
    }
  ];

  const handleSearch = (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    setTimeout(() => {
      setResults([
        {
          source: "2025 Annual Impact & Outcomes Report (Chunk 4)",
          relevance: 0.94,
          excerpt: "Across all participating Title I schools, 85% of enrolled students demonstrated measurable gains in core math standards, with 92% reporting increased enthusiasm for technical careers."
        },
        {
          source: "IRS Form 990 Filing 2024 (Chunk 2)",
          relevance: 0.88,
          excerpt: "Youth Education Alliance allocated $399,150 (88.7% of total revenue) directly toward educational programming and hardware kits, maintaining administrative overhead strictly under 11.3%."
        }
      ]);
      setIsSearching(false);
    }, 400);
  };

  return (
    <div>
      {/* Title Header */}
      <div style={{ marginBottom: '2rem' }}>
        <h2 className="font-heading" style={{ fontSize: '2.5rem', lineHeight: '1', color: 'var(--ink)' }}>
          RAG ORGANIZATIONAL KNOWLEDGE BASE
        </h2>
        <p style={{ color: 'var(--ink-muted)', fontSize: '0.95rem' }}>
          Vector-indexed organizational documentation empowering the Matcher and Drafter agents with verified organizational facts.
        </p>
      </div>

      {/* Semantic Search Box */}
      <div className="brutalist-card" style={{ padding: '1.25rem 1.5rem', marginBottom: '2rem' }}>
        <form onSubmit={handleSearch} className="search-form-container">
          <div style={{ position: 'relative', flex: 1 }}>
            <input
              type="text"
              placeholder="Test RAG retrieval (e.g., 'What was our past NSF grant amount?' or 'math improvement rate')..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                padding: '0.75rem 1rem 0.75rem 2.75rem',
                fontSize: '0.9rem',
                fontFamily: 'var(--font-body)',
                border: '2px solid var(--border-dark)',
                outline: 'none',
                background: '#FFFFFF'
              }}
            />
            <Search size={18} style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--ink-muted)' }} />
          </div>

          <button type="submit" className="brutalist-btn btn-primary" style={{ padding: '0.65rem 1.25rem' }}>
            {isSearching ? 'SEARCHING...' : 'QUERY VECTORS'}
          </button>
        </form>

        {/* Search Results Display */}
        {results && (
          <div style={{ marginTop: '1.5rem' }}>
            <div style={{ fontSize: '0.8rem', fontFamily: 'var(--font-mono)', fontWeight: 700, marginBottom: '0.75rem', color: 'var(--ink)' }}>
              TOP VECTOR RETRIEVAL MATCHES (HYBRID 0.7 COSINE / 0.3 LEXICAL):
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {results.map((r, idx) => (
                <div key={idx} style={{ background: 'var(--card-alt-bg)', border: '1px solid var(--border-dark)', padding: '1rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>{r.source}</span>
                    <span className="tag-badge tag-amber">{Math.round(r.relevance * 100)}% RELEVANCE</span>
                  </div>
                  <p style={{ fontSize: '0.88rem', color: 'var(--ink-muted)', fontStyle: 'italic' }}>
                    "{r.excerpt}"
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Grid of Indexed Knowledge Documents */}
      <h3 className="font-heading" style={{ fontSize: '1.75rem', marginBottom: '1.25rem' }}>
        INDEXED ORGANIZATIONAL CORPUS (4 DOCUMENTS)
      </h3>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem' }}>
        {indexedDocs.map((doc, idx) => (
          <div key={idx} className="brutalist-card" style={{ padding: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
              <span className="tag-badge tag-dark">{doc.category}</span>
              <span className="tag-badge tag-green">
                <CheckCircle size={12} /> INDEXED
              </span>
            </div>

            <h4 className="font-heading" style={{ fontSize: '1.4rem', lineHeight: '1.1', marginBottom: '0.5rem' }}>
              {doc.title}
            </h4>

            <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-muted)', marginBottom: '1rem' }}>
              {doc.chunks} PARAGRAPH CHUNKS • {doc.embedding}
            </div>

            <hr className="dashed-divider" />

            <div style={{ fontSize: '0.82rem', color: 'var(--ink)' }}>
              <div style={{ fontWeight: 700, marginBottom: '0.35rem', fontSize: '0.75rem', textTransform: 'uppercase' }}>
                Extracted Ground Truths:
              </div>
              <ul style={{ paddingLeft: '1.2rem', color: 'var(--ink-muted)', fontSize: '0.8rem', lineHeight: '1.5' }}>
                {doc.facts.map((f, fIdx) => (
                  <li key={fIdx}>{f}</li>
                ))}
              </ul>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
