import React from 'react';
import { NavLink, Link } from 'react-router-dom';
import { Compass, Zap, Activity } from 'lucide-react';
import { useGrants } from '../context/GrantContext';

export default function Header() {
  const { isScanning, runScanCycle } = useGrants();

  const navItems = [
    { to: '/', label: 'PIPELINE' },
    { to: '/drafts', label: 'APPLICATION DRAFTS' },
    { to: '/knowledge', label: 'RAG KNOWLEDGE BASE' },
    { to: '/optimization', label: 'COST OPTIMIZATION' }
  ];

  return (
    <header style={{
      borderBottom: '2px solid var(--border-dark)',
      backgroundColor: 'var(--card-bg)',
      position: 'sticky',
      top: 0,
      zIndex: 50,
      width: '100%'
    }}>
      {/* Top Banner Ticker */}
      <div className="ticker-bar" style={{
        backgroundColor: 'var(--ink)',
        color: 'var(--canvas-bg)',
        padding: '0.35rem 1.5rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        fontSize: '0.75rem',
        fontFamily: 'var(--font-mono)',
        overflowX: 'auto',
        whiteSpace: 'nowrap'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span className="live-indicator"></span>
          <span>STRANDS AGENTS SDK 1.52.0</span>
          <span>•</span>
          <span>AMAZON BEDROCK (CLAUDE SONNET 4.5 & HAIKU 4.5)</span>
          <span>•</span>
          <span>RAG HYBRID VECTOR SEARCH</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginLeft: '1rem' }}>
          <span style={{ color: '#22C55E' }}>● LIVE SYSTEM HEALTH: NORMAL</span>
          <span>PORT 8000</span>
        </div>
      </div>

      {/* Main Header Bar */}
      <div className="header-main-bar" style={{
        maxWidth: '1440px',
        margin: '0 auto',
        padding: '1rem 1.5rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        {/* Brand Wordmark */}
        <Link to="/" style={{ textDecoration: 'none', color: 'inherit', display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <div style={{
            background: 'var(--ink)',
            color: 'var(--canvas-bg)',
            width: '42px',
            height: '42px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: '2px solid var(--border-dark)',
            boxShadow: '2px 2px 0px var(--border-dark)',
            flexShrink: 0
          }}>
            <Compass size={24} strokeWidth={2.5} />
          </div>
          <div>
            <h1 className="font-heading" style={{ fontSize: '2.2rem', lineHeight: '1', color: 'var(--ink)' }}>
              GRANTSCOUT
            </h1>
            <p style={{ fontSize: '0.7rem', color: 'var(--ink-muted)', fontWeight: 700, letterSpacing: '0.05em' }}>
              AUTONOMOUS GRANT INTELLIGENCE & PROPOSAL PRE-FILL ENGINE
            </p>
          </div>
        </Link>

        {/* Navigation Links */}
        <nav className="nav-container">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `font-heading ${isActive ? 'active-nav' : ''}`}
              style={({ isActive }) => ({
                padding: '0.45rem 0.85rem',
                fontSize: '1rem',
                background: isActive ? 'var(--ink)' : 'transparent',
                color: isActive ? 'var(--canvas-bg)' : 'var(--ink)',
                border: '2px solid',
                borderColor: isActive ? 'var(--border-dark)' : 'transparent',
                boxShadow: isActive ? '2px 2px 0px var(--border-dark)' : 'none',
                cursor: 'pointer',
                textDecoration: 'none',
                transition: 'all 0.1s ease',
                whiteSpace: 'nowrap'
              })}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* Action Button */}
        <button
          onClick={runScanCycle}
          disabled={isScanning}
          className="brutalist-btn btn-amber"
          style={{ padding: '0.5rem 1.15rem', fontSize: '1rem' }}
        >
          {isScanning ? (
            <>
              <Activity className="animate-spin" size={16} />
              SCANNING GRANTS.GOV...
            </>
          ) : (
            <>
              <Zap size={16} />
              RUN DISCOVERY CYCLE
            </>
          )}
        </button>
      </div>
    </header>
  );
}
