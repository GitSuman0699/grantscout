import React, { useState, useEffect } from 'react';
import { createSSEStream } from '../services/api';

export default function AgentThoughtStream() {
  const [events, setEvents] = useState([
    {
      id: 'init-1',
      agent: 'ScannerAgent',
      tier: 'Fast Tier (Claude Haiku)',
      step: 'Query Generation',
      thought: 'Generated keyword query set for active mission: [STEM, robotics, coding].',
      timestamp: new Date().toLocaleTimeString(),
    },
    {
      id: 'init-2',
      agent: 'MatcherAgent',
      tier: 'Standard Tier (Claude Sonnet)',
      step: 'Rubric Fit Analysis',
      thought: 'Evaluated NSF Youth STEM Innovation Labs against 5-dimension rubric: Score 94/100.',
      timestamp: new Date().toLocaleTimeString(),
    },
  ]);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    const sse = createSSEStream(
      (data) => {
        if (data && (data.message || data.thought || data.agent)) {
          const newEvt = {
            id: `evt-${Date.now()}-${Math.random()}`,
            agent: data.agent || (data.event_type ? data.event_type.replace('_', ' ').toUpperCase() : 'Agent Core'),
            tier: data.tier || 'Standard Tier (Claude Sonnet)',
            step: data.step || data.event_type || 'Execution Step',
            thought: data.thought || data.message || JSON.stringify(data.details || {}),
            timestamp: new Date().toLocaleTimeString(),
          };
          setEvents((prev) => [newEvt, ...prev.slice(0, 24)]);
          // Auto-expand telemetry feed when live agent events stream in
          setExpanded(true);
        }
      },
      (err) => console.warn('SSE stream error:', err)
    );

    return () => sse.close();
  }, []);

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '16px',
        right: '16px',
        zIndex: 1000,
        width: expanded ? '420px' : 'auto',
        maxWidth: 'calc(100vw - 32px)',
      }}
    >
      <div
        style={{
          background: '#18181B',
          color: '#FAF8F5',
          border: '2px solid #3F3F46',
          boxShadow: '4px 4px 0px rgba(0,0,0,0.4)',
          borderRadius: '2px',
          overflow: 'hidden',
          fontFamily: 'JetBrains Mono, monospace',
        }}
      >
        {/* Header Toggle */}
        <div
          onClick={() => setExpanded(!expanded)}
          style={{
            padding: '10px 14px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
            cursor: 'pointer',
            background: '#27272A',
            borderBottom: expanded ? '1px solid #3F3F46' : 'none',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: '#22C55E', animation: 'pulse 2s infinite' }} />
            <span style={{ fontSize: '12px', fontWeight: '800', letterSpacing: '0.04em' }}>
              AGENT THOUGHT STREAM
            </span>
            <span style={{ fontSize: '10px', background: '#3F3F46', padding: '2px 6px', borderRadius: '2px', color: '#A1A1AA' }}>
              {events.length} logs
            </span>
          </div>

          <span style={{ fontSize: '11px', color: '#A1A1AA' }}>{expanded ? '▼ Hide' : '▲ Live Telemetry'}</span>
        </div>

        {/* Expanded Feed */}
        {expanded && (
          <div
            style={{
              maxHeight: '320px',
              overflowY: 'auto',
              padding: '12px',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
              background: '#18181B',
            }}
          >
            {events.map((evt) => (
              <div
                key={evt.id}
                style={{
                  padding: '8px 10px',
                  background: '#27272A',
                  borderLeft: '3px solid #22C55E',
                  fontSize: '11px',
                  lineHeight: '1.4',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: '#A1A1AA', fontSize: '10px' }}>
                  <span style={{ fontWeight: '700', color: '#22C55E' }}>[{evt.agent}]</span>
                  <span>{evt.timestamp}</span>
                </div>
                <div style={{ color: '#E4E4E7', marginTop: '2px' }}>{evt.thought}</div>
                <div style={{ fontSize: '9px', color: '#71717A', marginTop: '4px' }}>
                  Tier: {evt.tier}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
