import React from 'react';
import { Cpu, DollarSign, Zap, Archive, Shield, CheckCircle2 } from 'lucide-react';

export default function OptimizationView() {
  const modelTiers = [
    {
      tier: 'FAST TIER',
      model: 'Claude Haiku 4.5',
      agents: 'Scanner Agent, Deadline Agent',
      costIn: '$0.0008 / 1K in',
      costOut: '$0.004 / 1K out',
      role: 'High-frequency opportunity filtering, Grants.gov pagination, and deadline date arithmetic.',
      speed: '<400ms'
    },
    {
      tier: 'STANDARD TIER',
      model: 'Claude Sonnet 4.5',
      agents: 'Matcher Agent, Orchestrator',
      costIn: '$0.003 / 1K in',
      costOut: '$0.015 / 1K out',
      role: '5-Dimension fit evaluation, 100-point rubric calculation, and Graph routing decisions.',
      speed: '~1,200ms'
    },
    {
      tier: 'PREMIUM TIER',
      model: 'Claude Sonnet 4.5 (8K Context)',
      agents: 'Drafter Agent (Narrative, Budget, Metrics)',
      costIn: '$0.003 / 1K in',
      costOut: '$0.015 / 1K out',
      role: 'Multi-section proposal drafting, financial plan calculations, and compliance verification.',
      speed: '~2,400ms'
    }
  ];

  return (
    <div>
      {/* Title Header */}
      <div style={{ marginBottom: '2rem' }}>
        <h2 className="font-heading" style={{ fontSize: '2.5rem', lineHeight: '1', color: 'var(--ink)' }}>
          COST & TOKEN OPTIMIZATION ENGINE
        </h2>
        <p style={{ color: 'var(--ink-muted)', fontSize: '0.95rem' }}>
          Intelligent model tiering, LRU response caching, and prompt compression ensuring sustainable, low-cost autonomous operation.
        </p>
      </div>

      {/* Summary Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1.25rem', marginBottom: '2.5rem' }}>
        <div className="brutalist-card" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <span className="tag-badge tag-green">ACTIVE CACHE</span>
            <Archive size={20} />
          </div>
          <div className="font-heading" style={{ fontSize: '2.5rem', lineHeight: '1' }}>
            82.4%
          </div>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--ink-muted)' }}>
            CACHE HIT RATE
          </div>
          <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-faint)', marginTop: '0.5rem' }}>
            LRU Cache with 1-Hour TTL (256 slots)
          </div>
        </div>

        <div className="brutalist-card" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <span className="tag-badge tag-amber">SAVINGS</span>
            <DollarSign size={20} />
          </div>
          <div className="font-heading" style={{ fontSize: '2.5rem', lineHeight: '1' }}>
            $0.0024
          </div>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--ink-muted)' }}>
            AVG COST PER MATCHED GRANT
          </div>
          <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-faint)', marginTop: '0.5rem' }}>
            ~88% cheaper than single-Opus setup
          </div>
        </div>

        <div className="brutalist-card" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <span className="tag-badge tag-dark">COMPRESSION</span>
            <Zap size={20} />
          </div>
          <div className="font-heading" style={{ fontSize: '2.5rem', lineHeight: '1' }}>
            -42%
          </div>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--ink-muted)' }}>
            INPUT TOKEN REDUCTION
          </div>
          <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-faint)', marginTop: '0.5rem' }}>
            Boilerplate stripping on Federal Synopses
          </div>
        </div>
      </div>

      {/* Model Tiers Table */}
      <div className="brutalist-card" style={{ padding: '1.75rem' }}>
        <h3 className="font-heading" style={{ fontSize: '1.75rem', marginBottom: '1.25rem' }}>
          TIERED MULTI-MODEL ROUTING CONFIGURATION
        </h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {modelTiers.map((t, idx) => (
            <div key={idx} style={{
              background: 'var(--card-alt-bg)',
              border: '2px solid var(--border-dark)',
              padding: '1.25rem',
              display: 'grid',
              gridTemplateColumns: '180px 1fr 220px',
              gap: '1.5rem',
              alignItems: 'center'
            }}>
              <div>
                <span className="tag-badge tag-dark" style={{ marginBottom: '0.4rem', display: 'inline-block' }}>{t.tier}</span>
                <div style={{ fontWeight: 800, fontSize: '1.05rem', color: 'var(--ink)' }}>{t.model}</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--ink-muted)', fontFamily: 'var(--font-mono)' }}>Latency: {t.speed}</div>
              </div>

              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--ink)', marginBottom: '0.2rem' }}>
                  Assigned Agents: {t.agents}
                </div>
                <div style={{ fontSize: '0.82rem', color: 'var(--ink-muted)', lineHeight: '1.4' }}>
                  {t.role}
                </div>
              </div>

              <div style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
                <div style={{ color: 'var(--ink)', fontWeight: 700 }}>{t.costIn}</div>
                <div style={{ color: 'var(--ink-muted)' }}>{t.costOut}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
