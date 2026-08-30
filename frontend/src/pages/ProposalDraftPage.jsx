import React, { useState, useEffect } from 'react';
import { useParams, Link, useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft, Download, Copy, Check, Sparkles, Target, Building2, Calendar, DollarSign, Loader2, ArrowRight } from 'lucide-react';
import { useGrants } from '../context/GrantContext';
import { fetchApplications, triggerDraft } from '../services/api';

export default function ProposalDraftPage() {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { getGrantById, refreshGrants } = useGrants();

  const grant = getGrantById(id);
  const [draft, setDraft] = useState(null);
  const [loadingDraft, setLoadingDraft] = useState(true);
  const [isDrafting, setIsDrafting] = useState(false);
  const [draftError, setDraftError] = useState(null);
  const [activeSectionIdx, setActiveSectionIdx] = useState(0);
  const [copied, setCopied] = useState(false);

  const fromPath = location.state?.from || '/drafts';

  const getBackLabel = (path) => {
    if (path.startsWith('/rubrics')) return 'BACK TO RUBRIC';
    if (path === '/pipeline') return 'BACK TO PIPELINE';
    if (path === '/') return 'BACK TO HOME';
    return 'BACK TO APPLICATION DRAFTS';
  };

  const backLabel = getBackLabel(fromPath);

  const handleBack = () => {
    if (window.history.state && window.history.state.idx > 0) {
      navigate(-1);
    } else {
      navigate(fromPath);
    }
  };

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
          GRANT APPLICATION NOT FOUND
        </h2>
        <p style={{ color: 'var(--ink-muted)', marginBottom: '1.5rem' }}>
          The requested proposal draft could not be located.
        </p>
        <button onClick={handleBack} className="brutalist-btn btn-primary">
          <ArrowLeft size={18} /> {backLabel}
        </button>
      </div>
    );
  }

  const score = grant.match_score || { total: 0 };
  const grantId = grant.grant_id || grant.id;
  const sections = draft?.sections && draft.sections.length > 0 ? draft.sections : [];

  const handleExportMarkdown = () => {
    if (sections.length === 0) return;
    const md = `# Grant Application Draft\n## ${grant.title}\n**Agency**: ${grant.agency}\n**Grant ID**: ${grantId}\n**Match Score**: ${score.total}/100\n\n---\n\n` +
      sections.map(s => `### ${s.title}\n\n${s.content}\n\n`).join('\n---\n\n');
    
    const blob = new Blob([md], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Application_Draft_${grantId.replace(/\s+/g, '_')}.md`;
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
      {/* Top Action Toolbar */}
      <div style={{ marginBottom: '1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
        <button onClick={handleBack} className="brutalist-btn btn-outline" style={{ padding: '0.45rem 0.95rem', fontSize: '0.9rem', cursor: 'pointer' }}>
          <ArrowLeft size={16} /> {backLabel}
        </button>

        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <Link
            to={`/rubrics/${grantId}`}
            state={{ from: location.pathname }}
            className="brutalist-btn btn-outline"
            style={{ padding: '0.45rem 1rem', fontSize: '0.95rem' }}
          >
            <Target size={16} /> INSPECT 5-DIMENSION RUBRIC ({score.total}/100)
          </Link>

          {sections.length > 0 && (
            <>
              <button onClick={handleExportMarkdown} className="brutalist-btn btn-amber" style={{ padding: '0.45rem 1rem', fontSize: '0.95rem' }}>
                <Download size={16} /> EXPORT .MD
              </button>
              <button onClick={handleCopy} className="brutalist-btn btn-outline" style={{ padding: '0.45rem 1rem', fontSize: '0.95rem' }}>
                {copied ? <Check size={16} /> : <Copy size={16} />} {copied ? 'COPIED' : 'COPY ALL'}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Header Banner */}
      <div className="brutalist-card workstation-header-card" style={{ padding: '1.75rem 2rem', marginBottom: '1.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.5rem', flexWrap: 'wrap' }}>
          <span className="tag-badge tag-green">6-SECTION PROPOSAL WORKSTATION</span>
          <span className="tag-badge tag-amber">
            RAG CITATION GROUNDED
          </span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--ink-muted)' }}>
            {grant.agency || 'Federal Agency'} • ID: {grantId}
          </span>
        </div>

        <h1 className="font-heading workstation-title" style={{ fontSize: '2.6rem', lineHeight: '1.05', color: 'var(--ink)', marginBottom: '0.65rem' }}>
          {grant.title}
        </h1>

        <p style={{ color: 'var(--ink-muted)', fontSize: '0.92rem', lineHeight: '1.5', maxWidth: '960px' }}>
          {grant.synopsis || 'Autonomous grant application draft pre-filled with verified 501(c)(3) organizational facts, budget calculations, and measurable outcomes.'}
        </p>

        {grant.award_ceiling && (
          <div style={{ display: 'flex', gap: '1rem', marginTop: '1.25rem', flexWrap: 'wrap', fontSize: '0.85rem' }}>
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

      {/* Main Proposal Editor Card */}
      <div className="brutalist-card" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden', padding: 0 }}>
        {loadingDraft ? (
          <div style={{ padding: '4rem 2rem', textAlign: 'center', color: 'var(--ink-muted)' }}>
            <Loader2 className="animate-spin" size={32} style={{ margin: '0 auto 1rem' }} />
            <div className="font-heading" style={{ fontSize: '1.5rem' }}>LOADING APPLICATION DRAFT...</div>
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
                      padding: '1rem 1.35rem',
                      fontSize: '1.05rem',
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

            {/* Active Section Content Pane */}
            {sections[activeSectionIdx] && (
              <div className="workstation-editor-pane" style={{ padding: '2rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div>
                    <span className="tag-badge tag-green" style={{ marginBottom: '0.35rem', display: 'inline-block' }}>
                      {sections[activeSectionIdx].is_auto_filled ? 'AUTONOMOUSLY PRE-FILLED (RAG GROUNDED)' : 'PYDANTIC SCHEMA ENFORCED'}
                    </span>
                    <h3 className="font-heading" style={{ fontSize: '1.9rem', color: 'var(--ink)', lineHeight: '1.1' }}>
                      {sections[activeSectionIdx].title}
                    </h3>
                  </div>

                  <span className="tag-badge tag-dark" style={{ fontSize: '0.82rem' }}>
                    {sections[activeSectionIdx].word_count || sections[activeSectionIdx].content?.split(/\s+/).filter(Boolean).length || 0} WORDS
                  </span>
                </div>

                <textarea
                  value={sections[activeSectionIdx].content}
                  readOnly
                  style={{
                    width: '100%',
                    minHeight: '380px',
                    padding: '1.25rem',
                    fontSize: '0.95rem',
                    lineHeight: '1.7',
                    fontFamily: 'var(--font-body)',
                    color: 'var(--ink)',
                    backgroundColor: 'var(--canvas-bg)',
                    border: '2px solid var(--border-dark)',
                    boxShadow: '3px 3px 0px var(--border-dark)',
                    resize: 'vertical'
                  }}
                />

                {/* Footer Section Navigation Info */}
                <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem', paddingTop: '1rem', borderTop: '1px dashed var(--border-dashed)' }}>
                  <div style={{ fontSize: '0.85rem', color: 'var(--ink-muted)' }}>
                    Section <strong>{activeSectionIdx + 1}</strong> of <strong>{sections.length}</strong> • Ready for staff review & submission
                  </div>

                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    {activeSectionIdx > 0 && (
                      <button
                        onClick={() => setActiveSectionIdx(prev => prev - 1)}
                        className="brutalist-btn btn-outline"
                        style={{ padding: '0.4rem 0.85rem', fontSize: '0.85rem' }}
                      >
                        ← PREVIOUS SECTION
                      </button>
                    )}
                    {activeSectionIdx < sections.length - 1 && (
                      <button
                        onClick={() => setActiveSectionIdx(prev => prev + 1)}
                        className="brutalist-btn btn-primary"
                        style={{ padding: '0.4rem 0.85rem', fontSize: '0.85rem' }}
                      >
                        NEXT SECTION →
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )}
          </>
        ) : (
          /* Empty / Trigger Drafter Agent State */
          <div style={{ padding: '4.5rem 2rem', textAlign: 'center' }}>
            <Sparkles size={44} color="var(--amber-signal)" style={{ margin: '0 auto 1.25rem' }} />
            <h3 className="font-heading" style={{ fontSize: '2.2rem', color: 'var(--ink)', marginBottom: '0.5rem' }}>
              AUTONOMOUS PROPOSAL DRAFTER
            </h3>
            <p style={{ color: 'var(--ink-muted)', fontSize: '0.95rem', maxWidth: '540px', margin: '0 auto 1.75rem', lineHeight: '1.6' }}>
              The Drafter Agent will construct a 6-section proposal package pre-populated with Youth Education Alliance organizational facts, audited financial ratios, and RAG citations.
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
              style={{ padding: '0.9rem 2.25rem', fontSize: '1.1rem' }}
            >
              {isDrafting ? 'GENERATING 6-SECTION PROPOSAL DRAFT...' : 'GENERATE APPLICATION DRAFT NOW'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
