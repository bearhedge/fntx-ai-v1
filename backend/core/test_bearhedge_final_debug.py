#!/usr/bin/env python3
"""
Final debug test with detailed output to understand why authentication still fails
"""

import os
import sys
import time
import hmac
import hashlib
import base64
import secrets
import json
import requests
import logging
from pathlib import Path
from urllib.parse import quote, quote_plus
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

# Enable DEBUG logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_with_extreme_detail():
    """Test with extreme detail to see exactly what's happening"""
    print("\n" + "="*80)
    print("FINAL DEBUG TEST WITH EXTREME DETAIL")
    print("="*80)
    
    # Initialize auth
    auth = IBRestAuth()
    auth.access_token = os.getenv('IB_ACCESS_TOKEN')
    auth.access_token_secret = os.getenv('IB_ACCESS_TOKEN_SECRET')
    
    print("1. Getting LST...")
    if not auth.get_live_session_token():
        print("❌ Failed to get LST")
        return
    print(f"✅ Got LST: {auth.live_session_token[:20]}...")
    
    # Manually construct request to see every detail
    url = f"{auth.base_url}/portfolio/accounts"
    method = "GET"
    
    # OAuth parameters WITH both fixes
    oauth_params = {
        'oauth_consumer_key': auth.consumer_key,
        'oauth_nonce': secrets.token_hex(16),
        'oauth_signature_method': 'HMAC-SHA256',
        'oauth_timestamp': str(int(time.time())),
        'oauth_token': auth.access_token,
        'oauth_version': '1.0'  # FIX 1: Include oauth_version
    }
    
    print("\n2. OAuth Parameters:")
    for k, v in oauth_params.items():
        if k == 'oauth_nonce':
            print(f"   {k}: {v[:10]}...")
        else:
            print(f"   {k}: {v}")
    
    # Create signature base string
    sorted_params = sorted(oauth_params.items())
    param_string = '&'.join([f"{quote(k, safe='~')}={quote(str(v), safe='~')}" for k, v in sorted_params])
    base_string = f"{method}&{quote(url, safe='')}&{quote(param_string, safe='')}"
    
    print("\n3. Base String:")
    print(f"   Length: {len(base_string)}")
    print(f"   First 200 chars: {base_string[:200]}...")
    
    # Check if oauth_version is in base string
    if 'oauth_version' in base_string:
        print("   ✅ oauth_version IS in base string")
    else:
        print("   ❌ oauth_version NOT in base string!")
    
    # Sign with LST
    lst_decoded = base64.b64decode(auth.live_session_token)
    signature_raw = hmac.new(lst_decoded, base_string.encode('utf-8'), hashlib.sha256).digest()
    signature_b64 = base64.b64encode(signature_raw).decode('utf-8')
    
    print(f"\n4. Signature (before encoding): {signature_b64[:30]}...")
    
    # FIX 2: URL-encode the signature
    signature_encoded = quote_plus(signature_b64)
    
    print(f"5. Signature (after quote_plus): {signature_encoded[:30]}...")
    
    # Check if encoding made a difference
    if signature_b64 != signature_encoded:
        print("   ✅ quote_plus DID encode the signature (contains special chars)")
    else:
        print("   ⚠️ quote_plus didn't change signature (no special chars)")
    
    # Add signature to params
    oauth_params['oauth_signature'] = signature_encoded
    
    # Create Authorization header
    auth_parts = []
    auth_parts.append(f'realm="{auth.realm}"')
    for k, v in sorted(oauth_params.items()):
        if k != 'realm':
            auth_parts.append(f'{k}="{v}"')
    auth_header = 'OAuth ' + ', '.join(auth_parts)
    
    print("\n6. Authorization Header:")
    print(f"   Length: {len(auth_header)}")
    
    # Check what's in the header
    if 'oauth_version' in auth_header:
        print("   ✅ oauth_version IS in header")
    else:
        print("   ❌ oauth_version NOT in header!")
    
    if quote_plus(signature_b64) in auth_header:
        print("   ✅ URL-encoded signature IS in header")
    elif signature_b64 in auth_header:
        print("   ❌ Raw signature in header (not URL-encoded!)")
    else:
        print("   ⚠️ Some other signature format in header")
    
    # Make request
    headers = {
        'Authorization': auth_header,
        'Accept': 'application/json'
    }
    
    print("\n7. Making Request...")
    print(f"   URL: {url}")
    print(f"   Method: {method}")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"\n8. Response:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("   ✅ SUCCESS! Authentication worked!")
            print(f"   Response: {response.text[:500]}")
        elif response.status_code == 401:
            print("   ❌ 401 Unauthorized")
            print(f"   Response: {response.text}")
            
            # Parse error if JSON
            try:
                error_data = response.json()
                print(f"   Error details: {json.dumps(error_data, indent=2)}")
            except:
                pass
        else:
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"   ❌ Request failed: {e}")
        import traceback
        traceback.print_exc()

def test_using_auth_class():
    """Test using the auth class directly to see if it works now"""
    print("\n" + "="*80)
    print("TESTING USING AUTH CLASS DIRECTLY")
    print("="*80)
    
    auth = IBRestAuth()
    auth.access_token = os.getenv('IB_ACCESS_TOKEN')
    auth.access_token_secret = os.getenv('IB_ACCESS_TOKEN_SECRET')
    
    print("1. Getting LST...")
    if not auth.get_live_session_token():
        print("❌ Failed to get LST")
        return
    
    print("2. Testing authentication...")
    result = auth.test_authentication()
    
    if result:
        print("✅ SUCCESS! Auth class works now!")
        accounts = auth.get_accounts()
        if accounts:
            print(f"Found {len(accounts)} accounts")
    else:
        print("❌ Auth class still fails")
        
        # Try a manual request with the class method
        print("\n3. Trying manual request with class method...")
        response = auth._make_authenticated_request('GET', f"{auth.base_url}/portfolio/accounts")
        if response:
            print(f"Response status: {response.status_code}")
            print(f"Response text: {response.text[:200]}")
        else:
            print("No response")

def main():
    """Run final debug tests"""
    print("\n" + "="*80)
    print("BEARHEDGE FINAL DEBUG - POST DOUBLE FIX")
    print("="*80)
    print(f"Time: {datetime.now()}")
    print("\nBoth fixes applied:")
    print("1. oauth_version='1.0' parameter")
    print("2. quote_plus encoding for HMAC signatures")
    
    # Test with extreme detail
    test_with_extreme_detail()
    
    # Test using auth class
    test_using_auth_class()
    
    print("\n" + "="*80)
    print("DEBUG COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()