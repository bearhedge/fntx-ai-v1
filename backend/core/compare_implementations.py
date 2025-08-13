#!/usr/bin/env python3
"""
Compare our implementation with IBind side by side
"""

import os
import sys
import base64
import hmac
import hashlib
from pathlib import Path

# Add parent directory to path
sys.path.append('/home/info/fntx-ai-v1')

# Load environment variables
env_path = Path('/home/info/fntx-ai-v1/config/.env')
if env_path.exists():
    with open(env_path, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                os.environ[key] = value

print("="*70)
print("COMPARING IMPLEMENTATIONS")
print("="*70)

# Common test values
consumer_key = "BEARHEDGE"
access_token = "8444def5466e38fb8b86"
access_token_secret = os.environ['IB_ACCESS_TOKEN_SECRET']

print("\n1. CREDENTIALS CHECK")
print(f"Consumer Key: {consumer_key}")
print(f"Access Token: {access_token}")
print(f"Access Token Secret: {access_token_secret[:50]}...")

# Check if we have a Live Session Token
lst_file = Path('/home/info/.ib_rest_tokens.json')
if lst_file.exists():
    import json
    with open(lst_file) as f:
        tokens = json.load(f)
    lst_b64 = tokens.get('live_session_token')
    print(f"\n2. LIVE SESSION TOKEN")
    print(f"LST (base64): {lst_b64}")
    
    if lst_b64:
        lst = base64.b64decode(lst_b64)
        print(f"LST (bytes): {lst.hex()}")
        print(f"LST length: {len(lst)} bytes")
        
        # Test validation IBind-style
        print("\n3. LST VALIDATION (IBind method)")
        print("IBind validates LST using: HMAC-SHA1(LST, consumer_key)")
        
        # This is what IBind does
        validation_hmac = hmac.new(lst, consumer_key.encode('utf-8'), hashlib.sha1)
        computed_sig = validation_hmac.hexdigest()
        print(f"Computed signature: {computed_sig}")
        
        # Note: We'd need the lst_signature from the response to compare
        print("Note: Need lst_signature from server response to validate")
        
        print("\n4. HMAC-SHA256 SIGNATURE FOR API CALLS")
        # Test base string
        test_base_string = "GET&https%3A%2F%2Fapi.ibkr.com%2Fv1%2Fapi%2Fportfolio%2Faccounts&oauth_consumer_key%3DBEARHEDGE%26oauth_nonce%3Dtest123%26oauth_signature_method%3DHMAC-SHA256%26oauth_timestamp%3D1234567890%26oauth_token%3D8444def5466e38fb8b86"
        
        print("Test base string (first 100 chars):")
        print(test_base_string[:100] + "...")
        
        # Generate HMAC-SHA256 signature
        signature = hmac.new(lst, test_base_string.encode('utf-8'), hashlib.sha256).digest()
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        print(f"\nGenerated signature (base64): {signature_b64}")
        
        # URL encode it
        from urllib.parse import quote_plus
        signature_encoded = quote_plus(signature_b64)
        print(f"URL-encoded signature: {signature_encoded}")
        
        print("\n5. WHAT SHOULD BE IN THE OAUTH HEADER")
        print(f'oauth_signature="{signature_encoded}"')

print("\n6. KEY DIFFERENCES FOUND")
print("- IBind validates LST using HMAC-SHA1(LST, consumer_key)")
print("- Our code was incorrectly validating with access_token_secret")
print("- Both implementations fail on regular API calls with 'Invalid signature'")
print("- This suggests the issue is NOT with our implementation")

print("\n7. POSSIBLE ROOT CAUSES")
print("a) OAuth not fully activated (needs weekend server restart)")
print("b) Credentials mismatch or corruption") 
print("c) Server-side issue with HMAC-SHA256 validation")
print("d) Missing step in the OAuth flow")