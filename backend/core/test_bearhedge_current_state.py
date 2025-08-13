#!/usr/bin/env python3
"""
Test current state of BEARHEDGE authentication after fixes
This is a fresh test to avoid any caching issues
"""

import os
import sys
import time
import hmac
import hashlib
import base64
import secrets
from pathlib import Path
from urllib.parse import quote

# Fresh import - no caching
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

# Import the module fresh
sys.path.insert(0, '/home/info/fntx-ai-v1/backend')
from core.trading.ib_rest_auth import IBRestAuth

def test_current_implementation():
    """Test the current implementation to see what's actually happening"""
    print("\n" + "="*80)
    print("TESTING CURRENT IMPLEMENTATION STATE")
    print("="*80)
    
    # Check what's actually in the file
    auth_file = "/home/info/fntx-ai-v1/backend/core/trading/ib_rest_auth.py"
    with open(auth_file, 'r') as f:
        content = f.read()
    
    print("\n1. Checking Current Fixes:")
    print("-" * 40)
    
    # Check oauth_version
    if "'oauth_version': '1.0'" in content:
        print("✅ oauth_version='1.0' is present in code")
    else:
        print("❌ oauth_version='1.0' NOT found")
    
    # Check HMAC signature method
    hmac_start = content.find("def _sign_hmac_sha256")
    if hmac_start > 0:
        hmac_method = content[hmac_start:hmac_start + 1000]
        if "quote_plus" in hmac_method:
            print("❌ quote_plus still present in HMAC method (WRONG)")
        else:
            print("✅ quote_plus NOT in HMAC method (CORRECT)")
    
    # Initialize auth
    print("\n2. Testing Authentication:")
    print("-" * 40)
    
    auth = IBRestAuth()
    auth.access_token = os.getenv('IB_ACCESS_TOKEN')
    auth.access_token_secret = os.getenv('IB_ACCESS_TOKEN_SECRET')
    
    # Get LST
    print("Getting Live Session Token...")
    if not auth.get_live_session_token():
        print("❌ Failed to get LST")
        return False
    
    print(f"✅ Got LST (length: {len(auth.live_session_token)})")
    
    # Test raw HMAC signature generation
    print("\n3. Testing HMAC Signature Generation:")
    print("-" * 40)
    
    test_base_string = "GET&https%3A%2F%2Fapi.ibkr.com%2Fv1%2Fapi%2Fportfolio%2Faccounts&oauth_consumer_key%3DBEARHEDGE"
    
    # Test what the method actually returns
    signature = auth._sign_hmac_sha256(test_base_string, auth.live_session_token)
    print(f"Signature from method: {signature[:30]}...")
    
    # Check if it contains special characters
    has_plus = '+' in signature
    has_slash = '/' in signature
    has_equals = '=' in signature
    
    print(f"Contains '+': {has_plus}")
    print(f"Contains '/': {has_slash}")
    print(f"Contains '=': {has_equals}")
    
    if has_plus or has_slash:
        print("✅ Signature contains base64 special chars (not URL-encoded)")
    else:
        print("⚠️ Signature might be URL-encoded or doesn't have special chars")
    
    # Test actual authentication
    print("\n4. Testing Actual API Call:")
    print("-" * 40)
    
    result = auth.test_authentication()
    
    if result:
        print("✅ Authentication SUCCESSFUL!")
        return True
    else:
        print("❌ Authentication FAILED")
        
        # Try manual request to see exact error
        print("\n5. Manual Request for Debug:")
        print("-" * 40)
        
        import requests
        
        url = f"{auth.base_url}/portfolio/accounts"
        oauth_params = {
            'oauth_consumer_key': auth.consumer_key,
            'oauth_nonce': secrets.token_hex(16),
            'oauth_signature_method': 'HMAC-SHA256',
            'oauth_timestamp': str(int(time.time())),
            'oauth_token': auth.access_token,
            'oauth_version': '1.0'
        }
        
        # Create base string
        sorted_params = sorted(oauth_params.items())
        param_string = '&'.join([f"{quote(k, safe='~')}={quote(str(v), safe='~')}" for k, v in sorted_params])
        base_string = f"GET&{quote(url, safe='')}&{quote(param_string, safe='')}"
        
        # Sign it
        signature = auth._sign_hmac_sha256(base_string, auth.live_session_token)
        oauth_params['oauth_signature'] = signature
        
        # Create header
        auth_parts = [f'realm="{auth.realm}"']
        for k, v in sorted(oauth_params.items()):
            auth_parts.append(f'{k}="{v}"')
        auth_header = 'OAuth ' + ', '.join(auth_parts)
        
        headers = {'Authorization': auth_header, 'Accept': 'application/json'}
        
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        
        return False

if __name__ == "__main__":
    success = test_current_implementation()
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    if success:
        print("✅ BEARHEDGE authentication is WORKING!")
    else:
        print("❌ BEARHEDGE authentication still failing")
        print("\nNext steps to try:")
        print("1. Check if the Authorization header format is correct")
        print("2. Verify the base string encoding matches IBKR's expectations")
        print("3. Check timestamp synchronization")