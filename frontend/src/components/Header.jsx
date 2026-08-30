import React, { useState, useEffect } from 'react';
import { NavLink, Link, useLocation } from 'react-router-dom';
import { Compass, Zap, Activity, Menu, X, ChevronRight, ActivitySquare } from 'lucide-react';
import { useGrants } from '../context/GrantContext';

export default function Header() {
  const { isScanning, runScanCycle, systemHealth } = useGrants();
  const isHealthy = systemHealth === 'healthy';
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();

  // Auto-close mobile menu on route change
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  const navItems = [
    { to: '/', label: 'HOME', end: true },
    { to: '/pipeline', label: 'PIPELINE' },
    { to: '/drafts', label: 'APPLICATION DRAFTS' },
    { to: '/knowledge', label: 'RAG KNOWLEDGE BASE' },
    { to: '/optimization', label: 'COST OPTIMIZATION' }
  ];

  const tickerText = "STRANDS AGENTS SDK 1.52.0 • AMAZON BEDROCK (CLAUDE SONNET 4.5 & HAIKU 4.5) • RAG HYBRID VECTOR SEARCH • 5-DIMENSION RUBRIC SCORING • ZERO HALLUCINATION FORM 990 FACTS • GRANTS.GOV REST API • ";

  return (
    <header style={{
      borderBottom: '2px solid var(--border-dark)',
      backgroundColor: 'var(--card-bg)',
      position: 'sticky',
      top: 0,
      zIndex: 50,
      width: '100%'
    }}>
      {/* Top Banner Ticker with Fixed Live Health Badge on Right */}
      <div className="ticker-marquee-container" style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
        {/* Scrolling Track (Slides underneath the fixed badge) */}
        <div className="ticker-marquee-track font-mono" style={{ fontSize: '0.7rem', letterSpacing: '0.04em', zIndex: 1 }}>
          <span>{tickerText}&nbsp;&nbsp;&nbsp;&nbsp;</span>
          <span>{tickerText}&nbsp;&nbsp;&nbsp;&nbsp;</span>
          <span>{tickerText}&nbsp;&nbsp;&nbsp;&nbsp;</span>
          <span>{tickerText}&nbsp;&nbsp;&nbsp;&nbsp;</span>
        </div>

        {/* Fixed Right Live Health Status Badge — Compact & Sleek */}
        <div style={{
          position: 'absolute',
          right: 0,
          top: 0,
          bottom: 0,
          display: 'flex',
          alignItems: 'center',
          zIndex: 10,
          backgroundColor: 'var(--ink)',
          borderLeft: '1px solid rgba(255, 255, 255, 0.18)',
          paddingLeft: '0.5rem',
          paddingRight: '0.75rem'
        }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.35rem',
            // background: 'rgba(34, 197, 94, 0.15)',
            // border: '1px solid rgba(34, 197, 94, 0.4)',
            padding: '0.rem',
            borderRadius: '2px',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.68rem',
            fontWeight: 800,
            whiteSpace: 'nowrap'
          }}>
            <span className={isHealthy ? 'live-indicator' : ''} style={{ width: '6px', height: '6px', backgroundColor: isHealthy ? undefined : '#EF4444', borderRadius: '50%' }}></span>
            <span style={{ color: isHealthy ? '#22C55E' : '#EF4444', letterSpacing: '0.06em' }}>{isHealthy ? 'LIVE' : 'OFFLINE'}</span>
            <span className="desktop-only" style={{ color: '#A1A1AA', fontSize: '0.62rem', fontWeight: 600 }}>
              (PORT 8000)
            </span>
          </div>
        </div>
      </div>

      {/* Main Header Bar */}
      <div style={{
        maxWidth: '1440px',
        margin: '0 auto',
        padding: '0.85rem 1.5rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '1rem'
      }}>
        {/* Brand Logo: ONLY 'GRANTSCOUT' on mobile; full title on desktop */}
        <Link to="/" style={{ textDecoration: 'none', color: 'inherit', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
            background: 'var(--ink)',
            color: 'var(--canvas-bg)',
            width: '38px',
            height: '38px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: '2px solid var(--border-dark)',
            boxShadow: '2px 2px 0px var(--border-dark)',
            flexShrink: 0
          }}>
            <Compass size={22} strokeWidth={2.5} />
          </div>
          <div>
            <h1 className="font-heading" style={{ fontSize: '2rem', lineHeight: '1', color: 'var(--ink)' }}>
              GRANTSCOUT
            </h1>
            <p className="desktop-only" style={{ fontSize: '0.65rem', color: 'var(--ink-muted)', fontWeight: 700, letterSpacing: '0.05em' }}>
              AUTONOMOUS GRANT INTELLIGENCE & PROPOSAL PRE-FILL
            </p>
          </div>
        </Link>

        {/* Desktop Navigation Links — Hidden on Mobile */}
        <nav className="nav-container desktop-only">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
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

        {/* Desktop Action Button — Hidden on Mobile */}
        <button
          onClick={runScanCycle}
          disabled={isScanning}
          className="brutalist-btn btn-amber desktop-only"
          style={{ padding: '0.5rem 1.15rem', fontSize: '1rem' }}
        >
          {isScanning ? (
            <>
              <Activity className="animate-spin" size={16} />
              SCANNING...
            </>
          ) : (
            <>
              <Zap size={16} />
              RUN DISCOVERY CYCLE
            </>
          )}
        </button>

        {/* Mobile Hamburger Toggle Button — Hidden on Desktop */}
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="mobile-only brutalist-btn btn-outline"
          aria-label="Toggle navigation menu"
          style={{
            padding: '0.45rem 0.6rem',
            background: mobileMenuOpen ? 'var(--ink)' : 'var(--card-bg)',
            color: mobileMenuOpen ? 'var(--canvas-bg)' : 'var(--ink)'
          }}
        >
          {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Mobile Menu Drawer (Slide Down) */}
      {mobileMenuOpen && (
        <div style={{
          backgroundColor: 'var(--canvas-bg)',
          borderTop: '2px solid var(--border-dark)',
          borderBottom: '2px solid var(--border-dark)',
          padding: '1.25rem 1.5rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
          boxShadow: '0 8px 20px rgba(0,0,0,0.12)'
        }}>
          {/* Navigation Links inside Mobile Drawer */}
          <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                onClick={() => setMobileMenuOpen(false)}
                className="font-heading"
                style={({ isActive }) => ({
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '0.75rem 1rem',
                  fontSize: '1.15rem',
                  background: isActive ? 'var(--ink)' : '#FFFFFF',
                  color: isActive ? 'var(--canvas-bg)' : 'var(--ink)',
                  border: '2px solid var(--border-dark)',
                  boxShadow: '2px 2px 0px var(--border-dark)',
                  textDecoration: 'none'
                })}
              >
                <span>{item.label}</span>
                <ChevronRight size={18} />
              </NavLink>
            ))}
          </nav>

          {/* Action Button inside Mobile Drawer */}
          <button
            onClick={() => {
              runScanCycle();
              setMobileMenuOpen(false);
            }}
            disabled={isScanning}
            className="brutalist-btn btn-amber"
            style={{ width: '100%', padding: '0.75rem', fontSize: '1.15rem' }}
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
      )}
    </header>
  );
}
