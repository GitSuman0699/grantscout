import React from 'react';
import { useGrants } from '../context/GrantContext';
import AgentTerminal from './AgentTerminal';

export default function LiveScanModal() {
  const { isScanning, scanThoughts } = useGrants();

  if (!isScanning) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(4px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1.25rem'
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '820px',
          boxShadow: '8px 8px 0px var(--border-dark)'
        }}
      >
        <AgentTerminal
          title="AUTONOMOUS DISCOVERY CYCLE (LIVE TELEMETRY)"
          badge="GRANTS.GOV SCANNER AGENT"
          thoughts={scanThoughts}
          isActive={isScanning}
          height="380px"
          emptyMessage="Initializing autonomous discovery cycle and connecting to Grants.gov..."
        />
      </div>
    </div>
  );
}

