import React from 'react';
import { Search, Target, Sparkles, ArrowRight, ShieldCheck, Cpu, Database } from 'lucide-react';

export default function MissionLoopBanner() {
  const steps = [
    {
      num: '01',
      agent: 'SCANNER AGENT',
      pattern: 'Workflow Pattern',
      title: 'FEDERAL DISCOVERY',
      desc: 'Continuously queries Grants.gov REST API using organizational keywords, eliminating duplicates in the background.',
      badge: 'LIVE GRANTS.GOV'
    },
    {
      num: '02',
      agent: 'MATCHER AGENT',
      pattern: 'Graph Routing Pattern',
      title: '5-DIMENSION RUBRIC',
      desc: 'Evaluates Mission (30), Eligibility (25), Capacity (20), Geography (15), and Track Record (10) on a 100-pt scale.',
      badge: 'PYDANTIC ENFORCED'
    },
    {
      num: '03',
      agent: 'DRAFTER AGENT',
      pattern: 'Swarm Pattern',
      title: 'RAG PROPOSAL PRE-FILL',
      desc: 'Synthesizes complete 6-section proposal drafts citing IRS Form 990 financial ratios and past NSF award evidence.',
      badge: 'ZERO HALLUCINATION'
    }
  ];

  return (
    <div className="brutalist-card" style={{
      padding: '1.5rem 1.75rem',
      marginBottom: '2.5rem',
      background: '#FFFFFF'
    }}>
      {/* Top Problem & Mission Banner */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        flexWrap: 'wrap',
        gap: '1rem',
        marginBottom: '1.25rem'
      }}>
        <div style={{ maxWidth: '850px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.4rem', flexWrap: 'wrap' }}>
            <span className="tag-badge tag-dark">THE $1.5T FEDERAL GRANT PROBLEM</span>
            <span className="tag-badge tag-green">STRANDS MULTI-AGENT ARCHITECTURE</span>
          </div>

          <h2 className="font-heading" style={{ fontSize: '1.85rem', lineHeight: '1.05', color: 'var(--ink)', marginTop: '0.35rem' }}>
            HOW GRANTSCOUT RUNS IN THE BACKGROUND
          </h2>
          
          <p style={{ color: 'var(--ink-muted)', fontSize: '0.88rem', lineHeight: '1.45', marginTop: '0.35rem' }}>
            Small community nonprofits miss billions in federal funding because they lack dedicated grant writers. GrantScout runs autonomously as a multi-agent system—discovering opportunities, scoring organizational fit, and pre-filling verified applications before alerting humans for final sign-off.
          </p>
        </div>

        {/* Target Org Info Tag */}
        <div style={{
          background: 'var(--card-alt-bg)',
          border: '1px solid var(--border-dark)',
          padding: '0.65rem 0.85rem',
          fontSize: '0.75rem',
          fontFamily: 'var(--font-mono)'
        }}>
          <div style={{ color: 'var(--ink-muted)', fontSize: '0.68rem', fontWeight: 700 }}>ACTIVE NONPROFIT PROFILE:</div>
          <div style={{ color: 'var(--ink)', fontWeight: 800 }}>Youth Education Alliance</div>
          <div style={{ color: 'var(--amber-signal)', fontWeight: 700 }}>501(c)(3) • Budget: $450K</div>
        </div>
      </div>

      {/* 3-Step Process Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
        gap: '1rem'
      }}>
        {steps.map((step, idx) => (
          <div
            key={idx}
            style={{
              background: 'var(--canvas-bg)',
              border: '2px solid var(--border-dark)',
              padding: '1.15rem',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              position: 'relative'
            }}
          >
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span className="font-heading" style={{ fontSize: '1.5rem', color: 'var(--amber-signal)', lineHeight: '1' }}>
                  STEP {step.num}
                </span>
                <span className="tag-badge tag-dark" style={{ fontSize: '0.65rem', padding: '0.15rem 0.4rem' }}>
                  {step.badge}
                </span>
              </div>

              <h4 className="font-heading" style={{ fontSize: '1.25rem', color: 'var(--ink)', marginBottom: '0.2rem' }}>
                {step.title}
              </h4>

              <div style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--mission-green)', fontWeight: 700, marginBottom: '0.4rem' }}>
                {step.agent} • {step.pattern}
              </div>

              <p style={{ fontSize: '0.8rem', color: 'var(--ink-muted)', lineHeight: '1.4' }}>
                {step.desc}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
