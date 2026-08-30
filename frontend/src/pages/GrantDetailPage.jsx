import React, { useState, useEffect } from 'react';
import { useParams, Link, useLocation } from 'react-router-dom';
import { ArrowLeft, Download, Copy, Check, Sparkles, BookOpen, AlertTriangle, Building2, Calendar, DollarSign, Loader2 } from 'lucide-react';
import { useGrants } from '../context/GrantContext';
import { fetchApplications, triggerDraft } from '../services/api';

export default function GrantDetailPage() {
  const { id } = useParams();
  const location = useLocation();
  const { getGrantById, refreshGrants } = useGrants();
  
  const grant = getGrantById(id);
  const [draft, setDraft] = useState(null);
  const [loadingDraft, setLoadingDraft] = useState(true);
  const [isDrafting, setIsDrafting] = useState(false);
  const [draftError, setDraftError] = useState(null);
  const [activeSectionIdx, setActiveSectionIdx] = useState(0);
  const [copied, setCopied] = useState(false);

  // Determine dynamic origin path and back button label
  const fromPath = location.state?.from || '/pipeline';
  
  const getBackLabel = (path) => {
    if (path === '/drafts') return 'BACK TO APPLICATION DRAFTS';
    if (path === '/') return 'BACK TO HOME';
    return 'BACK TO PIPELINE';
  };

  const backLabel = getBackLabel(fromPath);

  // Fetch drafted application for this grant from API
  useEffect(() => {
    const loadDraft = async () => {
      if (!grant) return;
      setLoadingDraft(true);
      try {
        const data = await fetchApplications();
        const grantId = grant.grant_id || grant.id;
        const matchingDraft = (data.applications || []).find(
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
      if (res.application) {
        setDraft(res.application);
      } else {
        // Refetch applications
        const appsData = await fetchApplications();
        const found = (appsData.applications || []).find(
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
        <Link to={fromPath} className="brutalist-btn btn-primary">
          <ArrowLeft size={18} /> {backLabel}
        </Link>
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

  return (
    <div className="page-container">
      {/* Top Dynamic Breadcrumb Bar */}
      <div style={{ marginBottom: '1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
        <Link to={fromPath} className="brutalist-btn btn-outline" style={{ padding: '0.4rem 0.85rem', fontSize: '0.9rem' }}>
          <ArrowLeft size={16} /> {backLabel}
        </Link>

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
      <div className="brutalist-card workstation-header-card" style={{ padding: '1.5rem 2rem', marginBottom: '1.75rem' }}>
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

      {/* Workstation 2-Column Responsive Layout */}
      <div className="workstation-container">
        {/* Left Column: 5-Dimension Rubric & Strengths */}
        <div className="brutalist-card" style={{ padding: '1.25rem' }}>
          {/* Fit Score Header */}
          <div style={{
            background: 'var(--card-alt-bg)',
            border: '2px solid var(--border-dark)',
            padding: '0.85rem 1rem',
            marginBottom: '1.25rem'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem', flexWrap: 'wrap', gap: '0.4rem' }}>
              <span className="font-heading" style={{ fontSize: '1.25rem' }}>FIT SCORE OVERVIEW</span>
              <span className={`tag-badge ${score.total >= 80 ? 'tag-amber' : 'tag-neutral'}`} style={{ fontSize: '0.85rem' }}>
                {score.total} / 100 {score.total >= 80 ? '• AUTO-DRAFT' : ''}
              </span>
            </div>
            <p style={{ fontSize: '0.78rem', color: 'var(--ink-muted)', lineHeight: '1.35' }}>
              Evaluated against organization profile and RAG-indexed filings.
            </p>
          </div>

          {/* 5-Dimension Progress Breakdown */}
          <h4 className="font-heading" style={{ fontSize: '1.1rem', marginBottom: '0.75rem', color: 'var(--ink)' }}>
            5-DIMENSION RUBRIC BREAKDOWN
          </h4>

          {[
            { label: 'Mission Alignment', score: score.mission_alignment || 0, max: 30 },
            { label: 'Eligibility Fit', score: score.eligibility_fit || 0, max: 25 },
            { label: 'Capacity Match', score: score.capacity_match || 0, max: 20 },
            { label: 'Geographic Fit', score: score.geographic_fit || 0, max: 15 },
            { label: 'Past Track Record', score: score.track_record || 0, max: 10 }
          ].map((dim, idx) => (
            <div key={idx} style={{ marginBottom: '0.85rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', fontWeight: 700, marginBottom: '0.2rem' }}>
                <span>{dim.label}</span>
                <span style={{ fontFamily: 'var(--font-mono)' }}>{dim.score} / {dim.max}</span>
              </div>
              <div style={{ height: '7px', background: '#E4E4E7', border: '1px solid var(--border-dark)' }}>
                <div style={{
                  height: '100%',
                  width: `${dim.max > 0 ? (dim.score / dim.max) * 100 : 0}%`,
                  backgroundColor: (dim.score / (dim.max || 1)) >= 0.8 ? 'var(--amber-signal)' : 'var(--ink)'
                }} />
              </div>
            </div>
          ))}

          {/* Key Strengths from Matcher Agent */}
          {grant.key_strengths && grant.key_strengths.length > 0 && (
            <>
              <hr className="dashed-divider" style={{ margin: '0.85rem 0' }} />
              <div style={{ fontSize: '0.8rem' }}>
                <div style={{ fontWeight: 700, marginBottom: '0.35rem', textTransform: 'uppercase' }}>
                  Key Strengths:
                </div>
                <ul style={{ paddingLeft: '1.1rem', color: 'var(--ink-muted)', lineHeight: '1.45', fontSize: '0.78rem' }}>
                  {grant.key_strengths.map((s, idx) => (
                    <li key={idx}>{s}</li>
                  ))}
                </ul>
              </div>
            </>
          )}

          {/* Potential Risks */}
          {grant.potential_risks && grant.potential_risks.length > 0 && (
            <>
              <hr className="dashed-divider" style={{ margin: '0.85rem 0' }} />
              <div style={{ fontSize: '0.8rem' }}>
                <div style={{ fontWeight: 700, marginBottom: '0.35rem', textTransform: 'uppercase', color: 'var(--amber-signal)' }}>
                  Potential Considerations:
                </div>
                <ul style={{ paddingLeft: '1.1rem', color: 'var(--ink-muted)', lineHeight: '1.45', fontSize: '0.78rem' }}>
                  {grant.potential_risks.map((r, idx) => (
                    <li key={idx}>{r}</li>
                  ))}
                </ul>
              </div>
            </>
          )}
        </div>

        {/* Right Column: 6-Section Document Editor or Generation CTA */}
        <div className="brutalist-card" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {loadingDraft ? (
            <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--ink-muted)' }}>
              <Loader2 className="animate-spin" size={28} style={{ margin: '0 auto 0.75rem' }} />
              <div>Loading application draft status...</div>
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
                        padding: '0.75rem 1rem',
                        fontSize: '0.92rem',
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
                <div className="workstation-editor-pane" style={{ padding: '1.75rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem', flexWrap: 'wrap', gap: '0.4rem' }}>
                    <h3 className="font-heading" style={{ fontSize: '1.5rem', color: 'var(--ink)' }}>
                      {sections[activeSectionIdx].title}
                    </h3>
                    <span className="tag-badge tag-dark">
                      {sections[activeSectionIdx].word_count || sections[activeSectionIdx].content?.split(/\s+/).filter(Boolean).length || 0} WORDS
                    </span>
                  </div>

                  <textarea
                    value={sections[activeSectionIdx].content}
                    readOnly
                    style={{
                      width: '100%',
                      minHeight: '260px',
                      padding: '1rem',
                      fontSize: '0.9rem',
                      lineHeight: '1.6',
                      fontFamily: 'var(--font-body)',
                      color: 'var(--ink)',
                      backgroundColor: 'var(--canvas-bg)',
                      border: '2px solid var(--border-dark)',
                      boxShadow: '3px 3px 0px var(--border-dark)',
                      resize: 'vertical'
                    }}
                  />
                </div>
              )}
            </>
          ) : (
            /* No draft yet: Trigger Drafting Action */
            <div style={{ padding: '3rem 2rem', textAlign: 'center' }}>
              <Sparkles size={36} color="var(--amber-signal)" style={{ margin: '0 auto 1rem' }} />
              <h3 className="font-heading" style={{ fontSize: '1.8rem', color: 'var(--ink)', marginBottom: '0.5rem' }}>
                AUTONOMOUS PROPOSAL DRAFTER
              </h3>
              <p style={{ color: 'var(--ink-muted)', fontSize: '0.92rem', maxWidth: '480px', margin: '0 auto 1.5rem', lineHeight: '1.5' }}>
                Generate a multi-section proposal draft pre-populated with organization facts, budget calculations, and RAG-verified citations.
              </p>

              {draftError && (
                <div className="brutalist-card" style={{ padding: '0.75rem 1rem', marginBottom: '1.25rem', borderLeft: '4px solid #EF4444', maxWidth: '480px', margin: '0 auto 1.25rem' }}>
                  <div style={{ fontSize: '0.82rem', color: '#EF4444' }}>
                    {draftError}
                  </div>
                </div>
              )}

              <button
                onClick={handleGenerateDraft}
                disabled={isDrafting}
                className="brutalist-btn btn-primary"
                style={{ padding: '0.75rem 1.75rem', fontSize: '1rem' }}
              >
                {isDrafting ? 'GENERATING PROPOSAL DRAFT...' : 'GENERATE APPLICATION DRAFT'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
