#!/usr/bin/env python3
"""
Test if we're following OAuth 1.0a spec EXACTLY
"""

import os
import sys
import time
import hmac
import hashlib
import base64
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

print("CHECKING OAUTH 1.0a SIGNATURE SPEC")
print("="*60)

auth = IBRestAuth()
auth.access_token = os.getenv('IB_ACCESS_TOKEN')
auth.access_token_secret = os.getenv('IB_ACCESS_TOKEN_SECRET')

if not auth.get_live_session_token():
    print("FAILED TO GET LST")
    exit(1)

url = "https://api.ibkr.com/v1/api/portfolio/accounts"
method = "GET"

# Step 1: OAuth parameters (NO realm in signature)
params = {
    'oauth_consumer_key': auth.consumer_key,
    'oauth_nonce': 'test123456789',  # Fixed for testing
    'oauth_signature_method': 'HMAC-SHA256',
    'oauth_timestamp': '1234567890',  # Fixed for testing
    'oauth_token': auth.access_token,
    'oauth_version': '1.0'
}

print("\n1. OAuth Parameters (for signature):")
for k, v in sorted(params.items()):
    print(f"   {k}={v}")

# Step 2: Parameter string
param_pairs = []
for k, v in sorted(params.items()):
    param_pairs.append(f"{quote(k, safe='')}={quote(v, safe='')}")
param_string = '&'.join(param_pairs)

print(f"\n2. Parameter String:")
print(f"   {param_string[:100]}...")

# Step 3: Base string
base_string = f"{method}&{quote(url, safe='')}&{quote(param_string, safe='')}"

print(f"\n3. Base String (before corrections):")
print(f"   {base_string[:150]}...")

# Step 4: IBKR corrections
base_string = base_string.replace('%257C', '%7C')
base_string = base_string.replace('%252C', '%2C')
base_string = base_string.replace('%253A', '%3A')

print(f"\n4. Base String (after IBKR corrections):")
print(f"   {base_string[:150]}...")

# Step 5: HMAC key - THIS IS THE CRITICAL PART
print(f"\n5. HMAC Key Options:")
print(f"   LST (base64): {auth.live_session_token[:20]}...")

lst_decoded = base64.b64decode(auth.live_session_token)
print(f"   LST decoded: {len(lst_decoded)} bytes")

# According to OAuth spec for HMAC-SHA256:
# The key is the concatenated values of:
# 1. Consumer secret (we don't have this for OAuth 1.0a with RSA)
# 2. An "&" character
# 3. Token secret (this is our LST)

# But IBKR might want just the LST
keys_to_try = [
    ("LST only (decoded)", lst_decoded),
    ("LST only (base64 string)", auth.live_session_token.encode('utf-8')),
    ("Empty&LST", b'&' + lst_decoded),
    ("ConsumerKey&LST", auth.consumer_key.encode('utf-8') + b'&' + lst_decoded),
]

for key_name, key in keys_to_try:
    print(f"\n6. Testing with key: {key_name}")
    
    # Generate signature
    signature_bytes = hmac.new(key, base_string.encode('utf-8'), hashlib.sha256).digest()
    signature = base64.b64encode(signature_bytes).decode('utf-8')
    
    print(f"   Signature: {signature}")
    
    # Add signature to params
    params_with_sig = params.copy()
    params_with_sig['oauth_signature'] = signature
    
    # Create header (realm first, then sorted params)
    header_parts = [f'realm="{auth.realm}"']
    for k, v in sorted(params_with_sig.items()):
        # OAuth spec says to percent-encode the values in the header
        header_parts.append(f'{k}="{quote(v, safe="")}"')
    
    auth_header = 'OAuth ' + ', '.join(header_parts)
    
    print(f"   Header: {auth_header[:100]}...")
    
    # Make request with REAL timestamp
    real_params = {
        'oauth_consumer_key': auth.consumer_key,
        'oauth_nonce': str(time.time()),
        'oauth_signature_method': 'HMAC-SHA256',
        'oauth_timestamp': str(int(time.time())),
        'oauth_token': auth.access_token,
        'oauth_version': '1.0'
    }
    
    # Recalculate with real params
    real_param_string = '&'.join([f"{quote(k, safe='')}={quote(v, safe='')}" for k, v in sorted(real_params.items())])
    real_base_string = f"{method}&{quote(url, safe='')}&{quote(real_param_string, safe='')}"
    real_base_string = real_base_string.replace('%257C', '%7C').replace('%252C', '%2C').replace('%253A', '%3A')
    
    real_signature_bytes = hmac.new(key, real_base_string.encode('utf-8'), hashlib.sha256).digest()
    real_signature = base64.b64encode(real_signature_bytes).decode('utf-8')
    
    real_params['oauth_signature'] = real_signature
    
    real_header_parts = [f'realm="{auth.realm}"']
    for k, v in sorted(real_params.items()):
        real_header_parts.append(f'{k}="{quote(v, safe="")}"')
    
    real_auth_header = 'OAuth ' + ', '.join(real_header_parts)
    
    headers = {'Authorization': real_auth_header, 'Accept': 'application/json'}
    response = requests.get(url, headers=headers, timeout=5)
    
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        print(f"   ✅ SUCCESS! The key format is: {key_name}")
        print(f"   Response: {response.text[:200]}")
        exit(0)
    else:
        print(f"   ❌ Failed: {response.text[:100]}")