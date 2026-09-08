import React, { useEffect, useRef } from 'react';
import { useGrants } from '../context/GrantContext';
import { Activity } from 'lucide-react';

export default function LiveScanModal() {
  const { isScanning, scanThoughts } = useGrants();
  const endOfLogRef = useRef(null);

  useEffect(() => {
    // Scroll to bottom whenever scanThoughts changes
    if (endOfLogRef.current) {
      endOfLogRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [scanThoughts, isScanning]);

  if (!isScanning) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.7)',
      backdropFilter: 'blur(4px)',
      zIndex: 9999,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '1rem'
    }}>
      <div style={{
        width: '100%',
        maxWidth: '800px',
        backgroundColor: 'var(--ink)',
        border: '3px solid var(--border-dark)',
        boxShadow: '8px 8px 0px var(--border-dark)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden'
      }}>
        {/* Modal Header */}
        <div style={{
          padding: '1rem',
          borderBottom: '2px solid var(--border-dark)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: 'var(--ink)',
          color: 'var(--canvas-bg)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Activity className="animate-spin" size={24} style={{ color: '#F59E0B' }} />
            <h2 className="font-heading" style={{ fontSize: '1.25rem', margin: 0, letterSpacing: '0.05em' }}>
              AUTONOMOUS DISCOVERY CYCLE
            </h2>
          </div>
          <div className="font-mono" style={{ fontSize: '0.75rem', color: '#9CA3AF' }}>
            AGENT TELEMETRY STREAM
          </div>
        </div>

        {/* Modal Body - Terminal Output */}
        <div className="font-mono" style={{
          height: '400px',
          overflowY: 'auto',
          padding: '1.5rem',
          backgroundColor: '#0a0a0a',
          color: '#10B981', // terminal green
          fontSize: '0.85rem',
          lineHeight: '1.6'
        }}>
          {scanThoughts.length === 0 ? (
            <div style={{ color: '#6B7280', fontStyle: 'italic' }}>
              Initializing scanner agent and connecting to Grants.gov...
            </div>
          ) : (
            scanThoughts.map((thought, idx) => (
              <div key={idx} style={{ marginBottom: '0.5rem', wordWrap: 'break-word' }}>
                <span style={{ color: '#4B5563', marginRight: '0.5rem' }}>{'>'}</span>
                {thought}
              </div>
            ))
          )}
          <div ref={endOfLogRef} />
        </div>
      </div>
    </div>
  );
}
