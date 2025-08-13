#!/usr/bin/env python3
"""
Fixed IB REST API OAuth Authentication based on demo code
"""

import os
import time
import json
import hashlib
import hmac
import base64
import logging
import requests
import random
import string
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlencode
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from dotenv import load_dotenv

# Load environment variables
project_root = Path(__file__).parent.parent.parent
env_path = project_root / 'config' / '.env'
load_dotenv(env_path)

class IBRestAuthFixed:
    """Fixed version based on demo implementation"""
    
    def __init__(self):
        self.consumer_key = os.getenv('IB_CONSUMER_KEY')
        self.realm = os.getenv('IB_REALM', 'test_realm')
        self.access_token = os.getenv('IB_ACCESS_TOKEN')
        self.access_token_secret = os.getenv('IB_ACCESS_TOKEN_SECRET')
        
        self.base_url = "https://api.ibkr.com/v1/api"
        self.oauth_base = f"{self.base_url}/oauth"
        
        self.signature_key_path = os.getenv('IB_SIGNATURE_KEY_PATH')
        self.encryption_key_path = os.getenv('IB_ENCRYPTION_KEY_PATH')
        
        # Use the demo's prime (256 bytes / 512 hex chars)
        self.dh_prime_hex = (
            "f51d7ab737a452668fd8b5eec12fcdc3c01a0744d93db2e9b1dc335bd2551ec6"
            "7e11becc60c33a73497a0f7c086d87e45781ada35b7af72708f31ae221347a1c"
            "6517575a347df83a321d05450547ee13a8182280ed81423002aa6337b48a251d"
            "840bfdabe8d41b8109284933a6c33bc6652ea9c7a5fd6b4945b7b39f1d951ae1"
            "9b9192061e2f9de84768b67c425258724cdb96975917cabdea87e7e0bc72b01a"
            "d008bc90e83f80d17ab5b7b96fcfcbf0dd97beaa5f3da9c0bb10864f2a3ecf27"
            "907a87de656d7a5cce3c24ee0c6ba4e0b9c6cbaba27e80c0c23e8f59fefc3c48"
            "4b1e4bfd8b5a4e1c6933e5b9c4a9b6fb23a76ae41ce3ddb05bc16f27a5b6c4cf"
        )
        self.dh_generator = 2
        
        self.logger = logging.getLogger(__name__)
        self.live_session_token = None
    
    def _generate_nonce(self) -> str:
        """Generate random nonce"""
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))
    
    def _get_timestamp(self) -> str:
        """Get current Unix timestamp"""
        return str(int(time.time()))
    
    def _percent_encode(self, string: str) -> str:
        """Percent encode according to OAuth spec"""
        return quote(str(string), safe='~')
    
    def _create_signature_base_string(self, method: str, url: str, params: Dict[str, str], 
                                    prepend: str = None) -> str:
        """Create OAuth signature base string"""
        # Sort parameters
        sorted_params = sorted(params.items())
        
        # Create parameter string
        param_string = '&'.join([f"{k}={self._percent_encode(v)}" for k, v in sorted_params])
        
        # Create base string
        base_string = f"{method.upper()}&{self._percent_encode(url)}&{self._percent_encode(param_string)}"
        
        # Add prepend if provided
        if prepend:
            base_string = prepend + base_string
        
        return base_string
    
    def _sign_rsa_sha256(self, base_string: str) -> str:
        """Sign using RSA-SHA256"""
        # Load private key
        with open(self.signature_key_path, 'rb') as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )
        
        # Sign the base string
        signature = private_key.sign(
            base_string.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        
        return base64.b64encode(signature).decode('utf-8')
    
    def _decrypt_token_secret(self) -> str:
        """Decrypt the access token secret"""
        # Load private encryption key
        with open(self.encryption_key_path, 'rb') as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )
        
        # Decode base64 secret
        encrypted_secret = base64.b64decode(self.access_token_secret)
        
        # Decrypt using PKCS1v15 padding
        decrypted = private_key.decrypt(
            encrypted_secret,
            padding.PKCS1v15()
        )
        
        # Return as hex string
        return decrypted.hex()
    
    def _create_oauth_header(self, params: Dict[str, str]) -> str:
        """Create OAuth authorization header"""
        header_params = []
        for key, value in sorted(params.items()):
            if key.startswith('oauth_') or key in ['realm', 'diffie_hellman_challenge']:
                header_params.append(f'{key}="{self._percent_encode(value)}"')
        
        return f"OAuth {', '.join(header_params)}"
    
    def get_live_session_token(self) -> bool:
        """Get live session token using demo approach"""
        try:
            url = f"{self.oauth_base}/live_session_token"
            
            # Generate DH parameters like the demo (25 bytes)
            dh_random_bytes = os.urandom(25)
            dh_random_hex = dh_random_bytes.hex()
            dh_random_int = int(dh_random_hex, 16)
            
            self.logger.info(f"DH Random (25 bytes): {dh_random_hex}")
            
            # Calculate A = g^a mod p
            dh_prime_int = int(self.dh_prime_hex, 16)
            dh_challenge = pow(self.dh_generator, dh_random_int, dh_prime_int)
            dh_challenge_hex = format(dh_challenge, 'x')
            
            self.logger.info(f"DH Challenge length: {len(dh_challenge_hex)} hex chars")
            
            # Decrypt token secret for prepend
            prepend = self._decrypt_token_secret()
            self.logger.info(f"Prepend (decrypted secret): {prepend}")
            
            # OAuth parameters
            oauth_params = {
                'diffie_hellman_challenge': dh_challenge_hex,
                'oauth_consumer_key': self.consumer_key,
                'oauth_nonce': self._generate_nonce(),
                'oauth_signature_method': 'RSA-SHA256',
                'oauth_timestamp': self._get_timestamp(),
                'oauth_token': self.access_token,
                'realm': self.realm
            }
            
            # Create signature base string with prepend
            base_string = self._create_signature_base_string('POST', url,
                {k: v for k, v in oauth_params.items() if k != 'realm'}, prepend=prepend)
            
            # Sign the request
            oauth_params['oauth_signature'] = self._sign_rsa_sha256(base_string)
            
            # Create authorization header
            auth_header = self._create_oauth_header(oauth_params)
            
            # Make request
            headers = {
                'Authorization': auth_header,
                'Content-Length': '0'
            }
            
            self.logger.info(f"Making request to: {url}")
            response = requests.post(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                dh_response_hex = data.get('diffie_hellman_response')
                lst_signature = data.get('live_session_token_signature')
                
                self.logger.info(f"Got DH response: {dh_response_hex[:50]}...")
                
                # Convert DH response from hex to int
                dh_response_int = int(dh_response_hex, 16)
                
                # Calculate shared secret K = B^a mod p
                shared_secret = pow(dh_response_int, dh_random_int, dh_prime_int)
                
                # Convert K to byte array (matching demo's toByteArray)
                k_hex = format(shared_secret, 'x')
                if len(k_hex) % 2 != 0:
                    k_hex = '0' + k_hex
                
                k_bytes = bytes.fromhex(k_hex)
                
                # Calculate LST = HMAC-SHA1(K, decrypted_token_secret)
                # The demo uses the decrypted secret as bytes
                decrypted_secret_bytes = bytes.fromhex(prepend)
                
                self.live_session_token = hmac.new(
                    k_bytes,
                    decrypted_secret_bytes,
                    hashlib.sha1
                ).digest()
                
                self.logger.info(f"✅ Got live session token!")
                self.logger.info(f"LST (base64): {base64.b64encode(self.live_session_token).decode()}")
                
                # Verify the signature
                computed_signature = hmac.new(
                    self.live_session_token,
                    self.consumer_key.encode(),
                    hashlib.sha1
                ).hexdigest()
                
                if computed_signature == lst_signature:
                    self.logger.info("✅ LST signature verified!")
                else:
                    self.logger.warning(f"LST signature mismatch: {computed_signature} != {lst_signature}")
                
                return True
            else:
                self.logger.error(f"Live session token failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error getting live session token: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_fixed_auth():
    """Test the fixed authentication"""
    logging.basicConfig(level=logging.INFO)
    
    auth = IBRestAuthFixed()
    
    print("\n=== Fixed Authentication Test ===")
    print(f"Consumer Key: {auth.consumer_key}")
    print(f"Access Token: {auth.access_token}")
    print(f"Realm: {auth.realm}")
    print(f"Using demo prime: {auth.dh_prime_hex[:50]}...")
    
    if auth.get_live_session_token():
        print("\n✅ Authentication successful!")
        return True
    else:
        print("\n❌ Authentication failed!")
        return False


if __name__ == "__main__":
    test_fixed_auth()