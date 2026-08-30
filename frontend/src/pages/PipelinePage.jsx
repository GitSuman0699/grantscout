import React from 'react';
import MetricsBar from '../components/MetricsBar';
import GrantCard, { calculateFitScore } from '../components/GrantCard';
import { useGrants } from '../context/GrantContext';
import { Layers, Sparkles, AlertTriangle } from 'lucide-react';

export default function PipelinePage() {
  const { grants, dashboardStats, sectorFilter, setSectorFilter, isLoading } = useGrants();

  const highFitCount = grants.filter(g => {
    const score = calculateFitScore(g);
    return score != null && score >= 80;
  }).length;

  const filters = [
    { id: 'ALL', label: 'ALL OPPORTUNITIES' },
    { id: 'STEM', label: 'YOUTH & STEM' },
    { id: 'WORKFORCE', label: 'WORKFORCE & LITERACY' },
    { id: 'HIGH_FIT', label: 'AUTO-DRAFT READY (≥80)' }
  ];

  const filteredGrants = grants.filter(g => {
    if (sectorFilter === 'ALL') return true;
    if (sectorFilter === 'HIGH_FIT') {
      const score = calculateFitScore(g);
      return score != null && score >= 80;
    }
    return g.category === sectorFilter;
  });

  // Derive stats from API or grants array
  const stats = dashboardStats ? {
    scanned: String(dashboardStats.total_scanned ?? dashboardStats.grants_scanned ?? grants.length),
    matched: String(dashboardStats.high_fit_matches ?? highFitCount),
    drafts: String(dashboardStats.drafts_prepared ?? 0),
    pipelineValue: dashboardStats.pipeline_value || dashboardStats.total_pipeline_value || `$${(grants.reduce((sum, g) => sum + (g.award_ceiling || 0), 0) / 1000).toFixed(0)}K`,
  } : {
    scanned: String(grants.length),
    matched: String(highFitCount),
    drafts: '0',
    pipelineValue: `$${(grants.reduce((sum, g) => sum + (g.award_ceiling || 0), 0) / 1000).toFixed(0)}K`,
  };

  return (
    <div className="page-container">
      {/* Pipeline Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-end',
        flexWrap: 'wrap',
        gap: '1rem',
        marginBottom: '2rem'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.4rem' }}>
            <span className="tag-badge tag-dark">LIVE DISCOVERY ENGINE</span>
            <span className="tag-badge tag-green">GRANTS.GOV REST API</span>
          </div>

          <h1 className="font-heading hero-title" style={{ fontSize: '2.8rem', lineHeight: '0.95', color: 'var(--ink)' }}>
            GRANT PIPELINE WORKSPACE ({filteredGrants.length})
          </h1>
          <p style={{ color: 'var(--ink-muted)', fontSize: '0.95rem', marginTop: '0.4rem', maxWidth: '750px' }}>
            Federal funding opportunities scanned in the background, quantified against Youth Education Alliance across 5 rubric dimensions.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', fontWeight: 700, flexWrap: 'wrap' }}>
          <span style={{ color: 'var(--ink-muted)' }}>TARGET ORG:</span>
          <span className="tag-badge tag-amber">YOUTH EDUCATION ALLIANCE (501c3)</span>
        </div>
      </div>

      {/* Metrics Bar */}
      <MetricsBar stats={stats} />

      {/* Sector Filter Bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.6rem',
        flexWrap: 'wrap',
        marginBottom: '1.75rem',
        paddingBottom: '1rem',
        borderBottom: '1px solid var(--border-dashed)'
      }}>
        <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--ink)', fontFamily: 'var(--font-mono)', marginRight: '0.5rem' }}>
          FILTER SECTOR:
        </span>
        {filters.map(f => (
          <button
            key={f.id}
            onClick={() => setSectorFilter(f.id)}
            className={`tag-badge ${sectorFilter === f.id ? 'tag-dark' : 'tag-neutral'}`}
            style={{ cursor: 'pointer', padding: '0.4rem 0.75rem', fontSize: '0.75rem' }}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Grant Cards Grid or Empty State */}
      {isLoading ? (
        <div className="brutalist-card" style={{ padding: '3rem', textAlign: 'center' }}>
          <div className="font-heading" style={{ fontSize: '1.5rem', color: 'var(--ink-muted)' }}>
            LOADING PIPELINE DATA...
          </div>
          <p style={{ color: 'var(--ink-muted)', fontSize: '0.9rem', marginTop: '0.5rem' }}>
            Connecting to GrantScout backend API
          </p>
        </div>
      ) : filteredGrants.length === 0 ? (
        <div className="brutalist-card" style={{ padding: '3rem', textAlign: 'center' }}>
          <AlertTriangle size={32} color="var(--amber-signal)" style={{ marginBottom: '0.75rem' }} />
          <div className="font-heading" style={{ fontSize: '1.5rem', color: 'var(--ink)' }}>
            NO GRANTS AVAILABLE
          </div>
          <p style={{ color: 'var(--ink-muted)', fontSize: '0.9rem', marginTop: '0.5rem', maxWidth: '500px', margin: '0.5rem auto 0' }}>
            No federal opportunities match the current filter. Try running a Discovery Cycle or adjusting the sector filter above.
          </p>
        </div>
      ) : (
        <div className="grants-grid">
          {filteredGrants.map(grant => (
            <GrantCard key={grant.id || grant.grant_id} grant={grant} />
          ))}
        </div>
      )}
    </div>
  );
}
