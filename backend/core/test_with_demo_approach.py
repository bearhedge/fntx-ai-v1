#!/usr/bin/env python3
"""
Test using the exact approach from the demo
"""

import os
import sys
import logging
import base64
import hmac
import hashlib
import random
from pathlib import Path
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

# Load environment variables
project_root = Path(__file__).parent.parent.parent
env_path = project_root / 'config' / '.env'
load_dotenv(env_path)

sys.path.append('/home/info/fntx-ai-v1/backend')
from core.trading.ib_rest_auth import IBRestAuth

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

print("=== Testing with Demo Approach ===")

# The demo uses this specific prime (from their store.js)
demo_prime_hex = (
    "f51d7ab737a452668fd8b5eec12fcdc3c01a0744d93db2e9b1dc335bd2551ec6"
    "7e11becc60c33a73497a0f7c086d87e45781ada35b7af72708f31ae221347a1c"
    "6517575a347df83a321d05450547ee13a8182280ed81423002aa6337b48a251d"
    "840bfdabe8d41b8109284933a6c33bc6652ea9c7a5fd6b4945b7b39f1d951ae1"
    "9b9192061e2f9de84768b67c425258724cdb96975917cabdea87e7e0bc72b01a"
    "d008bc90e83f80d17ab5b7b96fcfcbf0dd97beaa5f3da9c0bb10864f2a3ecf27"
    "907a87de656d7a5cce3c24ee0c6ba4e0b9c6cbaba27e80c0c23e8f59fefc3c48"
    "4b1e4bfd8b5a4e1c6933e5b9c4a9b6fb23a76ae41ce3ddb05bc16f27a5b6c4cf"
)

# IB's standard prime from the documentation
ib_prime_hex = (
    "00e9c0372154feb9e1b24eaa5d290fbffc6e5ac0adb6db1d1cf6b9edee93cf5e"
    "d5e004ad2ba4bde0a0b1f6b9e9d020e67fb3e5bb66ac0f9f0dd6b613b5c10c4f"
    "b527aedf5c7eee088ed43e36a0540b586de88b1cdecf045a17e9df5fe0cb3074"
    "f9c6b2bbfa8ad4461ab69db963852366e40838c4b03283c51810efb8f1db53e6"
    "9d2ec0372154feb9e1b24eaa5d290fbffc6e5ac0adb6db1d1cf6b9edee93cf5e"
    "d5e004ad2ba4bde0a0b1f6b9e9d020e67fb3e5bb66ac0f9f0dd6b613b5c10c4f"
    "b527aedf5c7eee088ed43e36a0540b586de88b1cdecf045a17e9df5fe0cb3074"
    "f9c6b2bbfa8ad4461ab69db963852366e40838c4b03283c51810efb8f1db53e6af"
)

print(f"\nDemo prime length: {len(demo_prime_hex)} hex chars")
print(f"IB prime length: {len(ib_prime_hex)} hex chars")

# Try with demo's approach: 25 bytes (50 hex chars) for random
demo_random_bytes = os.urandom(25)
demo_random_hex = demo_random_bytes.hex()
demo_random_int = int(demo_random_hex, 16)

print(f"\nDemo random (25 bytes): {demo_random_hex}")
print(f"Demo random int: {demo_random_int}")

# Calculate challenge using demo prime
demo_prime_int = int(demo_prime_hex, 16)
demo_challenge = pow(2, demo_random_int, demo_prime_int)
demo_challenge_hex = format(demo_challenge, 'x')

print(f"\nDemo challenge (first 50 chars): {demo_challenge_hex[:50]}...")
print(f"Demo challenge length: {len(demo_challenge_hex)} hex chars")

# Try with IB's documented prime
ib_prime_int = int(ib_prime_hex, 16)
ib_challenge = pow(2, demo_random_int, ib_prime_int)
ib_challenge_hex = format(ib_challenge, 'x')

print(f"\nIB challenge (first 50 chars): {ib_challenge_hex[:50]}...")
print(f"IB challenge length: {len(ib_challenge_hex)} hex chars")

# Check if we can decrypt the token secret properly
auth = IBRestAuth()
auth.access_token = os.getenv('IB_ACCESS_TOKEN')
auth.access_token_secret = os.getenv('IB_ACCESS_TOKEN_SECRET')

try:
    decrypted = auth._decrypt_token_secret()
    print(f"\n✅ Token secret decrypted: {decrypted}")
except Exception as e:
    print(f"\n❌ Failed to decrypt token secret: {e}")