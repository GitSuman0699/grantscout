import React from 'react';
import { Compass, Zap, ShieldCheck, Sparkles, Activity } from 'lucide-react';

export default function Header({ activeTab, setActiveTab, onRunScan, isScanning }) {
  const navItems = [
    { id: 'pipeline', label: 'PIPELINE' },
    { id: 'drafts', label: 'APPLICATION DRAFTS' },
    { id: 'knowledge', label: 'RAG KNOWLEDGE BASE' },
    { id: 'optimization', label: 'COST OPTIMIZATION' }
  ];

  return (
    <header style={{
      borderBottom: '2px solid var(--border-dark)',
      backgroundColor: 'var(--card-bg)',
      position: 'sticky',
      top: 0,
      zIndex: 50
    }}>
      {/* Top Banner Ticker */}
      <div style={{
        backgroundColor: 'var(--ink)',
        color: 'var(--canvas-bg)',
        padding: '0.35rem 1.5rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        fontSize: '0.75rem',
        fontFamily: 'var(--font-mono)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span className="live-indicator"></span>
          <span>STRANDS AGENTS SDK 1.52.0</span>
          <span>•</span>
          <span>AMAZON BEDROCK (CLAUDE SONNET 4.5 & HAIKU 4.5)</span>
          <span>•</span>
          <span>RAG HYBRID VECTOR SEARCH</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <span style={{ color: '#22C55E' }}>● LIVE SYSTEM HEALTH: NORMAL</span>
          <span>API: PORT 8000</span>
        </div>
      </div>

      {/* Main Header Bar */}
      <div style={{
        maxWidth: '1440px',
        margin: '0 auto',
        padding: '1rem 2rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        {/* Brand Wordmark */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{
            background: 'var(--ink)',
            color: 'var(--canvas-bg)',
            width: '44px',
            height: '44px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: '2px solid var(--border-dark)',
            boxShadow: '2px 2px 0px var(--border-dark)'
          }}>
            <Compass size={26} strokeWidth={2.5} />
          </div>
          <div>
            <h1 className="font-heading" style={{ fontSize: '2.4rem', lineHeight: '1', color: 'var(--ink)' }}>
              GRANTSCOUT
            </h1>
            <p style={{ fontSize: '0.75rem', color: 'var(--ink-muted)', fontWeight: 600, letterSpacing: '0.05em' }}>
              AUTONOMOUS GRANT INTELLIGENCE & PROPOSAL PRE-FILL ENGINE
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className="font-heading"
                style={{
                  padding: '0.5rem 1rem',
                  fontSize: '1.05rem',
                  background: isActive ? 'var(--ink)' : 'transparent',
                  color: isActive ? 'var(--canvas-bg)' : 'var(--ink)',
                  border: '2px solid',
                  borderColor: isActive ? 'var(--border-dark)' : 'transparent',
                  boxShadow: isActive ? '2px 2px 0px var(--border-dark)' : 'none',
                  cursor: 'pointer',
                  transition: 'all 0.1s ease'
                }}
              >
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* Action Button */}
        <button
          onClick={onRunScan}
          disabled={isScanning}
          className="brutalist-btn btn-amber"
          style={{ padding: '0.55rem 1.25rem', fontSize: '1.05rem' }}
        >
          {isScanning ? (
            <>
              <Activity className="animate-spin" size={18} />
              SCANNING GRANTS.GOV...
            </>
          ) : (
            <>
              <Zap size={18} />
              RUN DISCOVERY CYCLE
            </>
          )}
        </button>
      </div>
    </header>
  );
}
