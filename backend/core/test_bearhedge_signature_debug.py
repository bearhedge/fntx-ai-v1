#!/usr/bin/env python3
"""
Debug BEARHEDGE HMAC-SHA256 signature generation
Comprehensive analysis and fix attempt
"""

import os
import sys
import time
import hmac
import hashlib
import base64
import secrets
import json
import requests
from pathlib import Path
from urllib.parse import quote, quote_plus
from typing import Dict, Optional

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

def percent_encode(string: str) -> str:
    """
    Percent encode string according to OAuth spec
    """
    # OAuth 1.0a requires specific encoding
    return quote(str(string), safe='~')

def create_base_string_debug(method: str, url: str, params: Dict) -> str:
    """
    Create OAuth signature base string with debug output
    """
    print("\n=== BASE STRING CREATION ===")
    
    # Sort parameters
    sorted_params = sorted(params.items())
    print(f"Sorted params: {sorted_params[:3]}...")  # Show first 3
    
    # Create parameter string
    param_parts = []
    for k, v in sorted_params:
        param_parts.append(f"{percent_encode(k)}={percent_encode(v)}")
    param_string = '&'.join(param_parts)
    print(f"Param string: {param_string[:100]}...")
    
    # Create base string
    base_parts = [
        method.upper(),
        percent_encode(url),
        percent_encode(param_string)
    ]
    base_string = '&'.join(base_parts)
    
    print(f"Method: {method.upper()}")
    print(f"URL (encoded): {percent_encode(url)[:50]}...")
    print(f"Base string length: {len(base_string)}")
    print(f"Base string: {base_string[:150]}...")
    
    return base_string

def test_signature_methods():
    """Test different HMAC-SHA256 signature methods"""
    print("\n" + "="*60)
    print("BEARHEDGE SIGNATURE DEBUG")
    print("="*60)
    
    # Initialize auth
    auth = IBRestAuth()
    auth.access_token = os.getenv('IB_ACCESS_TOKEN')
    auth.access_token_secret = os.getenv('IB_ACCESS_TOKEN_SECRET')
    
    # Get LST
    print("\n1. Getting Live Session Token:")
    print("-" * 40)
    if not auth.get_live_session_token():
        print("❌ Failed to get LST")
        return
    
    print(f"✅ Got LST successfully")
    print(f"   Length: {len(auth.live_session_token)} chars")
    print(f"   First 20 chars: {auth.live_session_token[:20]}...")
    
    # Decode LST to check format
    try:
        lst_decoded = base64.b64decode(auth.live_session_token)
        print(f"   Decoded length: {len(lst_decoded)} bytes")
        print(f"   Is valid base64: ✅")
    except Exception as e:
        print(f"   Base64 decode error: {e}")
        return
    
    # Test parameters
    url = f"{auth.base_url}/portfolio/accounts"
    method = "GET"
    
    # OAuth parameters (minimal set)
    oauth_params = {
        'oauth_consumer_key': auth.consumer_key,
        'oauth_nonce': secrets.token_hex(16),
        'oauth_signature_method': 'HMAC-SHA256',
        'oauth_timestamp': str(int(time.time())),
        'oauth_token': auth.access_token
    }
    
    print("\n2. OAuth Parameters:")
    print("-" * 40)
    for k, v in oauth_params.items():
        if k == 'oauth_nonce':
            print(f"   {k}: {v[:10]}...")
        else:
            print(f"   {k}: {v}")
    
    # Create base string
    print("\n3. Creating Base String:")
    print("-" * 40)
    base_string = create_base_string_debug(method, url, oauth_params)
    
    # Test different signature methods
    print("\n4. Testing Signature Methods:")
    print("-" * 40)
    
    signatures = []
    
    # Method 1: Decoded LST as key (current implementation)
    print("\nMethod 1: Base64-decoded LST as HMAC key")
    try:
        lst_decoded = base64.b64decode(auth.live_session_token)
        sig_raw = hmac.new(lst_decoded, base_string.encode('utf-8'), hashlib.sha256).digest()
        sig1 = base64.b64encode(sig_raw).decode('utf-8')
        print(f"   Signature: {sig1[:30]}...")
        signatures.append(("Decoded LST", sig1))
    except Exception as e:
        print(f"   Error: {e}")
    
    # Method 2: Raw LST string as key
    print("\nMethod 2: Raw LST string as HMAC key")
    try:
        sig_raw = hmac.new(auth.live_session_token.encode('utf-8'), base_string.encode('utf-8'), hashlib.sha256).digest()
        sig2 = base64.b64encode(sig_raw).decode('utf-8')
        print(f"   Signature: {sig2[:30]}...")
        signatures.append(("Raw LST", sig2))
    except Exception as e:
        print(f"   Error: {e}")
    
    # Method 3: URL-safe base64 decoding
    print("\nMethod 3: URL-safe base64 decoded LST")
    try:
        # Try URL-safe base64 decoding
        lst_decoded = base64.urlsafe_b64decode(auth.live_session_token + '==')  # Add padding
        sig_raw = hmac.new(lst_decoded, base_string.encode('utf-8'), hashlib.sha256).digest()
        sig3 = base64.b64encode(sig_raw).decode('utf-8')
        print(f"   Signature: {sig3[:30]}...")
        signatures.append(("URL-safe decoded", sig3))
    except Exception as e:
        print(f"   Error: {e}")
    
    # Method 4: Different base string encoding
    print("\nMethod 4: Alternative base string encoding")
    try:
        # Try without percent encoding in parameter string
        simple_params = '&'.join([f"{k}={v}" for k, v in sorted(oauth_params.items())])
        alt_base = f"{method}&{percent_encode(url)}&{percent_encode(simple_params)}"
        
        lst_decoded = base64.b64decode(auth.live_session_token)
        sig_raw = hmac.new(lst_decoded, alt_base.encode('utf-8'), hashlib.sha256).digest()
        sig4 = base64.b64encode(sig_raw).decode('utf-8')
        print(f"   Signature: {sig4[:30]}...")
        signatures.append(("Alt encoding", sig4))
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test each signature with actual API call
    print("\n5. Testing API Calls:")
    print("-" * 40)
    
    for name, sig in signatures:
        print(f"\nTesting {name}:")
        
        # Add signature to params
        test_params = oauth_params.copy()
        test_params['oauth_signature'] = sig
        
        # Create authorization header
        auth_parts = []
        auth_parts.append(f'realm="{auth.realm}"')
        for k, v in sorted(test_params.items()):
            auth_parts.append(f'{k}="{v}"')
        auth_header = 'OAuth ' + ', '.join(auth_parts)
        
        headers = {
            'Authorization': auth_header,
            'Accept': 'application/json'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=5)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ SUCCESS! This method works!")
                print(f"   Response: {response.text[:100]}...")
                return True
            elif response.status_code == 401:
                print(f"   ❌ 401 Unauthorized")
                error_text = response.text[:200]
                if 'Invalid signature' in error_text:
                    print(f"   Error: Invalid signature")
                elif 'Invalid consumer' in error_text:
                    print(f"   Error: Invalid consumer")
                else:
                    print(f"   Error: {error_text}")
            else:
                print(f"   Status: {response.status_code}")
                print(f"   Response: {response.text[:100]}")
                
        except Exception as e:
            print(f"   Request error: {e}")
    
    return False

def test_with_different_realm():
    """Test with different realm values"""
    print("\n" + "="*60)
    print("TESTING DIFFERENT REALMS")
    print("="*60)
    
    auth = IBRestAuth()
    auth.access_token = os.getenv('IB_ACCESS_TOKEN')
    auth.access_token_secret = os.getenv('IB_ACCESS_TOKEN_SECRET')
    
    if not auth.get_live_session_token():
        print("❌ Failed to get LST")
        return
    
    realms = ['limited_poa', 'test_realm', 'api_only', '']
    url = f"{auth.base_url}/portfolio/accounts"
    
    for realm in realms:
        print(f"\nTesting realm: '{realm}'")
        
        oauth_params = {
            'oauth_consumer_key': auth.consumer_key,
            'oauth_nonce': secrets.token_hex(16),
            'oauth_signature_method': 'HMAC-SHA256',
            'oauth_timestamp': str(int(time.time())),
            'oauth_token': auth.access_token
        }
        
        # Create base string (realm not included in signature)
        sorted_params = sorted(oauth_params.items())
        param_string = '&'.join([f"{percent_encode(k)}={percent_encode(v)}" for k, v in sorted_params])
        base_string = f"GET&{percent_encode(url)}&{percent_encode(param_string)}"
        
        # Sign with decoded LST
        lst_decoded = base64.b64decode(auth.live_session_token)
        sig_raw = hmac.new(lst_decoded, base_string.encode('utf-8'), hashlib.sha256).digest()
        signature = base64.b64encode(sig_raw).decode('utf-8')
        
        oauth_params['oauth_signature'] = signature
        
        # Create header with realm
        auth_parts = []
        if realm:
            auth_parts.append(f'realm="{realm}"')
        for k, v in sorted(oauth_params.items()):
            auth_parts.append(f'{k}="{v}"')
        auth_header = 'OAuth ' + ', '.join(auth_parts)
        
        headers = {
            'Authorization': auth_header,
            'Accept': 'application/json'
        }
        
        response = requests.get(url, headers=headers, timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✅ SUCCESS with realm '{realm}'!")
            return True

def main():
    """Run comprehensive signature debugging"""
    print("\n" + "="*60)
    print("BEARHEDGE COMPREHENSIVE SIGNATURE DEBUG")
    print("="*60)
    print("Testing all possible signature variations")
    
    # Test main signature methods
    success = test_signature_methods()
    
    if not success:
        # Try different realms
        print("\n" + "="*60)
        print("SIGNATURE FAILED - TRYING DIFFERENT REALMS")
        print("="*60)
        success = test_with_different_realm()
    
    # Summary
    print("\n" + "="*60)
    print("DEBUG SUMMARY")
    print("="*60)
    
    if success:
        print("✅ Found working signature method!")
        print("Update ib_rest_auth.py with the working method")
    else:
        print("⚠️ All signature methods failed")
        print("\nPossible issues:")
        print("1. OAuth token might need refresh")
        print("2. LST might have expired")
        print("3. Base string format might be incorrect")
        print("4. Realm might be wrong")
        print("\nBut BEARHEDGE is definitely active (LST generation works)")

if __name__ == "__main__":
    main()