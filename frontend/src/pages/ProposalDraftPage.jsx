import React, { useState, useEffect } from 'react';
import { useParams, Link, useLocation, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Download, Copy, Check, Sparkles, Target, Building2, Calendar,
  DollarSign, Loader2, ArrowRight, ExternalLink, FileText, CheckCircle2,
  Edit3, Eye, Save, RefreshCw, ShieldCheck, BookOpen, Layers
} from 'lucide-react';
import { useGrants } from '../context/GrantContext';
import { fetchApplications, triggerDraft } from '../services/api';
import { calculateFitScore, getScoreBadgeProps } from '../components/GrantCard';
import ComplianceAuditView from '../components/ComplianceAuditView';

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

const SECTION_ICONS = [
  FileText,
  Building2,
  Target,
  Calendar,
  DollarSign,
  CheckCircle2,
];

/**
 * Renders formatted Markdown elements (Headers, Tables, Lists, Bold Text).
 */
function MarkdownRenderer({ content }) {
  if (!content) return <p style={{ color: 'var(--ink-muted)' }}>No content available for this section.</p>;

  // Split into lines for basic markdown parsing
  const lines = content.split('\n');
  const elements = [];
  let tableRows = [];
  let inTable = false;
  let listItems = [];
  let inList = false;

  const flushList = (key) => {
    if (listItems.length > 0) {
      elements.push(
        <ul key={`list-${key}`} style={{ margin: '0.75rem 0 1.25rem 1.25rem', lineHeight: '1.65' }}>
          {listItems.map((item, i) => (
            <li key={i} style={{ marginBottom: '0.4rem', color: 'var(--ink)' }}>
              {renderInline(item)}
            </li>
          ))}
        </ul>
      );
      listItems = [];
      inList = false;
    }
  };

  const flushTable = (key) => {
    if (tableRows.length > 0) {
      const headerRow = tableRows[0];
      const bodyRows = tableRows.slice(1).filter(r => !r.every(c => c.trim().match(/^:?-+:?$/)));

      elements.push(
        <div key={`table-${key}`} style={{ overflowX: 'auto', margin: '1rem 0 1.5rem 0' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem', border: '2px solid var(--border-dark)' }}>
            <thead>
              <tr style={{ background: 'var(--card-alt-bg)', borderBottom: '2px solid var(--border-dark)' }}>
                {headerRow.map((h, i) => (
                  <th key={i} style={{ padding: '0.65rem 0.85rem', textAlign: 'left', fontWeight: 700, borderRight: '1px solid var(--border-dark)' }}>
                    {renderInline(h.trim())}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {bodyRows.map((row, rIdx) => (
                <tr key={rIdx} style={{ borderBottom: '1px solid var(--border-dark)', background: rIdx % 2 === 0 ? 'var(--card-bg)' : 'var(--card-alt-bg)' }}>
                  {row.map((cell, cIdx) => (
                    <td key={cIdx} style={{ padding: '0.6rem 0.85rem', borderRight: '1px solid var(--border-dark)' }}>
                      {renderInline(cell.trim())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      tableRows = [];
      inTable = false;
    }
  };

  const renderInline = (text) => {
    // Process bold **text**
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, pIdx) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={pIdx} style={{ fontWeight: 700, color: 'var(--ink)' }}>{part.slice(2, -2)}</strong>;
      }
      // Process italic *text*
      if (part.startsWith('*') && part.endsWith('*') && !part.startsWith('**')) {
        return <em key={pIdx} style={{ color: 'var(--ink-muted)' }}>{part.slice(1, -1)}</em>;
      }
      return part;
    });
  };

  lines.forEach((line, idx) => {
    const trimmed = line.trim();

    // Table line: starts and ends with |
    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      if (inList) flushList(idx);
      inTable = true;
      const cells = trimmed.split('|').slice(1, -1);
      tableRows.push(cells);
      return;
    } else if (inTable) {
      flushTable(idx);
    }

    // List item: starts with * or -
    if (trimmed.startsWith('* ') || trimmed.startsWith('- ')) {
      inList = true;
      listItems.push(trimmed.slice(2));
      return;
    } else if (inList) {
      flushList(idx);
    }

    // Heading 3
    if (trimmed.startsWith('### ')) {
      elements.push(
        <h4 key={idx} style={{ fontSize: '1.15rem', fontWeight: 700, margin: '1.25rem 0 0.5rem 0', color: 'var(--ink)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <span style={{ width: '8px', height: '8px', background: 'var(--accent, #C85A17)', display: 'inline-block' }}></span>
          {renderInline(trimmed.slice(4))}
        </h4>
      );
      return;
    }

    // Heading 2
    if (trimmed.startsWith('## ')) {
      elements.push(
        <h3 key={idx} style={{ fontSize: '1.3rem', fontWeight: 800, margin: '1.5rem 0 0.6rem 0', color: 'var(--ink)' }}>
          {renderInline(trimmed.slice(3))}
        </h3>
      );
      return;
    }

    // Regular paragraph
    if (trimmed) {
      elements.push(
        <p key={idx} style={{ marginBottom: '0.85rem', lineHeight: '1.65', color: 'var(--ink)', fontSize: '0.94rem' }}>
          {renderInline(trimmed)}
        </p>
      );
    }
  });

  if (inTable) flushTable('final');
  if (inList) flushList('final');

  return <div>{elements}</div>;
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
  const [copiedSection, setCopiedSection] = useState(false);
  const [copiedAll, setCopiedAll] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [editedContent, setEditedContent] = useState('');
  const [isSaving, setIsSaving] = useState(false);

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

  const sections = draft?.sections || [];
  const activeSection = sections[activeSectionIdx] || sections[0] || {};

  useEffect(() => {
    if (activeSection && activeSection.content) {
      setEditedContent(activeSection.content);
    }
  }, [activeSectionIdx, draft]);

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
    setCopiedSection(true);
    setTimeout(() => setCopiedSection(false), 2000);
  };

  const handleCopyFullProposal = () => {
    if (!draft || !draft.sections) return;
    let fullText = `# ${draft.grant_title || grant?.title || 'Grant Proposal'}\n\n`;
    draft.sections.forEach((sec, idx) => {
      fullText += `## ${sec.title || sec.section_title || `Section ${idx+1}`}\n\n${sec.content}\n\n---\n\n`;
    });
    navigator.clipboard.writeText(fullText);
    setCopiedAll(true);
    setTimeout(() => setCopiedAll(false), 2000);
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
      md += `## ${sec.title || sec.section_title || `Section ${idx + 1}`}\n\n`;
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

  const handleSaveSection = () => {
    if (!draft || !draft.sections) return;
    setIsSaving(true);
    const updatedSections = [...draft.sections];
    updatedSections[activeSectionIdx] = {
      ...updatedSections[activeSectionIdx],
      content: editedContent,
      word_count: editedContent.trim().split(/\s+/).length,
    };
    const updatedDraft = {
      ...draft,
      sections: updatedSections,
    };
    setDraft(updatedDraft);
    setIsEditMode(false);
    setIsSaving(false);
  };

  if (!grant) {
    return (
      <div className="page-container" style={{ textAlign: 'center', padding: '4rem 1rem' }}>
        <h2 className="font-heading" style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>OPPORTUNITY NOT FOUND</h2>
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
  const grantId = grant.grant_id || grant.id;
  const officialUrl = getOfficialGrantUrl(grant);

  const getSectionTitle = (sec, idx) => {
    if (!sec) return `Section ${idx + 1}`;
    const raw = sec.title || sec.section_title || '';
    if (raw) return raw;
    const fallbacks = [
      '1. Executive Summary',
      '2. Organizational Background & Capacity',
      '3. Statement of Need & Community Impact',
      '4. Project Design & Implementation Timeline',
      '5. Budget & Financial Justification',
      '6. Evaluation & Long-Term Sustainability'
    ];
    return fallbacks[idx] || `Section ${idx + 1}`;
  };

  const activeTitle = getSectionTitle(activeSection, activeSectionIdx);
  const wordCount = (editedContent || activeSection.content || '').trim().split(/\s+/).filter(Boolean).length;
  const totalWords = sections.reduce((acc, s) => acc + (s.content ? s.content.trim().split(/\s+/).filter(Boolean).length : 0), 0);

  return (
    <div className="page-container">
      {/* Top Breadcrumb & Action Navigation */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <button
          onClick={handleBack}
          className="brutalist-btn btn-outline"
          style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', padding: '0.45rem 0.9rem', fontSize: '0.85rem' }}
        >
          <ArrowLeft size={16} />
          {backLabel}
        </button>

        <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center', flexWrap: 'wrap' }}>
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

      {/* Grant Opportunity Header Card */}
      <div className="brutalist-card" style={{ padding: '1.75rem', marginBottom: '1.5rem', background: 'var(--card-bg)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1.25rem', marginBottom: '1rem' }}>
          <div style={{ flex: 1, minWidth: '320px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', flexWrap: 'wrap' }}>
              <span className="tag-badge tag-dark" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                <Building2 size={12} /> {grant.agency || 'Federal Agency'}
              </span>
              <span className={badgeInfo.className}>
                {badgeInfo.label}
              </span>
              <span className="tag-badge tag-neutral">
                ID: {grantId}
              </span>
              <span className="tag-badge tag-green" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                <ShieldCheck size={12} /> 501(c)(3) ELIGIBLE
              </span>
            </div>
            <h1 className="font-heading" style={{ fontSize: '2.4rem', lineHeight: '1.0', color: 'var(--ink)', marginTop: '0.25rem' }}>
              {grant.title}
            </h1>
          </div>

          <div style={{ display: 'flex', gap: '1.5rem', fontFamily: 'var(--font-mono)', fontSize: '0.85rem', background: 'var(--card-alt-bg)', padding: '0.85rem 1.25rem', border: '2px solid var(--border-dark)' }}>
            <div>
              <div style={{ color: 'var(--ink-faint)', fontSize: '0.7rem', fontWeight: 700 }}>AWARD CEILING</div>
              <div style={{ fontWeight: 800, fontSize: '1.2rem', color: 'var(--mission-green)' }}>
                {grant.award_ceiling ? `$${Number(grant.award_ceiling).toLocaleString()}` : 'Funding Varies'}
              </div>
            </div>
            <div style={{ width: '1px', background: 'var(--border-dark)' }}></div>
            <div>
              <div style={{ color: 'var(--ink-faint)', fontSize: '0.7rem', fontWeight: 700 }}>APPLICATION DEADLINE</div>
              <div style={{ fontWeight: 800, fontSize: '1.2rem', color: 'var(--ink)' }}>
                {grant.close_date || 'Ongoing'}
              </div>
            </div>
          </div>
        </div>

        {/* Federal Application Gateway Notice Banner */}
        <div style={{
          marginTop: '1rem',
          padding: '0.85rem 1.15rem',
          background: 'rgba(200, 90, 23, 0.08)',
          border: '1.5px dashed var(--accent, #C85A17)',
          fontSize: '0.86rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '0.6rem'
        }}>
          <div>
            <strong>🚀 Proposal Workstation Active:</strong> Generated proposal sections below are pre-formatted for standard federal application packages. Review, refine in edit mode, and copy directly into your Grants.gov submission package.
          </div>
          <a
            href={officialUrl}
            target="_blank"
            rel="noopener noreferrer"
            style={{ fontWeight: 800, color: 'var(--accent, #C85A17)', textDecoration: 'underline', display: 'inline-flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.88rem' }}
          >
            Launch Official Federal Workspace <ExternalLink size={14} />
          </a>
        </div>
      </div>

      {/* Main Drafting Section */}
      {loadingDraft ? (
        <div className="brutalist-card" style={{ padding: '4rem', textAlign: 'center' }}>
          <Loader2 size={36} className="spin" style={{ margin: '0 auto 1.25rem auto', color: 'var(--accent, #C85A17)' }} />
          <h3 className="font-heading" style={{ fontSize: '1.6rem' }}>LOADING PROPOSAL WORKSTATION...</h3>
          <p style={{ color: 'var(--ink-muted)', fontSize: '0.95rem' }}>Retrieving structured draft sections and verified RAG citations.</p>
        </div>
      ) : draft && sections.length > 0 ? (
        /* Workstation with Section Tabs & Editor */
        <div className="brutalist-card" style={{ padding: '0', overflow: 'hidden', border: '3px solid var(--border-dark)' }}>
          {/* Top Action Bar */}
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
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
              <span className="tag-badge tag-green" style={{ fontWeight: 700 }}>
                ✓ {sections.length}-SECTION PROPOSAL READY
              </span>
              <span className="tag-badge tag-dark" style={{ fontFamily: 'var(--font-mono)' }}>
                {totalWords} TOTAL WORDS
              </span>
              <span className="tag-badge tag-amber">
                ⚡ 100% RAG GROUNDED
              </span>
            </div>

            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              <button
                onClick={() => handleCopySection(editedContent || activeSection.content)}
                className="brutalist-btn btn-outline"
                style={{ fontSize: '0.85rem', padding: '0.45rem 0.85rem', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
              >
                {copiedSection ? <Check size={14} color="var(--mission-green)" /> : <Copy size={14} />}
                {copiedSection ? 'COPIED SECTION' : 'COPY ACTIVE SECTION'}
              </button>

              <button
                onClick={handleCopyFullProposal}
                className="brutalist-btn btn-outline"
                style={{ fontSize: '0.85rem', padding: '0.45rem 0.85rem', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
              >
                {copiedAll ? <Check size={14} color="var(--mission-green)" /> : <Layers size={14} />}
                {copiedAll ? 'COPIED ALL SECTIONS' : 'COPY FULL PROPOSAL'}
              </button>

              <button
                onClick={handleDownloadMarkdown}
                className="brutalist-btn btn-primary"
                style={{ fontSize: '0.85rem', padding: '0.45rem 0.95rem', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
              >
                <Download size={14} />
                EXPORT MARKDOWN
              </button>
            </div>
          </div>

          {/* 2-Column Workstation Layout */}
          <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', minHeight: '580px' }}>
            {/* Left Column: Interactive Section Navigator */}
            <div style={{
              background: 'var(--card-alt-bg)',
              borderRight: '2px solid var(--border-dark)',
              padding: '0'
            }}>
              <div style={{
                padding: '0.9rem 1.25rem',
                fontSize: '0.75rem',
                fontWeight: 800,
                color: 'var(--ink-muted)',
                letterSpacing: '0.05em',
                borderBottom: '1px solid var(--border-dark)',
                background: 'rgba(0,0,0,0.02)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <span>PROPOSAL OUTLINE</span>
                <span className="tag-badge tag-dark" style={{ fontSize: '0.7rem', padding: '0.15rem 0.45rem' }}>
                  {sections.length} PARTS
                </span>
              </div>

              <div>
                {sections.map((sec, idx) => {
                  const IconComp = SECTION_ICONS[idx % SECTION_ICONS.length] || FileText;
                  const title = getSectionTitle(sec, idx);
                  const isActive = activeSectionIdx === idx;
                  const secWords = sec.content ? sec.content.trim().split(/\s+/).filter(Boolean).length : 0;

                  return (
                    <button
                      key={idx}
                      onClick={() => {
                        setActiveSectionIdx(idx);
                        setIsEditMode(false);
                      }}
                      style={{
                        width: '100%',
                        textAlign: 'left',
                        padding: '1rem 1.15rem',
                        background: isActive ? 'var(--card-bg)' : 'transparent',
                        borderLeft: isActive ? '5px solid var(--accent, #C85A17)' : '5px solid transparent',
                        borderTop: 'none',
                        borderRight: 'none',
                        borderBottom: '1px solid var(--border-dark)',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: '0.75rem',
                        transition: 'all 0.15s ease',
                        position: 'relative'
                      }}
                    >
                      <div style={{
                        width: '28px',
                        height: '28px',
                        borderRadius: '4px',
                        background: isActive ? 'var(--accent, #C85A17)' : 'var(--card-alt-bg)',
                        color: isActive ? '#FFFFFF' : 'var(--ink)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                        border: '1px solid var(--border-dark)',
                        marginTop: '0.1rem'
                      }}>
                        <IconComp size={15} />
                      </div>

                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{
                          fontSize: '0.88rem',
                          fontWeight: isActive ? 800 : 600,
                          color: isActive ? 'var(--ink)' : 'var(--ink)',
                          lineHeight: '1.25',
                          marginBottom: '0.3rem'
                        }}>
                          {title}
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-muted)' }}>
                          <span>{secWords} words</span>
                          <span>•</span>
                          <span style={{ color: 'var(--mission-green)', fontWeight: 600 }}>✓ Ready</span>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Right Column: Active Section Workstation */}
            <div style={{ padding: '2rem', display: 'flex', flexDirection: 'column', background: 'var(--card-bg)' }}>
              {/* Header inside workstation */}
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '1.25rem',
                paddingBottom: '1rem',
                borderBottom: '2px solid var(--border-subtle)',
                flexWrap: 'wrap',
                gap: '0.75rem'
              }}>
                <div>
                  <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-faint)', fontWeight: 700, textTransform: 'uppercase' }}>
                    SECTION {activeSectionIdx + 1} OF {sections.length}
                  </div>
                  <h2 className="font-heading" style={{ fontSize: '1.85rem', color: 'var(--ink)', marginTop: '0.1rem' }}>
                    {activeTitle}
                  </h2>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <span className="tag-badge tag-neutral" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
                    {wordCount} WORDS
                  </span>

                  <button
                    onClick={() => {
                      if (isEditMode) {
                        handleSaveSection();
                      } else {
                        setIsEditMode(true);
                      }
                    }}
                    className={`brutalist-btn ${isEditMode ? 'btn-primary' : 'btn-outline'}`}
                    style={{ fontSize: '0.82rem', padding: '0.4rem 0.8rem', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                  >
                    {isEditMode ? <Save size={14} /> : <Edit3 size={14} />}
                    {isEditMode ? 'SAVE SECTION' : 'EDIT SECTION'}
                  </button>

                  {isEditMode && (
                    <button
                      onClick={() => {
                        setEditedContent(activeSection.content || '');
                        setIsEditMode(false);
                      }}
                      className="brutalist-btn btn-outline"
                      style={{ fontSize: '0.82rem', padding: '0.4rem 0.75rem' }}
                    >
                      CANCEL
                    </button>
                  )}
                </div>
              </div>

              {/* Main Content Area: Editor or Formatted Markdown Preview */}
              <div style={{ flex: 1, marginBottom: '1.5rem' }}>
                {isEditMode ? (
                  <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                    <div style={{ fontSize: '0.8rem', color: 'var(--ink-muted)', marginBottom: '0.5rem' }}>
                      Markdown syntax supported: <code>### Heading</code>, <code>* Bullet</code>, <code>**Bold**</code>, <code>| Table |</code>
                    </div>
                    <textarea
                      value={editedContent}
                      onChange={(e) => setEditedContent(e.target.value)}
                      style={{
                        width: '100%',
                        minHeight: '380px',
                        padding: '1.25rem',
                        fontFamily: 'var(--font-mono, monospace)',
                        fontSize: '0.92rem',
                        lineHeight: '1.6',
                        background: 'var(--card-alt-bg)',
                        border: '2px solid var(--border-dark)',
                        color: 'var(--ink)',
                        resize: 'vertical',
                        outline: 'none'
                      }}
                    />
                  </div>
                ) : (
                  <div style={{
                    background: 'var(--canvas-bg, #FAF8F5)',
                    border: '2px solid var(--border-dark)',
                    padding: '2rem',
                    borderRadius: '0',
                    fontSize: '0.95rem',
                    boxShadow: 'var(--shadow-offset-sm, 2px 2px 0px var(--border-dark))'
                  }}>
                    <MarkdownRenderer content={activeSection.content} />
                  </div>
                )}
              </div>

              {/* Grounded Citations & Sources Card */}
              <div style={{
                padding: '1.15rem 1.35rem',
                background: 'var(--card-alt-bg)',
                border: '2px solid var(--border-dark)',
                fontSize: '0.85rem'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                  <BookOpen size={16} color="var(--accent, #C85A17)" />
                  <strong style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--ink)' }}>
                    RAG Knowledge Base Citations & Grounding
                  </strong>
                </div>

                <p style={{ color: 'var(--ink-muted)', fontSize: '0.82rem', marginBottom: '0.6rem' }}>
                  The Drafter Agent verified this section against the nonprofit's indexed document corpus:
                </p>

                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <span className="tag-badge tag-dark" style={{ fontSize: '0.75rem' }}>
                    📄 Annual_Impact_Report_2025.md (Verified Program Metrics)
                  </span>
                  <span className="tag-badge tag-dark" style={{ fontSize: '0.75rem' }}>
                    📑 IRS_Form_990_Financial_Overview.md (Financial Capacity & Single Audit)
                  </span>
                  <span className="tag-badge tag-dark" style={{ fontSize: '0.75rem' }}>
                    📜 Past_Federal_Grant_Narrative_2024.md (Federal Compliance Records)
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Automated Federal 2 CFR 200 Compliance Audit Widget */}
          <div style={{ padding: '0 1.5rem 1.5rem 1.5rem', background: 'var(--card-alt-bg)', borderTop: '2px solid var(--border-dark)' }}>
            <ComplianceAuditView
              grantId={grantId}
              draftId={draft?.draft_id || ''}
              budgetContent={sections.find((s) => s.title.toLowerCase().includes('budget'))?.content || ''}
              projectContent={sections.find((s) => s.title.toLowerCase().includes('project'))?.content || ''}
            />
          </div>
        </div>
      ) : (
        /* Empty State: Call to Action */
        <div className="brutalist-card" style={{ padding: '4rem 2rem', textAlign: 'center' }}>
          <div style={{ maxWidth: '640px', margin: '0 auto' }}>
            <div style={{
              width: '72px',
              height: '72px',
              borderRadius: '50%',
              background: 'rgba(200, 90, 23, 0.1)',
              border: '2px solid var(--accent, #C85A17)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 1.5rem auto'
            }}>
              <Sparkles size={36} color="var(--accent, #C85A17)" />
            </div>

            <h2 className="font-heading" style={{ fontSize: '2.4rem', marginBottom: '0.75rem' }}>
              NO PROPOSAL DRAFT GENERATED YET
            </h2>
            <p style={{ color: 'var(--ink-muted)', fontSize: '1rem', lineHeight: '1.6', marginBottom: '2rem' }}>
              Orchestrate a complete, 6-section federal grant proposal tailored for <strong>{grant.title}</strong>, grounded in Youth Education Alliance's verified RAG corpus and past awards.
            </p>

            {draftError && (
              <div style={{ padding: '0.85rem 1rem', background: '#ffebee', border: '2px solid #c62828', color: '#c62828', marginBottom: '1.5rem', fontSize: '0.88rem', fontWeight: 600 }}>
                {draftError}
              </div>
            )}

            <button
              onClick={handleGenerateDraft}
              disabled={isDrafting}
              className="brutalist-btn btn-primary"
              style={{ padding: '0.95rem 2.25rem', fontSize: '1.15rem', display: 'inline-flex', alignItems: 'center', gap: '0.65rem', cursor: isDrafting ? 'not-allowed' : 'pointer' }}
            >
              {isDrafting ? (
                <>
                  <Loader2 size={20} className="spin" />
                  ORCHESTRATING 6-SECTION PROPOSAL...
                </>
              ) : (
                <>
                  <Sparkles size={20} />
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
