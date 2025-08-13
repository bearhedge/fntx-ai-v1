#!/usr/bin/env python3
"""
Test full OAuth flow with TESTCONS
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
project_root = Path(__file__).parent.parent.parent
env_path = project_root / 'config' / '.env'
load_dotenv(env_path)

sys.path.append('/home/info/fntx-ai-v1/backend')
from core.trading.ib_rest_auth import IBRestAuth

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_full_oauth_flow():
    """Test the complete OAuth flow"""
    print("\n" + "="*60)
    print("FULL OAUTH FLOW TEST WITH TESTCONS")
    print("="*60)
    
    # Initialize auth handler
    auth = IBRestAuth()
    
    print(f"\nConfiguration:")
    print(f"Consumer Key: {auth.consumer_key}")
    print(f"Realm: {auth.realm}")
    print(f"OAuth Base URL: {auth.oauth_base}")
    
    # Step 1: Request Token
    print("\n" + "-"*60)
    print("Step 1: Getting Request Token")
    print("-"*60)
    
    if auth.get_request_token():
        print(f"✅ Got request token: {auth.request_token}")
        
        # Step 2: Authorization
        print("\n" + "-"*60)
        print("Step 2: Authorization")
        print("-"*60)
        print(f"In a real flow, user would visit:")
        print(f"https://www.interactivebrokers.com/authorize?oauth_token={auth.request_token}")
        print("And get a verifier token")
        
        # For testing, we'll skip this step
        print("⚠️  Skipping authorization step for test")
        
        # Step 3: Access Token
        print("\n" + "-"*60)
        print("Step 3: Getting Access Token")
        print("-"*60)
        print("⚠️  This would normally require a verifier from step 2")
        
        # Try without verifier (might fail)
        if auth.get_access_token():
            print(f"✅ Got access token: {auth.access_token}")
            print(f"✅ Got access token secret: {auth.access_token_secret[:50]}...")
            
            # Step 4: Live Session Token
            print("\n" + "-"*60)
            print("Step 4: Getting Live Session Token")
            print("-"*60)
            
            if auth.get_live_session_token():
                print("✅ Got live session token!")
            else:
                print("❌ Failed to get live session token")
        else:
            print("❌ Failed to get access token (expected without verifier)")
    else:
        print("❌ Failed to get request token")
        print("\nThis might mean:")
        print("1. TESTCONS is not active yet")
        print("2. Keys are not properly configured")
        print("3. Network/firewall issues")

if __name__ == "__main__":
    test_full_oauth_flow()