import React, { useState, useEffect } from 'react';
import { Compass, Cpu, Database, ShieldCheck, Zap, Activity } from 'lucide-react';

const BOOT_STEPS = [
  { label: 'Booting Strands Agents SDK Kernel...', icon: Cpu, delay: 0 },
  { label: 'Connecting to Amazon Bedrock (Claude Sonnet 4.5 & Haiku 4.5)...', icon: Zap, delay: 350 },
  { label: 'Hydrating Form 990 & 2 CFR 200 RAG Vector Knowledge Base...', icon: Database, delay: 700 },
  { label: 'Synchronizing Grants.gov Federal Opportunity Pipeline...', icon: Activity, delay: 1050 },
];

export default function SplashScreen({ isLoading, onFinished }) {
  // Check if session has already booted in this browser tab
  const alreadyBooted = typeof window !== 'undefined' && sessionStorage.getItem('grantscout_booted') === 'true';

  const [activeStep, setActiveStep] = useState(alreadyBooted ? BOOT_STEPS.length : 0);
  const [fadeOut, setFadeOut] = useState(false);
  const [visible, setVisible] = useState(!alreadyBooted);

  useEffect(() => {
    if (alreadyBooted) return;

    // Progress through boot steps
    const timers = BOOT_STEPS.map((_, idx) => {
      return setTimeout(() => {
        setActiveStep(idx + 1);
      }, (idx + 1) * 320);
    });

    return () => timers.forEach(clearTimeout);
  }, [alreadyBooted]);

  useEffect(() => {
    if (alreadyBooted) return;

    // When isLoading becomes false and all steps completed, fade out and remember session
    if (!isLoading && activeStep >= BOOT_STEPS.length) {
      const timer = setTimeout(() => {
        setFadeOut(true);
        setTimeout(() => {
          setVisible(false);
          try {
            sessionStorage.setItem('grantscout_booted', 'true');
          } catch (e) {
            console.warn('sessionStorage write error:', e);
          }
          if (onFinished) onFinished();
        }, 450); // 450ms fade out transition
      }, 350);

      return () => clearTimeout(timer);
    }
  }, [isLoading, activeStep, alreadyBooted, onFinished]);

  if (!visible) return null;

  const progressPct = Math.min(100, Math.round((activeStep / BOOT_STEPS.length) * 100));

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'var(--canvas-bg, #FAF8F5)',
        backgroundImage: 'radial-gradient(#18181B 0.75px, transparent 0.75px)',
        backgroundSize: '16px 16px',
        zIndex: 99999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        opacity: fadeOut ? 0 : 1,
        transform: fadeOut ? 'scale(1.02)' : 'scale(1)',
        transition: 'opacity 0.5s cubic-bezier(0.16, 1, 0.3, 1), transform 0.5s cubic-bezier(0.16, 1, 0.3, 1)',
        pointerEvents: fadeOut ? 'none' : 'auto',
      }}
    >
      <div
        style={{
          width: '540px',
          maxWidth: '100%',
          backgroundColor: '#FFFFFF',
          border: '3px solid #18181B',
          boxShadow: '8px 8px 0px #18181B',
          padding: '32px',
          borderRadius: '2px',
        }}
      >
        {/* Header Branding */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', borderBottom: '2px solid #18181B', paddingBottom: '20px', marginBottom: '24px' }}>
          <div
            style={{
              width: '54px',
              height: '54px',
              backgroundColor: '#18181B',
              color: '#FAF8F5',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '2px solid #18181B',
              boxShadow: '3px 3px 0px #C85A17',
              flexShrink: 0,
              animation: 'spin 12s linear infinite',
            }}
          >
            <Compass size={32} strokeWidth={2.5} />
          </div>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h1
                style={{
                  fontFamily: 'var(--font-heading, "Bebas Neue", sans-serif)',
                  fontSize: '2.4rem',
                  lineHeight: '1',
                  margin: 0,
                  color: '#18181B',
                  letterSpacing: '0.04em',
                }}
              >
                GRANTSCOUT
              </h1>
              <span
                style={{
                  backgroundColor: '#C85A17',
                  color: '#FFFFFF',
                  fontSize: '10px',
                  fontWeight: '800',
                  padding: '2px 6px',
                  borderRadius: '2px',
                  fontFamily: 'var(--font-mono, monospace)',
                }}
              >
                v1.0.0
              </span>
            </div>
            <p
              style={{
                margin: '4px 0 0 0',
                fontSize: '11px',
                fontWeight: '700',
                color: '#71717A',
                letterSpacing: '0.05em',
                textTransform: 'uppercase',
                fontFamily: 'var(--font-mono, monospace)',
              }}
            >
              AUTONOMOUS GRANT INTELLIGENCE & PROPOSAL WORKSTATION
            </p>
          </div>
        </div>

        {/* Progress Step Feed */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '24px' }}>
          {BOOT_STEPS.map((step, idx) => {
            const isCompleted = activeStep > idx;
            const isCurrent = activeStep === idx + 1;
            const IconComponent = step.icon;

            return (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  padding: '10px 14px',
                  backgroundColor: isCompleted ? '#F0FDF4' : isCurrent ? '#FAF8F5' : '#F4F4F5',
                  border: '1px solid #18181B',
                  borderLeft: `4px solid ${isCompleted ? '#166534' : isCurrent ? '#C85A17' : '#A1A1AA'}`,
                  transition: 'all 0.25s ease',
                  opacity: isCompleted || isCurrent ? 1 : 0.5,
                }}
              >
                <div style={{ color: isCompleted ? '#166534' : isCurrent ? '#C85A17' : '#71717A', display: 'flex', alignItems: 'center' }}>
                  {isCompleted ? (
                    <span style={{ fontWeight: '800', fontSize: '14px', color: '#166534' }}>✓</span>
                  ) : isCurrent ? (
                    <span style={{ display: 'inline-block', width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#C85A17', animation: 'pulse 1.5s infinite' }} />
                  ) : (
                    <span style={{ fontSize: '12px', color: '#A1A1AA' }}>○</span>
                  )}
                </div>

                <div style={{ flex: 1, fontSize: '12px', fontFamily: 'var(--font-mono, monospace)', fontWeight: isCurrent ? '700' : '600', color: isCompleted ? '#166534' : isCurrent ? '#18181B' : '#71717A' }}>
                  {step.label}
                </div>

                {isCurrent && (
                  <span style={{ fontSize: '10px', fontWeight: '800', color: '#C85A17', fontFamily: 'var(--font-mono, monospace)' }}>
                    ACTIVE...
                  </span>
                )}
              </div>
            );
          })}
        </div>

        {/* Brutalist Striped Progress Bar */}
        <div style={{ marginBottom: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px', fontSize: '11px', fontFamily: 'var(--font-mono, monospace)', fontWeight: '700' }}>
            <span style={{ color: '#18181B' }}>SYSTEM INITIALIZATION</span>
            <span style={{ color: '#C85A17' }}>{progressPct}%</span>
          </div>

          <div
            style={{
              height: '14px',
              backgroundColor: '#F4F4F5',
              border: '2px solid #18181B',
              boxShadow: '2px 2px 0px #18181B',
              overflow: 'hidden',
              position: 'relative',
            }}
          >
            <div
              style={{
                height: '100%',
                width: `${progressPct}%`,
                backgroundColor: '#166534',
                backgroundImage: 'repeating-linear-gradient(45deg, rgba(255,255,255,0.2) 0, rgba(255,255,255,0.2) 10px, transparent 10px, transparent 20px)',
                transition: 'width 0.35s ease',
              }}
            />
          </div>
        </div>

        {/* Telemetry Footer */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '10px',
            color: '#71717A',
            fontFamily: 'var(--font-mono, monospace)',
            borderTop: '1px solid #E4E4E7',
            paddingTop: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#22C55E' }} />
            <span>PORT 8000 (LIVE API)</span>
          </div>

          <span>AMAZON BEDROCK ROUTER ACTIVE</span>
        </div>
      </div>
    </div>
  );
}
