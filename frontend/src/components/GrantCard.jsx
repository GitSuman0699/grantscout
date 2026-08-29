import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Building2, Sparkles, ChevronRight } from 'lucide-react';

export default function GrantCard({ grant }) {
  const location = useLocation();
  const isHighFit = grant.match_score?.total >= 80;
  const isReview = grant.match_score?.total >= 50 && grant.match_score?.total < 80;
  
  // Format award
  const awardText = grant.award_ceiling 
    ? `$${(grant.award_ceiling).toLocaleString()}` 
    : 'Funding Varies';

  const grantUrl = `/grants/${grant.id || grant.grant_id}`;
  const navigationState = { from: location.pathname };

  return (
    <div
      className="brutalist-card"
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        overflow: 'hidden'
      }}
    >
      {/* Top Banner & Badges */}
      <div style={{
        background: 'var(--card-alt-bg)',
        borderBottom: '2px solid var(--border-dark)',
        padding: '0.85rem 1.25rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: '0.5rem',
        flexWrap: 'wrap'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', fontWeight: 700, color: 'var(--ink)' }}>
          <Building2 size={16} />
          <span>{grant.agency || 'Federal Agency'}</span>
        </div>

        {grant.match_score?.total && (
          <span className={`tag-badge ${isHighFit ? 'tag-amber' : isReview ? 'tag-green' : 'tag-neutral'}`}>
            {grant.match_score.total}% FIT {isHighFit ? '• AUTO-DRAFT' : ''}
          </span>
        )}
      </div>

      {/* Card Body */}
      <div style={{ padding: '1.25rem', flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Category Tags */}
        <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', marginBottom: '0.85rem' }}>
          {(grant.tags || ['501(c)(3)', 'EDUCATION', 'STEM']).map((t, idx) => (
            <span key={idx} className="tag-badge tag-dark">
              {t}
            </span>
          ))}
        </div>

        {/* Title */}
        <Link to={grantUrl} state={navigationState} style={{ textDecoration: 'none', color: 'inherit' }}>
          <h3
            className="font-heading"
            style={{
              fontSize: '1.75rem',
              lineHeight: '1.1',
              color: 'var(--ink)',
              marginBottom: '0.75rem',
              transition: 'color 0.15s ease'
            }}
          >
            {grant.title}
          </h3>
        </Link>

        {/* Synopsis Excerpt */}
        <p style={{
          fontSize: '0.88rem',
          color: 'var(--ink-muted)',
          lineHeight: '1.45',
          marginBottom: '1rem',
          flex: 1
        }}>
          {grant.synopsis 
            ? grant.synopsis.slice(0, 140) + (grant.synopsis.length > 140 ? '...' : '') 
            : 'Federal funding opportunity for qualifying 501(c)(3) nonprofit organizations.'}
        </p>

        {/* Dashed Divider */}
        <hr className="dashed-divider" style={{ margin: '0.5rem 0 1rem 0' }} />

        {/* Metadata Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '0.75rem',
          fontSize: '0.8rem',
          fontFamily: 'var(--font-mono)',
          marginBottom: '1.25rem'
        }}>
          <div>
            <div style={{ color: 'var(--ink-faint)', fontSize: '0.7rem', fontWeight: 600 }}>AWARD CEILING</div>
            <div style={{ fontWeight: 700, color: 'var(--ink)' }}>{awardText}</div>
          </div>
          <div>
            <div style={{ color: 'var(--ink-faint)', fontSize: '0.7rem', fontWeight: 600 }}>CLOSE DATE</div>
            <div style={{ fontWeight: 700, color: 'var(--ink)' }}>{grant.close_date || 'Ongoing'}</div>
          </div>
        </div>

        {/* Action Button Row with Page Navigation & Origin Tracking */}
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <Link
            to={grantUrl}
            state={navigationState}
            className="brutalist-btn btn-outline"
            style={{ flex: 1, padding: '0.55rem', fontSize: '0.95rem' }}
          >
            INSPECT RUBRIC
          </Link>
          
          <Link
            to={grantUrl}
            state={navigationState}
            className="brutalist-btn btn-primary"
            style={{ flex: 1, padding: '0.55rem', fontSize: '0.95rem' }}
          >
            <Sparkles size={16} />
            PRE-FILL DRAFT
          </Link>
        </div>
      </div>
    </div>
  );
}
