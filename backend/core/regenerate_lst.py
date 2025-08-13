#!/usr/bin/env python3
"""
Regenerate Live Session Token
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
print("Regenerating Live Session Token")
print("="*70)

# Initialize auth
auth = IBRestAuth()

print(f"\nCurrent Configuration:")
print(f"  Consumer Key: {auth.consumer_key}")
print(f"  Access Token: {auth.access_token}")
print(f"  Has LST: {bool(auth.live_session_token)}")

# Force regeneration of LST
print("\nRegenerating LST...")
auth.live_session_token = None  # Clear existing

if auth.get_live_session_token():
    print("✅ Successfully regenerated Live Session Token")
    
    # Test it
    print("\nTesting new LST...")
    response = auth._make_authenticated_request('GET', 'https://api.ibkr.com/v1/api/portfolio/accounts')
    
    if response:
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        
        if response.status_code == 200:
            print("✅ NEW LST WORKS!")
        else:
            print("❌ Still getting error with new LST")
    else:
        print("❌ No response")
else:
    print("❌ Failed to regenerate LST")