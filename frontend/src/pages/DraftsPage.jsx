import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import GrantCard, { calculateFitScore } from '../components/GrantCard';
import { useGrants } from '../context/GrantContext';
import { FileText, CheckCircle2, Search, Sparkles, ArrowRight } from 'lucide-react';

export default function DraftsPage() {
  const { grants, isLoading } = useGrants();
  const [filterAgency, setFilterAgency] = useState('ALL');
  
  const draftedGrants = grants.filter(g => {
    const score = calculateFitScore(g);
    return score != null && score >= 80;
  });

  const agencies = ['ALL', ...Array.from(new Set(draftedGrants.map(g => g.agency).filter(Boolean)))];

  const displayedDrafts = draftedGrants.filter(g => {
    if (filterAgency === 'ALL') return true;
    return g.agency === filterAgency;
  });

  return (
    <div className="page-container">
      {/* Header Banner */}
      <div style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', flexWrap: 'wrap' }}>
          <span className="tag-badge tag-dark">AUTONOMOUS DRAFTER AGENT</span>
          <span className="tag-badge tag-green">
            <CheckCircle2 size={12} /> 6-SECTION PYDANTIC SCHEMA
          </span>
          <span className="tag-badge tag-amber">
            <Sparkles size={12} /> RAG CITATION VERIFIED
          </span>
        </div>

        <h1 className="font-heading hero-title" style={{ fontSize: '2.8rem', lineHeight: '0.95', color: 'var(--ink)' }}>
          PRE-FILLED PROPOSAL DRAFTS ({draftedGrants.length})
        </h1>
        <p style={{ color: 'var(--ink-muted)', fontSize: '0.95rem', marginTop: '0.4rem', maxWidth: '750px' }}>
          Opportunities scoring ≥80% fit are automatically pre-drafted across Executive Summary, Budget, Narrative, and Metrics sections. Click any card to enter the full-screen workstation editor.
        </p>
      </div>

      {/* Agency Filter Pills */}
      {agencies.length > 2 && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          flexWrap: 'wrap',
          marginBottom: '1.75rem',
          paddingBottom: '1rem',
          borderBottom: '1px solid var(--border-dashed)'
        }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--ink)', fontFamily: 'var(--font-mono)', marginRight: '0.5rem' }}>
            AGENCY:
          </span>
          {agencies.map(agency => (
            <button
              key={agency}
              onClick={() => setFilterAgency(agency)}
              className={`tag-badge ${filterAgency === agency ? 'tag-dark' : 'tag-neutral'}`}
              style={{ cursor: 'pointer', padding: '0.35rem 0.65rem', fontSize: '0.75rem' }}
            >
              {agency}
            </button>
          ))}
        </div>
      )}

      {/* Grid of Draft Cards or Empty State */}
      {isLoading ? (
        <div className="brutalist-card" style={{ padding: '3rem', textAlign: 'center' }}>
          <div className="font-heading" style={{ fontSize: '1.5rem', color: 'var(--ink-muted)' }}>
            LOADING APPLICATION DRAFTS...
          </div>
        </div>
      ) : draftedGrants.length === 0 ? (
        <div className="brutalist-card" style={{ padding: '3.5rem 2rem', textAlign: 'center' }}>
          <FileText size={36} color="var(--ink-muted)" style={{ margin: '0 auto 1rem' }} />
          <div className="font-heading" style={{ fontSize: '1.6rem', color: 'var(--ink)', marginBottom: '0.5rem' }}>
            NO APPLICATION DRAFTS PREPARED YET
          </div>
          <p style={{ color: 'var(--ink-muted)', fontSize: '0.92rem', maxWidth: '520px', margin: '0 auto 1.5rem', lineHeight: '1.5' }}>
            When grant opportunities achieve an autonomous match score of ≥80%, the Drafter Agent will automatically generate 6-section proposal packages.
          </p>
          <Link to="/pipeline" className="brutalist-btn btn-primary" style={{ padding: '0.65rem 1.4rem' }}>
            BROWSE ACTIVE PIPELINE <ArrowRight size={18} />
          </Link>
        </div>
      ) : (
        <div className="grants-grid">
          {displayedDrafts.map(grant => (
            <GrantCard key={grant.id || grant.grant_id} grant={grant} />
          ))}
        </div>
      )}
    </div>
  );
}
