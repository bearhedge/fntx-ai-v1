#!/usr/bin/env python3
"""
Minimal test for BEARHEDGE consumer key
Tests direct authentication without OAuth portal flow
"""

import os
import sys
import logging
from pathlib import Path

# Load environment variables manually
project_root = Path(__file__).parent.parent.parent
env_path = project_root / 'config' / '.env'

if env_path.exists():
    with open(env_path, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                os.environ[key] = value

sys.path.append('/home/info/fntx-ai-v1/backend')
from core.trading.ib_rest_auth import IBRestAuth

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_bearhedge_direct():
    """Test BEARHEDGE with direct access token approach"""
    print("\n" + "="*60)
    print("BEARHEDGE DIRECT AUTHENTICATION TEST")
    print("="*60)
    print("Testing without OAuth portal flow as confirmed by IBKR")
    
    # Check environment
    print("\n1. Checking Environment Variables:")
    print("-" * 40)
    consumer_key = os.getenv('IB_CONSUMER_KEY')
    access_token = os.getenv('IB_ACCESS_TOKEN')
    access_token_secret = os.getenv('IB_ACCESS_TOKEN_SECRET')
    
    print(f"Consumer Key: {consumer_key}")
    print(f"Access Token: {access_token}")
    print(f"Access Token Secret: {'SET' if access_token_secret else 'NOT SET'}")
    print(f"Secret Length: {len(access_token_secret) if access_token_secret else 0} chars")
    
    if not all([consumer_key, access_token, access_token_secret]):
        print("\n❌ Missing required credentials!")
        return False
    
    # Initialize auth handler
    print("\n2. Initializing Authentication Handler:")
    print("-" * 40)
    try:
        auth = IBRestAuth()
        print(f"✅ Handler initialized")
        print(f"   Base URL: {auth.base_url}")
        print(f"   Realm: {auth.realm}")
        
        # Set tokens directly (skip request token flow)
        auth.access_token = access_token
        auth.access_token_secret = access_token_secret
        print(f"✅ Access tokens set directly")
        
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return False
    
    # Get Live Session Token
    print("\n3. Getting Live Session Token (LST):")
    print("-" * 40)
    try:
        if auth.get_live_session_token():
            print(f"✅ Got LST successfully!")
            print(f"   LST Length: {len(auth.live_session_token)} chars")
        else:
            print(f"❌ Failed to get LST")
            print("   This might mean BEARHEDGE is not activated")
            return False
    except Exception as e:
        print(f"❌ LST generation error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test API Access
    print("\n4. Testing API Access - Get Accounts:")
    print("-" * 40)
    try:
        accounts = auth.get_accounts()
        if accounts:
            print(f"✅ SUCCESS! Retrieved {len(accounts)} accounts:")
            for account in accounts:
                print(f"   - {account.get('accountId')} ({account.get('type')})")
            return True
        else:
            print(f"❌ No accounts retrieved (but no error)")
            return False
    except Exception as e:
        print(f"❌ API call failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_endpoint():
    """Test a simple endpoint that doesn't require brokerage session"""
    print("\n" + "="*60)
    print("TESTING SIMPLE ENDPOINT")
    print("="*60)
    
    try:
        auth = IBRestAuth()
        auth.access_token = os.getenv('IB_ACCESS_TOKEN')
        auth.access_token_secret = os.getenv('IB_ACCESS_TOKEN_SECRET')
        
        # Try to get LST
        if not auth.get_live_session_token():
            print("❌ Could not get LST")
            return False
        
        # Try portfolio endpoint
        print("\nTrying /portfolio/accounts endpoint...")
        response = auth._make_authenticated_request(
            'GET', 
            f"{auth.base_url}/portfolio/accounts"
        )
        
        if response:
            print(f"Response Status: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
            if response.status_code == 200:
                print("✅ Endpoint accessible!")
                return True
            elif response.status_code == 401:
                print("❌ 401 Unauthorized - Authentication issue")
            elif response.status_code == 403:
                print("❌ 403 Forbidden - Permission issue")
            else:
                print(f"❌ Unexpected status: {response.status_code}")
        else:
            print("❌ No response received")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("BEARHEDGE CONSUMER KEY TEST")
    print("="*60)
    print("Testing direct Python access as confirmed by IBKR")
    print("No OAuth portal flow needed!")
    
    # Test 1: Direct authentication
    success = test_bearhedge_direct()
    
    if not success:
        print("\n" + "="*60)
        print("TRYING ALTERNATE ENDPOINT")
        print("="*60)
        # Test 2: Try simple endpoint
        success = test_simple_endpoint()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    if success:
        print("✅ BEARHEDGE WORKS! You can use Python directly.")
        print("\nNext steps:")
        print("1. Run full test suite: python test_ib_rest_auth.py")
        print("2. Test trading endpoints: python test_bearhedge_endpoints.py")
        print("3. Execute trades: python execute_spy_trades_rest.py")
    else:
        print("❌ BEARHEDGE authentication failed")
        print("\nPossible issues:")
        print("1. BEARHEDGE consumer key not activated by IBKR")
        print("2. Access token/secret may be incorrect")
        print("3. Keys may not be properly associated")
        print("\nContact IBKR support to verify:")
        print("- BEARHEDGE consumer key is active")
        print("- Public keys are properly uploaded and saved")
        print("- Access token/secret are valid")

if __name__ == "__main__":
    main()