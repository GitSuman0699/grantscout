import React, { useEffect, useRef } from 'react';
import { Loader2 } from 'lucide-react';

/**
 * Shared Agent Terminal Component
 * Provides a unified, brutalist-styled live telemetry terminal
 * for background agent loops (Discovery Cycle scanner, Bedrock Drafter swarm, etc.).
 */
export default function AgentTerminal({
  title = 'AUTONOMOUS AGENT TELEMETRY',
  badge = 'AGENT TELEMETRY STREAM',
  thoughts = [],
  isActive = true,
  height = '260px',
  emptyMessage = 'INITIALIZING AGENT TELEMETRY STREAM',
  className = '',
  style = {},
}) {
  const terminalEndRef = useRef(null);

  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [thoughts, isActive]);

  return (
    <div
      className={`brutalist-card ${className}`}
      style={{
        padding: '1.25rem 1.5rem',
        background: '#0a0a0a',
        border: '3px solid var(--border-dark)',
        color: '#10B981',
        fontFamily: 'var(--font-mono, monospace)',
        display: 'flex',
        flexDirection: 'column',
        ...style
      }}
    >
      {/* Terminal Title Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '0.6rem',
          marginBottom: '0.9rem',
          borderBottom: '1px solid #27272A',
          paddingBottom: '0.6rem',
          flexShrink: 0
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', minWidth: 0 }}>
          <Loader2
            size={16}
            className={isActive ? 'spin' : ''}
            style={{ color: '#F59E0B', flexShrink: 0 }}
          />
          <span
            style={{
              fontWeight: 800,
              color: '#F59E0B',
              fontSize: '0.82rem',
              letterSpacing: '0.05em',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis'
            }}
          >
            {title}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexShrink: 0 }}>
          {badge && (
            <span
              style={{
                fontSize: '0.72rem',
                color: '#9CA3AF',
                letterSpacing: '0.05em',
                fontWeight: 600
              }}
            >
              {badge}
            </span>
          )}
          {isActive && (
            <span
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                backgroundColor: '#10B981',
                boxShadow: '0 0 6px #10B981',
                display: 'inline-block'
              }}
            />
          )}
        </div>
      </div>

      {/* Terminal Telemetry Body */}
      <div
        className="agent-terminal-body"
        style={{
          height: height,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.45rem',
          scrollbarColor: '#333333 #111111',
          scrollbarWidth: 'thin',
          paddingRight: '0.25rem'
        }}
      >
        {thoughts.length === 0 ? (
          <div
            style={{
              display: 'flex',
              gap: '0.6rem',
              alignItems: 'flex-start',
              fontSize: '0.85rem',
              lineHeight: '1.5'
            }}
          >
            <span style={{ color: '#6B7280', flexShrink: 0 }}>&gt;</span>
            <span style={{ color: '#34D399' }}>
              {emptyMessage}
              {isActive ? <span className="animated-dots"></span> : null}
            </span>
          </div>
        ) : (
          thoughts.map((thought, idx) => {
            const isLast = idx === thoughts.length - 1;
            const baseText = typeof thought === 'string' ? thought.replace(/\.*$/, '') : String(thought);
            return (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  gap: '0.6rem',
                  alignItems: 'flex-start',
                  opacity: isLast ? 1 : 0.7,
                  wordBreak: 'break-word',
                  lineHeight: '1.5',
                  fontSize: '0.85rem'
                }}
              >
                <span style={{ color: '#6B7280', flexShrink: 0 }}>&gt;</span>
                <span style={{ color: isLast && isActive ? '#34D399' : '#9CA3AF' }}>
                  {baseText}
                  {isLast && isActive ? <span className="animated-dots"></span> : null}
                </span>
              </div>
            );
          })
        )}
        <div ref={terminalEndRef} />
      </div>
    </div>
  );
}
