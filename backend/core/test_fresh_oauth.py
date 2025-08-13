#!/usr/bin/env python3
"""
Test OAuth with fresh LST generation
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add parent directory to path
sys.path.append('/home/info/fntx-ai-v1')

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

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

from backend.core.trading.ib_rest_auth import IBRestAuth

def main():
    print("="*70)
    print("Testing OAuth Authentication with Fresh LST")
    print("="*70)
    
    # Delete existing tokens to force fresh generation
    token_file = os.path.expanduser("~/.ib_rest_tokens.json")
    if os.path.exists(token_file):
        print(f"Removing existing token file: {token_file}")
        os.remove(token_file)
    
    # Initialize auth
    auth = IBRestAuth()
    
    print("\nStep 1: Generate fresh Live Session Token")
    print("-" * 50)
    
    # Use existing access token from environment
    auth.access_token = os.environ['IB_ACCESS_TOKEN']
    auth.access_token_secret = os.environ['IB_ACCESS_TOKEN_SECRET']
    
    # Try to get fresh LST
    if auth.get_live_session_token():
        print("✅ Live Session Token generated successfully!")
        
        # Save tokens
        auth._save_tokens()
        
        # Now test API calls
        print("\nStep 2: Test API Endpoints")
        print("-" * 50)
        
        # Test accounts endpoint
        print("\nTesting /portfolio/accounts:")
        response = auth._make_authenticated_request('GET', f"{auth.base_url}/portfolio/accounts")
        
        if response and response.status_code == 200:
            print(f"✅ SUCCESS! Got {len(response.json())} accounts")
            for account in response.json():
                print(f"  - Account: {account.get('accountId')}")
        else:
            status = response.status_code if response else 'No response'
            print(f"❌ Failed: {status}")
            if response:
                print(f"Error: {response.text}")
                # Check if signature error
                if "Invalid signature" in response.text:
                    # Show request details for debugging
                    print("\nDebug info:")
                    print(f"Status code: {response.status_code}")
                    print(f"Response headers: {response.headers}")
        
        # Test allocation endpoint
        print("\nTesting /portfolio/allocation:")
        response = auth._make_authenticated_request('GET', f"{auth.base_url}/portfolio/allocation")
        
        if response and response.status_code == 200:
            print(f"✅ SUCCESS! Got allocation data")
        else:
            print(f"❌ Failed: {response.status_code if response else 'No response'}")
            if response:
                print(f"Error: {response.text}")
                
    else:
        print("❌ Failed to generate Live Session Token")
        print("Check the logs above for details")

if __name__ == "__main__":
    main()