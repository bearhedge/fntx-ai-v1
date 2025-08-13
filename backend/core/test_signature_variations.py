#!/usr/bin/env python3
"""
Test different signature variations to find what IB expects
"""

import os
import sys
import json
import base64
import hmac
import hashlib
import requests
from urllib.parse import quote

# Load tokens
with open('/home/info/.ib_rest_tokens.json', 'r') as f:
    tokens = json.load(f)

access_token = tokens['access_token']
lst_b64 = tokens['live_session_token']
lst_bytes = base64.b64decode(lst_b64)
access_secret = tokens['access_token_secret']

print("Testing different signature approaches...")
print("="*70)

# Test parameters
oauth_params = {
    'oauth_consumer_key': 'BEARHEDGE',
    'oauth_nonce': 'test123456789',
    'oauth_signature_method': 'HMAC-SHA256',
    'oauth_timestamp': '1754900000',
    'oauth_token': access_token
}

method = 'GET'
url = 'https://api.ibkr.com/v1/api/portfolio/accounts'

# Sort params (no realm in signature)
sorted_params = sorted(oauth_params.items())
param_string = '&'.join([f"{k}={quote(str(v), safe='~')}" for k, v in sorted_params])

print(f"Parameter String:\n{param_string}\n")

# Create base string
base_string = f"{method}&{quote(url, safe='~')}&{quote(param_string, safe='~')}"
print(f"Base String:\n{base_string}\n")

# Test 1: Sign with LST directly
print("Test 1: Sign with LST directly")
sig1 = hmac.new(lst_bytes, base_string.encode('utf-8'), hashlib.sha256).digest()
sig1_b64 = base64.b64encode(sig1).decode('utf-8')
print(f"Signature: {sig1_b64}")

# Test 2: Sign with access_token_secret (decoded)
print("\nTest 2: Sign with decoded access_token_secret")
try:
    secret_bytes = base64.b64decode(access_secret)
    sig2 = hmac.new(secret_bytes, base_string.encode('utf-8'), hashlib.sha256).digest()
    sig2_b64 = base64.b64encode(sig2).decode('utf-8')
    print(f"Signature: {sig2_b64}")
except Exception as e:
    print(f"Error: {e}")

# Test 3: Sign with LST + access_secret combination
print("\nTest 3: Sign with LST + '&' + access_secret")
try:
    # OAuth 1.0a typically uses consumer_secret&token_secret
    # But we're using LST, so maybe it's LST&access_secret?
    combined_key = lst_bytes + b'&' + access_secret.encode('utf-8')
    sig3 = hmac.new(combined_key, base_string.encode('utf-8'), hashlib.sha256).digest()
    sig3_b64 = base64.b64encode(sig3).decode('utf-8')
    print(f"Signature: {sig3_b64}")
except Exception as e:
    print(f"Error: {e}")

# Test 4: Sign with consumer_secret (if we had one) + LST
print("\nTest 4: Sign with '&' + LST (no consumer secret)")
try:
    # Maybe it's just &LST (no consumer secret for First Party OAuth)
    combined_key = b'&' + base64.b64encode(lst_bytes)
    sig4 = hmac.new(combined_key, base_string.encode('utf-8'), hashlib.sha256).digest()
    sig4_b64 = base64.b64encode(sig4).decode('utf-8')
    print(f"Signature: {sig4_b64}")
except Exception as e:
    print(f"Error: {e}")

# Test each signature
signatures = [
    ("LST directly", sig1_b64),
    # Add more as needed
]

print("\n" + "="*70)
print("Testing each signature with actual request...")
print("="*70)

for desc, sig in signatures:
    print(f"\nTesting: {desc}")
    
    # Create header
    oauth_header_params = oauth_params.copy()
    oauth_header_params['oauth_signature'] = sig
    oauth_header_params['realm'] = 'limited_poa'
    
    header_parts = []
    for k, v in sorted(oauth_header_params.items()):
        if k.startswith('oauth_') or k == 'realm':
            header_parts.append(f'{k}="{quote(str(v), safe="~")}"')
    
    auth_header = f"OAuth {', '.join(header_parts)}"
    
    headers = {
        'Authorization': auth_header,
        'Accept': 'application/json',
        'User-Agent': 'python/3.11'
    }
    
    response = requests.get(url, headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code != 401:
        print(f"Response: {response.text[:200]}")
        print("✅ THIS SIGNATURE WORKS!")
        break
    else:
        print(f"Response: {response.text}")