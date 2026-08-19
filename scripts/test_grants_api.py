"""Quick test script for grants.gov API tools."""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests

# Test 1: Search grants.gov API directly
print("=" * 60)
print("TEST 1: Search grants.gov API (STEM education)")
print("=" * 60)

response = requests.post(
    "https://api.grants.gov/v1/api/search2",
    headers={"Content-Type": "application/json"},
    json={
        "keyword": "STEM education youth",
        "oppStatuses": "posted",
        "rows": 5,
        "startRecordNum": 0,
    },
    timeout=30,
)

if response.status_code == 200:
    data = response.json()
    hits = data.get("data", {}).get("oppHits", [])
    total = data.get("data", {}).get("totalCount", 0)
    print(f"Total matches: {total}")
    print(f"Returned: {len(hits)} grants\n")
    
    for i, hit in enumerate(hits, 1):
        print(f"  {i}. {hit.get('title', 'No title')}")
        print(f"     Agency: {hit.get('agency', 'N/A')}")
        print(f"     ID: {hit.get('id', 'N/A')}")
        print(f"     Close: {hit.get('closeDate', 'N/A')}")
        print(f"     Award Ceiling: {hit.get('awardCeiling', 'N/A')}")
        print()
else:
    print(f"ERROR: Status {response.status_code}")
    print(response.text[:500])

# Test 2: Fetch details for first result
if response.status_code == 200 and hits:
    print("=" * 60)
    print(f"TEST 2: Fetch details for grant ID {hits[0].get('id')}")
    print("=" * 60)
    
    detail_response = requests.post(
        "https://api.grants.gov/v1/api/fetchOpportunity",
        headers={"Content-Type": "application/json"},
        json={"opportunityId": hits[0].get("id")},
        timeout=30,
    )
    
    if detail_response.status_code == 200:
        detail = detail_response.json()
        opp = detail.get("data", {})
        synopsis = opp.get("synopsis", {})
        
        print(f"Title: {opp.get('opportunityTitle', 'N/A')}")
        print(f"Agency: {synopsis.get('agencyName', 'N/A')}")
        print(f"Award Ceiling: {synopsis.get('awardCeiling', 'N/A')}")
        print(f"Award Floor: {synopsis.get('awardFloor', 'N/A')}")
        print(f"Close Date: {synopsis.get('responseDate', 'N/A')}")
        print(f"Synopsis (first 300 chars): {synopsis.get('synopsisDesc', 'N/A')[:300]}...")
    else:
        print(f"ERROR: Status {detail_response.status_code}")

print("\nDone!")
