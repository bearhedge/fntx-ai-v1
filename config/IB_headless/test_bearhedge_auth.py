#!/usr/bin/env python3
"""
Test script for IBKR OAuth authentication with BEARHEDGE consumer key
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.IB_headless.ib_rest_auth_consolidated import IBRestAuth

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_authentication():
    """Test OAuth authentication flow"""
    print("\n" + "="*60)
    print("IBKR OAuth Authentication Test with BEARHEDGE")
    print("="*60)
    
    # Initialize with BEARHEDGE consumer key
    auth = IBRestAuth(
        consumer_key='BEARHEDGE',
        realm='limited_poa'
    )
    
    print(f"\nConsumer Key: {auth.consumer_key}")
    print(f"Realm: {auth.realm}")
    print(f"Signature Key: {auth.signature_key_path}")
    print(f"Encryption Key: {auth.encryption_key_path}")
    print(f"DH Param Path: {auth.dh_param_path}")
    
    # Check if we have pre-configured tokens
    access_token = os.getenv('IB_ACCESS_TOKEN')
    access_token_secret = os.getenv('IB_ACCESS_TOKEN_SECRET')
    
    if access_token and access_token_secret:
        print(f"\nFound pre-configured tokens:")
        print(f"Access Token: {access_token}")
        print(f"Access Token Secret: {access_token_secret[:20]}...")
        
        auth.access_token = access_token
        auth.access_token_secret = access_token_secret
        
        # Try to get live session token
        print("\n" + "-"*40)
        print("Getting Live Session Token...")
        print("-"*40)
        
        if auth.get_live_session_token():
            print("✓ Successfully got Live Session Token")
            print(f"LST: {auth.live_session_token[:20]}...")
        else:
            print("✗ Failed to get Live Session Token")
            return False
    else:
        print("\n⚠ No pre-configured tokens found")
        print("For BEARHEDGE testing, you need to set:")
        print("  - IB_ACCESS_TOKEN")
        print("  - IB_ACCESS_TOKEN_SECRET")
        return False
    
    return True

def test_api_calls(auth):
    """Test various API endpoints"""
    print("\n" + "="*60)
    print("Testing API Endpoints")
    print("="*60)
    
    # Test 1: Get Accounts (should work with BEARHEDGE)
    print("\n1. Testing /portfolio/accounts")
    print("-"*40)
    
    response = auth.make_authenticated_request('GET', '/portfolio/accounts')
    if response:
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✓ SUCCESS - Got accounts")
            accounts = response.json()
            print(f"Response: {accounts}")
        else:
            print(f"✗ Failed: {response.text}")
    else:
        print("✗ No response received")
    
    # Test 2: Get Account Summary
    print("\n2. Testing /portfolio/U19860056/summary")
    print("-"*40)
    
    response = auth.make_authenticated_request('GET', '/portfolio/U19860056/summary')
    if response:
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✓ SUCCESS - Got account summary")
            print(f"Response: {response.json()}")
        else:
            print(f"✗ Failed: {response.text}")
    
    # Test 3: Get Positions
    print("\n3. Testing /portfolio/U19860056/positions/0")
    print("-"*40)
    
    response = auth.make_authenticated_request('GET', '/portfolio/U19860056/positions/0')
    if response:
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✓ SUCCESS - Got positions")
            print(f"Response: {response.json()}")
        else:
            print(f"✗ Failed: {response.text}")

def main():
    """Main test function"""
    try:
        # Create auth instance
        auth = IBRestAuth(
            consumer_key='BEARHEDGE',
            realm='limited_poa'
        )
        
        # Test authentication
        if test_authentication():
            print("\n✓ Authentication setup successful")
            
            # Test API calls
            test_api_calls(auth)
        else:
            print("\n✗ Authentication setup failed")
            return 1
        
        print("\n" + "="*60)
        print("Test Complete")
        print("="*60)
        return 0
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())