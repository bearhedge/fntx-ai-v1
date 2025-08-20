#!/usr/bin/env python3
import os
import sys
sys.path.append('/home/info/fntx-ai-v1/config/IB_headless')
from ib_rest_auth_consolidated import IBRestAuth

# Create auth object
auth = IBRestAuth()

# Load the saved tokens
auth._load_tokens()

print("Loaded Live Session Token:", auth.live_session_token)
print("\nTesting API calls with saved LST:\n")

# Test endpoints
test_endpoints = [
    "/portfolio/accounts",
    "/portfolio/U19860056/summary",
]

for endpoint in test_endpoints:
    print(f"Testing {endpoint}...")
    response = auth.make_authenticated_request('GET', endpoint)
    if response:
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            print(f"  ✓ SUCCESS - Data retrieved")
        else:
            print(f"  ✗ FAILED - {response.text}")
    print()

