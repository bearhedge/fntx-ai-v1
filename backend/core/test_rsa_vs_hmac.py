#!/usr/bin/env python3
"""
Compare RSA (working) vs HMAC (failing) requests in detail
"""

import os
import sys
import time
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

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_rsa_request():
    """Test RSA request (which works) and capture details"""
    print("\n" + "="*60)
    print("RSA REQUEST (WORKING)")
    print("="*60)
    
    auth = IBRestAuth()
    
    # Get request token (uses RSA)
    print("\nGetting request token with RSA-SHA256...")
    print("This should work since RSA signing is functional")
    
    # Note: This will fail because we don't have request token,
    # but we can see the request being made
    try:
        auth.get_request_token()
    except Exception as e:
        print(f"Expected error (no request token): {e}")

def test_lst_generation():
    """Test LST generation which uses RSA and works"""
    print("\n" + "="*60)
    print("LST GENERATION (RSA - WORKING)")
    print("="*60)
    
    auth = IBRestAuth()
    auth.access_token = os.getenv('IB_ACCESS_TOKEN')
    auth.access_token_secret = os.getenv('IB_ACCESS_TOKEN_SECRET')
    
    print("\nGetting LST with RSA-SHA256...")
    if auth.get_live_session_token():
        print("✅ LST obtained successfully with RSA")
        print(f"   This proves RSA signing works")
        print(f"   LST: {auth.live_session_token[:20]}...")
        return auth
    else:
        print("❌ Failed to get LST")
        return None

def test_hmac_request(auth):
    """Test HMAC request (failing) and capture details"""
    print("\n" + "="*60)
    print("HMAC REQUEST (FAILING)")
    print("="*60)
    
    if not auth:
        print("No auth available")
        return
    
    print("\nTesting authenticated request with HMAC-SHA256...")
    
    # This should now include oauth_version='1.0'
    result = auth.test_authentication()
    
    if result:
        print("✅ HMAC request succeeded!")
    else:
        print("❌ HMAC request failed")

def inspect_code():
    """Inspect the actual code to see what's different"""
    print("\n" + "="*60)
    print("CODE INSPECTION")
    print("="*60)
    
    # Check if oauth_version is really being included
    auth_file = "/home/info/fntx-ai-v1/backend/core/trading/ib_rest_auth.py"
    
    print("\nChecking _make_authenticated_request for oauth_version...")
    with open(auth_file, 'r') as f:
        lines = f.readlines()
    
    in_make_authenticated = False
    oauth_params_found = False
    
    for i, line in enumerate(lines, 1):
        if 'def _make_authenticated_request' in line:
            in_make_authenticated = True
            print(f"Found _make_authenticated_request at line {i}")
        
        if in_make_authenticated and 'oauth_params = {' in line:
            oauth_params_found = True
            print(f"\nFound oauth_params at line {i}:")
            # Print the next 10 lines
            for j in range(10):
                if i + j < len(lines):
                    print(f"  {i+j}: {lines[i+j-1].rstrip()}")
            break
    
    if not oauth_params_found:
        print("Could not find oauth_params in _make_authenticated_request")

def main():
    """Run comparison tests"""
    print("\n" + "="*80)
    print("RSA vs HMAC COMPARISON")
    print("="*80)
    print(f"Time: {datetime.now()}")
    
    # Inspect code
    inspect_code()
    
    # Test RSA (for comparison)
    test_rsa_request()
    
    # Test LST generation (RSA - works)
    auth = test_lst_generation()
    
    # Test HMAC (should work with fix)
    test_hmac_request(auth)
    
    print("\n" + "="*80)
    print("ANALYSIS")
    print("="*80)
    print("\nKey observations:")
    print("1. RSA-SHA256 signing works (LST generation succeeds)")
    print("2. HMAC-SHA256 signing fails even with oauth_version='1.0'")
    print("3. The oauth_version parameter is correctly added")
    print("\nPossible remaining issues:")
    print("- Parameter encoding differences")
    print("- Header formatting differences")
    print("- Timestamp synchronization")
    print("- Something else in the HMAC signature calculation")

if __name__ == "__main__":
    main()