import React from 'react';
import { Link } from 'react-router-dom';
import MissionLoopBanner from '../components/MissionLoopBanner';
import MetricsBar from '../components/MetricsBar';
import { calculateFitScore } from '../components/GrantCard';
import { Compass, ArrowRight, ShieldCheck, Cpu, Database, Sparkles, Target, Zap, Clock } from 'lucide-react';
import { useGrants } from '../context/GrantContext';
import { formatAsOfDate } from '../utils/dateUtils';

export default function HomePage() {
  const { grants, dashboardStats } = useGrants();
  const asOfInfo = formatAsOfDate(dashboardStats?.last_scan, grants);
  const highFitCount = grants.filter(g => {
    const score = calculateFitScore(g);
    return score != null && score >= 80;
  }).length;

  // Derive stats from context
  const stats = dashboardStats ? {
    scanned: String(dashboardStats.grants_discovered ?? dashboardStats.total_scanned ?? dashboardStats.grants_scanned ?? grants.length),
    matched: String(dashboardStats.high_matches ?? dashboardStats.high_fit_matches ?? highFitCount),
    drafts: String(dashboardStats.applications_drafted ?? dashboardStats.drafts_prepared ?? 0),
    pipelineValue: dashboardStats.pipeline_value || dashboardStats.total_pipeline_value || `$${(grants.reduce((sum, g) => sum + (g.award_ceiling || 0), 0) / 1000).toFixed(0)}K`,
  } : {
    scanned: String(grants.length),
    matched: String(highFitCount),
    drafts: '0',
    pipelineValue: `$${(grants.reduce((sum, g) => sum + (g.award_ceiling || 0), 0) / 1000).toFixed(0)}K`,
  };

  return (
    <div className="page-container">
      {/* 3-Step Autonomous Loop & Mission Overview Banner */}
      <MissionLoopBanner />

      {/* Live System Metrics Quick Overview */}
      <div style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem', flexWrap: 'wrap' }}>
              <span className="tag-badge tag-dark">
                REAL-TIME AGENT TELEMETRY
              </span>
              <span className="tag-badge tag-green" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                <Clock size={12} /> GRANTS LISTED AS OF {asOfInfo.dateString}
              </span>
            </div>
            <h3 className="font-heading" style={{ fontSize: '2rem', lineHeight: '1', color: 'var(--ink)' }}>
              PIPELINE INTELLIGENCE OVERVIEW
            </h3>
          </div>

          <Link to="/pipeline" className="brutalist-btn btn-primary" style={{ padding: '0.55rem 1.25rem' }}>
            LAUNCH PIPELINE WORKSPACE <ArrowRight size={18} />
          </Link>
        </div>

        <MetricsBar stats={stats} />
      </div>

      {/* Feature Highlights Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        gap: '1.5rem',
        marginBottom: '2rem'
      }}>
        <div className="brutalist-card" style={{ padding: '1.5rem', background: '#FFFFFF' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <span className="tag-badge tag-dark">5-DIMENSION RUBRIC</span>
            <Target size={20} color="var(--amber-signal)" />
          </div>
          <h4 className="font-heading" style={{ fontSize: '1.4rem', marginBottom: '0.4rem' }}>
            MATCHER AGENT SCORING
          </h4>
          <p style={{ fontSize: '0.85rem', color: 'var(--ink-muted)', lineHeight: '1.5' }}>
            Quantifies fit across Mission (30), Eligibility (25), Capacity (20), Geography (15), and Track Record (10) with Pydantic schema validation.
          </p>
          <hr className="dashed-divider" />
          <Link to="/pipeline" style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--ink)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
            VIEW ACTIVE MATCHES →
          </Link>
        </div>

        <div className="brutalist-card" style={{ padding: '1.5rem', background: '#FFFFFF' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <span className="tag-badge tag-green">ZERO HALLUCINATION</span>
            <Database size={20} color="var(--mission-green)" />
          </div>
          <h4 className="font-heading" style={{ fontSize: '1.4rem', marginBottom: '0.4rem' }}>
            RAG KNOWLEDGE RETRIEVAL
          </h4>
          <p style={{ fontSize: '0.85rem', color: 'var(--ink-muted)', lineHeight: '1.5' }}>
            Indexes IRS 990 filings, 2025 impact reports, and past NSF proposals using Amazon Bedrock Titan Text Embeddings V2 for grounded citations.
          </p>
          <hr className="dashed-divider" />
          <Link to="/knowledge" style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--ink)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
            EXPLORE KNOWLEDGE BASE →
          </Link>
        </div>

        <div className="brutalist-card" style={{ padding: '1.5rem', background: '#FFFFFF' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <span className="tag-badge tag-amber">TIERED ROUTING</span>
            <Zap size={20} color="var(--amber-signal)" />
          </div>
          <h4 className="font-heading" style={{ fontSize: '1.4rem', marginBottom: '0.4rem' }}>
            COST & TOKEN OPTIMIZATION
          </h4>
          <p style={{ fontSize: '0.85rem', color: 'var(--ink-muted)', lineHeight: '1.5' }}>
            Routes high-volume scans to Claude Haiku 4.5 and proposal drafts to Sonnet 4.5 with LRU response caching to maximize AWS credit longevity.
          </p>
          <hr className="dashed-divider" />
          <Link to="/optimization" style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--ink)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
            VIEW COST METRICS →
          </Link>
        </div>
      </div>
    </div>
  );
}
