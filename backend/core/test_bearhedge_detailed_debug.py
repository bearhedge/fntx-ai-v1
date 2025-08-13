#!/usr/bin/env python3
"""
Detailed debug of BEARHEDGE authentication after oauth_version fix
Shows exactly what's being sent and received
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
from pathlib import Path
from urllib.parse import quote
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

def test_with_manual_request():
    """Manually construct and test the request to see exact error"""
    print("\n" + "="*60)
    print("MANUAL REQUEST TEST WITH OAUTH_VERSION")
    print("="*60)
    
    # Initialize auth to get LST
    auth = IBRestAuth()
    auth.access_token = os.getenv('IB_ACCESS_TOKEN')
    auth.access_token_secret = os.getenv('IB_ACCESS_TOKEN_SECRET')
    
    print("1. Getting LST...")
    if not auth.get_live_session_token():
        print("❌ Failed to get LST")
        return
    print(f"✅ Got LST: {auth.live_session_token[:20]}...")
    
    # Manually construct request
    url = f"{auth.base_url}/portfolio/accounts"
    method = "GET"
    
    # OAuth parameters WITH oauth_version
    oauth_params = {
        'oauth_consumer_key': auth.consumer_key,
        'oauth_nonce': secrets.token_hex(16),
        'oauth_signature_method': 'HMAC-SHA256',
        'oauth_timestamp': str(int(time.time())),
        'oauth_token': auth.access_token,
        'oauth_version': '1.0'  # INCLUDED!
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
    
    print("\n3. Signature Base String:")
    print(f"   Length: {len(base_string)}")
    print(f"   First 200 chars: {base_string[:200]}...")
    
    # Check if oauth_version is in the base string
    if 'oauth_version' in base_string:
        print("   ✅ oauth_version IS in base string")
    else:
        print("   ❌ oauth_version NOT in base string!")
    
    # Sign with LST
    lst_decoded = base64.b64decode(auth.live_session_token)
    signature = base64.b64encode(
        hmac.new(lst_decoded, base_string.encode('utf-8'), hashlib.sha256).digest()
    ).decode('utf-8')
    
    print(f"\n4. Signature: {signature[:30]}...")
    
    # Add signature to params
    oauth_params['oauth_signature'] = signature
    
    # Create Authorization header
    auth_parts = []
    auth_parts.append(f'realm="{auth.realm}"')
    for k, v in sorted(oauth_params.items()):
        if k != 'realm':
            auth_parts.append(f'{k}="{v}"')
    auth_header = 'OAuth ' + ', '.join(auth_parts)
    
    print("\n5. Authorization Header:")
    print(f"   Length: {len(auth_header)}")
    print(f"   First 200 chars: {auth_header[:200]}...")
    
    # Check if oauth_version is in the header
    if 'oauth_version' in auth_header:
        print("   ✅ oauth_version IS in header")
    else:
        print("   ❌ oauth_version NOT in header!")
    
    # Make request
    headers = {
        'Authorization': auth_header,
        'Accept': 'application/json'
    }
    
    print("\n6. Making Request...")
    print(f"   URL: {url}")
    print(f"   Method: {method}")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"\n7. Response:")
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

def compare_with_rsa_request():
    """Compare parameters between working RSA and failing HMAC requests"""
    print("\n" + "="*60)
    print("COMPARING RSA vs HMAC PARAMETERS")
    print("="*60)
    
    auth = IBRestAuth()
    
    print("\n1. RSA Request Parameters (from get_request_token):")
    print("   - oauth_callback")
    print("   - oauth_consumer_key")
    print("   - oauth_nonce")
    print("   - oauth_signature_method (RSA-SHA256)")
    print("   - oauth_timestamp")
    print("   - oauth_version ✅")
    print("   - realm (in header, not signature)")
    
    print("\n2. HMAC Request Parameters (from _make_authenticated_request):")
    print("   - oauth_consumer_key")
    print("   - oauth_nonce")
    print("   - oauth_signature_method (HMAC-SHA256)")
    print("   - oauth_timestamp")
    print("   - oauth_token")
    print("   - oauth_version ✅ (NOW ADDED)")
    print("   - realm (in header, not signature)")
    
    print("\n3. Key Differences:")
    print("   - RSA has oauth_callback, HMAC doesn't (expected)")
    print("   - HMAC has oauth_token, RSA doesn't (expected)")
    print("   - Both now have oauth_version='1.0'")

def check_implementation():
    """Verify the fix was applied correctly"""
    print("\n" + "="*60)
    print("CHECKING IMPLEMENTATION")
    print("="*60)
    
    # Read the file to verify the fix
    auth_file = "/home/info/fntx-ai-v1/backend/core/trading/ib_rest_auth.py"
    with open(auth_file, 'r') as f:
        content = f.read()
    
    # Check if oauth_version is in _make_authenticated_request
    if "'oauth_version': '1.0'" in content:
        print("✅ oauth_version='1.0' found in file")
        
        # Find the context
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if "'oauth_version': '1.0'" in line:
                print(f"   Found at line {i+1}")
                print(f"   Context:")
                for j in range(max(0, i-3), min(len(lines), i+4)):
                    print(f"      {j+1}: {lines[j]}")
                break
    else:
        print("❌ oauth_version='1.0' NOT found in file!")

def main():
    """Run all debug tests"""
    print("\n" + "="*80)
    print("BEARHEDGE DETAILED DEBUG - POST FIX")
    print("="*80)
    print(f"Time: {datetime.now()}")
    
    # Check implementation
    check_implementation()
    
    # Compare parameters
    compare_with_rsa_request()
    
    # Test with manual request
    test_with_manual_request()
    
    print("\n" + "="*80)
    print("DEBUG COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()