#!/usr/bin/env python3
"""
Test direct request with manual OAuth header
"""

import json
import base64
import hmac
import hashlib
import requests
import time
from urllib.parse import quote

# Load tokens
with open('/home/info/.ib_rest_tokens.json', 'r') as f:
    tokens = json.load(f)

access_token = tokens['access_token']
lst_b64 = tokens['live_session_token']
lst_bytes = base64.b64decode(lst_b64)

print("Testing direct OAuth request with fixed signature...")
print("="*70)

# OAuth parameters
oauth_params = {
    'oauth_consumer_key': 'BEARHEDGE',
    'oauth_nonce': 'test' + str(int(time.time())),
    'oauth_signature_method': 'HMAC-SHA256',
    'oauth_timestamp': str(int(time.time())),
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
print(f"Base String (first 200 chars):\n{base_string[:200]}...\n")

# Test different signing key formats
print("Testing different key formats:")
print("-"*40)

# Format 1: Just LST
print("1. Using LST directly as key")
sig1 = hmac.new(lst_bytes, base_string.encode('utf-8'), hashlib.sha256).digest()
sig1_b64 = base64.b64encode(sig1).decode('utf-8')
print(f"   Signature: {sig1_b64[:30]}...")

# Format 2: "&" + LST (OAuth 1.0a standard)
print("\n2. Using '&' + LST as key (OAuth 1.0a standard)")
signing_key = b'&' + lst_bytes
sig2 = hmac.new(signing_key, base_string.encode('utf-8'), hashlib.sha256).digest()
sig2_b64 = base64.b64encode(sig2).decode('utf-8')
print(f"   Signature: {sig2_b64[:30]}...")

# Test both signatures
signatures_to_test = [
    ("LST directly", sig1_b64),
    ("'&' + LST", sig2_b64)
]

print("\n" + "="*70)
print("Testing each signature...")
print("="*70)

for desc, sig in signatures_to_test:
    print(f"\nTesting: {desc}")
    
    # Create OAuth header
    oauth_header_params = oauth_params.copy()
    oauth_header_params['oauth_signature'] = sig
    oauth_header_params['realm'] = 'limited_poa'
    
    header_parts = []
    for k, v in sorted(oauth_header_params.items()):
        if k.startswith('oauth_') or k == 'realm':
            header_parts.append(f'{k}="{quote(str(v), safe="~")}"')
    
    auth_header = f"OAuth {', '.join(header_parts)}"
    print(f"Auth Header (first 100 chars): {auth_header[:100]}...")
    
    headers = {
        'Authorization': auth_header,
        'Accept': 'application/json',
        'User-Agent': 'python/3.11'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ THIS WORKS!")
            print(f"Response: {response.text[:200]}")
            break
        else:
            print(f"Response: {response.text[:100]}")
    except Exception as e:
        print(f"Error: {e}")