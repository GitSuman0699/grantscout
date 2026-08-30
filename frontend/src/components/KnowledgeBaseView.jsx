import React, { useState, useEffect } from 'react';
import { Database, Search, FileText, CheckCircle, Sparkles, Layers, ArrowRight, AlertTriangle } from 'lucide-react';
import { fetchDocuments, searchDocuments } from '../services/api';

/**
 * Format raw document file name into human readable title.
 * e.g. "IRS_Form_990_Financial_Overview.md" -> "IRS Form 990 Financial Overview"
 */
function formatDocTitle(fileName) {
  if (!fileName) return 'Document';
  return fileName
    .replace(/\.md$/i, '')
    .replace(/_/g, ' ')
    .replace(/-/g, ' ');
}

/**
 * Format raw category into clean badge text.
 * e.g. "irs_990" -> "IRS 990", "past_proposal" -> "PAST PROPOSAL"
 */
function formatCategory(category) {
  if (!category) return 'DOCUMENT';
  return category.replace(/_/g, ' ').toUpperCase();
}

export default function KnowledgeBaseView() {
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [indexedDocs, setIndexedDocs] = useState([]);
  const [docsLoading, setDocsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch documents from backend on mount
  useEffect(() => {
    const loadDocs = async () => {
      setDocsLoading(true);
      try {
        const data = await fetchDocuments();
        setIndexedDocs(data.documents || []);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch documents from API:', err.message);
        setError(`Unable to connect to Knowledge Base API: ${err.message}`);
        setIndexedDocs([]);
      } finally {
        setDocsLoading(false);
      }
    };
    loadDocs();
  }, []);

  // Search via real backend API
  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    try {
      const data = await searchDocuments(searchQuery, 5);
      const mappedResults = (data.results || []).map(r => ({
        source: r.doc_name || 'Unknown Document',
        category: r.category || 'general',
        relevance: r.relevance_score || 0,
        excerpt: r.content || ''
      }));
      setResults(mappedResults.length > 0 ? mappedResults : [
        { source: 'No matches found', relevance: 0, excerpt: `No vector passages matched the query "${searchQuery}". Try rephrasing or using different keywords.` }
      ]);
    } catch (err) {
      console.error('Search failed:', err.message);
      setResults([
        { source: 'Search Error', relevance: 0, excerpt: `API error: ${err.message}. Make sure the backend is running on port 8000.` }
      ]);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div>
      {/* Title Header */}
      <div style={{ marginBottom: '2rem' }}>
        <h2 className="font-heading hero-title" style={{ fontSize: '2.5rem', lineHeight: '1', color: 'var(--ink)' }}>
          RAG ORGANIZATIONAL KNOWLEDGE BASE
        </h2>
        <p style={{ color: 'var(--ink-muted)', fontSize: '0.95rem', marginTop: '0.4rem', maxWidth: '750px' }}>
          Vector-indexed organizational documentation empowering the Matcher and Drafter agents with verified organizational facts.
        </p>
      </div>

      {/* Semantic Search Box */}
      <div className="brutalist-card" style={{ padding: '1.25rem 1.5rem', marginBottom: '2rem' }}>
        <form onSubmit={handleSearch} className="search-form-container">
          <div style={{ position: 'relative', flex: 1, minWidth: 0 }}>
            <input
              type="text"
              placeholder="Test RAG retrieval (e.g., 'What was our past NSF grant amount?' or 'math improvement rate')..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                boxSizing: 'border-box',
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

          <button type="submit" className="brutalist-btn btn-primary" style={{ padding: '0.65rem 1.25rem', whiteSpace: 'nowrap' }}>
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
                <div key={idx} style={{ background: 'var(--card-alt-bg)', border: '1px solid var(--border-dark)', padding: '1rem', minWidth: 0, overflow: 'hidden' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem', flexWrap: 'wrap', gap: '0.4rem' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.85rem', wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                      {formatDocTitle(r.source)}
                    </span>
                    {r.relevance > 0 && (
                      <span className="tag-badge tag-amber">{Math.round(r.relevance * 100)}% RELEVANCE</span>
                    )}
                  </div>
                  <p style={{ fontSize: '0.88rem', color: 'var(--ink-muted)', fontStyle: 'italic', wordBreak: 'break-word', overflowWrap: 'anywhere', lineHeight: '1.5' }}>
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
        INDEXED ORGANIZATIONAL CORPUS ({indexedDocs.length} DOCUMENTS)
      </h3>

      {docsLoading ? (
        <div className="brutalist-card" style={{ padding: '3rem', textAlign: 'center' }}>
          <div className="font-heading" style={{ fontSize: '1.5rem', color: 'var(--ink-muted)' }}>
            LOADING KNOWLEDGE BASE...
          </div>
          <p style={{ color: 'var(--ink-muted)', fontSize: '0.9rem', marginTop: '0.5rem' }}>
            Retrieving indexed document corpus from server
          </p>
        </div>
      ) : error ? (
        <div className="brutalist-card" style={{ padding: '2rem', textAlign: 'center' }}>
          <AlertTriangle size={32} color="var(--amber-signal)" style={{ marginBottom: '0.75rem' }} />
          <div className="font-heading" style={{ fontSize: '1.3rem', color: 'var(--ink)' }}>
            KNOWLEDGE BASE UNAVAILABLE
          </div>
          <p style={{ color: 'var(--ink-muted)', fontSize: '0.88rem', marginTop: '0.5rem' }}>
            {error}
          </p>
        </div>
      ) : indexedDocs.length === 0 ? (
        <div className="brutalist-card" style={{ padding: '3rem', textAlign: 'center' }}>
          <Database size={32} color="var(--ink-muted)" style={{ marginBottom: '0.75rem' }} />
          <div className="font-heading" style={{ fontSize: '1.5rem', color: 'var(--ink)' }}>
            NO DOCUMENTS INDEXED
          </div>
          <p style={{ color: 'var(--ink-muted)', fontSize: '0.9rem', marginTop: '0.5rem' }}>
            No documents have been indexed into the RAG Knowledge Base yet.
          </p>
        </div>
      ) : (
        <div className="knowledge-grid">
          {indexedDocs.map((doc, idx) => (
            <div key={idx} className="brutalist-card knowledge-card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div>
                {/* Badge Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <span className="tag-badge tag-dark" style={{ maxWidth: '100%', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {formatCategory(doc.category)}
                  </span>
                  <span className="tag-badge tag-green">
                    <CheckCircle size={12} /> INDEXED
                  </span>
                </div>

                {/* Formatted Title */}
                <h4 className="font-heading knowledge-card-title">
                  {formatDocTitle(doc.doc_name)}
                </h4>

                {/* File Reference */}
                <div className="knowledge-card-filename">
                  📄 {doc.doc_name}
                </div>
              </div>

              {/* Meta & Embedding Footer */}
              <div>
                <hr className="dashed-divider" style={{ margin: '0.75rem 0' }} />
                
                <div className="knowledge-card-meta">
                  {doc.chunk_count} {doc.chunk_count === 1 ? 'PARAGRAPH CHUNK' : 'PARAGRAPH CHUNKS'} • ~{doc.total_words} ESTIMATED TOKENS
                </div>

                <div style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-faint)', wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                  EMBEDDING: Titan Text Embeddings V2 (1024-dim)
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
