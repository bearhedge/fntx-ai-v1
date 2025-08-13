#!/usr/bin/env python3
"""
Test base string construction to match IBind's implementation
"""

import os
import time
import hmac
import hashlib
import base64
from urllib.parse import quote, quote_plus, urlencode

# Test parameters
method = "GET"
url = "https://api.ibkr.com/v1/api/portfolio/accounts"
oauth_params = {
    'oauth_consumer_key': 'BEARHEDGE',
    'oauth_nonce': 'test123456',
    'oauth_signature_method': 'HMAC-SHA256',
    'oauth_timestamp': '1731324000',
    'oauth_token': '8444def5466e38fb8b86',
}

def ibind_style_base_string(method, url, params):
    """IBind's approach from oauth1a.py lines 258-286"""
    list_separator = '&'
    encoded_request_url = quote_plus(url)
    
    # Sort params and create param string
    oauth_params_string = list_separator.join([f'{k}={v}' for k, v in sorted(params.items())])
    encoded_oauth_params_string = quote_plus(oauth_params_string)
    
    base_string = list_separator.join([method, encoded_request_url, encoded_oauth_params_string])
    return base_string

def our_style_base_string(method, url, params):
    """Our current approach"""
    # Sort parameters
    sorted_params = sorted(params.items())
    
    # Create parameter string with percent encoding
    param_string = '&'.join([f"{k}={quote(str(v), safe='~')}" for k, v in sorted_params])
    
    # Create base string
    base_string = f"{method.upper()}&{quote(url, safe='~')}&{quote(param_string, safe='~')}"
    
    return base_string

# Test both approaches
print("="*70)
print("Base String Comparison")
print("="*70)

ibind_base = ibind_style_base_string(method, url, oauth_params)
our_base = our_style_base_string(method, url, oauth_params)

print("\nIBind style base string:")
print(ibind_base[:200] + "...")

print("\nOur style base string:")
print(our_base[:200] + "...")

print("\nDifferences:")
if ibind_base == our_base:
    print("✅ Base strings match!")
else:
    print("❌ Base strings differ!")
    
    # Find differences
    print("\nDetailed comparison:")
    parts_ibind = ibind_base.split('&')
    parts_our = our_base.split('&')
    
    print(f"IBind method: {parts_ibind[0]}")
    print(f"Our method: {parts_our[0]}")
    print(f"Match: {parts_ibind[0] == parts_our[0]}")
    
    print(f"\nIBind URL: {parts_ibind[1][:50]}...")
    print(f"Our URL: {parts_our[1][:50]}...")
    
    # Check URL encoding differences
    print("\nURL encoding comparison:")
    print(f"IBind uses quote_plus: {quote_plus(url)[:50]}...")
    print(f"We use quote: {quote(url, safe='~')[:50]}...")

# Test signature generation with both
lst_b64 = "qBfObg98KLB+aA/WhUq5nolBlq4="
lst = base64.b64decode(lst_b64)

print("\n" + "="*70)
print("Signature Generation")
print("="*70)

def generate_signature(base_string, key):
    """Generate HMAC-SHA256 signature"""
    signature = hmac.new(key, base_string.encode('utf-8'), hashlib.sha256).digest()
    signature_b64 = base64.b64encode(signature).decode('utf-8')
    return quote_plus(signature_b64)

sig_ibind = generate_signature(ibind_base, lst)
sig_our = generate_signature(our_base, lst)

print(f"\nIBind-style signature: {sig_ibind}")
print(f"Our-style signature: {sig_our}")
print(f"Match: {sig_ibind == sig_our}")