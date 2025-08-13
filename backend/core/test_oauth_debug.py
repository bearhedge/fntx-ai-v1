#!/usr/bin/env python3
"""
Debug OAuth signature generation
"""

import os
import sys
import logging
import json
import base64
import hmac
import hashlib
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

# Add backend to path
sys.path.append('/home/info/fntx-ai-v1/backend')
from core.trading.ib_rest_auth import IBRestAuth

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(message)s'
)

def load_env_vars():
    """Load environment variables from .env file"""
    env_path = Path('/home/info/fntx-ai-v1/config/.env')
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    os.environ[key] = value

def test_signature_manually():
    """Manually create a signature to compare with the automated one"""
    
    print("="*70)
    print("MANUAL SIGNATURE TEST")
    print("="*70)
    
    # Load tokens
    with open('/home/info/.ib_rest_tokens.json', 'r') as f:
        tokens = json.load(f)
    
    # Get values
    access_token = tokens['access_token']
    lst_b64 = tokens['live_session_token']
    lst_bytes = base64.b64decode(lst_b64)
    
    # Create OAuth params
    oauth_params = {
        'oauth_consumer_key': 'BEARHEDGE',
        'oauth_nonce': 'test123456789',
        'oauth_signature_method': 'HMAC-SHA256',
        'oauth_timestamp': '1754900000',
        'oauth_token': access_token
    }
    
    # URL
    method = 'GET'
    url = 'https://api.ibkr.com/v1/api/portfolio/accounts'
    
    # Sort params (no realm in signature)
    sorted_params = sorted(oauth_params.items())
    
    # Create param string
    param_string = '&'.join([f"{k}={quote(str(v), safe='~')}" for k, v in sorted_params])
    print(f"\nParameter String:\n{param_string}")
    
    # Create base string
    base_string = f"{method}&{quote(url, safe='~')}&{quote(param_string, safe='~')}"
    print(f"\nBase String:\n{base_string}")
    
    # Create HMAC signature
    signature = hmac.new(lst_bytes, base_string.encode('utf-8'), hashlib.sha256).digest()
    signature_b64 = base64.b64encode(signature).decode('utf-8')
    print(f"\nSignature:\n{signature_b64}")
    
    # Create OAuth header
    oauth_params['oauth_signature'] = signature_b64  # Don't quote here
    oauth_params['realm'] = 'limited_poa'
    
    header_parts = []
    for k, v in sorted(oauth_params.items()):
        if k.startswith('oauth_') or k == 'realm':
            # Only quote if not already the signature
            if k == 'oauth_signature':
                header_parts.append(f'{k}="{quote(str(v), safe="~")}"')
            else:
                header_parts.append(f'{k}="{v}"')
    
    auth_header = f"OAuth {', '.join(header_parts)}"
    print(f"\nAuthorization Header:\n{auth_header}")
    
    # Now test with actual request
    import requests
    headers = {
        'Authorization': auth_header,
        'Accept': 'application/json',
        'User-Agent': 'python/3.11'
    }
    
    print(f"\nMaking request to: {url}")
    response = requests.get(url, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:200]}")

def main():
    load_env_vars()
    
    # First test manual signature
    test_signature_manually()
    
    print("\n" + "="*70)
    print("AUTOMATED SIGNATURE TEST")
    print("="*70)
    
    # Now test with the library
    auth = IBRestAuth()
    
    # Monkey patch to add logging
    original_sign = auth._sign_hmac_sha256
    def logged_sign(base_string, key):
        print(f"\n[AUTO] Base String:\n{base_string}")
        result = original_sign(base_string, key)
        print(f"[AUTO] Signature:\n{result}")
        return result
    auth._sign_hmac_sha256 = logged_sign
    
    # Test
    response = auth._make_authenticated_request('GET', 'https://api.ibkr.com/v1/api/portfolio/accounts')
    if response:
        print(f"\n[AUTO] Status: {response.status_code}")
        print(f"[AUTO] Response: {response.text[:200]}")

if __name__ == "__main__":
    main()