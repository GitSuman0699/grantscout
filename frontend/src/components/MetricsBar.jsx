import React from 'react';
import { Search, Target, FileText, DollarSign, TrendingUp } from 'lucide-react';

export default function MetricsBar({ stats }) {
  const items = [
    {
      label: 'GRANTS SCANNED',
      value: stats?.scanned || '78',
      meta: 'Grants.gov Live REST API',
      icon: Search,
      badge: 'AUTONOMOUS'
    },
    {
      label: 'HIGH FIT MATCHES',
      value: stats?.matched || '14',
      meta: '≥80% Rubric Threshold',
      icon: Target,
      badge: '5-DIMENSION'
    },
    {
      label: 'DRAFTS PREPARED',
      value: stats?.drafts || '6',
      meta: '6-Section Pydantic Schema',
      icon: FileText,
      badge: 'RAG ENHANCED'
    },
    {
      label: 'TOTAL PIPELINE VALUE',
      value: stats?.pipelineValue || '$1.45M',
      meta: 'Active Opportunities',
      icon: DollarSign,
      badge: 'FEDERAL CEILING'
    }
  ];

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
      gap: '1.25rem',
      marginBottom: '2rem'
    }}>
      {items.map((item, idx) => {
        const Icon = item.icon;
        return (
          <div
            key={idx}
            className="brutalist-card"
            style={{
              padding: '1.25rem 1.5rem',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              position: 'relative'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
              <span className="tag-badge tag-dark">{item.badge}</span>
              <div style={{
                background: 'var(--card-alt-bg)',
                padding: '0.4rem',
                border: '1px solid var(--border-dark)'
              }}>
                <Icon size={18} strokeWidth={2} />
              </div>
            </div>

            <div>
              <div className="font-heading" style={{ fontSize: '2.5rem', lineHeight: '1', color: 'var(--ink)', marginBottom: '0.25rem' }}>
                {item.value}
              </div>
              <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--ink-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                {item.label}
              </div>
            </div>

            <hr className="dashed-divider" style={{ margin: '0.75rem 0' }} />

            <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-muted)' }}>
              {item.meta}
            </div>
          </div>
        );
      })}
    </div>
  );
}
