import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Building2, Sparkles, Target, ExternalLink } from 'lucide-react';

/**
 * Universal calculation of grant fit percentage score.
 * Handles match_score.total, match_score 5-dimension objects, numbers, and raw score fields.
 */
export function calculateFitScore(grant) {
  if (!grant) return null;
  const ms = grant.match_score;
  if (typeof ms === 'number') return ms;
  if (ms && typeof ms.total === 'number') return ms.total;
  if (ms && typeof ms === 'object') {
    const sum = (ms.mission_alignment || 0) +
                (ms.eligibility_fit || 0) +
                (ms.capacity_match || 0) +
                (ms.geographic_fit || 0) +
                (ms.track_record || 0);
    if (sum > 0) return sum;
  }
  if (typeof grant.score === 'number') return grant.score;
  return null;
}

/**
 * Returns the direct official URL to the federal opportunity / application portal.
 */
export function getOfficialGrantUrl(grant) {
  if (!grant) return 'https://www.grants.gov';
  if (grant.application_url) return grant.application_url;
  if (grant.additional_info_url) return grant.additional_info_url;
  if (grant.url) return grant.url;
  
  const id = String(grant.grant_id || grant.id || '');
  const numMatch = id.replace('grants-gov-', '').trim();
  if (/^\d+$/.test(numMatch)) {
    return `https://www.grants.gov/search-results-detail/${numMatch}`;
  }
  return `https://www.grants.gov/search-grants?keywords=${encodeURIComponent(grant.title || id)}`;
}

/**
 * Returns intuitive semantic color badge information based on fit score:
 * - 80-100%: Green (High Match / Auto-Draft)
 * - 50-79%: Amber (Moderate Match / Review)
 * - 0-49%: Red (Low Match / Ineligible)
 */
export function getScoreBadgeProps(score) {
  if (score == null) {
    return {
      className: 'tag-badge tag-neutral',
      label: 'DISCOVERED • SCORING QUEUED'
    };
  }
  if (score >= 80) {
    return {
      className: 'tag-badge tag-score-high',
      label: `${score}% FIT • HIGH MATCH`
    };
  }
  if (score >= 50) {
    return {
      className: 'tag-badge tag-score-med',
      label: `${score}% FIT • MODERATE`
    };
  }
  return {
    className: 'tag-badge tag-score-low',
    label: `${score}% FIT • LOW MATCH`
  };
}

export default function GrantCard({ grant }) {
  const location = useLocation();
  const fitScore = calculateFitScore(grant);
  const badgeInfo = getScoreBadgeProps(fitScore);
  const officialUrl = getOfficialGrantUrl(grant);
  
  // Format award
  const awardText = grant.award_ceiling 
    ? `$${(grant.award_ceiling).toLocaleString()}` 
    : 'Funding Varies';

  const grantId = grant.grant_id || grant.id;
  const rubricUrl = `/rubrics/${grantId}`;
  const draftUrl = `/drafts/${grantId}`;
  const navState = { from: location.pathname };

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
        <a
          href={officialUrl}
          target="_blank"
          rel="noopener noreferrer"
          title="Open official notice on Grants.gov"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            fontSize: '0.8rem',
            fontWeight: 700,
            color: 'var(--ink)',
            textDecoration: 'none'
          }}
        >
          <Building2 size={16} />
          <span>{grant.agency || 'Federal Agency'}</span>
          <ExternalLink size={12} color="var(--ink-muted)" />
        </a>

        <span className={badgeInfo.className}>
          {badgeInfo.label}
        </span>
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
        <Link
          to={rubricUrl}
          state={navState}
          style={{ textDecoration: 'none', color: 'inherit' }}
        >
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

        {/* Action Buttons: Distinct separate routes */}
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <Link
            to={rubricUrl}
            state={navState}
            className="brutalist-btn btn-outline"
            style={{ flex: 1, padding: '0.55rem', fontSize: '0.95rem' }}
          >
            <Target size={16} />
            INSPECT RUBRIC
          </Link>
          
          <Link
            to={draftUrl}
            state={navState}
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
