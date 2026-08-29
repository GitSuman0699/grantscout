import React, { useState } from 'react';
import Header from './components/Header';
import MetricsBar from './components/MetricsBar';
import GrantCard from './components/GrantCard';
import DraftInspectorModal from './components/DraftInspectorModal';
import KnowledgeBaseView from './components/KnowledgeBaseView';
import OptimizationView from './components/OptimizationView';
import { Sparkles, ArrowUpRight, Filter, ShieldCheck } from 'lucide-react';

const INITIAL_GRANTS = [
  {
    id: 900001,
    grant_id: 'NSF-2026-STEM-0982',
    title: 'Youth STEM Innovation Labs for Underserved Communities',
    agency: 'National Science Foundation',
    synopsis: 'Funding for 501(c)(3) nonprofits to deliver hands-on robotics, coding, and science workshops to low-income students ages 8-18 in urban settings.',
    award_ceiling: 75000,
    award_floor: 25000,
    close_date: '2026-11-15',
    category: 'STEM',
    tags: ['EDUCATION', 'YOUTH STEM', '501(c)(3)', 'ROBOTICS'],
    match_score: {
      mission_alignment: 28,
      eligibility_fit: 24,
      capacity_match: 18,
      geographic_fit: 14,
      track_record: 10,
      total: 94
    },
    recommended_action: 'auto_draft'
  },
  {
    id: 900004,
    grant_id: 'ED-GRANTS-2026-041',
    title: 'After-School Coding Academies for K-12 Title I Schools',
    agency: 'Department of Education',
    synopsis: 'Competitive federal grants supporting structured after-school coding and computer science programs for elementary and secondary school students.',
    award_ceiling: 50000,
    award_floor: 15000,
    close_date: '2026-12-01',
    category: 'STEM',
    tags: ['K-12', 'AFTER-SCHOOL', 'CODING', '501(c)(3)'],
    match_score: {
      mission_alignment: 27,
      eligibility_fit: 23,
      capacity_match: 17,
      geographic_fit: 13,
      track_record: 8,
      total: 88
    },
    recommended_action: 'auto_draft'
  },
  {
    id: 900003,
    grant_id: 'DOL-ETA-2026-883',
    title: 'Community Digital Literacy & Workforce Readiness Initiative',
    agency: 'Department of Labor',
    synopsis: 'Grants for community-based organizations to provide computer literacy training, digital skills, and workforce development for disadvantaged populations.',
    award_ceiling: 100000,
    award_floor: 30000,
    close_date: '2027-01-20',
    category: 'WORKFORCE',
    tags: ['WORKFORCE', 'DIGITAL EQUITY', 'COMMUNITY'],
    match_score: {
      mission_alignment: 20,
      eligibility_fit: 22,
      capacity_match: 14,
      geographic_fit: 11,
      track_record: 5,
      total: 72
    },
    recommended_action: 'manual_review'
  },
  {
    id: 900006,
    grant_id: 'NASA-EXP-2026-119',
    title: 'Aerospace & Robotics Hands-on Discovery for High Schoolers',
    agency: 'NASA Office of STEM Engagement',
    synopsis: 'Supports hands-on rocketry, robotics kits, and aerospace engineering challenges for high school students in underrepresented STEM districts.',
    award_ceiling: 65000,
    award_floor: 20000,
    close_date: '2026-10-30',
    category: 'STEM',
    tags: ['ROBOTICS', 'AEROSPACE', 'HIGH SCHOOL'],
    match_score: {
      mission_alignment: 26,
      eligibility_fit: 24,
      capacity_match: 18,
      geographic_fit: 13,
      track_record: 9,
      total: 90
    },
    recommended_action: 'auto_draft'
  }
];

export default function App() {
  const [activeTab, setActiveTab] = useState('pipeline');
  const [sectorFilter, setSectorFilter] = useState('ALL');
  const [grants, setGrants] = useState(INITIAL_GRANTS);
  const [isScanning, setIsScanning] = useState(false);
  const [activeModalGrant, setActiveModalGrant] = useState(null);

  const filters = [
    { id: 'ALL', label: 'ALL OPPORTUNITIES' },
    { id: 'STEM', label: 'YOUTH & STEM' },
    { id: 'WORKFORCE', label: 'WORKFORCE & LITERACY' },
    { id: 'HIGH_FIT', label: 'AUTO-DRAFT READY (≥80)' }
  ];

  const filteredGrants = grants.filter(g => {
    if (sectorFilter === 'ALL') return true;
    if (sectorFilter === 'HIGH_FIT') return g.match_score?.total >= 80;
    return g.category === sectorFilter;
  });

  const handleRunScan = () => {
    setIsScanning(true);
    setTimeout(() => {
      setIsScanning(false);
    }, 1800);
  };

  const handleInspect = (grant) => {
    setActiveModalGrant(grant);
  };

  const handleDraft = (grant) => {
    setActiveModalGrant(grant);
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onRunScan={handleRunScan}
        isScanning={isScanning}
      />

      <main style={{
        maxWidth: '1440px',
        margin: '0 auto',
        padding: '2.5rem 2rem',
        flex: 1,
        width: '100%'
      }}>
        {activeTab === 'pipeline' && (
          <>
            {/* Hero / Statement Section */}
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'flex-end',
              flexWrap: 'wrap',
              gap: '1rem',
              marginBottom: '2rem'
            }}>
              <div>
                <span className="tag-badge tag-dark" style={{ marginBottom: '0.5rem', display: 'inline-block' }}>
                  AUTONOMOUS MISSION EXPLORER
                </span>
                <h2 className="font-heading" style={{ fontSize: '2.8rem', lineHeight: '0.95', color: 'var(--ink)' }}>
                  CURATED FEDERAL GRANT PIPELINE
                </h2>
                <p style={{ color: 'var(--ink-muted)', fontSize: '1rem', marginTop: '0.4rem', maxWidth: '720px' }}>
                  Scanning Grants.gov in the background, calculating 5-dimension organizational fit, and auto-drafting proposal packages.
                </p>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', fontWeight: 700 }}>
                <span style={{ color: 'var(--ink-muted)' }}>TARGET ORG:</span>
                <span className="tag-badge tag-amber">YOUTH EDUCATION ALLIANCE (501c3)</span>
              </div>
            </div>

            {/* Metrics Bar */}
            <MetricsBar stats={{ scanned: '78', matched: '14', drafts: '6', pipelineValue: '$1.45M' }} />

            {/* Filter Pills Bar */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem',
              flexWrap: 'wrap',
              marginBottom: '1.75rem',
              paddingBottom: '1rem',
              borderBottom: '1px solid var(--border-dashed)'
            }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--ink)', fontFamily: 'var(--font-mono)', marginRight: '0.5rem' }}>
                FILTER SECTOR:
              </span>
              {filters.map(f => (
                <button
                  key={f.id}
                  onClick={() => setSectorFilter(f.id)}
                  className={`tag-badge ${sectorFilter === f.id ? 'tag-dark' : 'tag-neutral'}`}
                  style={{ cursor: 'pointer', padding: '0.4rem 0.75rem', fontSize: '0.75rem' }}
                >
                  {f.label}
                </button>
              ))}
            </div>

            {/* Grant Opportunity Grid */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
              gap: '1.75rem'
            }}>
              {filteredGrants.map(grant => (
                <GrantCard
                  key={grant.id}
                  grant={grant}
                  onInspect={handleInspect}
                  onDraft={handleDraft}
                />
              ))}
            </div>
          </>
        )}

        {activeTab === 'drafts' && (
          <div>
            <div style={{ marginBottom: '2rem' }}>
              <h2 className="font-heading" style={{ fontSize: '2.5rem', lineHeight: '1' }}>
                PRE-FILLED PROPOSAL DRAFTS (6 SECTIONS)
              </h2>
              <p style={{ color: 'var(--ink-muted)' }}>
                Structured grant application packages pre-generated by the Drafter agent with Pydantic schema validation.
              </p>
            </div>

            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
              gap: '1.75rem'
            }}>
              {grants.filter(g => g.match_score?.total >= 80).map(grant => (
                <GrantCard
                  key={grant.id}
                  grant={grant}
                  onInspect={handleInspect}
                  onDraft={handleDraft}
                />
              ))}
            </div>
          </div>
        )}

        {activeTab === 'knowledge' && <KnowledgeBaseView />}
        {activeTab === 'optimization' && <OptimizationView />}
      </main>

      {/* Footer */}
      <footer style={{
        borderTop: '2px solid var(--border-dark)',
        backgroundColor: 'var(--ink)',
        color: 'var(--canvas-bg)',
        padding: '2rem'
      }}>
        <div style={{
          maxWidth: '1440px',
          margin: '0 auto',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          fontSize: '0.82rem'
        }}>
          <div>
            <div className="font-heading" style={{ fontSize: '1.4rem' }}>GRANTSCOUT</div>
            <div style={{ color: '#A1A1AA' }}>Built with Strands Agents SDK 1.52.0 & Amazon Bedrock for the AWS Agents for Humans Hackathon</div>
          </div>

          <div style={{ fontFamily: 'var(--font-mono)', color: '#A1A1AA' }}>
            © 2026 GrantScout • MIT License
          </div>
        </div>
      </footer>

      {/* Modal Inspector */}
      {activeModalGrant && (
        <DraftInspectorModal
          grant={activeModalGrant}
          onClose={() => setActiveModalGrant(null)}
        />
      )}
    </div>
  );
}
