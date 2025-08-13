#!/usr/bin/env python3
"""
Compare the EXACT differences between RSA (working) and HMAC (failing) requests
"""

import os
import sys
import time
import hmac
import hashlib
import base64
from pathlib import Path
from urllib.parse import quote
import logging

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG)

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

print("COMPARING RSA vs HMAC REQUESTS")
print("="*60)

# Monkey-patch to capture what's being sent
original_make_request = IBRestAuth._make_authenticated_request

def capture_hmac_request(self, method, url, params=None, data=None):
    print("\nHMAC REQUEST DETAILS:")
    print("-"*40)
    
    # Show the oauth params being created
    oauth_params = {
        'oauth_consumer_key': self.consumer_key,
        'oauth_nonce': self._generate_nonce(),
        'oauth_signature_method': 'HMAC-SHA256',
        'oauth_timestamp': self._get_timestamp(),
        'oauth_token': self.access_token,
        'oauth_version': '1.0',
        'realm': self.realm
    }
    
    print(f"OAuth params:")
    for k, v in oauth_params.items():
        if k == 'oauth_nonce':
            print(f"  {k}: {v[:10]}...")
        else:
            print(f"  {k}: {v}")
    
    # Show base string creation
    sig_params = {k: v for k, v in oauth_params.items() if k != 'realm'}
    sorted_params = sorted(sig_params.items())
    param_string = '&'.join([f"{self._percent_encode(k)}={self._percent_encode(v)}" for k, v in sorted_params])
    base_string = f"{method.upper()}&{self._percent_encode(url)}&{self._percent_encode(param_string)}"
    
    # Apply corrections
    base_string = base_string.replace('%257C', '%7C')
    base_string = base_string.replace('%252C', '%2C')
    base_string = base_string.replace('%253A', '%3A')
    
    print(f"\nBase string: {base_string[:150]}...")
    
    # Show signature
    signature = self._sign_hmac_sha256(base_string, self.live_session_token)
    print(f"\nSignature: {signature}")
    print(f"  Contains +: {'+' in signature}")
    print(f"  Contains /: {'/' in signature}")
    print(f"  Contains =: {'=' in signature}")
    
    return original_make_request(self, method, url, params, data)

# Apply monkey patch
IBRestAuth._make_authenticated_request = capture_hmac_request

# Now test
auth = IBRestAuth()
auth.access_token = os.getenv('IB_ACCESS_TOKEN')
auth.access_token_secret = os.getenv('IB_ACCESS_TOKEN_SECRET')

print("\n1. Getting LST (RSA - WORKS):")
print("="*40)
# This uses RSA and works
if auth.get_live_session_token():
    print("✅ LST obtained with RSA")
else:
    print("❌ Failed to get LST")
    exit(1)

print("\n2. Testing API call (HMAC - FAILS):")
print("="*40)
# This uses HMAC and fails
result = auth.test_authentication()

if result:
    print("\n✅ HMAC WORKED!")
else:
    print("\n❌ HMAC FAILED")

print("\n" + "="*60)
print("KEY OBSERVATION:")
print("RSA works for LST generation")
print("HMAC fails for API calls with same OAuth flow")
print("The difference must be in the signature calculation")