#!/usr/bin/env python3
"""
Test and fix BEARHEDGE signature generation
The consumer key works but signature is invalid
"""

import os
import sys
import logging
import time
import hmac
import hashlib
import base64
from pathlib import Path
from urllib.parse import quote

# Load environment variables manually
project_root = Path(__file__).parent.parent.parent
env_path = project_root / 'config' / '.env'

if env_path.exists():
    with open(env_path, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                os.environ[key] = value

sys.path.append('/home/info/fntx-ai-v1/backend')
from core.trading.ib_rest_auth import IBRestAuth

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_signature_variations():
    """Test different signature generation methods"""
    print("\n" + "="*60)
    print("BEARHEDGE SIGNATURE DIAGNOSIS")
    print("="*60)
    
    # Initialize auth
    auth = IBRestAuth()
    auth.access_token = os.getenv('IB_ACCESS_TOKEN')
    auth.access_token_secret = os.getenv('IB_ACCESS_TOKEN_SECRET')
    
    # Get LST first
    print("\n1. Getting Live Session Token:")
    print("-" * 40)
    if not auth.get_live_session_token():
        print("❌ Failed to get LST")
        return
    
    print(f"✅ Got LST: {len(auth.live_session_token)} chars")
    print(f"   LST (base64): {auth.live_session_token[:20]}...")
    
    # Test different signature methods
    print("\n2. Testing Signature Variations:")
    print("-" * 40)
    
    url = f"{auth.base_url}/portfolio/accounts"
    method = "GET"
    
    # OAuth params
    oauth_params = {
        'oauth_consumer_key': auth.consumer_key,
        'oauth_nonce': auth._generate_nonce(),
        'oauth_signature_method': 'HMAC-SHA256',
        'oauth_timestamp': auth._get_timestamp(),
        'oauth_token': auth.access_token,
    }
    
    # Create base string
    sorted_params = sorted(oauth_params.items())
    param_string = '&'.join([f"{k}={quote(str(v), safe='~')}" for k, v in sorted_params])
    base_string = f"{method.upper()}&{quote(url, safe='')}&{quote(param_string, safe='')}"
    
    print("\nBase string components:")
    print(f"  Method: {method}")
    print(f"  URL: {url}")
    print(f"  Params: {param_string[:100]}...")
    
    # Test different key formats
    print("\n3. Testing Different Key Formats:")
    print("-" * 40)
    
    # Method 1: Direct base64 decoded LST
    try:
        lst_bytes = base64.b64decode(auth.live_session_token)
        sig1 = base64.b64encode(
            hmac.new(lst_bytes, base_string.encode('utf-8'), hashlib.sha256).digest()
        ).decode('utf-8')
        print(f"Method 1 (decoded LST): {sig1[:30]}...")
    except Exception as e:
        print(f"Method 1 failed: {e}")
    
    # Method 2: LST as string (current implementation)
    try:
        sig2 = auth._sign_hmac_sha256(base_string, auth.live_session_token)
        print(f"Method 2 (current impl): {sig2[:30]}...")
    except Exception as e:
        print(f"Method 2 failed: {e}")
    
    # Method 3: LST without base64 decoding
    try:
        sig3 = base64.b64encode(
            hmac.new(auth.live_session_token.encode('utf-8'), base_string.encode('utf-8'), hashlib.sha256).digest()
        ).decode('utf-8')
        print(f"Method 3 (LST as string): {sig3[:30]}...")
    except Exception as e:
        print(f"Method 3 failed: {e}")
    
    # Test actual API call with each signature
    print("\n4. Testing API Calls with Each Signature:")
    print("-" * 40)
    
    import requests
    
    signatures = [
        ("Method 1 (decoded LST)", sig1 if 'sig1' in locals() else None),
        ("Method 2 (current impl)", sig2 if 'sig2' in locals() else None),
        ("Method 3 (LST as string)", sig3 if 'sig3' in locals() else None),
    ]
    
    for name, sig in signatures:
        if sig:
            oauth_params_copy = oauth_params.copy()
            oauth_params_copy['oauth_signature'] = sig
            oauth_params_copy['realm'] = auth.realm
            
            # Create header
            header_params = {k: v for k, v in oauth_params_copy.items() if k != 'realm'}
            auth_header = 'OAuth realm="' + auth.realm + '", ' + ', '.join(
                [f'{k}="{v}"' for k, v in sorted(header_params.items())]
            )
            
            headers = {
                'Authorization': auth_header,
                'Accept': 'application/json'
            }
            
            try:
                response = requests.get(url, headers=headers, timeout=5)
                print(f"\n{name}:")
                print(f"  Status: {response.status_code}")
                print(f"  Response: {response.text[:100]}")
                
                if response.status_code == 200:
                    print(f"  ✅ SUCCESS! This signature method works!")
                    return True
                    
            except Exception as e:
                print(f"  Error: {e}")
    
    return False

def test_simplified_auth():
    """Test with simplified auth flow"""
    print("\n" + "="*60)
    print("SIMPLIFIED AUTH TEST")
    print("="*60)
    
    # Try using the test script that might have different logic
    try:
        import subprocess
        result = subprocess.run(
            ['python3', '/home/info/fntx-ai-v1/backend/core/test_direct_auth.py'],
            capture_output=True,
            text=True,
            timeout=10
        )
        print("Output from test_direct_auth.py:")
        print(result.stdout)
        if result.stderr:
            print("Errors:")
            print(result.stderr)
    except Exception as e:
        print(f"Failed to run test_direct_auth.py: {e}")

def main():
    """Run signature diagnosis"""
    print("\n" + "="*60)
    print("BEARHEDGE SIGNATURE FIX")
    print("="*60)
    print("BEARHEDGE works! Just need to fix signature generation.")
    
    # Test signatures
    success = test_signature_variations()
    
    if not success:
        print("\n" + "="*60)
        print("TRYING SIMPLIFIED AUTH")
        print("="*60)
        test_simplified_auth()
    
    # Summary
    print("\n" + "="*60)
    print("DIAGNOSIS SUMMARY")
    print("="*60)
    
    if success:
        print("✅ Found working signature method!")
        print("The implementation needs to be updated.")
    else:
        print("⚠️ Signature issue persists")
        print("\nThe issue is likely:")
        print("1. LST encoding/decoding mismatch")
        print("2. Base string generation issue")
        print("3. HMAC key format problem")
        print("\nBEARHEDGE is active and working!")
        print("Just need to fix the signature generation.")

if __name__ == "__main__":
    main()