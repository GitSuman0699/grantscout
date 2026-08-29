import React from 'react';
import MetricsBar from '../components/MetricsBar';
import GrantCard from '../components/GrantCard';
import MissionLoopBanner from '../components/MissionLoopBanner';
import { useGrants } from '../context/GrantContext';

export default function DashboardPage() {
  const { grants, sectorFilter, setSectorFilter } = useGrants();

  const filters = [
    { id: 'ALL', label: 'ALL OPPORTUNITIES' },
    { id: 'STEM', label: 'YOUTH & STEM' },
    { id: 'WORKFORCE', label: 'WORKFORCE & LITERACY' },
    { id: 'HIGH_FIT', label: 'AUTO-DRAFT READY (≥80)' }
  ];

  const filteredGrants = grants.filter(g => {
    if (sectorFilter === 'ALL') return true;
    if (sectorFilter === 'HIGH_FIT') return g.match_score?.total >= 80;
    return g.category === sectorFilter;
  });

  return (
    <div className="page-container">
      {/* 3-Step Autonomous Loop & Mission Strip */}
      <MissionLoopBanner />

      {/* Metrics Bar */}
      <MetricsBar stats={{ scanned: '78', matched: '14', drafts: '6', pipelineValue: '$1.45M' }} />

      {/* Pipeline Section Title */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-end',
        flexWrap: 'wrap',
        gap: '1rem',
        marginBottom: '1.25rem'
      }}>
        <div>
          <span className="tag-badge tag-dark" style={{ marginBottom: '0.4rem', display: 'inline-block' }}>
            LIVE FEDERAL PIPELINE
          </span>
          <h2 className="font-heading hero-title" style={{ fontSize: '2.5rem', lineHeight: '0.95', color: 'var(--ink)' }}>
            ACTIVE GRANT OPPORTUNITIES ({filteredGrants.length})
          </h2>
        </div>
      </div>

      {/* Filter Pills Bar */}
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

      {/* Grant Opportunity Grid */}
      <div className="grants-grid">
        {filteredGrants.map(grant => (
          <GrantCard key={grant.id} grant={grant} />
        ))}
      </div>
    </div>
  );
}
