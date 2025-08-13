#!/usr/bin/env python3
"""
Test the OAuth fix - using "&" + LST as signing key
"""

import os
import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.append('/home/info/fntx-ai-v1/backend')

# Load environment variables
env_path = Path('/home/info/fntx-ai-v1/config/.env')
if env_path.exists():
    with open(env_path, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                os.environ[key] = value

from core.trading.ib_rest_auth import IBRestAuth

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print("="*70)
print("Testing OAuth Fix - Using '&' + LST as signing key")
print("="*70)

# Initialize auth
auth = IBRestAuth()

print(f"\nConfiguration:")
print(f"  Consumer Key: {auth.consumer_key}")
print(f"  Access Token: {auth.access_token}")
print(f"  Has LST: {bool(auth.live_session_token)}")

# Test authentication
print("\nTesting authentication with fixed signature...")
response = auth._make_authenticated_request('GET', 'https://api.ibkr.com/v1/api/portfolio/accounts')

if response:
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ SUCCESS! OAuth is now working!")
        print(f"Response: {response.text[:500]}")
        
        # Test a few more endpoints to be sure
        print("\n" + "="*70)
        print("Testing additional endpoints...")
        print("="*70)
        
        # Test tickle
        print("\n1. Testing /tickle endpoint...")
        resp = auth._make_authenticated_request('GET', 'https://api.ibkr.com/v1/api/tickle')
        if resp:
            print(f"   Status: {resp.status_code}")
            if resp.status_code == 200:
                print("   ✅ Works!")
            else:
                print(f"   ❌ Failed: {resp.text[:100]}")
        
        # Test iserver/accounts
        print("\n2. Testing /iserver/accounts endpoint...")
        resp = auth._make_authenticated_request('GET', 'https://api.ibkr.com/v1/api/iserver/accounts')
        if resp:
            print(f"   Status: {resp.status_code}")
            if resp.status_code == 200:
                print("   ✅ Works!")
            else:
                print(f"   ❌ Failed: {resp.text[:100]}")
        
        # Test SSODH init
        print("\n3. Testing /iserver/auth/ssodh/init endpoint...")
        resp = auth._make_authenticated_request('POST', 'https://api.ibkr.com/v1/api/iserver/auth/ssodh/init',
                                               data={'compete': 'false', 'publish': 'true'})
        if resp:
            print(f"   Status: {resp.status_code}")
            if resp.status_code == 200:
                print("   ✅ Works!")
            else:
                print(f"   ❌ Failed: {resp.text[:100]}")
                
    else:
        print(f"❌ Still failing with status {response.status_code}")
        print(f"Response: {response.text}")
else:
    print("❌ No response received")

print("\n" + "="*70)
print("Test Complete")
print("="*70)