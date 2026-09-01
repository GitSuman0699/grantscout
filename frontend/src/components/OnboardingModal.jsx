import React, { useState } from 'react';
import { onboardOrganization } from '../services/api';

export default function OnboardingModal({ isOpen, onClose, onProfileUpdated }) {
  const [formData, setFormData] = useState({
    name: '',
    ein: '',
    annual_budget: 350000,
    service_area: '',
    target_population: '',
    mission: '',
    keywordsText: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.name || !formData.mission) {
      setError('Organization name and mission statement are required.');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const keywords = formData.keywordsText
        .split(',')
        .map((k) => k.trim())
        .filter(Boolean);

      const payload = {
        name: formData.name,
        ein: formData.ein || '00-0000000',
        annual_budget: Number(formData.annual_budget) || 0,
        service_area: formData.service_area || 'Regional Community Area',
        target_population: formData.target_population || 'Community members',
        mission: formData.mission,
        keywords: keywords.length ? keywords : ['community development', 'education', 'nonprofit'],
        programs: [],
        past_grants: [],
      };

      await onboardOrganization(payload);
      if (onProfileUpdated) onProfileUpdated(payload);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to onboard organization profile.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(24, 24, 27, 0.75)',
        zIndex: 1100,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
      }}
    >
      <div
        style={{
          background: '#FAF8F5',
          border: '3px solid #18181B',
          boxShadow: '6px 6px 0px #18181B',
          width: '560px',
          maxWidth: '100%',
          maxHeight: '90vh',
          overflowY: 'auto',
          padding: '24px',
          borderRadius: '2px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '2px solid #18181B', paddingBottom: '12px' }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '18px', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              🏢 Onboard Nonprofit Profile
            </h2>
            <div style={{ fontSize: '12px', color: '#71717A', marginTop: '2px' }}>
              Configure custom mission parameters from Form 990 / charter filings.
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              fontSize: '18px',
              fontWeight: '800',
              cursor: 'pointer',
            }}
          >
            ✕
          </button>
        </div>

        {error && (
          <div style={{ marginTop: '12px', padding: '8px 12px', background: '#FEF2F2', border: '1px solid #991B1B', color: '#991B1B', fontSize: '12px' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginTop: '16px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', textTransform: 'uppercase', marginBottom: '4px' }}>
              Organization Legal Name *
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Hope Community Health Clinic"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              style={{
                width: '100%',
                padding: '8px 12px',
                border: '2px solid #18181B',
                background: '#FFFFFF',
                fontFamily: 'inherit',
                fontSize: '13px',
                boxSizing: 'border-box',
              }}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', textTransform: 'uppercase', marginBottom: '4px' }}>
                IRS EIN
              </label>
              <input
                type="text"
                placeholder="XX-XXXXXXX"
                value={formData.ein}
                onChange={(e) => setFormData({ ...formData, ein: e.target.value })}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  border: '2px solid #18181B',
                  background: '#FFFFFF',
                  fontFamily: 'inherit',
                  fontSize: '13px',
                  boxSizing: 'border-box',
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', textTransform: 'uppercase', marginBottom: '4px' }}>
                Annual Budget ($)
              </label>
              <input
                type="number"
                placeholder="450000"
                value={formData.annual_budget}
                onChange={(e) => setFormData({ ...formData, annual_budget: e.target.value })}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  border: '2px solid #18181B',
                  background: '#FFFFFF',
                  fontFamily: 'inherit',
                  fontSize: '13px',
                  boxSizing: 'border-box',
                }}
              />
            </div>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', textTransform: 'uppercase', marginBottom: '4px' }}>
              Service Area & Target Population
            </label>
            <input
              type="text"
              placeholder="e.g. Metro Atlanta — Low-income families and seniors"
              value={formData.service_area}
              onChange={(e) => setFormData({ ...formData, service_area: e.target.value })}
              style={{
                width: '100%',
                padding: '8px 12px',
                border: '2px solid #18181B',
                background: '#FFFFFF',
                fontFamily: 'inherit',
                fontSize: '13px',
                boxSizing: 'border-box',
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', textTransform: 'uppercase', marginBottom: '4px' }}>
              Mission Statement & Core Activities *
            </label>
            <textarea
              rows={3}
              required
              placeholder="Describe your organization's core mission, programmatic outcomes, and community impact..."
              value={formData.mission}
              onChange={(e) => setFormData({ ...formData, mission: e.target.value })}
              style={{
                width: '100%',
                padding: '8px 12px',
                border: '2px solid #18181B',
                background: '#FFFFFF',
                fontFamily: 'inherit',
                fontSize: '13px',
                boxSizing: 'border-box',
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', textTransform: 'uppercase', marginBottom: '4px' }}>
              Discovery Keywords (comma-separated)
            </label>
            <input
              type="text"
              placeholder="e.g. community health, mobile clinic, preventive care, Medicaid"
              value={formData.keywordsText}
              onChange={(e) => setFormData({ ...formData, keywordsText: e.target.value })}
              style={{
                width: '100%',
                padding: '8px 12px',
                border: '2px solid #18181B',
                background: '#FFFFFF',
                fontFamily: 'inherit',
                fontSize: '13px',
                boxSizing: 'border-box',
              }}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '12px' }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                padding: '8px 16px',
                background: '#FFFFFF',
                border: '2px solid #18181B',
                fontWeight: '700',
                cursor: 'pointer',
                fontFamily: 'inherit',
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              style={{
                padding: '8px 18px',
                background: '#166534',
                color: '#FFFFFF',
                border: '2px solid #18181B',
                boxShadow: '2px 2px 0px #18181B',
                fontWeight: '800',
                cursor: loading ? 'wait' : 'pointer',
                fontFamily: 'inherit',
              }}
            >
              {loading ? 'Saving...' : '✓ Activate Organization'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
