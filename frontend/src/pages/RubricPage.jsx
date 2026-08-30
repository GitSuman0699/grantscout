import React from 'react';
import { useParams, Link, useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft, Target, Sparkles, BookOpen, AlertTriangle, Building2, Calendar, DollarSign, ArrowRight } from 'lucide-react';
import { useGrants } from '../context/GrantContext';

export default function RubricPage() {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { getGrantById } = useGrants();

  const grant = getGrantById(id);
  const fromPath = location.state?.from || '/pipeline';

  const getBackLabel = (path) => {
    if (path === '/drafts') return 'BACK TO APPLICATION DRAFTS';
    if (path === '/') return 'BACK TO HOME';
    return 'BACK TO PIPELINE';
  };

  const backLabel = getBackLabel(fromPath);

  const handleBack = () => {
    if (window.history.state && window.history.state.idx > 0) {
      navigate(-1);
    } else {
      navigate(fromPath);
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
        <button onClick={handleBack} className="brutalist-btn btn-primary">
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

  const grantId = grant.grant_id || grant.id;

  return (
    <div className="page-container">
      {/* Top Breadcrumb Bar */}
      <div style={{ marginBottom: '1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
        <button onClick={handleBack} className="brutalist-btn btn-outline" style={{ padding: '0.45rem 0.95rem', fontSize: '0.9rem', cursor: 'pointer' }}>
          <ArrowLeft size={16} /> {backLabel}
        </button>

        <Link
          to={`/drafts/${grantId}`}
          state={{ from: location.pathname }}
          className="brutalist-btn btn-primary"
          style={{ padding: '0.45rem 1.15rem', fontSize: '0.95rem' }}
        >
          <Sparkles size={16} /> OPEN PROPOSAL DRAFT <ArrowRight size={16} />
        </Link>
      </div>

      {/* Grant Overview Header Card */}
      <div className="brutalist-card workstation-header-card" style={{ padding: '1.75rem 2rem', marginBottom: '1.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.5rem', flexWrap: 'wrap' }}>
          <span className="tag-badge tag-dark">5-DIMENSION RUBRIC INSPECTOR</span>
          <span className={`tag-badge ${score.total >= 80 ? 'tag-amber' : 'tag-neutral'}`}>
            {score.total}% FIT SCORE
          </span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--ink-muted)' }}>
            {grant.agency || 'Federal Agency'} • ID: {grantId}
          </span>
        </div>

        <h1 className="font-heading workstation-title" style={{ fontSize: '2.6rem', lineHeight: '1.05', color: 'var(--ink)', marginBottom: '0.65rem' }}>
          {grant.title}
        </h1>

        <p style={{ color: 'var(--ink-muted)', fontSize: '0.92rem', lineHeight: '1.5', maxWidth: '960px' }}>
          {grant.synopsis || 'Federal grant opportunity evaluated across Mission Alignment, Eligibility, Organizational Capacity, Geographic Target, and Historical Track Record.'}
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

      {/* Main Rubric Inspection Card */}
      <div className="brutalist-card" style={{ padding: '2rem', marginBottom: '2rem' }}>
        {/* Total Score Banner */}
        <div style={{
          background: 'var(--card-alt-bg)',
          border: '2px solid var(--border-dark)',
          padding: '1.25rem 1.5rem',
          marginBottom: '2rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem'
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
              <Target size={20} color="var(--amber-signal)" />
              <span className="font-heading" style={{ fontSize: '1.6rem', color: 'var(--ink)' }}>
                OVERALL MATCH ASSESSMENT
              </span>
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--ink-muted)', margin: 0 }}>
              Evaluated by Matcher Agent against Youth Education Alliance profile & IRS Form 990 financials.
            </p>
          </div>

          <div style={{ textAlign: 'right' }}>
            <div className="font-heading" style={{ fontSize: '2.8rem', lineHeight: '1', color: 'var(--ink)' }}>
              {score.total} <span style={{ fontSize: '1.4rem', color: 'var(--ink-muted)' }}>/ 100</span>
            </div>
            <span className={`tag-badge ${score.total >= 80 ? 'tag-amber' : 'tag-neutral'}`} style={{ fontSize: '0.78rem' }}>
              {score.total >= 80 ? 'AUTO-DRAFT RECOMMENDED' : 'MANUAL REVIEW REQUIRED'}
            </span>
          </div>
        </div>

        {/* 5-Dimension Score Grid */}
        <h3 className="font-heading" style={{ fontSize: '1.6rem', marginBottom: '1.25rem', color: 'var(--ink)' }}>
          5-DIMENSION RUBRIC BREAKDOWN
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem', marginBottom: '2rem' }}>
          {[
            { label: 'Mission Alignment', score: score.mission_alignment || 0, max: 30, desc: 'Alignment with youth STEM education, coding curriculum, and equity focus.' },
            { label: 'Eligibility Fit', score: score.eligibility_fit || 0, max: 25, desc: 'Active 501(c)(3) status, SAM.gov registration, and non-profit classification.' },
            { label: 'Capacity Match', score: score.capacity_match || 0, max: 20, desc: 'Award ceiling alignment with $450K operating budget and instructional staff.' },
            { label: 'Geographic Fit', score: score.geographic_fit || 0, max: 15, desc: 'Service area alignment across Metro Atlanta partner community centers.' },
            { label: 'Past Track Record', score: score.track_record || 0, max: 10, desc: 'Historical performance on past NSF awards (#24-9182 for $25,000 closed cleanly).' }
          ].map((dim, idx) => (
            <div key={idx} className="brutalist-card" style={{ padding: '1.25rem', background: 'var(--card-alt-bg)', border: '1px solid var(--border-dark)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', fontWeight: 800, marginBottom: '0.4rem' }}>
                <span>{dim.label}</span>
                <span style={{ fontFamily: 'var(--font-mono)' }}>{dim.score} / {dim.max}</span>
              </div>
              <div style={{ height: '8px', background: '#E4E4E7', border: '1px solid var(--border-dark)', marginBottom: '0.5rem' }}>
                <div style={{
                  height: '100%',
                  width: `${dim.max > 0 ? (dim.score / dim.max) * 100 : 0}%`,
                  backgroundColor: (dim.score / (dim.max || 1)) >= 0.8 ? 'var(--amber-signal)' : 'var(--ink)'
                }} />
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--ink-muted)', lineHeight: '1.4' }}>
                {dim.desc}
              </div>
            </div>
          ))}
        </div>

        {/* Alignment Strengths & Risk Factors */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
          {grant.key_strengths && grant.key_strengths.length > 0 && (
            <div style={{ background: '#FFFFFF', border: '2px solid var(--border-dark)', padding: '1.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <span className="tag-badge tag-green">VERIFIED FIT</span>
                <span style={{ fontWeight: 800, fontSize: '1rem', textTransform: 'uppercase' }}>Key Strengths</span>
              </div>
              <ul style={{ paddingLeft: '1.2rem', color: 'var(--ink)', lineHeight: '1.7', fontSize: '0.88rem' }}>
                {grant.key_strengths.map((s, idx) => (
                  <li key={idx} style={{ marginBottom: '0.4rem' }}>{s}</li>
                ))}
              </ul>
            </div>
          )}

          {grant.potential_risks && grant.potential_risks.length > 0 && (
            <div style={{ background: '#FFFFFF', border: '2px solid var(--border-dark)', padding: '1.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <span className="tag-badge tag-amber">REVIEW REQUIRED</span>
                <span style={{ fontWeight: 800, fontSize: '1rem', textTransform: 'uppercase' }}>Potential Considerations</span>
              </div>
              <ul style={{ paddingLeft: '1.2rem', color: 'var(--ink-muted)', lineHeight: '1.7', fontSize: '0.88rem' }}>
                {grant.potential_risks.map((r, idx) => (
                  <li key={idx} style={{ marginBottom: '0.4rem' }}>{r}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Bottom CTA to Jump to Draft */}
        <div style={{
          padding: '1.5rem',
          background: 'var(--card-alt-bg)',
          border: '2px solid var(--border-dark)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem'
        }}>
          <div>
            <div className="font-heading" style={{ fontSize: '1.4rem', color: 'var(--ink)' }}>
              NEXT STEP: PROPOSAL DRAFTING
            </div>
            <div style={{ fontSize: '0.85rem', color: 'var(--ink-muted)' }}>
              Proceed to the dedicated 6-section proposal workstation pre-populated with RAG citations.
            </div>
          </div>

          <Link
            to={`/drafts/${grantId}`}
            state={{ from: location.pathname }}
            className="brutalist-btn btn-primary"
            style={{ padding: '0.75rem 1.5rem', fontSize: '1rem' }}
          >
            <Sparkles size={16} /> OPEN PROPOSAL DRAFT WORKSTATION <ArrowRight size={16} />
          </Link>
        </div>
      </div>
    </div>
  );
}
