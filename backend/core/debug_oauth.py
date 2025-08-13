#!/usr/bin/env python3
"""
Debug OAuth signature generation for IB REST API
"""

import os
import sys
import time
import hashlib
import hmac
import base64
import logging
from urllib.parse import quote
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
project_root = Path(__file__).parent.parent.parent
env_path = project_root / 'config' / '.env'
load_dotenv(env_path)

sys.path.append('/home/info/fntx-ai-v1/backend')
from core.trading.ib_rest_auth import IBRestAuth

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Test basic OAuth signature
auth = IBRestAuth()

print("=== OAuth Debug Information ===")
print(f"Consumer Key: {auth.consumer_key}")
print(f"Realm: {auth.realm}")
print(f"Base URL: {auth.base_url}")
print(f"OAuth URL: {auth.oauth_base}")

# Test signature generation
print("\n=== Testing Signature Generation ===")
url = f"{auth.oauth_base}/request_token"
nonce = auth._generate_nonce()
timestamp = auth._get_timestamp()

print(f"URL: {url}")
print(f"Nonce: {nonce}")
print(f"Timestamp: {timestamp}")

# Create OAuth parameters
oauth_params = {
    'oauth_callback': 'oob',
    'oauth_consumer_key': auth.consumer_key,
    'oauth_nonce': nonce,
    'oauth_signature_method': 'RSA-SHA256',
    'oauth_timestamp': timestamp,
}

print("\n=== OAuth Parameters ===")
for k, v in sorted(oauth_params.items()):
    print(f"{k}: {v}")

# Create base string
params_for_base = {k: v for k, v in oauth_params.items()}
base_string = auth._create_signature_base_string('POST', url, params_for_base)
print(f"\n=== Base String ===")
print(base_string)

# Try to sign
try:
    signature = auth._sign_rsa_sha256(base_string)
    print(f"\n=== Signature ===")
    print(f"Signature (first 50 chars): {signature[:50]}...")
    print(f"Signature length: {len(signature)}")
except Exception as e:
    print(f"\n=== Signature Error ===")
    print(f"Error: {e}")

# Check if we can load the private key
print("\n=== Key Verification ===")
try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    
    with open(auth.signature_key_path, 'rb') as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend()
        )
    print("✅ Private key loaded successfully")
    print(f"Key size: {private_key.key_size} bits")
except Exception as e:
    print(f"❌ Failed to load private key: {e}")

# Test percent encoding
print("\n=== Percent Encoding Test ===")
test_strings = ['hello world', 'test@example.com', 'key=value&other=data']
for s in test_strings:
    encoded = auth._percent_encode(s)
    print(f"'{s}' -> '{encoded}'")