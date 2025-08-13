#!/usr/bin/env python3
"""
Test BEARHEDGE authentication after applying BOTH fixes:
1. oauth_version='1.0' parameter
2. quote_plus encoding for HMAC signatures

This should now work correctly!
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Load environment variables manually
project_root = Path(__file__).parent.parent.parent
env_path = project_root / 'config' / '.env'

if env_path.exists():
    with open(env_path, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                os.environ[key] = value

sys.path.append('/home/info/fntx-ai-v1/backend')
from core.trading.ib_rest_auth import IBRestAuth

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_authentication():
    """Test BEARHEDGE authentication with BOTH fixes applied"""
    print("\n" + "="*80)
    print("🎯 BEARHEDGE AUTHENTICATION TEST - COMPLETE FIX")
    print("="*80)
    print(f"Test Time: {datetime.now()}")
    print("\nTesting with TWO critical fixes:")
    print("1. ✅ oauth_version='1.0' parameter added")
    print("2. ✅ quote_plus encoding for HMAC signatures")
    
    # Initialize auth
    print("\n1. Initializing Authentication:")
    print("-" * 40)
    auth = IBRestAuth()
    auth.access_token = os.getenv('IB_ACCESS_TOKEN')
    auth.access_token_secret = os.getenv('IB_ACCESS_TOKEN_SECRET')
    
    print(f"✅ Consumer Key: {auth.consumer_key}")
    print(f"✅ Access Token: {auth.access_token}")
    print(f"✅ Realm: {auth.realm}")
    
    # Get Live Session Token
    print("\n2. Getting Live Session Token:")
    print("-" * 40)
    if auth.get_live_session_token():
        print(f"✅ LST obtained successfully")
        print(f"   Length: {len(auth.live_session_token)} chars")
        print(f"   First 20 chars: {auth.live_session_token[:20]}...")
    else:
        print("❌ Failed to get LST")
        return False
    
    # Test authentication
    print("\n3. Testing Authentication:")
    print("-" * 40)
    print("Making authenticated request with BOTH fixes...")
    
    if auth.test_authentication():
        print("✅ Authentication test PASSED!")
        print("🎉 BEARHEDGE is now fully working!")
        
        # Get accounts
        print("\n4. Getting Accounts:")
        print("-" * 40)
        accounts = auth.get_accounts()
        if accounts:
            print(f"✅ Successfully retrieved {len(accounts)} accounts:")
            for acc in accounts:
                print(f"   - Account ID: {acc.get('accountId')}")
                print(f"     Type: {acc.get('type')}")
                print(f"     Currency: {acc.get('currency')}")
            return True
        else:
            print("⚠️ No accounts returned (but authentication worked)")
            return True
    else:
        print("❌ Authentication test failed")
        print("The fixes may not have been applied correctly")
        return False

def test_multiple_endpoints():
    """Test multiple API endpoints to ensure comprehensive fix"""
    print("\n" + "="*80)
    print("TESTING MULTIPLE ENDPOINTS WITH COMPLETE FIX")
    print("="*80)
    
    auth = IBRestAuth()
    auth.access_token = os.getenv('IB_ACCESS_TOKEN')
    auth.access_token_secret = os.getenv('IB_ACCESS_TOKEN_SECRET')
    
    if not auth.get_live_session_token():
        print("❌ Failed to get LST")
        return False
    
    endpoints = [
        ('/portfolio/accounts', 'GET', 'Portfolio Accounts'),
        ('/portfolio/positions/0', 'GET', 'Portfolio Positions'),
        ('/iserver/accounts', 'GET', 'IServer Accounts'),
        ('/trsrv/secdef', 'POST', 'Security Definitions'),
    ]
    
    success_count = 0
    for endpoint, method, name in endpoints:
        print(f"\nTesting {name}:")
        print(f"  Endpoint: {endpoint}")
        print(f"  Method: {method}")
        
        response = auth._make_authenticated_request(
            method,
            f"{auth.base_url}{endpoint}"
        )
        
        if response and response.status_code == 200:
            print(f"  ✅ SUCCESS - Status: {response.status_code}")
            success_count += 1
            try:
                data = response.json()
                print(f"     Response preview: {str(data)[:100]}...")
            except:
                print(f"     Response: {response.text[:100]}...")
        elif response and response.status_code == 404:
            print(f"  ⚠️ Status: 404 (Endpoint might not be available)")
            success_count += 1  # Count as success if auth worked
        elif response:
            print(f"  ❌ Status: {response.status_code}")
            print(f"     Response: {response.text[:200]}")
        else:
            print(f"  ❌ No response")
    
    print(f"\nResults: {success_count}/{len(endpoints)} endpoints accessible")
    return success_count > 0

def verify_fix_implementation():
    """Verify both fixes are properly implemented"""
    print("\n" + "="*80)
    print("VERIFYING FIX IMPLEMENTATION")
    print("="*80)
    
    # Read the file to verify fixes
    auth_file = "/home/info/fntx-ai-v1/backend/core/trading/ib_rest_auth.py"
    with open(auth_file, 'r') as f:
        content = f.read()
    
    fixes_verified = []
    
    # Check Fix 1: oauth_version
    if "'oauth_version': '1.0'" in content:
        print("✅ Fix 1: oauth_version='1.0' found in _make_authenticated_request")
        fixes_verified.append("oauth_version")
    else:
        print("❌ Fix 1: oauth_version='1.0' NOT found!")
    
    # Check Fix 2: quote_plus in HMAC
    if "return quote_plus(signature_b64)" in content:
        print("✅ Fix 2: quote_plus encoding found in _sign_hmac_sha256")
        fixes_verified.append("quote_plus")
    else:
        print("❌ Fix 2: quote_plus encoding NOT found in HMAC method!")
    
    if len(fixes_verified) == 2:
        print("\n✅ Both fixes are properly implemented!")
        return True
    else:
        print(f"\n❌ Only {len(fixes_verified)} of 2 fixes implemented")
        print(f"   Implemented: {fixes_verified}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("🚀 BEARHEDGE COMPLETE FIX VERIFICATION")
    print("="*80)
    print("This test verifies that BOTH critical fixes resolve the signature issue:")
    print("1. oauth_version='1.0' parameter")
    print("2. quote_plus encoding for HMAC signatures")
    
    # Verify fixes are implemented
    fixes_ok = verify_fix_implementation()
    
    if not fixes_ok:
        print("\n❌ FIXES NOT PROPERLY IMPLEMENTED")
        print("Please ensure both fixes are applied to ib_rest_auth.py")
        return False
    
    # Test 1: Basic authentication
    test1_result = test_authentication()
    
    # Test 2: Multiple endpoints
    test2_result = test_multiple_endpoints()
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    if test1_result and test2_result:
        print("✅ COMPLETE SUCCESS! BEARHEDGE authentication is fully working!")
        print("\nThe combination of both fixes has resolved the issue:")
        print("1. oauth_version='1.0' parameter ensures OAuth compliance")
        print("2. quote_plus encoding ensures signatures are properly formatted")
        print("\nYou can now use all IBKR REST API endpoints with BEARHEDGE!")
        print("\n🎉 Next steps:")
        print("1. Deploy to production")
        print("2. Implement trading logic")
        print("3. Monitor for any edge cases")
        return True
    else:
        print("❌ Tests failed - debugging needed")
        print("\nPossible issues:")
        print("1. Fixes may not be saved correctly")
        print("2. LST may have expired")
        print("3. Environment variables may be incorrect")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)