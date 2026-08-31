import React, { useState, useEffect } from 'react';
import { useParams, Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Download, Copy, Check, Sparkles, Target, BookOpen, AlertTriangle, Building2, Calendar, DollarSign, Loader2, Columns, ArrowRight } from 'lucide-react';
import { useGrants } from '../context/GrantContext';
import { fetchApplications, triggerDraft } from '../services/api';

export default function GrantDetailPage() {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { getGrantById, refreshGrants } = useGrants();
  
  const grant = getGrantById(id);
  const [draft, setDraft] = useState(null);
  const [loadingDraft, setLoadingDraft] = useState(true);
  const [isDrafting, setIsDrafting] = useState(false);
  const [draftError, setDraftError] = useState(null);
  const [activeSectionIdx, setActiveSectionIdx] = useState(0);
  const [copied, setCopied] = useState(false);

  // View state: 'rubric' | 'draft' | 'split'
  const initialView = searchParams.get('view') || location.state?.view || 'rubric';
  const [activeViewMode, setActiveViewMode] = useState(initialView);

  // Sync state if URL query param changes
  useEffect(() => {
    const viewParam = searchParams.get('view');
    if (viewParam && ['rubric', 'draft', 'split'].includes(viewParam)) {
      setActiveViewMode(viewParam);
    }
  }, [searchParams]);

  // Determine dynamic origin path and back button label
  const fromPath = location.state?.from || '/pipeline';
  
  const getBackLabel = (path) => {
    if (path === '/drafts') return 'BACK TO APPLICATION DRAFTS';
    if (path === '/') return 'BACK TO HOME';
    return 'BACK TO PIPELINE';
  };

  const backLabel = getBackLabel(fromPath);

  const handleBackNavigation = () => {
    if (window.history.state && window.history.state.idx > 0) {
      navigate(-1);
    } else {
      navigate(fromPath);
    }
  };

  const switchView = (mode) => {
    setActiveViewMode(mode);
    setSearchParams({ view: mode });
  };

  // Fetch drafted application for this grant from API
  useEffect(() => {
    const loadDraft = async () => {
      if (!grant) return;
      setLoadingDraft(true);
      try {
        const data = await fetchApplications();
        const appsList = Array.isArray(data) ? data : (data?.applications || []);
        const grantId = grant.grant_id || grant.id;
        const matchingDraft = appsList.find(
          a => String(a.grant_id) === String(grantId) || String(a.grant_id) === String(grant.id)
        );
        if (matchingDraft) {
          setDraft(matchingDraft);
        }
      } catch (err) {
        console.warn('Could not fetch drafts for grant:', err.message);
      } finally {
        setLoadingDraft(false);
      }
    };
    loadDraft();
  }, [grant]);

  const handleGenerateDraft = async () => {
    if (!grant) return;
    setIsDrafting(true);
    setDraftError(null);
    try {
      const grantId = grant.grant_id || grant.id;
      const res = await triggerDraft(grantId);
      if (res && res.application) {
        setDraft(res.application);
      } else {
        const appsData = await fetchApplications();
        const appsList = Array.isArray(appsData) ? appsData : (appsData?.applications || []);
        const found = appsList.find(
          a => String(a.grant_id) === String(grantId)
        );
        if (found) setDraft(found);
      }
      refreshGrants();
    } catch (err) {
      console.error('Draft generation failed:', err.message);
      setDraftError(err.message);
    } finally {
      setIsDrafting(false);
    }
  };

  if (!grant) {
    return (
      <div className="page-container" style={{ textAlign: 'center', padding: '4rem 1rem' }}>
        <h2 className="font-heading" style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>
          GRANT OPPORTUNITY NOT FOUND
        </h2>
        <p style={{ color: 'var(--ink-muted)', marginBottom: '1.5rem' }}>
          The requested federal opportunity could not be located.
        </p>
        <button onClick={handleBackNavigation} className="brutalist-btn btn-primary">
          <ArrowLeft size={18} /> {backLabel}
        </button>
      </div>
    );
  }

  const score = grant.match_score || {
    mission_alignment: 0,
    eligibility_fit: 0,
    capacity_match: 0,
    geographic_fit: 0,
    track_record: 0,
    total: 0
  };

  const sections = draft?.sections && draft.sections.length > 0 ? draft.sections : [];

  const handleExportMarkdown = () => {
    if (sections.length === 0) return;
    const md = `# Grant Application Draft\n## ${grant.title}\n**Agency**: ${grant.agency}\n**Grant ID**: ${grant.grant_id || grant.id}\n**Match Score**: ${score.total}/100\n\n---\n\n` +
      sections.map(s => `### ${s.title}\n\n${s.content}\n\n`).join('\n---\n\n');
    
    const blob = new Blob([md], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Application_Draft_${(grant.grant_id || 'grant').replace(/\s+/g, '_')}.md`;
    a.click();
  };

  const handleCopy = () => {
    if (sections.length === 0) return;
    const text = sections.map(s => `${s.title}\n\n${s.content}`).join('\n\n====================\n\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // ─────────────────────────────────────────────
  //  Rubric Component (Left / Standalone)
  // ─────────────────────────────────────────────
  const renderRubricPanel = (isFullWidth = false) => (
    <div className="brutalist-card" style={{ padding: isFullWidth ? '2rem' : '1.25rem' }}>
      {/* Fit Score Header */}
      <div style={{
        background: 'var(--card-alt-bg)',
        border: '2px solid var(--border-dark)',
        padding: isFullWidth ? '1.25rem 1.5rem' : '0.85rem 1rem',
        marginBottom: '1.5rem'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem', flexWrap: 'wrap', gap: '0.4rem' }}>
          <span className="font-heading" style={{ fontSize: isFullWidth ? '1.6rem' : '1.25rem' }}>
            5-DIMENSION FIT SCORE OVERVIEW
          </span>
          <span className={`tag-badge ${score.total >= 80 ? 'tag-amber' : 'tag-neutral'}`} style={{ fontSize: '0.95rem', padding: '0.35rem 0.75rem' }}>
            {score.total} / 100 {score.total >= 80 ? '• AUTO-DRAFT READY' : ''}
          </span>
        </div>
        <p style={{ fontSize: '0.85rem', color: 'var(--ink-muted)', lineHeight: '1.4' }}>
          Autonomous scoring calculated by the Matcher Agent against Youth Education Alliance organization profile, financial ratios, and RAG-indexed documents.
        </p>
      </div>

      {/* 5-Dimension Progress Breakdown */}
      <h3 className="font-heading" style={{ fontSize: isFullWidth ? '1.4rem' : '1.1rem', marginBottom: '1rem', color: 'var(--ink)' }}>
        5-DIMENSION RUBRIC BREAKDOWN
      </h3>

      <div style={{ display: isFullWidth ? 'grid' : 'block', gridTemplateColumns: isFullWidth ? 'repeat(auto-fit, minmax(280px, 1fr))' : '1fr', gap: '1.25rem', marginBottom: '1.5rem' }}>
        {[
          { label: 'Mission Alignment', score: score.mission_alignment || 0, max: 30, desc: 'Alignment with nonprofit focus areas, keywords, and programmatic priorities.' },
          { label: 'Eligibility Fit', score: score.eligibility_fit || 0, max: 25, desc: '501(c)(3) active status, SAM.gov registration, and applicant type constraints.' },
          { label: 'Capacity Match', score: score.capacity_match || 0, max: 20, desc: 'Award ceiling alignment with $450K operating budget and 14 instructional staff.' },
          { label: 'Geographic Fit', score: score.geographic_fit || 0, max: 15, desc: 'Target geography, municipal service area, and designated Title I district fit.' },
          { label: 'Past Track Record', score: score.track_record || 0, max: 10, desc: 'Prior federal award close-out compliance and historical execution benchmarks.' }
        ].map((dim, idx) => (
          <div key={idx} style={{ marginBottom: isFullWidth ? '0' : '0.85rem', background: isFullWidth ? 'var(--card-alt-bg)' : 'transparent', padding: isFullWidth ? '1rem' : '0', border: isFullWidth ? '1px solid var(--border-dark)' : 'none' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', fontWeight: 700, marginBottom: '0.35rem' }}>
              <span>{dim.label}</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>{dim.score} / {dim.max}</span>
            </div>
            <div style={{ height: '8px', background: '#E4E4E7', border: '1px solid var(--border-dark)', marginBottom: '0.35rem' }}>
              <div style={{
                height: '100%',
                width: `${dim.max > 0 ? (dim.score / dim.max) * 100 : 0}%`,
                backgroundColor: (dim.score / (dim.max || 1)) >= 0.8 ? 'var(--amber-signal)' : 'var(--ink)'
              }} />
            </div>
            {isFullWidth && (
              <div style={{ fontSize: '0.72rem', color: 'var(--ink-muted)', lineHeight: '1.3' }}>
                {dim.desc}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Key Strengths & Alignment */}
      {grant.key_strengths && grant.key_strengths.length > 0 && (
        <div style={{ marginBottom: '1.5rem' }}>
          <hr className="dashed-divider" style={{ margin: '1rem 0' }} />
          <div style={{ fontWeight: 800, fontSize: '0.9rem', marginBottom: '0.5rem', textTransform: 'uppercase', color: 'var(--ink)' }}>
            ✅ Key Alignment Strengths:
          </div>
          <ul style={{ paddingLeft: '1.2rem', color: 'var(--ink)', lineHeight: '1.6', fontSize: '0.85rem' }}>
            {grant.key_strengths.map((s, idx) => (
              <li key={idx} style={{ marginBottom: '0.35rem' }}>{s}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Potential Risks */}
      {grant.potential_risks && grant.potential_risks.length > 0 && (
        <div style={{ marginBottom: '1.5rem' }}>
          <hr className="dashed-divider" style={{ margin: '1rem 0' }} />
          <div style={{ fontWeight: 800, fontSize: '0.9rem', marginBottom: '0.5rem', textTransform: 'uppercase', color: 'var(--amber-signal)' }}>
            ⚠️ Potential Considerations & Compliance Notes:
          </div>
          <ul style={{ paddingLeft: '1.2rem', color: 'var(--ink-muted)', lineHeight: '1.6', fontSize: '0.85rem' }}>
            {grant.potential_risks.map((r, idx) => (
              <li key={idx} style={{ marginBottom: '0.35rem' }}>{r}</li>
            ))}
          </ul>
        </div>
      )}

      {/* CTA to proceed to draft workstation if in Rubric View */}
      {activeViewMode === 'rubric' && (
        <div style={{
          marginTop: '2rem',
          padding: '1.25rem',
          background: 'var(--card-alt-bg)',
          border: '2px solid var(--border-dark)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem'
        }}>
          <div>
            <div style={{ fontWeight: 800, fontSize: '1.1rem' }}>READY TO PRE-FILL APPLICATION?</div>
            <div style={{ fontSize: '0.82rem', color: 'var(--ink-muted)' }}>
              Open the 6-section proposal draft workstation grounded with RAG facts.
            </div>
          </div>
          <button
            onClick={() => switchView('draft')}
            className="brutalist-btn btn-primary"
            style={{ padding: '0.65rem 1.4rem', fontSize: '0.95rem' }}
          >
            <Sparkles size={16} /> OPEN PROPOSAL WORKSTATION <ArrowRight size={16} />
          </button>
        </div>
      )}
    </div>
  );

  // ─────────────────────────────────────────────
  //  Proposal Draft Workstation Component
  // ─────────────────────────────────────────────
  const renderDraftWorkstation = (isFullWidth = false) => (
    <div className="brutalist-card" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {loadingDraft ? (
        <div style={{ padding: '4rem 2rem', textAlign: 'center', color: 'var(--ink-muted)' }}>
          <Loader2 className="animate-spin" size={32} style={{ margin: '0 auto 1rem' }} />
          <div className="font-heading" style={{ fontSize: '1.4rem' }}>LOADING APPLICATION DRAFT...</div>
        </div>
      ) : sections.length > 0 ? (
        <>
          {/* Section Tabs Strip */}
          <div style={{
            display: 'flex',
            overflowX: 'auto',
            WebkitOverflowScrolling: 'touch',
            borderBottom: '2px solid var(--border-dark)',
            backgroundColor: 'var(--card-alt-bg)',
            whiteSpace: 'nowrap'
          }}>
            {sections.map((s, idx) => {
              const isActive = activeSectionIdx === idx;
              return (
                <button
                  key={idx}
                  onClick={() => setActiveSectionIdx(idx)}
                  className="font-heading"
                  style={{
                    padding: '0.85rem 1.15rem',
                    fontSize: '0.95rem',
                    whiteSpace: 'nowrap',
                    borderRight: '1px solid var(--border-dashed)',
                    borderTop: 'none',
                    borderLeft: 'none',
                    borderBottom: isActive ? '3px solid var(--amber-signal)' : 'none',
                    backgroundColor: isActive ? '#FFFFFF' : 'transparent',
                    color: isActive ? 'var(--amber-signal)' : 'var(--ink)',
                    cursor: 'pointer'
                  }}
                >
                  {s.title}
                </button>
              );
            })}
          </div>

          {/* Active Section Content */}
          {sections[activeSectionIdx] && (
            <div className="workstation-editor-pane" style={{ padding: isFullWidth ? '2rem' : '1.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                <div>
                  <span className="tag-badge tag-green" style={{ marginBottom: '0.35rem', display: 'inline-block' }}>
                    {sections[activeSectionIdx].is_auto_filled ? 'AI AUTONOMOUSLY PRE-FILLED' : 'PYDANTIC SCHEMA VALIDATED'}
                  </span>
                  <h3 className="font-heading" style={{ fontSize: isFullWidth ? '1.8rem' : '1.5rem', color: 'var(--ink)', lineHeight: '1.1' }}>
                    {sections[activeSectionIdx].title}
                  </h3>
                </div>

                <span className="tag-badge tag-dark" style={{ fontSize: '0.78rem' }}>
                  {sections[activeSectionIdx].word_count || sections[activeSectionIdx].content?.split(/\s+/).filter(Boolean).length || 0} WORDS
                </span>
              </div>

              <textarea
                value={sections[activeSectionIdx].content}
                readOnly
                style={{
                  width: '100%',
                  minHeight: isFullWidth ? '380px' : '280px',
                  padding: '1.25rem',
                  fontSize: '0.92rem',
                  lineHeight: '1.65',
                  fontFamily: 'var(--font-body)',
                  color: 'var(--ink)',
                  backgroundColor: 'var(--canvas-bg)',
                  border: '2px solid var(--border-dark)',
                  boxShadow: '3px 3px 0px var(--border-dark)',
                  resize: 'vertical'
                }}
              />

              {/* Bottom Quick Context */}
              {activeViewMode === 'draft' && (
                <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
                  <button
                    onClick={() => switchView('rubric')}
                    className="brutalist-btn btn-outline"
                    style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}
                  >
                    <Target size={15} /> ← VIEW 5-DIMENSION MATCHING RUBRIC
                  </button>
                  <div style={{ fontSize: '0.78rem', color: 'var(--ink-muted)' }}>
                    Section {activeSectionIdx + 1} of {sections.length} • Formatted with RAG citations
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      ) : (
        /* No draft yet: Trigger Drafting Action */
        <div style={{ padding: '4rem 2rem', textAlign: 'center' }}>
          <Sparkles size={40} color="var(--amber-signal)" style={{ margin: '0 auto 1.25rem' }} />
          <h3 className="font-heading" style={{ fontSize: '2rem', color: 'var(--ink)', marginBottom: '0.5rem' }}>
            AUTONOMOUS PROPOSAL DRAFTER
          </h3>
          <p style={{ color: 'var(--ink-muted)', fontSize: '0.95rem', maxWidth: '520px', margin: '0 auto 1.75rem', lineHeight: '1.55' }}>
            Generate a complete 6-section proposal draft pre-populated with Youth Education Alliance organizational facts, budget calculations, and RAG-verified citations.
          </p>

          {draftError && (
            <div className="brutalist-card" style={{ padding: '0.85rem 1.25rem', marginBottom: '1.5rem', borderLeft: '4px solid #EF4444', maxWidth: '520px', margin: '0 auto 1.5rem' }}>
              <div style={{ fontSize: '0.85rem', color: '#EF4444' }}>
                {draftError}
              </div>
            </div>
          )}

          <button
            onClick={handleGenerateDraft}
            disabled={isDrafting}
            className="brutalist-btn btn-primary"
            style={{ padding: '0.85rem 2rem', fontSize: '1.05rem' }}
          >
            {isDrafting ? 'GENERATING PROPOSAL DRAFT...' : 'GENERATE APPLICATION DRAFT'}
          </button>
        </div>
      )}
    </div>
  );

  return (
    <div className="page-container">
      {/* Top Navigation & Action Toolbar */}
      <div style={{ marginBottom: '1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
        <button onClick={handleBackNavigation} className="brutalist-btn btn-outline" style={{ padding: '0.45rem 0.95rem', fontSize: '0.9rem', cursor: 'pointer' }}>
          <ArrowLeft size={16} /> {backLabel}
        </button>

        {sections.length > 0 && (
          <div className="workstation-action-bar" style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button onClick={handleExportMarkdown} className="brutalist-btn btn-amber" style={{ padding: '0.45rem 1rem', fontSize: '0.95rem' }}>
              <Download size={16} /> EXPORT .MD
            </button>
            <button onClick={handleCopy} className="brutalist-btn btn-outline" style={{ padding: '0.45rem 1rem', fontSize: '0.95rem' }}>
              {copied ? <Check size={16} /> : <Copy size={16} />} {copied ? 'COPIED' : 'COPY ALL'}
            </button>
          </div>
        )}
      </div>

      {/* Grant Overview Header Card */}
      <div className="brutalist-card workstation-header-card" style={{ padding: '1.5rem 2rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.5rem', flexWrap: 'wrap' }}>
          <span className={`tag-badge ${score.total >= 80 ? 'tag-amber' : 'tag-neutral'}`}>
            {score.total >= 80 ? 'HIGH FIT OPPORTUNITY' : 'OPPORTUNITY'}
          </span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--ink-muted)' }}>
            {grant.agency || 'Federal Agency'} • ID: {grant.grant_id || grant.id}
          </span>
        </div>

        <h1 className="font-heading workstation-title" style={{ fontSize: '2.5rem', lineHeight: '1.05', color: 'var(--ink)', marginBottom: '0.65rem' }}>
          {grant.title}
        </h1>

        <p style={{ color: 'var(--ink-muted)', fontSize: '0.9rem', lineHeight: '1.45', maxWidth: '960px' }}>
          {grant.synopsis || 'Federal grant opportunity scanned and analyzed by the GrantScout Autonomous Agent Pipeline.'}
        </p>

        {grant.award_ceiling && (
          <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem', flexWrap: 'wrap', fontSize: '0.85rem' }}>
            <span className="tag-badge tag-dark">
              AWARD CEILING: ${grant.award_ceiling.toLocaleString()}
            </span>
            {grant.close_date && (
              <span className="tag-badge tag-neutral">
                DEADLINE: {grant.close_date}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Top Workstation View Mode Switcher */}
      <div className="workstation-view-toggle">
        <button
          onClick={() => switchView('rubric')}
          className={`workstation-tab-btn ${activeViewMode === 'rubric' ? 'active' : ''}`}
        >
          <Target size={16} /> 5-DIMENSION RUBRIC ({score.total}/100)
        </button>
        <button
          onClick={() => switchView('draft')}
          className={`workstation-tab-btn ${activeViewMode === 'draft' ? 'active' : ''}`}
        >
          <Sparkles size={16} /> PROPOSAL WORKSTATION {sections.length > 0 ? `(${sections.length} SECTIONS)` : ''}
        </button>
        <button
          onClick={() => switchView('split')}
          className={`workstation-tab-btn ${activeViewMode === 'split' ? 'active' : ''}`}
        >
          <Columns size={16} /> SPLIT VIEW
        </button>
      </div>

      {/* Dynamic View Layout Rendering */}
      {activeViewMode === 'rubric' ? (
        <div className="workstation-container layout-single">
          {renderRubricPanel(true)}
        </div>
      ) : activeViewMode === 'draft' ? (
        <div className="workstation-container layout-single">
          {renderDraftWorkstation(true)}
        </div>
      ) : (
        /* Split View: Side by Side */
        <div className="workstation-container layout-split">
          {renderRubricPanel(false)}
          {renderDraftWorkstation(false)}
        </div>
      )}
    </div>
  );
}
