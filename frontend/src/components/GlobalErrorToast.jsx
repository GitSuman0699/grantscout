import React, { useEffect } from 'react';
import { AlertOctagon, X } from 'lucide-react';
import { useGrants } from '../context/GrantContext';

export default function GlobalErrorToast() {
  const { error, setError } = useGrants();

  // Auto-dismiss after 15 seconds if ignored
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => {
        setError(null);
      }, 15000);
      return () => clearTimeout(timer);
    }
  }, [error, setError]);

  if (!error) return null;

  return (
    <div style={{
      position: 'fixed',
      bottom: '2rem',
      right: '2rem',
      zIndex: 10000,
      width: '100%',
      maxWidth: '450px',
      backgroundColor: '#EF4444',
      color: '#FFFFFF',
      border: '3px solid var(--border-dark)',
      boxShadow: '6px 6px 0px var(--border-dark)',
      display: 'flex',
      flexDirection: 'column',
      animation: 'slideUp 0.3s ease-out'
    }}>
      <style>
        {`
          @keyframes slideUp {
            from { transform: translateY(100%); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
          }
        `}
      </style>
      <div style={{
        padding: '1rem',
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        gap: '1rem'
      }}>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <AlertOctagon size={24} style={{ flexShrink: 0 }} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
            <h3 className="font-heading" style={{ margin: 0, fontSize: '1.1rem', letterSpacing: '0.05em' }}>
              SYSTEM ALERT
            </h3>
            <p style={{ margin: 0, fontSize: '0.9rem', lineHeight: '1.4' }}>
              {error}
            </p>
          </div>
        </div>
        <button
          onClick={() => setError(null)}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#FFFFFF',
            cursor: 'pointer',
            padding: '0.25rem'
          }}
          aria-label="Dismiss error"
        >
          <X size={20} />
        </button>
      </div>
    </div>
  );
}
