import React from 'react';
import GrantCard from '../components/GrantCard';
import { useGrants } from '../context/GrantContext';
import { FileText, CheckCircle2 } from 'lucide-react';

export default function DraftsPage() {
  const { grants } = useGrants();
  const draftedGrants = grants.filter(g => g.match_score?.total >= 80);

  return (
    <div className="page-container">
      <div style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
          <span className="tag-badge tag-dark">AUTONOMOUS DRAFTER AGENT</span>
          <span className="tag-badge tag-green">
            <CheckCircle2 size={12} /> 6-SECTION PYDANTIC SCHEMA
          </span>
        </div>

        <h1 className="font-heading hero-title" style={{ fontSize: '2.8rem', lineHeight: '0.95', color: 'var(--ink)' }}>
          PRE-FILLED PROPOSAL DRAFTS ({draftedGrants.length})
        </h1>
        <p style={{ color: 'var(--ink-muted)', fontSize: '0.95rem', marginTop: '0.4rem', maxWidth: '750px' }}>
          Opportunities scoring ≥80% fit are automatically pre-drafted across Executive Summary, Budget, Narrative, and Metrics sections. Click any card to enter the full-screen workstation editor.
        </p>
      </div>

      <div className="grants-grid">
        {draftedGrants.map(grant => (
          <GrantCard key={grant.id} grant={grant} />
        ))}
      </div>
    </div>
  );
}
