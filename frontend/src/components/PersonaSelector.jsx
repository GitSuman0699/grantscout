import React, { useState, useEffect } from 'react';
import { fetchPersonas, switchPersona } from '../services/api';

export default function PersonaSelector({ onPersonaChanged }) {
  const [personas, setPersonas] = useState([]);
  const [selectedId, setSelectedId] = useState('youth-stem');
  const [loading, setLoading] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);

  useEffect(() => {
    fetchPersonas()
      .then((data) => {
        if (data && data.personas) {
          setPersonas(data.personas);
        }
      })
      .catch((err) => console.warn('Could not load personas:', err));
  }, []);

  const handleSelect = async (persona) => {
    if (persona.id === selectedId) {
      setDropdownOpen(false);
      return;
    }
    setLoading(true);
    try {
      await switchPersona(persona.id);
      setSelectedId(persona.id);
      setDropdownOpen(false);
      if (onPersonaChanged) onPersonaChanged(persona);
    } catch (err) {
      console.error('Failed to switch persona:', err);
    } finally {
      setLoading(false);
    }
  };

  const currentPersona = personas.find((p) => p.id === selectedId) || personas[0] || {
    name: 'Youth Education Alliance',
    sector: 'STEM Education & Youth Development',
  };

  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      <button
        onClick={() => setDropdownOpen(!dropdownOpen)}
        disabled={loading}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          background: '#FAF8F5',
          border: '2px solid #18181B',
          boxShadow: '2px 2px 0px #18181B',
          padding: '6px 12px',
          fontSize: '13px',
          fontWeight: '600',
          cursor: loading ? 'wait' : 'pointer',
          borderRadius: '2px',
          fontFamily: 'inherit',
        }}
        title="Switch active nonprofit sector persona"
      >
        <span style={{ fontSize: '14px' }}>🏢</span>
        <div style={{ textAlign: 'left', lineHeight: '1.2' }}>
          <div style={{ color: '#18181B', fontWeight: '700' }}>
            {loading ? 'Switching...' : currentPersona.name}
          </div>
          <div style={{ fontSize: '10px', color: '#71717A', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            {currentPersona.sector}
          </div>
        </div>
        <span style={{ fontSize: '10px', marginLeft: '4px', transform: dropdownOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>
          ▼
        </span>
      </button>

      {dropdownOpen && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 4px)',
            left: 0,
            width: '320px',
            background: '#FAF8F5',
            border: '2px solid #18181B',
            boxShadow: '4px 4px 0px #18181B',
            zIndex: 999,
            borderRadius: '2px',
            padding: '6px 0',
          }}
        >
          <div style={{ padding: '6px 12px', borderBottom: '1px solid #E4E4E7', fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', color: '#71717A' }}>
            Select Sector Persona
          </div>
          {personas.map((p) => {
            const isSelected = p.id === selectedId;
            return (
              <div
                key={p.id}
                onClick={() => handleSelect(p)}
                style={{
                  padding: '8px 12px',
                  cursor: 'pointer',
                  background: isSelected ? '#F4F4F5' : 'transparent',
                  borderLeft: isSelected ? '4px solid #166534' : '4px solid transparent',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = '#F4F4F5')}
                onMouseLeave={(e) => (e.currentTarget.style.background = isSelected ? '#F4F4F5' : 'transparent')}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: '700', fontSize: '13px', color: '#18181B' }}>{p.name}</span>
                  <span style={{ fontSize: '11px', color: '#166534', fontWeight: '700' }}>
                    ${(p.annual_budget / 1000).toFixed(0)}k/yr
                  </span>
                </div>
                <div style={{ fontSize: '11px', color: '#52525B', marginTop: '2px' }}>{p.sector}</div>
                <div style={{ fontSize: '10px', color: '#71717A', marginTop: '4px', fontStyle: 'italic' }}>
                  {p.tagline}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
