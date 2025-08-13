#!/usr/bin/env python3
"""
Minimal authentication test - try the simplest possible approach
"""

import requests
import time
import hashlib
import hmac
import secrets
import base64
from urllib.parse import quote
from datetime import datetime

def test_minimal_request():
    """Test with minimal OAuth parameters"""
    print("="*60)
    print("MINIMAL OAUTH REQUEST TEST")
    print("="*60)
    
    # Minimal OAuth parameters
    oauth_params = {
        'oauth_consumer_key': 'BEARHEDGE',
        'oauth_nonce': secrets.token_hex(16),
        'oauth_signature_method': 'HMAC-SHA1',  # Try HMAC instead of RSA
        'oauth_timestamp': str(int(time.time())),
        'oauth_version': '1.0'
    }
    
    # Create signature base string
    method = 'POST'
    url = 'https://api.ibkr.com/v1/api/oauth/request_token'
    
    # Sort parameters
    sorted_params = sorted(oauth_params.items())
    param_string = '&'.join([f"{k}={quote(str(v), safe='')}" for k, v in sorted_params])
    
    # Create base string
    base_string = f"{method}&{quote(url, safe='')}&{quote(param_string, safe='')}"
    
    print(f"\nBase String: {base_string[:100]}...")
    
    # Create signature with empty key (for testing)
    signature = base64.b64encode(
        hmac.new(b'&', base_string.encode(), hashlib.sha1).digest()
    ).decode()
    
    oauth_params['oauth_signature'] = signature
    
    # Create authorization header
    auth_parts = []
    for k, v in sorted(oauth_params.items()):
        auth_parts.append(f'{k}="{quote(str(v), safe="")}"')
    auth_header = f"OAuth {', '.join(auth_parts)}"
    
    print(f"\nAuthorization Header: {auth_header[:100]}...")
    
    # Make request
    headers = {
        'Authorization': auth_header,
        'Accept': 'application/json'
    }
    
    print(f"\nMaking request to: {url}")
    response = requests.post(url, headers=headers, timeout=10)
    
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    return response

def test_with_callback():
    """Test with oauth_callback parameter"""
    print("\n" + "="*60)
    print("OAUTH REQUEST WITH CALLBACK TEST")
    print("="*60)
    
    # OAuth parameters with callback
    oauth_params = {
        'oauth_callback': 'oob',  # Out of band
        'oauth_consumer_key': 'BEARHEDGE',
        'oauth_nonce': secrets.token_hex(16),
        'oauth_signature_method': 'PLAINTEXT',  # Try plaintext
        'oauth_timestamp': str(int(time.time())),
        'oauth_version': '1.0'
    }
    
    # For PLAINTEXT, signature is consumer_secret&token_secret
    # Since we don't have consumer secret, try empty
    oauth_params['oauth_signature'] = '&'
    
    # Create authorization header
    auth_parts = []
    for k, v in sorted(oauth_params.items()):
        if k != 'oauth_signature':
            auth_parts.append(f'{k}="{quote(str(v), safe="")}"')
    auth_parts.append(f'oauth_signature="{oauth_params["oauth_signature"]}"')
    auth_header = f"OAuth {', '.join(auth_parts)}"
    
    print(f"\nAuthorization Header: {auth_header}")
    
    # Make request
    url = 'https://api.ibkr.com/v1/api/oauth/request_token'
    headers = {
        'Authorization': auth_header,
        'Accept': 'application/json'
    }
    
    response = requests.post(url, headers=headers, timeout=10)
    
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    return response

if __name__ == "__main__":
    print("Testing IBKR OAuth with minimal approach")
    print(f"Timestamp: {datetime.now()}")
    
    # Test 1: Minimal HMAC-SHA1
    test_minimal_request()
    
    # Test 2: With callback
    test_with_callback()