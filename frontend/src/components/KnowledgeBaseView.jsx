import React, { useState, useEffect } from 'react';
import {
  Database,
  Search,
  FileText,
  CheckCircle,
  Sparkles,
  Layers,
  ArrowRight,
  AlertTriangle,
  Upload,
  Edit3,
  Trash2,
  Eye,
  X,
  Plus,
  RefreshCw,
  FileUp,
  Save,
  Check,
  Filter
} from 'lucide-react';
import {
  fetchDocuments,
  searchDocuments,
  fetchDocumentByName,
  indexDocument,
  deleteDocument,
} from '../services/api';

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

const CATEGORY_OPTIONS = [
  { value: 'impact_report', label: 'Impact Report' },
  { value: 'irs_990', label: 'IRS 990 Financials' },
  { value: 'past_proposal', label: 'Past Grant Proposal' },
  { value: 'strategic_plan', label: 'Strategic Plan' },
  { value: 'staff_bios', label: 'Staff Bios & Governance' },
  { value: 'program_outcomes', label: 'Program Outcomes' },
  { value: 'general', label: 'General Documentation' },
];

export default function KnowledgeBaseView() {
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [indexedDocs, setIndexedDocs] = useState([]);
  const [docsLoading, setDocsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedCategoryFilter, setSelectedCategoryFilter] = useState('all');

  // Flash notification state
  const [notification, setNotification] = useState(null);

  // Upload Modal State
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [uploadMode, setUploadMode] = useState('file'); // 'file' or 'paste'
  const [uploadForm, setUploadForm] = useState({
    doc_name: '',
    category: 'general',
    content: '',
  });
  const [isIndexing, setIsIndexing] = useState(false);
  const [uploadError, setUploadError] = useState(null);

  // Inspect / Edit Modal State
  const [isInspectOpen, setIsInspectOpen] = useState(false);
  const [inspectDocName, setInspectDocName] = useState(null);
  const [inspectedDoc, setInspectedDoc] = useState(null);
  const [inspectLoading, setInspectLoading] = useState(false);
  const [inspectError, setInspectError] = useState(null);
  const [isEditMode, setIsEditMode] = useState(false);
  const [editForm, setEditForm] = useState({ category: 'general', content: '' });
  const [isSaving, setIsSaving] = useState(false);

  // Delete Confirmation State
  const [docToDelete, setDocToDelete] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const showNotification = (type, message) => {
    setNotification({ type, message });
    setTimeout(() => {
      setNotification((curr) => (curr && curr.message === message ? null : curr));
    }, 6000);
  };

  // Fetch documents from backend
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

  useEffect(() => {
    loadDocs();
  }, []);

  // Search via real backend API
  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    try {
      const data = await searchDocuments(searchQuery, 5);
      const mappedResults = (data.results || []).map((r) => ({
        source: r.doc_name || 'Unknown Document',
        category: r.category || 'general',
        relevance: r.relevance_score || 0,
        excerpt: r.content || '',
      }));
      setResults(
        mappedResults.length > 0
          ? mappedResults
          : [
              {
                source: 'No matches found',
                relevance: 0,
                excerpt: `No vector passages matched the query "${searchQuery}". Try rephrasing or using different keywords.`,
              },
            ]
      );
    } catch (err) {
      console.error('Search failed:', err.message);
      setResults([
        {
          source: 'Search Error',
          relevance: 0,
          excerpt: `API error: ${err.message}. Make sure the backend is running on port 8000.`,
        },
      ]);
    } finally {
      setIsSearching(false);
    }
  };

  // Handle local file selection / drop
  const handleFileSelected = (file) => {
    if (!file) return;
    const fileName = file.name;
    let autoCategory = 'general';
    const lower = fileName.toLowerCase();
    if (lower.includes('990') || lower.includes('tax') || lower.includes('financial')) {
      autoCategory = 'irs_990';
    } else if (lower.includes('proposal') || lower.includes('grant')) {
      autoCategory = 'past_proposal';
    } else if (lower.includes('impact') || lower.includes('report') || lower.includes('eval')) {
      autoCategory = 'impact_report';
    } else if (lower.includes('bio') || lower.includes('staff') || lower.includes('board')) {
      autoCategory = 'staff_bios';
    } else if (lower.includes('strategic') || lower.includes('plan')) {
      autoCategory = 'strategic_plan';
    } else if (lower.includes('outcome') || lower.includes('metric')) {
      autoCategory = 'program_outcomes';
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result || '';
      setUploadForm({
        doc_name: fileName,
        category: autoCategory,
        content: typeof content === 'string' ? content : '',
      });
      setUploadError(null);
    };
    reader.onerror = () => {
      setUploadError('Failed to read file from disk. Please try another file or paste text directly.');
    };
    reader.readAsText(file);
  };

  // Submit new document to vector index
  const handleUploadSubmit = async (e) => {
    e.preventDefault();
    if (!uploadForm.doc_name.trim()) {
      setUploadError('Document filename or title is required.');
      return;
    }
    if (!uploadForm.content.trim()) {
      setUploadError('Document content cannot be empty.');
      return;
    }

    setIsIndexing(true);
    setUploadError(null);
    try {
      const res = await indexDocument({
        doc_name: uploadForm.doc_name.trim(),
        content: uploadForm.content.trim(),
        category: uploadForm.category,
      });

      showNotification(
        'success',
        `Indexed "${res.doc_name}" into vector knowledge base (${res.chunks} paragraph chunks generated with Amazon Titan Text Embeddings V2).`
      );
      setIsUploadOpen(false);
      setUploadForm({ doc_name: '', category: 'general', content: '' });
      await loadDocs();
    } catch (err) {
      console.error('Failed to index document:', err.message);
      setUploadError(err.message || 'Indexing failed. Ensure backend and AWS Bedrock are accessible.');
    } finally {
      setIsIndexing(false);
    }
  };

  // Open inspection/edit modal
  const handleOpenInspect = async (docName) => {
    setInspectDocName(docName);
    setIsInspectOpen(true);
    setIsEditMode(false);
    setInspectLoading(true);
    setInspectError(null);
    try {
      const doc = await fetchDocumentByName(docName);
      setInspectedDoc(doc);
      setEditForm({
        category: doc.category || 'general',
        content: doc.content || '',
      });
    } catch (err) {
      console.error(`Failed to inspect document ${docName}:`, err.message);
      setInspectError(err.message || 'Could not retrieve full document details.');
    } finally {
      setInspectLoading(false);
    }
  };

  // Save changes and re-index
  const handleSaveAndReindex = async () => {
    if (!editForm.content.trim()) {
      setInspectError('Document content cannot be empty.');
      return;
    }

    setIsSaving(true);
    setInspectError(null);
    try {
      const res = await indexDocument({
        doc_name: inspectDocName,
        content: editForm.content.trim(),
        category: editForm.category,
      });

      showNotification(
        'success',
        `Re-indexed "${inspectDocName}" (${res.chunks} chunks re-embedded with Amazon Titan). Vector index updated.`
      );

      // Refresh inspected document view
      const updatedDoc = await fetchDocumentByName(inspectDocName);
      setInspectedDoc(updatedDoc);
      setIsEditMode(false);
      await loadDocs();
    } catch (err) {
      console.error(`Failed to re-index document ${inspectDocName}:`, err.message);
      setInspectError(err.message || 'Failed to re-index document.');
    } finally {
      setIsSaving(false);
    }
  };

  // Confirm and delete document
  const handleConfirmDelete = async () => {
    if (!docToDelete) return;
    setIsDeleting(true);
    try {
      await deleteDocument(docToDelete);
      showNotification('info', `Removed "${docToDelete}" and purged its embeddings from the vector store.`);
      if (isInspectOpen && inspectDocName === docToDelete) {
        setIsInspectOpen(false);
      }
      setDocToDelete(null);
      await loadDocs();
    } catch (err) {
      console.error(`Failed to delete document ${docToDelete}:`, err.message);
      showNotification('error', `Failed to delete document: ${err.message}`);
    } finally {
      setIsDeleting(false);
    }
  };

  // Filtered documents list
  const filteredDocs =
    selectedCategoryFilter === 'all'
      ? indexedDocs
      : indexedDocs.filter((d) => d.category === selectedCategoryFilter);

  return (
    <div>
      {/* Title Header with Action Button */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: '1.25rem',
          marginBottom: '2rem',
        }}
      >
        <div>
          <h2 className="font-heading hero-title" style={{ fontSize: '2.5rem', lineHeight: '1', color: 'var(--ink)' }}>
            RAG ORGANIZATIONAL KNOWLEDGE BASE
          </h2>
          <p style={{ color: 'var(--ink-muted)', fontSize: '0.95rem', marginTop: '0.4rem', maxWidth: '750px' }}>
            Vector-indexed organizational documentation empowering the Matcher and Drafter agents with verified facts,
            program statistics, and IRS 990 financials.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <button
            onClick={() => {
              setUploadForm({ doc_name: '', category: 'general', content: '' });
              setUploadError(null);
              setIsUploadOpen(true);
            }}
            className="brutalist-btn btn-primary"
            style={{ padding: '0.65rem 1.4rem' }}
          >
            <Plus size={18} /> UPLOAD DOCUMENT
          </button>
        </div>
      </div>

      {/* Global Notification Banner */}
      {notification && (
        <div
          className="brutalist-card"
          style={{
            marginBottom: '1.5rem',
            padding: '1rem 1.25rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background:
              notification.type === 'error'
                ? '#FEE2E2'
                : notification.type === 'success'
                ? '#ECFDF5'
                : '#FEF3C7',
            borderColor:
              notification.type === 'error'
                ? '#DC2626'
                : notification.type === 'success'
                ? '#059669'
                : '#D97706',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            {notification.type === 'success' ? (
              <CheckCircle size={20} color="#059669" />
            ) : notification.type === 'error' ? (
              <AlertTriangle size={20} color="#DC2626" />
            ) : (
              <Sparkles size={20} color="#D97706" />
            )}
            <span
              style={{
                fontSize: '0.9rem',
                fontFamily: 'var(--font-mono)',
                fontWeight: 600,
                color:
                  notification.type === 'error'
                    ? '#991B1B'
                    : notification.type === 'success'
                    ? '#065F46'
                    : '#92400E',
              }}
            >
              {notification.message}
            </span>
          </div>
          <button
            onClick={() => setNotification(null)}
            style={{
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--ink-muted)',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <X size={16} />
          </button>
        </div>
      )}

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
                background: '#FFFFFF',
              }}
            />
            <Search
              size={18}
              style={{
                position: 'absolute',
                left: '1rem',
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--ink-muted)',
              }}
            />
          </div>

          <button
            type="submit"
            className="brutalist-btn btn-primary"
            style={{ padding: '0.65rem 1.25rem', whiteSpace: 'nowrap' }}
          >
            {isSearching ? 'SEARCHING...' : 'QUERY VECTORS'}
          </button>
        </form>

        {/* Search Results Display */}
        {results && (
          <div style={{ marginTop: '1.5rem' }}>
            <div
              style={{
                fontSize: '0.8rem',
                fontFamily: 'var(--font-mono)',
                fontWeight: 700,
                marginBottom: '0.75rem',
                color: 'var(--ink)',
              }}
            >
              TOP VECTOR RETRIEVAL MATCHES (HYBRID 0.7 COSINE / 0.3 LEXICAL):
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {results.map((r, idx) => (
                <div
                  key={idx}
                  style={{
                    background: 'var(--card-alt-bg)',
                    border: '1px solid var(--border-dark)',
                    padding: '1rem',
                    minWidth: 0,
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: '0.4rem',
                      flexWrap: 'wrap',
                      gap: '0.4rem',
                    }}
                  >
                    <span
                      style={{
                        fontWeight: 700,
                        fontSize: '0.85rem',
                        wordBreak: 'break-word',
                        overflowWrap: 'anywhere',
                      }}
                    >
                      {formatDocTitle(r.source)}
                    </span>
                    {r.relevance > 0 && (
                      <span className="tag-badge tag-amber">{Math.round(r.relevance * 100)}% RELEVANCE</span>
                    )}
                  </div>
                  <p
                    style={{
                      fontSize: '0.88rem',
                      color: 'var(--ink-muted)',
                      fontStyle: 'italic',
                      wordBreak: 'break-word',
                      overflowWrap: 'anywhere',
                      lineHeight: '1.5',
                    }}
                  >
                    "{r.excerpt}"
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Document Category Filters & Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          marginBottom: '1.25rem',
        }}
      >
        <h3 className="font-heading" style={{ fontSize: '1.75rem', margin: 0 }}>
          INDEXED ORGANIZATIONAL CORPUS ({indexedDocs.length} DOCUMENTS)
        </h3>

        {/* Category Filter Pills */}
        <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
          <button
            onClick={() => setSelectedCategoryFilter('all')}
            className={`brutalist-btn ${selectedCategoryFilter === 'all' ? 'btn-primary' : 'btn-outline'}`}
            style={{ fontSize: '0.75rem', padding: '0.35rem 0.75rem' }}
          >
            ALL ({indexedDocs.length})
          </button>
          {Array.from(new Set(indexedDocs.map((d) => d.category))).map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategoryFilter(cat)}
              className={`brutalist-btn ${selectedCategoryFilter === cat ? 'btn-primary' : 'btn-outline'}`}
              style={{ fontSize: '0.75rem', padding: '0.35rem 0.75rem' }}
            >
              {formatCategory(cat)}
            </button>
          ))}
        </div>
      </div>

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
      ) : filteredDocs.length === 0 ? (
        <div className="brutalist-card" style={{ padding: '3rem', textAlign: 'center' }}>
          <Database size={32} color="var(--ink-muted)" style={{ marginBottom: '0.75rem' }} />
          <div className="font-heading" style={{ fontSize: '1.5rem', color: 'var(--ink)' }}>
            NO DOCUMENTS FOUND
          </div>
          <p style={{ color: 'var(--ink-muted)', fontSize: '0.9rem', marginTop: '0.5rem' }}>
            {selectedCategoryFilter === 'all'
              ? 'No documents have been indexed into the RAG Knowledge Base yet. Click "+ UPLOAD DOCUMENT" above to add verified organizational materials.'
              : `No documents in the "${formatCategory(selectedCategoryFilter)}" category.`}
          </p>
        </div>
      ) : (
        <div className="knowledge-grid">
          {filteredDocs.map((doc, idx) => (
            <div
              key={idx}
              className="brutalist-card knowledge-card"
              style={{
                padding: '1.5rem',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                transition: 'transform 0.15s ease, box-shadow 0.15s ease',
              }}
            >
              <div>
                {/* Badge Header & Quick Actions */}
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '0.75rem',
                    flexWrap: 'wrap',
                    gap: '0.5rem',
                  }}
                >
                  <span
                    className="tag-badge tag-dark"
                    style={{ maxWidth: '100%', overflow: 'hidden', textOverflow: 'ellipsis' }}
                  >
                    {formatCategory(doc.category)}
                  </span>

                  <div style={{ display: 'flex', gap: '0.35rem', alignItems: 'center' }}>
                    <span className="tag-badge tag-green">
                      <CheckCircle size={12} /> INDEXED
                    </span>
                    <button
                      onClick={() => setDocToDelete(doc.doc_name)}
                      title="Delete document from knowledge base"
                      style={{
                        background: 'transparent',
                        border: '1px solid var(--border-dark)',
                        color: 'var(--ink-muted)',
                        padding: '3px 6px',
                        cursor: 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        borderRadius: '2px',
                        transition: 'all 0.15s ease',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = '#FEE2E2';
                        e.currentTarget.style.color = '#DC2626';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'transparent';
                        e.currentTarget.style.color = 'var(--ink-muted)';
                      }}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>

                {/* Formatted Title */}
                <h4 className="font-heading knowledge-card-title">{formatDocTitle(doc.doc_name)}</h4>

                {/* File Reference */}
                <div className="knowledge-card-filename">📄 {doc.doc_name}</div>
              </div>

              {/* Meta & Embedding Footer & Inspect Action */}
              <div>
                <hr className="dashed-divider" style={{ margin: '0.75rem 0' }} />

                <div className="knowledge-card-meta">
                  {doc.chunk_count} {doc.chunk_count === 1 ? 'PARAGRAPH CHUNK' : 'PARAGRAPH CHUNKS'} • ~
                  {doc.total_words} ESTIMATED TOKENS
                </div>

                <div
                  style={{
                    fontSize: '0.72rem',
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--ink-faint)',
                    wordBreak: 'break-word',
                    overflowWrap: 'anywhere',
                    marginBottom: '0.85rem',
                  }}
                >
                  EMBEDDING: Titan Text Embeddings V2 (1024-dim)
                </div>

                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    onClick={() => handleOpenInspect(doc.doc_name)}
                    className="brutalist-btn btn-outline"
                    style={{
                      width: '100%',
                      fontSize: '0.82rem',
                      padding: '0.45rem 0.8rem',
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '0.4rem',
                    }}
                  >
                    <Eye size={14} /> INSPECT & EDIT
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ───────────────────────────────────────────── */}
      {/*  UPLOAD MODAL                                */}
      {/* ───────────────────────────────────────────── */}
      {isUploadOpen && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(24, 24, 27, 0.75)',
            backdropFilter: 'blur(3px)',
            zIndex: 1100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px',
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget && !isIndexing) setIsUploadOpen(false);
          }}
        >
          <div
            style={{
              background: '#FAF8F5',
              border: '3px solid #18181B',
              boxShadow: '8px 8px 0px #18181B',
              width: '740px',
              maxWidth: '100%',
              maxHeight: '90vh',
              overflowY: 'auto',
              padding: '24px',
              borderRadius: '2px',
            }}
          >
            {/* Modal Header */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                borderBottom: '2px solid #18181B',
                paddingBottom: '12px',
                marginBottom: '16px',
              }}
            >
              <div>
                <h2
                  style={{
                    margin: 0,
                    fontSize: '20px',
                    fontWeight: '800',
                    fontFamily: 'var(--font-heading)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                  }}
                >
                  <FileUp size={22} /> Upload to RAG Knowledge Base
                </h2>
                <div style={{ fontSize: '13px', color: '#71717A', marginTop: '2px' }}>
                  Index organizational documents into Bedrock Titan Vector Store for accurate grant matching & drafting.
                </div>
              </div>
              <button
                onClick={() => !isIndexing && setIsUploadOpen(false)}
                disabled={isIndexing}
                style={{
                  background: 'transparent',
                  border: 'none',
                  fontSize: '20px',
                  fontWeight: '800',
                  cursor: isIndexing ? 'not-allowed' : 'pointer',
                  color: '#18181B',
                  padding: '4px 8px',
                }}
              >
                ✕
              </button>
            </div>

            {/* Upload Mode Selector */}
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem' }}>
              <button
                type="button"
                onClick={() => setUploadMode('file')}
                className={`brutalist-btn ${uploadMode === 'file' ? 'btn-primary' : 'btn-outline'}`}
                style={{ fontSize: '0.85rem', padding: '0.45rem 1rem' }}
              >
                📁 Choose File (.md, .txt, .json, .csv)
              </button>
              <button
                type="button"
                onClick={() => setUploadMode('paste')}
                className={`brutalist-btn ${uploadMode === 'paste' ? 'btn-primary' : 'btn-outline'}`}
                style={{ fontSize: '0.85rem', padding: '0.45rem 1rem' }}
              >
                ✍️ Direct Text Paste
              </button>
            </div>

            {uploadError && (
              <div
                style={{
                  background: '#FEE2E2',
                  border: '2px solid #DC2626',
                  color: '#991B1B',
                  padding: '0.75rem 1rem',
                  fontSize: '0.85rem',
                  fontFamily: 'var(--font-mono)',
                  marginBottom: '1rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                }}
              >
                <AlertTriangle size={18} /> {uploadError}
              </div>
            )}

            <form onSubmit={handleUploadSubmit}>
              {/* File Dropzone (if in file mode) */}
              {uploadMode === 'file' && (
                <div
                  style={{
                    border: '2px dashed var(--border-dark)',
                    background: '#FFFFFF',
                    padding: '1.5rem',
                    textAlign: 'center',
                    marginBottom: '1.25rem',
                    cursor: 'pointer',
                  }}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                      handleFileSelected(e.dataTransfer.files[0]);
                    }
                  }}
                  onClick={() => document.getElementById('file-upload-input')?.click()}
                >
                  <input
                    id="file-upload-input"
                    type="file"
                    accept=".md,.txt,.json,.csv"
                    style={{ display: 'none' }}
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        handleFileSelected(e.target.files[0]);
                      }
                    }}
                  />
                  <FileUp size={36} color="var(--ink-muted)" style={{ marginBottom: '0.5rem' }} />
                  <div style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--ink)' }}>
                    Drag and drop file here or click to browse
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--ink-muted)', marginTop: '0.25rem' }}>
                    Supports Markdown (.md), Plain Text (.txt), JSON (.json), CSV (.csv)
                  </div>
                </div>
              )}

              {/* Document Filename and Category */}
              <div style={{ display: 'grid', gridTemplateColumns: '1.8fr 1.2fr', gap: '1rem', marginBottom: '1rem' }}>
                <div>
                  <label
                    style={{
                      display: 'block',
                      fontSize: '0.78rem',
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      marginBottom: '0.35rem',
                      color: 'var(--ink)',
                    }}
                  >
                    Document Name / Title *
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. STEM_Outcomes_Report_2025.md"
                    value={uploadForm.doc_name}
                    onChange={(e) => setUploadForm({ ...uploadForm, doc_name: e.target.value })}
                    style={{
                      width: '100%',
                      boxSizing: 'border-box',
                      padding: '0.65rem 0.85rem',
                      border: '2px solid var(--border-dark)',
                      outline: 'none',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.85rem',
                      background: '#FFFFFF',
                    }}
                  />
                </div>

                <div>
                  <label
                    style={{
                      display: 'block',
                      fontSize: '0.78rem',
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      marginBottom: '0.35rem',
                      color: 'var(--ink)',
                    }}
                  >
                    Corpus Category *
                  </label>
                  <select
                    value={uploadForm.category}
                    onChange={(e) => setUploadForm({ ...uploadForm, category: e.target.value })}
                    style={{
                      width: '100%',
                      boxSizing: 'border-box',
                      padding: '0.65rem 0.85rem',
                      border: '2px solid var(--border-dark)',
                      outline: 'none',
                      fontFamily: 'var(--font-body)',
                      fontSize: '0.85rem',
                      background: '#FFFFFF',
                    }}
                  >
                    {CATEGORY_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Document Content */}
              <div style={{ marginBottom: '1.25rem' }}>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '0.35rem',
                  }}
                >
                  <label
                    style={{
                      fontSize: '0.78rem',
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      color: 'var(--ink)',
                    }}
                  >
                    Full Text Content *
                  </label>
                  <span style={{ fontSize: '0.75rem', color: 'var(--ink-muted)', fontFamily: 'var(--font-mono)' }}>
                    {uploadForm.content.length} characters • ~{Math.round(uploadForm.content.split(/\s+/).filter(Boolean).length * 1.3)} tokens
                  </span>
                </div>
                <textarea
                  rows={10}
                  placeholder="Paste or edit the full document content here. The backend RAG engine will chunk by double-newlines and create vector embeddings using Amazon Bedrock Titan Text Embeddings V2..."
                  value={uploadForm.content}
                  onChange={(e) => setUploadForm({ ...uploadForm, content: e.target.value })}
                  style={{
                    width: '100%',
                    boxSizing: 'border-box',
                    padding: '0.85rem',
                    border: '2px solid var(--border-dark)',
                    outline: 'none',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.83rem',
                    lineHeight: '1.5',
                    background: '#FFFFFF',
                    resize: 'vertical',
                  }}
                />
              </div>

              {/* Action Buttons */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'flex-end',
                  gap: '0.75rem',
                  borderTop: '2px solid #18181B',
                  paddingTop: '16px',
                }}
              >
                <button
                  type="button"
                  onClick={() => setIsUploadOpen(false)}
                  disabled={isIndexing}
                  className="brutalist-btn btn-outline"
                  style={{ fontSize: '0.88rem', padding: '0.55rem 1.1rem' }}
                >
                  CANCEL
                </button>
                <button
                  type="submit"
                  disabled={isIndexing}
                  className="brutalist-btn btn-primary"
                  style={{ fontSize: '0.88rem', padding: '0.55rem 1.35rem' }}
                >
                  {isIndexing ? (
                    <>
                      <RefreshCw size={16} className="spin-slow" /> INDEXING VECTORS...
                    </>
                  ) : (
                    <>
                      <Sparkles size={16} /> INDEX INTO VECTOR STORE
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ───────────────────────────────────────────── */}
      {/*  INSPECT & EDIT MODAL                         */}
      {/* ───────────────────────────────────────────── */}
      {isInspectOpen && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(24, 24, 27, 0.75)',
            backdropFilter: 'blur(3px)',
            zIndex: 1100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px',
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget && !isSaving) setIsInspectOpen(false);
          }}
        >
          <div
            style={{
              background: '#FAF8F5',
              border: '3px solid #18181B',
              boxShadow: '8px 8px 0px #18181B',
              width: '840px',
              maxWidth: '100%',
              maxHeight: '92vh',
              display: 'flex',
              flexDirection: 'column',
              borderRadius: '2px',
              overflow: 'hidden',
            }}
          >
            {/* Modal Top Bar */}
            <div
              style={{
                padding: '16px 24px',
                borderBottom: '2px solid #18181B',
                background: '#FAF8F5',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '0.75rem',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.2rem' }}>
                  <span className="tag-badge tag-dark">
                    {formatCategory(inspectedDoc?.category || 'DOCUMENT')}
                  </span>
                  <span className="tag-badge tag-green">
                    <CheckCircle size={12} /> TITAN V2 EMBEDDED
                  </span>
                </div>
                <h2
                  style={{
                    margin: 0,
                    fontSize: '1.25rem',
                    fontWeight: 800,
                    fontFamily: 'var(--font-heading)',
                    color: 'var(--ink)',
                  }}
                >
                  {formatDocTitle(inspectDocName)}
                </h2>
                <div style={{ fontSize: '0.78rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-muted)' }}>
                  📄 {inspectDocName}
                </div>
              </div>

              {/* Mode Toggle Buttons */}
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <button
                  type="button"
                  onClick={() => setIsEditMode(false)}
                  className={`brutalist-btn ${!isEditMode ? 'btn-primary' : 'btn-outline'}`}
                  style={{ fontSize: '0.78rem', padding: '0.4rem 0.8rem' }}
                >
                  <Eye size={13} /> PREVIEW
                </button>
                <button
                  type="button"
                  onClick={() => setIsEditMode(true)}
                  className={`brutalist-btn ${isEditMode ? 'btn-primary' : 'btn-outline'}`}
                  style={{ fontSize: '0.78rem', padding: '0.4rem 0.8rem' }}
                >
                  <Edit3 size={13} /> EDIT & RE-INDEX
                </button>
                <button
                  onClick={() => !isSaving && setIsInspectOpen(false)}
                  disabled={isSaving}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    fontSize: '20px',
                    fontWeight: '800',
                    cursor: isSaving ? 'not-allowed' : 'pointer',
                    color: '#18181B',
                    marginLeft: '0.5rem',
                  }}
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Error banner in modal */}
            {inspectError && (
              <div
                style={{
                  background: '#FEE2E2',
                  borderBottom: '2px solid #DC2626',
                  color: '#991B1B',
                  padding: '0.65rem 1.25rem',
                  fontSize: '0.85rem',
                  fontFamily: 'var(--font-mono)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                }}
              >
                <AlertTriangle size={16} /> {inspectError}
              </div>
            )}

            {/* Modal Body */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>
              {inspectLoading ? (
                <div style={{ textAlign: 'center', padding: '3rem' }}>
                  <RefreshCw size={28} className="spin-slow" color="var(--ink-muted)" />
                  <div style={{ marginTop: '0.75rem', fontFamily: 'var(--font-heading)', fontSize: '1.1rem' }}>
                    LOADING DOCUMENT CHUNKS...
                  </div>
                </div>
              ) : !inspectedDoc ? (
                <div style={{ textAlign: 'center', padding: '2rem' }}>
                  <AlertTriangle size={28} color="var(--amber-signal)" />
                  <p style={{ marginTop: '0.5rem' }}>Unable to load document contents.</p>
                </div>
              ) : isEditMode ? (
                /* EDIT MODE */
                <div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                    <div>
                      <label
                        style={{
                          display: 'block',
                          fontSize: '0.75rem',
                          fontFamily: 'var(--font-mono)',
                          fontWeight: 700,
                          marginBottom: '0.3rem',
                        }}
                      >
                        DOCUMENT FILENAME
                      </label>
                      <input
                        type="text"
                        value={inspectDocName}
                        disabled
                        style={{
                          width: '100%',
                          boxSizing: 'border-box',
                          padding: '0.55rem 0.75rem',
                          border: '2px solid var(--border-dark)',
                          background: '#E4E4E7',
                          fontFamily: 'var(--font-mono)',
                          fontSize: '0.82rem',
                          cursor: 'not-allowed',
                        }}
                      />
                    </div>

                    <div>
                      <label
                        style={{
                          display: 'block',
                          fontSize: '0.75rem',
                          fontFamily: 'var(--font-mono)',
                          fontWeight: 700,
                          marginBottom: '0.3rem',
                        }}
                      >
                        CORPUS CATEGORY
                      </label>
                      <select
                        value={editForm.category}
                        onChange={(e) => setEditForm({ ...editForm, category: e.target.value })}
                        style={{
                          width: '100%',
                          boxSizing: 'border-box',
                          padding: '0.55rem 0.75rem',
                          border: '2px solid var(--border-dark)',
                          background: '#FFFFFF',
                          fontFamily: 'var(--font-body)',
                          fontSize: '0.85rem',
                        }}
                      >
                        {CATEGORY_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div style={{ marginBottom: '1rem' }}>
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: '0.35rem',
                      }}
                    >
                      <label
                        style={{
                          fontSize: '0.75rem',
                          fontFamily: 'var(--font-mono)',
                          fontWeight: 700,
                          color: 'var(--ink)',
                        }}
                      >
                        EDIT CONTENT (SPLIT BY DOUBLE NEWLINES INTO PARAGRAPH VECTORS)
                      </label>
                      <span style={{ fontSize: '0.75rem', color: 'var(--ink-muted)', fontFamily: 'var(--font-mono)' }}>
                        {editForm.content.length} characters • ~
                        {Math.round(editForm.content.split(/\s+/).filter(Boolean).length * 1.3)} tokens
                      </span>
                    </div>
                    <textarea
                      rows={14}
                      value={editForm.content}
                      onChange={(e) => setEditForm({ ...editForm, content: e.target.value })}
                      style={{
                        width: '100%',
                        boxSizing: 'border-box',
                        padding: '1rem',
                        border: '2px solid var(--border-dark)',
                        outline: 'none',
                        fontFamily: 'var(--font-mono)',
                        fontSize: '0.85rem',
                        lineHeight: '1.6',
                        background: '#FFFFFF',
                        resize: 'vertical',
                      }}
                    />
                  </div>

                  <div
                    style={{
                      background: '#FEF3C7',
                      border: '1px solid #D97706',
                      padding: '0.75rem 1rem',
                      fontSize: '0.8rem',
                      color: '#92400E',
                      marginBottom: '1rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                    }}
                  >
                    <Sparkles size={16} /> Saving changes will immediately regenerate Amazon Bedrock Titan Text
                    Embeddings (1024-dim) for all chunks in this document.
                  </div>
                </div>
              ) : (
                /* PREVIEW MODE */
                <div>
                  {/* Stats Ribbon */}
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                      gap: '0.75rem',
                      marginBottom: '1.25rem',
                    }}
                  >
                    <div
                      style={{
                        background: '#FFFFFF',
                        border: '1px solid var(--border-dark)',
                        padding: '0.65rem 0.85rem',
                      }}
                    >
                      <div style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-muted)' }}>
                        PARAGRAPH CHUNKS
                      </div>
                      <div style={{ fontSize: '1.15rem', fontWeight: 800, fontFamily: 'var(--font-heading)' }}>
                        {inspectedDoc.chunk_count} CHUNKS
                      </div>
                    </div>

                    <div
                      style={{
                        background: '#FFFFFF',
                        border: '1px solid var(--border-dark)',
                        padding: '0.65rem 0.85rem',
                      }}
                    >
                      <div style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-muted)' }}>
                        ESTIMATED CORPUS TOKENS
                      </div>
                      <div style={{ fontSize: '1.15rem', fontWeight: 800, fontFamily: 'var(--font-heading)' }}>
                        ~{inspectedDoc.total_words} TOKENS
                      </div>
                    </div>

                    <div
                      style={{
                        background: '#FFFFFF',
                        border: '1px solid var(--border-dark)',
                        padding: '0.65rem 0.85rem',
                      }}
                    >
                      <div style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-muted)' }}>
                        VECTOR EMBEDDING MODEL
                      </div>
                      <div style={{ fontSize: '0.88rem', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                        Titan Text V2 (1024-D)
                      </div>
                    </div>
                  </div>

                  {/* Document Raw Content Preview */}
                  <div style={{ marginBottom: '1.5rem' }}>
                    <div
                      style={{
                        fontSize: '0.78rem',
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        color: 'var(--ink)',
                        marginBottom: '0.5rem',
                      }}
                    >
                      FULL DOCUMENT TEXT PREVIEW
                    </div>
                    <div
                      style={{
                        background: '#FFFFFF',
                        border: '2px solid var(--border-dark)',
                        padding: '1.25rem',
                        maxHeight: '320px',
                        overflowY: 'auto',
                        whiteSpace: 'pre-wrap',
                        fontFamily: 'var(--font-body)',
                        fontSize: '0.9rem',
                        lineHeight: '1.6',
                        color: 'var(--ink)',
                      }}
                    >
                      {inspectedDoc.content}
                    </div>
                  </div>

                  {/* Chunks Breakdown */}
                  {inspectedDoc.chunks && inspectedDoc.chunks.length > 0 && (
                    <div>
                      <div
                        style={{
                          fontSize: '0.78rem',
                          fontFamily: 'var(--font-mono)',
                          fontWeight: 700,
                          textTransform: 'uppercase',
                          color: 'var(--ink)',
                          marginBottom: '0.5rem',
                        }}
                      >
                        INDEXED VECTOR CHUNKS ({inspectedDoc.chunks.length})
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        {inspectedDoc.chunks.map((chunk, cIdx) => (
                          <div
                            key={chunk.chunk_id || cIdx}
                            style={{
                              background: 'var(--card-alt-bg)',
                              border: '1px solid var(--border-dark)',
                              padding: '0.75rem 1rem',
                            }}
                          >
                            <div
                              style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                fontSize: '0.72rem',
                                fontFamily: 'var(--font-mono)',
                                color: 'var(--ink-muted)',
                                marginBottom: '0.3rem',
                              }}
                            >
                              <span>CHUNK #{chunk.chunk_index + 1} ({chunk.chunk_id})</span>
                              <span>~{chunk.token_estimate} tokens</span>
                            </div>
                            <div
                              style={{
                                fontSize: '0.85rem',
                                color: 'var(--ink)',
                                lineHeight: '1.45',
                                fontStyle: 'italic',
                              }}
                            >
                              "{chunk.content}"
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Modal Bottom Actions */}
            <div
              style={{
                padding: '16px 24px',
                borderTop: '2px solid #18181B',
                background: '#FAF8F5',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '0.75rem',
              }}
            >
              <button
                type="button"
                onClick={() => setDocToDelete(inspectDocName)}
                disabled={isSaving}
                className="brutalist-btn"
                style={{
                  fontSize: '0.82rem',
                  padding: '0.45rem 0.9rem',
                  background: '#FEE2E2',
                  color: '#991B1B',
                  borderColor: '#DC2626',
                }}
              >
                <Trash2 size={14} /> DELETE DOCUMENT
              </button>

              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <button
                  type="button"
                  onClick={() => setIsInspectOpen(false)}
                  disabled={isSaving}
                  className="brutalist-btn btn-outline"
                  style={{ fontSize: '0.82rem', padding: '0.45rem 1rem' }}
                >
                  CLOSE
                </button>

                {isEditMode ? (
                  <button
                    type="button"
                    onClick={handleSaveAndReindex}
                    disabled={isSaving}
                    className="brutalist-btn btn-primary"
                    style={{ fontSize: '0.82rem', padding: '0.45rem 1.25rem' }}
                  >
                    {isSaving ? (
                      <>
                        <RefreshCw size={14} className="spin-slow" /> SAVING & RE-INDEXING...
                      </>
                    ) : (
                      <>
                        <Save size={14} /> SAVE & RE-INDEX
                      </>
                    )}
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => setIsEditMode(true)}
                    className="brutalist-btn btn-primary"
                    style={{ fontSize: '0.82rem', padding: '0.45rem 1.25rem' }}
                  >
                    <Edit3 size={14} /> EDIT DOCUMENT
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ───────────────────────────────────────────── */}
      {/*  DELETE CONFIRMATION MODAL                   */}
      {/* ───────────────────────────────────────────── */}
      {docToDelete && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(24, 24, 27, 0.75)',
            backdropFilter: 'blur(3px)',
            zIndex: 1200,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px',
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget && !isDeleting) setDocToDelete(null);
          }}
        >
          <div
            style={{
              background: '#FAF8F5',
              border: '3px solid #DC2626',
              boxShadow: '8px 8px 0px #DC2626',
              width: '500px',
              maxWidth: '100%',
              padding: '24px',
              borderRadius: '2px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
              <div
                style={{
                  background: '#FEE2E2',
                  padding: '8px',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Trash2 size={24} color="#DC2626" />
              </div>
              <h3
                style={{
                  margin: 0,
                  fontSize: '1.2rem',
                  fontWeight: 800,
                  fontFamily: 'var(--font-heading)',
                  color: '#991B1B',
                }}
              >
                DELETE DOCUMENT FROM KNOWLEDGE BASE?
              </h3>
            </div>

            <p style={{ fontSize: '0.9rem', lineHeight: '1.5', color: 'var(--ink)', marginBottom: '1rem' }}>
              Are you sure you want to permanently delete <strong>{docToDelete}</strong>?
            </p>

            <div
              style={{
                background: '#FFF1F2',
                border: '1px solid #FECDD3',
                padding: '0.75rem',
                fontSize: '0.8rem',
                color: '#9F1239',
                marginBottom: '1.5rem',
              }}
            >
              ⚠️ All paragraph chunks and 1024-dimensional vector embeddings associated with this document will be
              purged from the knowledge index. The Matcher and Drafter agents will no longer reference these facts.
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button
                type="button"
                onClick={() => setDocToDelete(null)}
                disabled={isDeleting}
                className="brutalist-btn btn-outline"
                style={{ fontSize: '0.85rem', padding: '0.45rem 1rem' }}
              >
                CANCEL
              </button>
              <button
                type="button"
                onClick={handleConfirmDelete}
                disabled={isDeleting}
                className="brutalist-btn"
                style={{
                  fontSize: '0.85rem',
                  padding: '0.45rem 1.25rem',
                  background: '#DC2626',
                  color: '#FFFFFF',
                  borderColor: '#991B1B',
                }}
              >
                {isDeleting ? (
                  <>
                    <RefreshCw size={14} className="spin-slow" /> DELETING...
                  </>
                ) : (
                  'YES, DELETE DOCUMENT'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
