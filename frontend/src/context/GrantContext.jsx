import React, { createContext, useContext, useState } from 'react';

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
    applicant_types: 'Nonprofits having a 501(c)(3) status',
    tags: ['EDUCATION', 'YOUTH STEM', '501(c)(3)', 'ROBOTICS'],
    match_score: {
      mission_alignment: 28,
      eligibility_fit: 24,
      capacity_match: 18,
      geographic_fit: 14,
      track_record: 10,
      total: 94
    },
    key_strengths: [
      'Direct mission alignment with youth STEM & robotics curriculum',
      'Eligible 501(c)(3) applicant type with clean Form 990 audit',
      'Requested $75K matches organizational capacity ($450K annual budget)'
    ],
    potential_risks: [
      'Quarterly milestone reporting requires structured outcome tracking'
    ],
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
    applicant_types: 'Nonprofits having a 501(c)(3) status',
    tags: ['K-12', 'AFTER-SCHOOL', 'CODING', '501(c)(3)'],
    match_score: {
      mission_alignment: 27,
      eligibility_fit: 23,
      capacity_match: 17,
      geographic_fit: 13,
      track_record: 8,
      total: 88
    },
    key_strengths: [
      'Focus on Title I school partnerships matches existing YEA after-school hubs',
      'Prior curriculum templates can be directly redeployed'
    ],
    potential_risks: [
      'Strict 30-day post-award implementation window'
    ],
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
    applicant_types: 'Nonprofits (other than institutions of higher education)',
    tags: ['WORKFORCE', 'DIGITAL EQUITY', 'COMMUNITY'],
    match_score: {
      mission_alignment: 20,
      eligibility_fit: 22,
      capacity_match: 14,
      geographic_fit: 11,
      track_record: 5,
      total: 72
    },
    key_strengths: [
      'Tech literacy focus aligns with digital education competencies',
      'High award ceiling ($100,000)'
    ],
    potential_risks: [
      'Adult workforce focus requires slight adaptation from pure youth K-12 model'
    ],
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
    applicant_types: '501(c)(3) Nonprofits and Community Organizations',
    tags: ['ROBOTICS', 'AEROSPACE', 'HIGH SCHOOL'],
    match_score: {
      mission_alignment: 26,
      eligibility_fit: 24,
      capacity_match: 18,
      geographic_fit: 13,
      track_record: 9,
      total: 90
    },
    key_strengths: [
      'High school robotics competition track record aligns with NASA criteria',
      'Eligible nonprofit applicant profile'
    ],
    potential_risks: [
      'Requires specialist aeronautics safety protocols'
    ],
    recommended_action: 'auto_draft'
  }
];

const GrantContext = createContext();

export function GrantProvider({ children }) {
  const [grants, setGrants] = useState(INITIAL_GRANTS);
  const [isScanning, setIsScanning] = useState(false);
  const [sectorFilter, setSectorFilter] = useState('ALL');

  const runScanCycle = () => {
    setIsScanning(true);
    setTimeout(() => {
      setIsScanning(false);
    }, 1600);
  };

  const getGrantById = (id) => {
    return grants.find(g => String(g.id) === String(id) || String(g.grant_id) === String(id));
  };

  return (
    <GrantContext.Provider value={{
      grants,
      setGrants,
      isScanning,
      runScanCycle,
      sectorFilter,
      setSectorFilter,
      getGrantById
    }}>
      {children}
    </GrantContext.Provider>
  );
}

export function useGrants() {
  return useContext(GrantContext);
}
