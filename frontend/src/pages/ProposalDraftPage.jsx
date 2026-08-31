import React, { useState, useEffect } from 'react';
import { useParams, Link, useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft, Download, Copy, Check, Sparkles, Target, Building2, Calendar, DollarSign, Loader2, ArrowRight, ExternalLink } from 'lucide-react';
import { useGrants } from '../context/GrantContext';
import { fetchApplications, triggerDraft } from '../services/api';
import { calculateFitScore, getScoreBadgeProps } from '../components/GrantCard';

/**
 * Returns the direct official URL to the federal opportunity / application portal.
 * Any numeric opportunity ID maps directly to its official Grants.gov notice.
 */
export function getOfficialGrantUrl(grant) {
  if (!grant) return 'https://www.grants.gov/search-grants';
  if (grant.application_url) return grant.application_url;
  if (grant.additional_info_url) return grant.additional_info_url;
  if (grant.url) return grant.url;

  const id = String(grant.grant_id || grant.id || '');
  const numMatch = id.replace('grants-gov-', '').trim();

  // If there's a numeric opportunity ID, link directly to its live official Grants.gov page
  if (/^\d+$/.test(numMatch)) {
    return `https://www.grants.gov/search-results-detail/${numMatch}`;
  }

  // Otherwise, link to live Grants.gov search
  if (grant.title) {
    const cleanTitle = grant.title.replace(/&amp;/g, '&').replace(/&ndash;/g, '-').replace(/&quot;/g, '"');
    return `https://www.grants.gov/search-grants?keywords=${encodeURIComponent(cleanTitle)}`;
  }

  return 'https://www.grants.gov/search-grants';
}

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

  // Preserve clean root origin: either '/pipeline', '/drafts', or '/'
  const rawFrom = location.state?.from || '';
  const fromPath = (rawFrom === '/drafts' || rawFrom === '/' || rawFrom === '/pipeline') 
    ? rawFrom 
    : '/pipeline';

  const getBackLabel = (path) => {
    if (path === '/drafts') return 'BACK TO APPLICATION DRAFTS';
    if (path === '/') return 'BACK TO HOME';
    return 'BACK TO PIPELINE';
  };

  const backLabel = getBackLabel(fromPath);

  const handleBack = () => {
    navigate(fromPath);
  };

  useEffect(() => {
    async function loadDraft() {
      if (!grant) {
        setLoadingDraft(false);
        return;
      }
      setLoadingDraft(true);
      setDraftError(null);
      try {
        const appsData = await fetchApplications();
        const appsList = Array.isArray(appsData) ? appsData : (appsData?.applications || []);
        const grantId = grant.grant_id || grant.id;
        const matchingApp = appsList.find(a => (a.grant_id === grantId || a.id === grantId));
        if (matchingApp) {
          setDraft(matchingApp);
        } else {
          setDraft(null);
        }
      } catch (err) {
        console.error('Failed to fetch draft:', err);
      } finally {
        setLoadingDraft(false);
      }
    }
    loadDraft();
  }, [grant, id]);

  const handleGenerateDraft = async () => {
    if (!grant) return;
    setIsDrafting(true);
    setDraftError(null);
    try {
      const grantId = grant.grant_id || grant.id;
      const res = await triggerDraft(grantId);
      if (res && res.application) {
        setDraft(res.application);
      } else if (res && res.sections) {
        setDraft(res);
      } else {
        const appsData = await fetchApplications();
        const appsList = Array.isArray(appsData) ? appsData : (appsData?.applications || []);
        const updated = appsList.find(a => (a.grant_id === grantId || a.id === grantId));
        if (updated) setDraft(updated);
      }
      if (refreshGrants) refreshGrants();
    } catch (err) {
      console.error('Drafting failed:', err);
      setDraftError(err.message || 'Failed to generate draft proposal.');
    } finally {
      setIsDrafting(false);
    }
  };

  const handleCopySection = (content) => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadMarkdown = () => {
    if (!draft || !draft.sections) return;
    const docTitle = draft.grant_title || grant?.title || 'Grant_Proposal_Draft';
    let md = `# Grant Proposal Draft: ${docTitle}\n\n`;
    md += `**Target Grant ID**: ${draft.grant_id || grant?.grant_id}\n`;
    md += `**Generated**: ${draft.generated_at || new Date().toISOString()}\n`;
    md += `**Completeness**: ${draft.completion_percentage || 100}%\n\n`;
    md += `---\n\n`;

    draft.sections.forEach((sec, idx) => {
      md += `## Section ${idx + 1}: ${sec.section_title}\n\n`;
      md += `${sec.content}\n\n`;
      if (sec.citations && sec.citations.length > 0) {
        md += `*Sources & Citations:*\n`;
        sec.citations.forEach(c => {
          md += `- ${c}\n`;
        });
        md += `\n`;
      }
      md += `---\n\n`;
    });

    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${docTitle.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_draft.md`;
    link.click();
    URL.revokeObjectURL(url);
  };

  if (!grant) {
    return (
      <div className="brutalist-card" style={{ padding: '3rem', textAlign: 'center' }}>
        <h2 className="font-heading" style={{ fontSize: '2rem', marginBottom: '1rem' }}>OPPORTUNITY NOT FOUND</h2>
        <p style={{ color: 'var(--ink-muted)', marginBottom: '1.5rem' }}>
          No grant opportunity was found matching ID: <code>{id}</code>.
        </p>
        <button onClick={handleBack} className="brutalist-btn btn-outline">
          <ArrowLeft size={16} />
          {backLabel}
        </button>
      </div>
    );
  }

  const fitScore = calculateFitScore(grant);
  const badgeInfo = getScoreBadgeProps(fitScore);
  const sections = draft?.sections || [];
  const activeSection = sections[activeSectionIdx] || sections[0];
  const grantId = grant.grant_id || grant.id;
  const officialUrl = getOfficialGrantUrl(grant);

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2.5rem 1.5rem 5rem 1.5rem' }}>
      {/* Top Breadcrumb Navigation */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <button
          onClick={handleBack}
          className="brutalist-btn btn-outline"
          style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', padding: '0.45rem 0.9rem', fontSize: '0.85rem' }}
        >
          <ArrowLeft size={16} />
          {backLabel}
        </button>

        <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center' }}>
          <a
            href={officialUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="brutalist-btn btn-outline"
            style={{ fontSize: '0.85rem', padding: '0.45rem 0.9rem', display: 'inline-flex', alignItems: 'center', gap: '0.4rem', color: 'var(--ink)' }}
            title="Open official opportunity page in Grants.gov"
          >
            <ExternalLink size={15} />
            OPEN IN GRANTS.GOV ↗
          </a>

          <Link
            to={`/rubrics/${grantId}`}
            state={{ from: fromPath }}
            className="brutalist-btn btn-outline"
            style={{ fontSize: '0.85rem', padding: '0.45rem 0.9rem', display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
          >
            <Target size={15} />
            INSPECT 5-DIMENSION RUBRIC
          </Link>
        </div>
      </div>

      {/* Grant Opportunity Header Banner */}
      <div className="brutalist-card" style={{ padding: '1.5rem', marginBottom: '1.5rem', background: 'var(--card-bg)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '0.75rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.4rem' }}>
              <span className="tag-badge tag-dark" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                <Building2 size={12} /> {grant.agency || 'Federal Agency'}
              </span>
              <span className={badgeInfo.className}>
                {badgeInfo.label}
              </span>
              <span className="tag-badge tag-neutral">
                ID: {grantId}
              </span>
            </div>
            <h1 className="font-heading" style={{ fontSize: '2.2rem', lineHeight: '1.05', color: 'var(--ink)' }}>
              {grant.title}
            </h1>
          </div>

          <div style={{ display: 'flex', gap: '1.25rem', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
            <div>
              <div style={{ color: 'var(--ink-faint)', fontSize: '0.7rem' }}>AWARD CEILING</div>
              <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>
                {grant.award_ceiling ? `$${(grant.award_ceiling).toLocaleString()}` : 'Funding Varies'}
              </div>
            </div>
            <div>
              <div style={{ color: 'var(--ink-faint)', fontSize: '0.7rem' }}>DEADLINE</div>
              <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>
                {grant.close_date || 'Ongoing'}
              </div>
            </div>
          </div>
        </div>

        {/* Federal Application Gateway Notice */}
        <div style={{
          marginTop: '1rem',
          padding: '0.75rem 1rem',
          background: 'rgba(255, 107, 0, 0.06)',
          border: '1px dashed var(--accent)',
          fontSize: '0.82rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '0.5rem'
        }}>
          <div>
            <strong>💡 Ready to Submit?</strong> Review and refine your generated proposal sections below, copy or export to Markdown, and paste into the official application form on Grants.gov.
          </div>
          <a
            href={officialUrl}
            target="_blank"
            rel="noopener noreferrer"
            style={{ fontWeight: 700, color: 'var(--accent)', textDecoration: 'underline', display: 'inline-flex', alignItems: 'center', gap: '0.2rem' }}
          >
            Launch Official Form Portal <ExternalLink size={13} />
          </a>
        </div>
      </div>

      {/* Main Drafting Section */}
      {loadingDraft ? (
        <div className="brutalist-card" style={{ padding: '3.5rem', textAlign: 'center' }}>
          <Loader2 size={32} className="spin" style={{ margin: '0 auto 1rem auto', color: 'var(--accent)' }} />
          <h3 className="font-heading" style={{ fontSize: '1.4rem' }}>LOADING PROPOSAL WORKSTATION...</h3>
          <p style={{ color: 'var(--ink-muted)', fontSize: '0.9rem' }}>Retrieving structured draft sections from local storage.</p>
        </div>
      ) : draft && sections.length > 0 ? (
        /* Workstation with Section Tabs & Editor */
        <div className="brutalist-card" style={{ padding: '0', overflow: 'hidden' }}>
          {/* Action Toolbar */}
          <div style={{
            padding: '1rem 1.5rem',
            background: 'var(--card-alt-bg)',
            borderBottom: '2px solid var(--border-dark)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '0.75rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className="tag-badge tag-green">✓ 6-SECTION SCHEMA READY</span>
              <span style={{ fontSize: '0.85rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-muted)' }}>
                {draft.completion_percentage || 100}% AUTO-COMPLETED
              </span>
            </div>

            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                onClick={() => handleCopySection(activeSection.content)}
                className="brutalist-btn btn-outline"
                style={{ fontSize: '0.85rem', padding: '0.45rem 0.85rem' }}
              >
                {copied ? <Check size={14} /> : <Copy size={14} />}
                {copied ? 'COPIED SECTION' : 'COPY SECTION'}
              </button>

              <button
                onClick={handleDownloadMarkdown}
                className="brutalist-btn btn-primary"
                style={{ fontSize: '0.85rem', padding: '0.45rem 0.85rem' }}
              >
                <Download size={14} />
                EXPORT FULL MARKDOWN
              </button>
            </div>
          </div>

          {/* 2-Column Section Layout */}
          <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', minHeight: '520px' }}>
            {/* Left Column: Section Index */}
            <div style={{
              background: 'var(--card-alt-bg)',
              borderRight: '2px solid var(--border-dark)',
              padding: '1rem 0'
            }}>
              <div style={{ padding: '0 1rem 0.75rem 1rem', fontSize: '0.75rem', fontWeight: 700, color: 'var(--ink-faint)' }}>
                PROPOSAL SECTIONS ({sections.length})
              </div>
              {sections.map((sec, idx) => (
                <button
                  key={idx}
                  onClick={() => setActiveSectionIdx(idx)}
                  style={{
                    width: '100%',
                    textAlign: 'left',
                    padding: '0.85rem 1rem',
                    background: activeSectionIdx === idx ? 'var(--card-bg)' : 'transparent',
                    borderLeft: activeSectionIdx === idx ? '4px solid var(--accent)' : '4px solid transparent',
                    borderTop: 'none',
                    borderRight: 'none',
                    borderBottom: '1px solid var(--border-dark)',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.2rem',
                    transition: 'all 0.1s ease'
                  }}
                >
                  <div style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-faint)', fontWeight: 600 }}>
                    SECTION {idx + 1}
                  </div>
                  <div style={{ fontSize: '0.9rem', fontWeight: activeSectionIdx === idx ? 700 : 500, color: 'var(--ink)' }}>
                    {sec.section_title}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--ink-muted)', fontFamily: 'var(--font-mono)' }}>
                    {sec.word_count || (sec.content ? sec.content.split(/\s+/).length : 0)} words
                  </div>
                </button>
              ))}
            </div>

            {/* Right Column: Active Section Viewer */}
            <div style={{ padding: '2rem', display: 'flex', flexDirection: 'column' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
                <h3 className="font-heading" style={{ fontSize: '1.6rem', color: 'var(--ink)' }}>
                  {activeSectionIdx + 1}. {activeSection.section_title}
                </h3>
                <span className="tag-badge tag-dark" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
                  {activeSection.content ? activeSection.content.split(/\s+/).length : 0} WORDS
                </span>
              </div>

              <div style={{
                background: 'var(--card-alt-bg)',
                border: '2px solid var(--border-dark)',
                padding: '1.5rem',
                fontSize: '0.95rem',
                lineHeight: '1.65',
                whiteSpace: 'pre-wrap',
                fontFamily: 'system-ui, -apple-system, sans-serif',
                color: 'var(--ink)',
                flex: 1,
                marginBottom: '1.5rem'
              }}>
                {activeSection.content}
              </div>

              {/* Citations & Evidence Base */}
              {activeSection.citations && activeSection.citations.length > 0 && (
                <div style={{
                  padding: '1rem',
                  background: 'var(--card-bg)',
                  border: '1px solid var(--border-dark)',
                  fontSize: '0.82rem'
                }}>
                  <strong style={{ color: 'var(--ink-faint)', fontSize: '0.72rem', textTransform: 'uppercase' }}>
                    RAG Knowledge Base Citations & Grounding:
                  </strong>
                  <ul style={{ margin: '0.4rem 0 0 1.2rem', padding: 0 }}>
                    {activeSection.citations.map((c, cIdx) => (
                      <li key={cIdx} style={{ color: 'var(--ink-muted)', marginBottom: '0.2rem' }}>
                        {c}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        /* Empty State: Pre-fill Call to Action */
        <div className="brutalist-card" style={{ padding: '3.5rem', textAlign: 'center' }}>
          <div style={{ maxWidth: '600px', margin: '0 auto' }}>
            <div style={{
              width: '64px',
              height: '64px',
              borderRadius: '50%',
              background: 'rgba(255, 107, 0, 0.1)',
              border: '2px solid var(--accent)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 1.5rem auto'
            }}>
              <Sparkles size={32} color="var(--accent)" />
            </div>

            <h2 className="font-heading" style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>
              NO PROPOSAL DRAFT CREATED YET
            </h2>
            <p style={{ color: 'var(--ink-muted)', fontSize: '0.95rem', lineHeight: '1.5', marginBottom: '2rem' }}>
              Generate a complete, 6-section grant proposal grounded in Youth Education Alliance's RAG knowledge corpus, structured budget figures, and proven track record.
            </p>

            {draftError && (
              <div style={{ padding: '0.75rem', background: '#ffebee', border: '1px solid #c62828', color: '#c62828', marginBottom: '1.5rem', fontSize: '0.85rem' }}>
                {draftError}
              </div>
            )}

            <button
              onClick={handleGenerateDraft}
              disabled={isDrafting}
              className="brutalist-btn btn-primary"
              style={{ padding: '0.85rem 2rem', fontSize: '1.1rem', display: 'inline-flex', alignItems: 'center', gap: '0.6rem' }}
            >
              {isDrafting ? (
                <>
                  <Loader2 size={18} className="spin" />
                  ORCHESTRATING 6-SECTION PROPOSAL...
                </>
              ) : (
                <>
                  <Sparkles size={18} />
                  GENERATE APPLICATION DRAFT NOW
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
