#!/usr/bin/env python3
"""
Debug Live Session Token generation
"""

import os
import sys
import logging
import base64
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

# Initialize auth
auth = IBRestAuth()
auth.access_token = os.getenv('IB_ACCESS_TOKEN')
auth.access_token_secret = os.getenv('IB_ACCESS_TOKEN_SECRET')

print("=== Access Token Info ===")
print(f"Access Token: {auth.access_token}")
print(f"Access Token Secret (first 50 chars): {auth.access_token_secret[:50]}...")
print(f"Access Token Secret Length: {len(auth.access_token_secret)}")

# Try to decrypt the token secret
print("\n=== Decrypting Token Secret ===")
try:
    decrypted = auth._decrypt_token_secret()
    print(f"✅ Decrypted successfully")
    print(f"Decrypted length: {len(decrypted)} chars")
    print(f"First 20 chars: {decrypted[:20]}...")
except Exception as e:
    print(f"❌ Decryption failed: {e}")
    
# Check the base64 encoding
print("\n=== Base64 Validation ===")
try:
    decoded = base64.b64decode(auth.access_token_secret)
    print(f"✅ Base64 decode successful")
    print(f"Decoded length: {len(decoded)} bytes")
except Exception as e:
    print(f"❌ Base64 decode failed: {e}")

# Test DH parameters
print("\n=== DH Parameters ===")
print("DH prime length: 512 hex chars (2048 bits)")
print("DH generator: 2")

# Manual LST request attempt
print("\n=== Manual LST Request ===")
url = f"{auth.oauth_base}/live_session_token"
print(f"URL: {url}")