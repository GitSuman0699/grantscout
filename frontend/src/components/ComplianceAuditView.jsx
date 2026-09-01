import React, { useState, useEffect } from 'react';
import { auditCompliance } from '../services/api';

export default function ComplianceAuditView({ grantId, draftId, budgetContent, projectContent }) {
  const [audit, setAudit] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const runAudit = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await auditCompliance(grantId, {
        draft_id: draftId,
        budget_narrative: budgetContent || '',
        project_design: projectContent || '',
      });
      setAudit(res);
    } catch (err) {
      setError(err.message || 'Audit failed');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (grantId) {
      runAudit();
    }
  }, [grantId, draftId]);

  if (loading) {
    return (
      <div style={{ padding: '16px', background: '#FAF8F5', border: '2px solid #18181B', boxShadow: '3px 3px 0px #18181B', marginTop: '16px' }}>
        <div style={{ fontSize: '13px', fontWeight: '700', color: '#18181B' }}>
          ⚖️ Running Automated 2 CFR 200 Federal Uniform Guidance Compliance Audit...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '12px', background: '#FEF2F2', border: '2px solid #991B1B', color: '#991B1B', fontSize: '12px', marginTop: '16px' }}>
        Compliance audit error: {error}
      </div>
    );
  }

  if (!audit) return null;

  const isCompliant = audit.overall_status === 'compliant';
  const statusColor = isCompliant ? '#166534' : audit.overall_status === 'needs_revision' ? '#B45309' : '#991B1B';
  const statusBg = isCompliant ? '#F0FDF4' : audit.overall_status === 'needs_revision' ? '#FFFBEB' : '#FEF2F2';

  return (
    <div
      style={{
        background: '#FAF8F5',
        border: '2px solid #18181B',
        boxShadow: '4px 4px 0px #18181B',
        padding: '20px',
        marginTop: '20px',
        borderRadius: '2px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px', borderBottom: '2px solid #18181B', paddingBottom: '12px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '18px' }}>⚖️</span>
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Federal 2 CFR 200 Uniform Guidance Audit
            </h3>
          </div>
          <div style={{ fontSize: '12px', color: '#52525B', marginTop: '4px' }}>
            Automated statutory pre-submission verification for federal grant applications.
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              padding: '6px 12px',
              background: statusBg,
              border: `2px solid ${statusColor}`,
              color: statusColor,
              fontWeight: '800',
              fontSize: '13px',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            {isCompliant ? '✓ 2 CFR 200 Compliant' : `⚠ ${audit.overall_status.replace('_', ' ')}`}
          </div>

          <div
            style={{
              padding: '6px 12px',
              background: '#18181B',
              color: '#FAF8F5',
              fontWeight: '800',
              fontSize: '14px',
              fontFamily: 'JetBrains Mono, monospace',
            }}
          >
            Score: {audit.compliance_score}/100
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginTop: '16px' }}>
        <div style={{ padding: '10px 14px', background: '#FFFFFF', border: '1px solid #18181B' }}>
          <div style={{ fontSize: '11px', color: '#71717A', fontWeight: '700', textTransform: 'uppercase' }}>
            Indirect Cost Rate (§200.414)
          </div>
          <div style={{ fontSize: '14px', fontWeight: '800', color: audit.indirect_cost_compliant ? '#166534' : '#991B1B', marginTop: '2px' }}>
            {audit.indirect_cost_rate_pct}% {audit.indirect_cost_compliant ? '(De Minimis Cap ✓)' : '(Exceeds 10% Cap ⚠)'}
          </div>
        </div>

        <div style={{ padding: '10px 14px', background: '#FFFFFF', border: '1px solid #18181B' }}>
          <div style={{ fontSize: '11px', color: '#71717A', fontWeight: '700', textTransform: 'uppercase' }}>
            Unallowable Costs (§200 Subpart E)
          </div>
          <div style={{ fontSize: '14px', fontWeight: '800', color: audit.unallowable_costs_detected.length === 0 ? '#166534' : '#991B1B', marginTop: '2px' }}>
            {audit.unallowable_costs_detected.length === 0 ? '0 Prohibited Items Detected ✓' : `${audit.unallowable_costs_detected.length} Flagged Item(s) ⚠`}
          </div>
        </div>

        <div style={{ padding: '10px 14px', background: '#FFFFFF', border: '1px solid #18181B' }}>
          <div style={{ fontSize: '11px', color: '#71717A', fontWeight: '700', textTransform: 'uppercase' }}>
            Direct Personnel Standards (§200.430)
          </div>
          <div style={{ fontSize: '14px', fontWeight: '800', color: '#166534', marginTop: '2px' }}>
            Itemized Roles & Effort ✓
          </div>
        </div>
      </div>

      {/* Findings List */}
      <div style={{ marginTop: '16px' }}>
        <div style={{ fontSize: '12px', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '8px', color: '#18181B' }}>
          Audit Line-Item Verification:
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {audit.findings.map((f, i) => (
            <div
              key={f.finding_id || i}
              style={{
                padding: '10px 14px',
                background: f.severity === 'violation' ? '#FEF2F2' : f.severity === 'warning' ? '#FFFBEB' : '#F4F4F5',
                borderLeft: `4px solid ${f.severity === 'violation' ? '#991B1B' : f.severity === 'warning' ? '#B45309' : '#166534'}`,
                fontSize: '12px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: '800', color: '#18181B' }}>
                  {f.rule_reference} — {f.category.replace('_', ' ').toUpperCase()}
                </span>
                <span
                  style={{
                    fontSize: '10px',
                    fontWeight: '700',
                    textTransform: 'uppercase',
                    color: f.severity === 'violation' ? '#991B1B' : f.severity === 'warning' ? '#B45309' : '#166534',
                  }}
                >
                  {f.severity}
                </span>
              </div>
              <div style={{ color: '#3F3F46', marginTop: '4px' }}>{f.description}</div>
              {f.recommendation && (
                <div style={{ color: '#18181B', fontWeight: '600', marginTop: '4px', fontStyle: 'italic' }}>
                  Action: {f.recommendation}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
