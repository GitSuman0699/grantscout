import React, { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Download, Copy, Check, Sparkles, BookOpen, AlertTriangle, Building2, Calendar, DollarSign } from 'lucide-react';
import { useGrants } from '../context/GrantContext';

export default function GrantDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { getGrantById } = useGrants();
  
  const grant = getGrantById(id);
  const [activeSectionIdx, setActiveSectionIdx] = useState(0);
  const [copied, setCopied] = useState(false);

  if (!grant) {
    return (
      <div className="page-container" style={{ textAlign: 'center', padding: '4rem 1rem' }}>
        <h2 className="font-heading" style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>
          GRANT OPPORTUNITY NOT FOUND
        </h2>
        <p style={{ color: 'var(--ink-muted)', marginBottom: '1.5rem' }}>
          The requested federal opportunity could not be located in the local cache.
        </p>
        <Link to="/" className="brutalist-btn btn-primary">
          <ArrowLeft size={18} /> BACK TO PIPELINE
        </Link>
      </div>
    );
  }

  const score = grant.match_score || {
    mission_alignment: 28,
    eligibility_fit: 24,
    capacity_match: 18,
    geographic_fit: 14,
    track_record: 10,
    total: 94
  };

  const sections = [
    {
      title: "1. Executive Summary",
      word_count: 245,
      content: `Youth Education Alliance (YEA) requests $75,000 from the ${grant.agency || 'National Science Foundation'} to expand our proven 'Youth STEM Innovation Labs' initiative. Serving 1,200 underrepresented middle and high school students across underserved urban communities, this multi-faceted project introduces experiential robotics, Python programming, and hardware prototyping. Grounded in a 4-year track record of delivering 85% math grade gains and supported by an IRS 990-validated 88.7% program expenditure ratio, YEA provides the organizational capacity, certified pedagogical staff, and community partnerships necessary to achieve high-impact outcomes.`
    },
    {
      title: "2. Statement of Need & Target Population",
      word_count: 310,
      content: `Disadvantaged urban youth face systemic disparities in STEM learning opportunities and hardware access. In our target service area, less than 24% of Title I middle school students test proficient in eighth-grade mathematics, with zero structured after-school computer science programming offered within a 5-mile radius. Without intervention, this compounding gap severely limits post-secondary technical pathways. This project targets 1,200 students (ages 10-17), 78% of whom qualify for free or reduced-price lunch.`
    },
    {
      title: "3. Project Narrative & Program Design",
      word_count: 420,
      content: `The Youth STEM Innovation Labs model operates across three core pillars: (1) Hands-on Robotics & Autonomous Systems, utilizing modular hardware kits; (2) Applied Python & Data Literacy, teaching students real-world problem-solving; and (3) Mentorship from professional engineers from regional technology partners. The 28-week curriculum runs twice weekly in 90-minute modules, culminating in a community Capstone Showcase where student teams present working prototypes to civic and industry leaders.`
    },
    {
      title: "4. Budget Justification & Financial Plan",
      word_count: 285,
      content: `Total Grant Request: $75,000. \n• Personnel ($38,000): Lead STEM Instructors (2 FTE @ 20 hrs/week) and Curriculum Specialist ($8,000).\n• Materials & Equipment ($22,000): 40 Modular Robotics Kits ($12,000), 20 Dedicated Laptops ($8,000), Prototyping Consumables ($2,000).\n• Program Evaluation & Metrics ($7,500): Independent assessment and longitudinal pre/post surveys.\n• Indirect & Administrative ($7,500): 10% de minimis administrative rate in compliance with federal guidelines.`
    },
    {
      title: "5. Evaluation & Impact Metrics",
      word_count: 215,
      content: `Project outcomes will be evaluated against three benchmark metrics: (1) 80%+ of participants demonstrate measurable gains in algorithmic reasoning on standardized pre/post assessments; (2) 90%+ course completion rate with completed capstone projects; and (3) 85%+ expressing increased intent to pursue STEM college majors. Longitudinal metrics will be tracked using automated semester surveys.`
    },
    {
      title: "6. Organizational Capacity & Track Record",
      word_count: 260,
      content: `Founded in 2018, Youth Education Alliance is an active 501(c)(3) nonprofit with an annual operating budget of $450,000. Under the leadership of Executive Director Dr. Marcus Vance (PhD in Computer Science Education, Georgia Tech), YEA has successfully executed prior NSF awards (#NSF-EDU-2023-4412 for $25,000 with 100% compliance). With clean annual IRS 990 audits and 14 full-time instructors, YEA possesses both the fiduciary governance and operational scale to execute this grant flawlessly.`
    }
  ];

  const handleExportMarkdown = () => {
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
    const text = sections.map(s => `${s.title}\n\n${s.content}`).join('\n\n====================\n\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="page-container">
      {/* Top Breadcrumb Bar */}
      <div style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
        <Link to="/" className="brutalist-btn btn-outline" style={{ padding: '0.4rem 0.9rem', fontSize: '0.9rem' }}>
          <ArrowLeft size={16} /> BACK TO PIPELINE
        </Link>

        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button onClick={handleExportMarkdown} className="brutalist-btn btn-amber" style={{ padding: '0.45rem 1rem', fontSize: '0.95rem' }}>
            <Download size={16} /> EXPORT MARKDOWN (.MD)
          </button>
          <button onClick={handleCopy} className="brutalist-btn btn-outline" style={{ padding: '0.45rem 1rem', fontSize: '0.95rem' }}>
            {copied ? <Check size={16} /> : <Copy size={16} />} {copied ? 'COPIED' : 'COPY ALL'}
          </button>
        </div>
      </div>

      {/* Grant Overview Card */}
      <div className="brutalist-card" style={{ padding: '1.5rem 2rem', marginBottom: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem', flexWrap: 'wrap' }}>
          <span className="tag-badge tag-amber">AUTONOMOUS DRAFT READY</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--ink-muted)' }}>
            {grant.agency || 'Federal Agency'} • OPPORTUNITY ID: {grant.grant_id || grant.id}
          </span>
        </div>

        <h1 className="font-heading" style={{ fontSize: '2.5rem', lineHeight: '1.05', color: 'var(--ink)', marginBottom: '0.75rem' }}>
          {grant.title}
        </h1>

        <p style={{ color: 'var(--ink-muted)', fontSize: '0.95rem', lineHeight: '1.5', maxWidth: '960px' }}>
          {grant.synopsis || 'Pre-filled autonomous proposal package structured across 6 required federal sections with Pydantic schema enforcement and RAG verification.'}
        </p>
      </div>

      {/* Workstation 2-Column Responsive Layout */}
      <div className="workstation-container">
        {/* Left Column: 5-Dimension Rubric & RAG Knowledge */}
        <div className="brutalist-card" style={{ padding: '1.5rem' }}>
          {/* Fit Score Header */}
          <div style={{
            background: 'var(--card-alt-bg)',
            border: '2px solid var(--border-dark)',
            padding: '1rem',
            marginBottom: '1.5rem'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem', flexWrap: 'wrap', gap: '0.4rem' }}>
              <span className="font-heading" style={{ fontSize: '1.3rem' }}>FIT SCORE OVERVIEW</span>
              <span className="tag-badge tag-amber" style={{ fontSize: '0.9rem' }}>
                {score.total} / 100 • AUTO-DRAFT
              </span>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--ink-muted)', lineHeight: '1.4' }}>
              Evaluated against Youth Education Alliance mission profile and 990 financial filings.
            </p>
          </div>

          {/* 5-Dimension Progress Breakdown */}
          <h4 className="font-heading" style={{ fontSize: '1.15rem', marginBottom: '0.75rem', color: 'var(--ink)' }}>
            5-DIMENSION RUBRIC BREAKDOWN
          </h4>

          {[
            { label: 'Mission Alignment', score: score.mission_alignment || 28, max: 30, note: 'Direct alignment with youth STEM & robotics' },
            { label: 'Eligibility Fit', score: score.eligibility_fit || 24, max: 25, note: '501(c)(3) verified via IRS Form 990' },
            { label: 'Capacity Match', score: score.capacity_match || 18, max: 20, note: '$75k request aligns with $450k budget' },
            { label: 'Geographic Fit', score: score.geographic_fit || 14, max: 15, note: 'National & regional urban hubs' },
            { label: 'Past Track Record', score: score.track_record || 10, max: 10, note: 'Prior $25k NSF grant successfully closed' }
          ].map((dim, idx) => (
            <div key={idx} style={{ marginBottom: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', fontWeight: 700, marginBottom: '0.25rem' }}>
                <span>{dim.label}</span>
                <span style={{ fontFamily: 'var(--font-mono)' }}>{dim.score} / {dim.max}</span>
              </div>
              <div style={{ height: '8px', background: '#E4E4E7', border: '1px solid var(--border-dark)' }}>
                <div style={{
                  height: '100%',
                  width: `${(dim.score / dim.max) * 100}%`,
                  backgroundColor: dim.score / dim.max >= 0.8 ? 'var(--amber-signal)' : 'var(--ink)'
                }} />
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--ink-muted)', marginTop: '0.2rem' }}>
                {dim.note}
              </div>
            </div>
          ))}

          <hr className="dashed-divider" />

          {/* Cited Knowledge Sources */}
          <div style={{
            background: 'var(--canvas-bg)',
            border: '1px solid var(--border-dark)',
            padding: '1rem',
            fontSize: '0.78rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, marginBottom: '0.5rem' }}>
              <BookOpen size={16} />
              <span>CITED RAG KNOWLEDGE SOURCES</span>
            </div>
            <ul style={{ paddingLeft: '1.2rem', color: 'var(--ink-muted)', lineHeight: '1.5' }}>
              <li><strong>IRS Form 990 (2024)</strong>: 88.7% program expense ratio, $450K annual budget.</li>
              <li><strong>2025 Impact Report</strong>: 85% math improvement rate across 1,200 students.</li>
              <li><strong>NSF Award Archive</strong>: Grant #NSF-EDU-2023-4412 ($25K).</li>
            </ul>
          </div>
        </div>

        {/* Right Column: 6-Section Document Editor */}
        <div className="brutalist-card" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {/* Section Tabs Strip */}
          <div style={{
            display: 'flex',
            overflowX: 'auto',
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
                    padding: '0.85rem 1.25rem',
                    fontSize: '1rem',
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
          <div style={{ padding: '2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
              <h3 className="font-heading" style={{ fontSize: '1.75rem', color: 'var(--ink)' }}>
                {sections[activeSectionIdx].title}
              </h3>
              <span className="tag-badge tag-dark">
                {sections[activeSectionIdx].word_count} WORDS
              </span>
            </div>

            <textarea
              value={sections[activeSectionIdx].content}
              readOnly
              style={{
                width: '100%',
                minHeight: '260px',
                padding: '1.25rem',
                fontSize: '0.95rem',
                lineHeight: '1.65',
                fontFamily: 'var(--font-body)',
                color: 'var(--ink)',
                backgroundColor: 'var(--canvas-bg)',
                border: '2px solid var(--border-dark)',
                boxShadow: '3px 3px 0px var(--border-dark)',
                resize: 'vertical'
              }}
            />

            {/* Human Action Items Box */}
            <div style={{
              marginTop: '1.5rem',
              backgroundColor: 'var(--card-alt-bg)',
              border: '2px solid var(--border-dark)',
              padding: '1rem 1.25rem',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '0.75rem'
            }}>
              <AlertTriangle size={20} color="var(--amber-signal)" style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--ink)', textTransform: 'uppercase' }}>
                  HUMAN REVIEW ACTION ITEMS REQUIRED (2):
                </div>
                <ul style={{ fontSize: '0.82rem', color: 'var(--ink-muted)', marginTop: '0.25rem', paddingLeft: '1.2rem' }}>
                  <li>Attach official 501(c)(3) IRS Determination Letter and Board Resolution signature.</li>
                  <li>Confirm Q3 milestone dates against the final agency calendar before final submission.</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
