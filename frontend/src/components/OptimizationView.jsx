import React from 'react';
import { Cpu, DollarSign, Zap, Archive, Shield, CheckCircle2, Layers } from 'lucide-react';

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
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
          <span className="tag-badge tag-dark">COST EFFICIENCY ENGINE</span>
          <span className="tag-badge tag-green">
            <CheckCircle2 size={12} /> TIERED MODEL ROUTING
          </span>
        </div>

        <h1 className="font-heading hero-title" style={{ fontSize: '2.8rem', lineHeight: '0.95', color: 'var(--ink)' }}>
          COST & TOKEN OPTIMIZATION
        </h1>
        <p style={{ color: 'var(--ink-muted)', fontSize: '0.95rem', marginTop: '0.4rem', maxWidth: '750px' }}>
          Intelligent model tiering, LRU response caching, and prompt compression ensuring sustainable, low-cost autonomous operation.
        </p>
      </div>

      {/* Summary Cards Grid — Responsive */}
      <div className="opt-summary-grid">
        <div className="brutalist-card" style={{ padding: '1.25rem 1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span className="tag-badge tag-green">ACTIVE CACHE</span>
            <Archive size={18} />
          </div>
          <div className="font-heading" style={{ fontSize: '2.4rem', lineHeight: '1', color: 'var(--ink)' }}>
            82.4%
          </div>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--ink-muted)' }}>
            CACHE HIT RATE
          </div>
          <div style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-faint)', marginTop: '0.35rem' }}>
            LRU Cache with 1-Hour TTL (256 slots)
          </div>
        </div>

        <div className="brutalist-card" style={{ padding: '1.25rem 1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span className="tag-badge tag-amber">SAVINGS</span>
            <DollarSign size={18} />
          </div>
          <div className="font-heading" style={{ fontSize: '2.4rem', lineHeight: '1', color: 'var(--ink)' }}>
            $0.0024
          </div>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--ink-muted)' }}>
            AVG COST PER MATCHED GRANT
          </div>
          <div style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-faint)', marginTop: '0.35rem' }}>
            ~88% cheaper than single-Opus setup
          </div>
        </div>

        <div className="brutalist-card" style={{ padding: '1.25rem 1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span className="tag-badge tag-dark">COMPRESSION</span>
            <Zap size={18} />
          </div>
          <div className="font-heading" style={{ fontSize: '2.4rem', lineHeight: '1', color: 'var(--ink)' }}>
            -42%
          </div>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--ink-muted)' }}>
            INPUT TOKEN REDUCTION
          </div>
          <div style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-faint)', marginTop: '0.35rem' }}>
            Boilerplate stripping on Federal Synopses
          </div>
        </div>
      </div>

      {/* Model Tiers List — Responsive Card Stacking on Mobile */}
      <div className="brutalist-card" style={{ padding: '1.5rem' }}>
        <h3 className="font-heading" style={{ fontSize: '1.6rem', marginBottom: '1.25rem' }}>
          TIERED MULTI-MODEL ROUTING CONFIGURATION
        </h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {modelTiers.map((t, idx) => (
            <div key={idx} className="model-tier-row">
              {/* Left Column / Header */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.35rem' }}>
                  <span className="tag-badge tag-dark">{t.tier}</span>
                  <span className="tag-badge tag-neutral" style={{ fontSize: '0.68rem' }}>Latency: {t.speed}</span>
                </div>
                <div style={{ fontWeight: 800, fontSize: '1.1rem', color: 'var(--ink)' }}>{t.model}</div>
              </div>

              {/* Middle Column / Description */}
              <div>
                <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--ink)', marginBottom: '0.2rem' }}>
                  Assigned Agents: <span style={{ fontWeight: 500, color: 'var(--ink-muted)' }}>{t.agents}</span>
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--ink-muted)', lineHeight: '1.4' }}>
                  {t.role}
                </div>
              </div>

              {/* Right Column / Rates */}
              <div className="model-tier-rates" style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
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
