import React, { useState } from 'react';
import GrantCard from '../components/GrantCard';
import { useGrants } from '../context/GrantContext';
import { FileText, CheckCircle2, Search, Sparkles } from 'lucide-react';

export default function DraftsPage() {
  const { grants } = useGrants();
  const [filterAgency, setFilterAgency] = useState('ALL');
  
  const draftedGrants = grants.filter(g => g.match_score?.total >= 80);

  const agencies = ['ALL', ...Array.from(new Set(draftedGrants.map(g => g.agency)))];

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

      {/* Grid of Draft Cards */}
      <div className="grants-grid">
        {displayedDrafts.map(grant => (
          <GrantCard key={grant.id} grant={grant} />
        ))}
      </div>
    </div>
  );
}
