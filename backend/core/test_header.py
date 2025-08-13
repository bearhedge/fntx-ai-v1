#!/usr/bin/env python3
"""
Test different Authorization header formats
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
from urllib.parse import quote, quote_plus

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

auth = IBRestAuth()
auth.access_token = os.getenv('IB_ACCESS_TOKEN')
auth.access_token_secret = os.getenv('IB_ACCESS_TOKEN_SECRET')

# Get LST
if not auth.get_live_session_token():
    print("FAILED TO GET LST")
    exit(1)

url = f"{auth.base_url}/portfolio/accounts"

# OAuth params
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

# IBKR corrections
base_string = base_string.replace('%257C', '%7C')
base_string = base_string.replace('%252C', '%2C')
base_string = base_string.replace('%253A', '%3A')

# Generate signature
lst_decoded = base64.b64decode(auth.live_session_token)
sig_raw = hmac.new(lst_decoded, base_string.encode('utf-8'), hashlib.sha256).digest()
signature = base64.b64encode(sig_raw).decode('utf-8')

print(f"Testing with signature: {signature}")

# Test 1: URL-encoded signature
p = oauth_params.copy()
p['oauth_signature'] = quote_plus(signature)
parts = [f'realm="{auth.realm}"']
for k, v in sorted(p.items()):
    parts.append(f'{k}="{v}"')
auth_header = 'OAuth ' + ', '.join(parts)

headers = {'Authorization': auth_header, 'Accept': 'application/json'}
response = requests.get(url, headers=headers, timeout=5)
print(f"URL-encoded signature: {response.status_code}")
if response.status_code == 200:
    print("✅ SUCCESS WITH URL-ENCODED SIGNATURE!")
else:
    print(f"Failed: {response.text}")