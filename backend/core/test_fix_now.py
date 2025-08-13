#!/usr/bin/env python3
"""
DIRECT FIX TEST - NO BULLSHIT
"""

import os
import sys
import time
import hmac
import hashlib
import base64
import secrets
import requests
from pathlib import Path
from urllib.parse import quote

# Load env
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

sys.path.insert(0, '/home/info/fntx-ai-v1/backend')
from core.trading.ib_rest_auth import IBRestAuth

def test_all_key_formats():
    """Try EVERY FUCKING POSSIBLE WAY to use the LST"""
    print("\nTESTING ALL LST KEY FORMATS")
    print("="*60)
    
    auth = IBRestAuth()
    auth.access_token = os.getenv('IB_ACCESS_TOKEN')
    auth.access_token_secret = os.getenv('IB_ACCESS_TOKEN_SECRET')
    
    # Get LST
    if not auth.get_live_session_token():
        print("FAILED TO GET LST")
        return
    
    lst = auth.live_session_token
    print(f"LST (base64): {lst[:20]}...")
    
    # Test URL
    url = f"{auth.base_url}/portfolio/accounts"
    
    # Create consistent OAuth params
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
    
    # Apply IBKR-specific corrections
    base_string = base_string.replace('%257C', '%7C')
    base_string = base_string.replace('%252C', '%2C')
    base_string = base_string.replace('%253A', '%3A')
    
    print(f"\nBase string: {base_string[:100]}...")
    
    # Try different key formats
    tests = [
        ("Base64 decoded LST", base64.b64decode(lst)),
        ("Raw LST string as bytes", lst.encode('utf-8')),
        ("Hex decoded LST", bytes.fromhex(lst) if all(c in '0123456789abcdefABCDEF' for c in lst) else None),
        ("Access token secret decoded", base64.b64decode(auth.access_token_secret)),
        ("LST + Access Secret combo", base64.b64decode(lst) + base64.b64decode(auth.access_token_secret)),
    ]
    
    for name, key in tests:
        if key is None:
            continue
            
        print(f"\n{name}:")
        
        # Generate signature
        sig_raw = hmac.new(key, base_string.encode('utf-8'), hashlib.sha256).digest()
        signature = base64.b64encode(sig_raw).decode('utf-8')
        
        print(f"  Signature: {signature[:30]}...")
        
        # Make request
        test_params = oauth_params.copy()
        test_params['oauth_signature'] = signature
        
        auth_parts = [f'realm="{auth.realm}"']
        for k, v in sorted(test_params.items()):
            auth_parts.append(f'{k}="{v}"')
        auth_header = 'OAuth ' + ', '.join(auth_parts)
        
        headers = {'Authorization': auth_header, 'Accept': 'application/json'}
        
        response = requests.get(url, headers=headers, timeout=5)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"  ✅ SUCCESS! THIS IS THE RIGHT KEY FORMAT!")
            print(f"  Response: {response.text[:100]}")
            return True
        else:
            print(f"  ❌ Failed: {response.text[:100]}")
    
    return False

if __name__ == "__main__":
    success = test_all_key_formats()
    
    if not success:
        print("\n" + "="*60)
        print("STILL FAILING - THE ISSUE MIGHT BE:")
        print("1. The base string format")
        print("2. The Authorization header format")
        print("3. Something else in the OAuth flow")