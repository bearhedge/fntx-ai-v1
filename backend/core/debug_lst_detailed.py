#\!/usr/bin/env python3
"""
Detailed debug of LST generation
"""

import os
import sys
import base64
import hmac
import hashlib
import time
import urllib.parse
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

def decrypt_access_token_secret():
    """Decrypt access token secret"""
    encrypted_secret = os.getenv('IB_ACCESS_TOKEN_SECRET', '').strip('"')
    encryption_key_path = os.getenv('IB_ENCRYPTION_KEY_PATH')
    
    with open(encryption_key_path, 'rb') as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend()
        )
    
    encrypted_bytes = base64.b64decode(encrypted_secret)
    decrypted_bytes = private_key.decrypt(
        encrypted_bytes,
        padding.PKCS1v15()
    )
    
    return decrypted_bytes.hex()

def main():
    print("="*60)
    print("DETAILED LST DEBUG")
    print("="*60)
    
    auth = IBRestAuth()
    
    # Decrypt access token secret
    decrypted_secret = decrypt_access_token_secret()
    print(f"\nDecrypted Access Token Secret:")
    print(f"Hex: {decrypted_secret}")
    print(f"Length: {len(decrypted_secret)//2} bytes")
    
    # Generate DH values
    auth._generate_dh_values()
    
    print(f"\nDH Values:")
    print(f"Random (hex): {auth.dh_random.hex() if hasattr(auth, 'dh_random') else 'N/A'}")
    print(f"Challenge: {auth.dh_challenge[:50]}..." if hasattr(auth, 'dh_challenge') else 'N/A')
    
    # Create OAuth parameters
    oauth_params = {
        'oauth_consumer_key': auth.consumer_key,
        'oauth_nonce': auth._generate_nonce(),
        'oauth_signature_method': 'RSA-SHA256',
        'oauth_timestamp': str(int(time.time())),
        'oauth_token': auth.access_token,
    }
    
    # Add DH parameter
    params = {'diffie_hellman_challenge': auth.dh_challenge}
    all_params = {**oauth_params, **params}
    
    # Create signature base string
    method = 'POST'
    url = f"{auth.oauth_base}/live_session_token"
    
    # Sort parameters
    sorted_params = sorted(all_params.items())
    param_string = '&'.join([f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in sorted_params])
    
    # Create base string
    base_string = f"{method}&{urllib.parse.quote(url, safe='')}&{urllib.parse.quote(param_string, safe='')}"
    
    print(f"\nSignature Base String:")
    print(base_string[:200] + "...")
    
    # Test prepend
    prepend = decrypted_secret
    prepended_base = prepend + base_string
    
    print(f"\nPrepended Base String:")
    print(f"Length: {len(prepended_base)}")
    print(f"First 100 chars: {prepended_base[:100]}...")
    
    # Create signature
    signature = auth._sign_rsa_sha256(prepended_base)
    print(f"\nSignature: {signature[:50]}...")
    
    # Show full request
    print(f"\nRequest Details:")
    print(f"URL: {url}")
    print(f"Method: {method}")
    print(f"OAuth Parameters:")
    for k, v in sorted(oauth_params.items()):
        print(f"  {k}: {v}")
    print(f"  oauth_signature: {signature[:50]}...")
    print(f"Body Parameters:")
    print(f"  diffie_hellman_challenge: {auth.dh_challenge[:50]}...")
    
    # Show authorization header
    oauth_params['oauth_signature'] = signature
    auth_parts = []
    for k, v in sorted(oauth_params.items()):
        auth_parts.append(f'{k}="{urllib.parse.quote(str(v), safe="")}"')
    auth_header = f"OAuth {', '.join(auth_parts)}"
    
    print(f"\nAuthorization Header:")
    print(auth_header[:200] + "...")

if __name__ == "__main__":
    main()
EOF < /dev/null
