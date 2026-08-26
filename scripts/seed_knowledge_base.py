"""Seed script to index organizational documents into the RAG KnowledgeBase."""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.rag.knowledge_base import knowledge_base

DOCUMENTS = [
    {
        "doc_name": "Annual_Impact_Report_2025.md",
        "category": "impact_report",
        "content": """# Youth Education Alliance: 2025 Annual Impact Report

## Executive Summary
In 2025, Youth Education Alliance (YEA) successfully delivered intensive after-school STEM workshops and summer learning labs to 330 underserved students across Metro Atlanta. 100% of participants came from low-income households qualifying for free or reduced-price lunch programs.

## Key Measurable Academic Outcomes
- Math & Science Academic Improvement: 85% of regular participants improved their cumulative math grades by at least one full letter grade within two academic semesters.
- Standardized Testing Benchmarks: Participating students outperformed their school district peers by 14% on the Georgia Milestones Science assessment.
- Career Interest & Self-Efficacy: 92% of surveyed participants expressed strong interest in pursuing STEM majors in college, up from 41% upon baseline intake.
- Retention & Completion: 88% of enrolled students completed the full 28-week robotics program, building and presenting an original capstone hardware device.

## Community Partnerships & Service Locations
YEA operates dedicated coding hubs at 4 partner community centers:
1. Westside Community Center (70 students)
2. Bankhead Youth Empowerment Center (85 students)
3. Grove Park Recreation Facility (65 students)
4. East Lake Community Hub (110 students)
Transportation subsidies and free daily nutritional meals were provided for all participants.
"""
    },
    {
        "doc_name": "IRS_Form_990_Financial_Overview.md",
        "category": "irs_990",
        "content": """# Youth Education Alliance: IRS Form 990 Summary & Financial Statement

## Fiscal Year 2025 Financial Overview
- Total Operating Revenue: $465,200
- Total Program Expenditures: $412,800 (88.7% program efficiency ratio)
- Administrative & Management Overhead: $36,400 (7.8%)
- Fundraising & Donor Development: $16,000 (3.5%)
- Ending Net Assets / Reserve: $84,300

## Revenue Diversification
- Foundation & Institutional Grants: 58% ($269,800)
- Corporate Contributions & Sponsorships: 26% ($120,950)
- Individual Donations & Board Giving: 16% ($74,450)

## Internal Controls & Independent Audit
An independent financial audit conducted by Williams & Associates CPA confirmed clean internal controls with no material weaknesses or compliance deficiencies. YEA maintains active registration in SAM.gov and holds a valid Unique Entity Identifier (UEI) for federal grant administration.
"""
    },
    {
        "doc_name": "Past_NSF_Grant_Narrative_2024.md",
        "category": "past_proposal",
        "content": """# Funded Project Narrative: NSF Informal STEM Learning (Award #24-9182)

## Project Title: 'RoboConnect: Community-Based Hardware Labs for Urban Youth'
Funded Amount: $25,000 | Project Period: January 2024 - December 2024

### Methodology & Technical Curriculum
The RoboConnect initiative deployed 45 modular Arduino and Raspberry Pi starter kits across community recreation centers. Students progressed through a sequenced 4-unit curriculum:
1. Computational Logic & Python Basics (Weeks 1-6)
2. Sensor Integration & Circuitry (Weeks 7-14)
3. Autonomous Robotics Navigation (Weeks 15-22)
4. Collaborative Community Capstone Solutions (Weeks 23-28)

### Past Project Evaluation Results
All performance milestones were delivered on schedule. 100% of awarded funds were expended in strict accordance with NSF uniform guidance. The project culminated in the Metro Atlanta Youth Science & Robotics Fair, where 3 student teams earned regional recognition.
"""
    },
    {
        "doc_name": "Leadership_and_Key_Personnel_Bios.md",
        "category": "bios",
        "content": """# Leadership Team and Principal Investigators

## Dr. Sarah Chen, Executive Director & Board Chair
Dr. Chen holds a Ph.D. in Computer Science from the Georgia Institute of Technology and has 14 years of experience leading educational technology initiatives. She has authored 18 peer-reviewed publications on informal computing education and previously served as Co-PI on multiple federal education research awards.

## Marcus Williams, CPA, Treasurer & Financial Officer
Marcus is a managing partner at Williams & Associates with 20 years of experience in nonprofit accounting, OMB Uniform Guidance compliance, and federal grant financial auditing.

## Jamila Vance, Director of STEM Programs
Jamila holds an M.Ed. in Curriculum Instruction and a B.S. in Mechanical Engineering. She oversees instructor training, student safety protocols, and curriculum alignment across all 4 center locations.
"""
    }
]


def seed_rag_documents():
    """Index all organizational documents into KnowledgeBase."""
    print("=" * 60)
    print("Indexing Nonprofit Documents into RAG Knowledge Base...")
    print("=" * 60)

    total_chunks = 0
    for doc in DOCUMENTS:
        chunks_count = knowledge_base.add_document(
            doc_name=doc["doc_name"],
            text=doc["content"],
            category=doc["category"],
        )
        total_chunks += chunks_count
        print(f"✓ Indexed {doc['doc_name']} ({chunks_count} chunks)")

    print(f"\n✅ Total {len(DOCUMENTS)} documents ({total_chunks} chunks) indexed successfully.")


if __name__ == "__main__":
    seed_rag_documents()
