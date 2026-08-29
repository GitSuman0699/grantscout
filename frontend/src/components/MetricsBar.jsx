import React from 'react';
import { Search, Target, FileText, DollarSign } from 'lucide-react';

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
    <div className="metrics-grid">
      {items.map((item, idx) => {
        const Icon = item.icon;
        return (
          <div
            key={idx}
            className="brutalist-card metric-card-inner"
            style={{
              padding: '1.25rem 1.5rem',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              position: 'relative'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem' }}>
              <span className="tag-badge tag-dark" style={{ fontSize: '0.68rem', padding: '0.2rem 0.45rem' }}>
                {item.badge}
              </span>
              <div style={{
                background: 'var(--card-alt-bg)',
                padding: '0.35rem',
                border: '1px solid var(--border-dark)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <Icon size={16} strokeWidth={2} />
              </div>
            </div>

            <div>
              <div className="font-heading metric-card-value" style={{ fontSize: '2.5rem', lineHeight: '1', color: 'var(--ink)', marginBottom: '0.25rem' }}>
                {item.value}
              </div>
              <div className="metric-card-label" style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--ink-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                {item.label}
              </div>
            </div>

            <div className="metric-card-meta">
              <hr className="dashed-divider" style={{ margin: '0.75rem 0' }} />
              <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-muted)' }}>
                {item.meta}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
