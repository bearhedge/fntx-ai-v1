#!/usr/bin/env python3
import os
import sys
import json
sys.path.append('/home/info/fntx-ai-v1/config/IB_headless')
from ib_rest_auth_consolidated import IBRestAuth

print("=" * 60)
print("PROOF THE PYTHON OAUTH WORKS")
print("=" * 60)

# Create auth object
auth = IBRestAuth()

# Load the saved tokens
auth._load_tokens()

print(f"\n1. SAVED LST: {auth.live_session_token}")
print(f"   From: ~/.ib_rest_tokens.json")
print(f"   Generated: 2025-08-18 16:44:49")

print("\n2. MAKING REAL API CALLS WITH THIS LST:")
print("-" * 40)

# Get accounts
response = auth.make_authenticated_request('GET', '/portfolio/accounts')
print(f"\nGET /portfolio/accounts")
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")

# Get account summary
response = auth.make_authenticated_request('GET', '/portfolio/U19860056/summary')
print(f"\nGET /portfolio/U19860056/summary")
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    # Show some key fields
    print("Account Summary (partial):")
    print(f"  accountready: {data.get('accountready')}")
    print(f"  accounttype: {data.get('accounttype')}")
    print(f"  netliquidation: {data.get('netliquidation')}")
    print(f"  totalcashvalue: {data.get('totalcashvalue')}")

# Get positions
response = auth.make_authenticated_request('GET', '/portfolio/U19860056/positions/0')
print(f"\nGET /portfolio/U19860056/positions/0")
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    if data:
        print(f"Positions found: {len(data)} position(s)")
        if len(data) > 0:
            print(f"First position: {data[0].get('contractDesc', 'N/A')}")

print("\n" + "=" * 60)
print("WHY CAN'T WE GENERATE A NEW LST?")
print("=" * 60)

print("""
The LST generation fails because the access_token_secret in .env 
is DIFFERENT from the one in the saved token file:

FROM .ENV (what we're trying to use):
Gn1dWkMnStmAPxA5TkWOJxdN0EIsvSpIMmN5x84i...

FROM SAVED TOKEN FILE (what actually works):
ORmHJD3tmzPNsIhAMgoxtl14UkbUEHaUMi5l0xRy...

These are DIFFERENT encrypted secrets! The one in .env is probably
from an older OAuth flow or different request token.

The saved LST was generated with the ORmHJD... secret, so it only
works with that specific access_token_secret.
""")

