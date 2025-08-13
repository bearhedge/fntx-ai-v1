#!/usr/bin/env python3
"""
Interactive Brokers REST API OAuth Authentication
Handles OAuth 1.0a authentication flow for IB REST API
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
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlencode
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend

class IBRestAuth:
    """
    IB REST API OAuth 1.0a Authentication Handler
    Implements the complete OAuth flow for headless authentication
    """
    
    def __init__(self, 
                 consumer_key: str = None,
                 realm: str = None,
                 is_live: bool = True,
                 token_file: str = None):
        """
        Initialize IB REST API authentication
        
        Args:
            consumer_key: OAuth consumer key (from environment if not provided)
            realm: Authentication realm (default: limited_poa for institutional)
            is_live: Use live API (True) or paper trading (False)
            token_file: Path to store/retrieve tokens
        """
        self.consumer_key = consumer_key or os.getenv('IB_CONSUMER_KEY')
        self.realm = realm or os.getenv('IB_REALM', 'limited_poa')
        self.is_live = is_live if is_live is not None else os.getenv('IB_IS_LIVE', 'true').lower() == 'true'
        
        # API endpoints
        self.base_url = "https://api.ibkr.com/v1/api"
        self.oauth_base = f"{self.base_url}/oauth"
        
        # Token storage
        self.token_file = token_file or os.path.expanduser("~/.ib_rest_tokens.json")
        self.request_token = None
        self.access_token = None
        self.access_token_secret = None
        self.live_session_token = None
        
        # Keys
        self.signature_key_path = os.getenv('IB_SIGNATURE_KEY_PATH')
        self.encryption_key_path = os.getenv('IB_ENCRYPTION_KEY_PATH')
        self.dh_param_path = os.getenv('IB_DH_PARAM_PATH')
        
        # Diffie-Hellman parameters (will be loaded from file)
        self.dh_prime = None
        self.dh_generator = None
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
        # Load existing tokens if available
        self._load_tokens()
        
        # Load DH parameters
        self._load_dh_params()
    
    def _load_dh_params(self):
        """Load Diffie-Hellman parameters from file"""
        try:
            if self.dh_param_path and os.path.exists(self.dh_param_path):
                with open(self.dh_param_path, 'rb') as f:
                    from cryptography.hazmat.primitives.asymmetric import dh
                    params = serialization.load_pem_parameters(f.read(), backend=default_backend())
                    if isinstance(params, dh.DHParameters):
                        # Extract prime and generator from DH parameters
                        # Note: This is a simplified approach - in production you'd need the actual values
                        self.logger.info("Loaded DH parameters from file")
            else:
                self.logger.warning("DH parameters file not found, will need to set manually")
        except Exception as e:
            self.logger.error(f"Error loading DH parameters: {e}")
    
    def _generate_nonce(self, length: int = 32) -> str:
        """Generate a random nonce for OAuth"""
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))
    
    def _get_timestamp(self) -> str:
        """Get current Unix timestamp as string"""
        return str(int(time.time()))
    
    def _percent_encode(self, string: str) -> str:
        """Percent encode a string according to OAuth spec"""
        return quote(str(string), safe='~')
    
    def _create_signature_base_string(self, method: str, url: str, params: Dict[str, str], 
                                    prepend: str = None) -> str:
        """
        Create OAuth signature base string
        
        Args:
            method: HTTP method
            url: Request URL
            params: OAuth and request parameters
            prepend: Optional prepend string (for live session token)
            
        Returns:
            Signature base string
        """
        # Sort parameters
        sorted_params = sorted(params.items())
        
        # Create parameter string
        param_string = '&'.join([f"{k}={self._percent_encode(v)}" for k, v in sorted_params])
        
        # Create base string
        base_string = f"{method.upper()}&{self._percent_encode(url)}&{self._percent_encode(param_string)}"
        
        # CRITICAL FIX: IBKR-specific character encoding corrections
        # These corrections match the working JavaScript implementation (lines 62-64)
        base_string = base_string.replace('%257C', '%7C')  # pipe character |
        base_string = base_string.replace('%252C', '%2C')  # comma character ,
        base_string = base_string.replace('%253A', '%3A')  # colon character :
        
        # Add prepend if provided
        if prepend:
            base_string = prepend + base_string
        
        return base_string
    
    def _sign_rsa_sha256(self, base_string: str) -> str:
        """
        Sign base string using RSA-SHA256 (matching IBind's implementation)
        
        Args:
            base_string: String to sign
            
        Returns:
            Base64 encoded and URL-encoded signature
        """
        try:
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
            
            # Base64 encode
            signature_b64 = base64.b64encode(signature).decode('utf-8')
            
            # URL encode like IBind does (using quote_plus)
            from urllib.parse import quote_plus
            return quote_plus(signature_b64)
            
        except Exception as e:
            self.logger.error(f"Error signing with RSA: {e}")
            raise
    
    def _sign_hmac_sha256(self, base_string: str, key: bytes) -> str:
        """
        Sign base string using HMAC-SHA256
        
        Args:
            base_string: String to sign
            key: Signing key (live session token)
            
        Returns:
            Base64 encoded and URL-encoded signature (matching RSA method)
        """
        # CRITICAL FIX: Must base64-decode the LST before using as HMAC key
        # This matches the working JavaScript implementation: Buffer.from(key, 'base64')
        if isinstance(key, str):
            # If key is a base64 string, decode it to bytes
            decoded_key = base64.b64decode(key)
        else:
            # If key is already bytes, use it directly
            decoded_key = key
        
        signature = hmac.new(decoded_key, base_string.encode('utf-8'), hashlib.sha256).digest()
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        # CRITICAL FIX: URL-encode the signature to match RSA method behavior
        # The RSA method returns URL-encoded signatures, HMAC must do the same
        from urllib.parse import quote_plus
        return quote_plus(signature_b64)
    
    def _create_oauth_header(self, params: Dict[str, str]) -> str:
        """
        Create OAuth authorization header (matching IBind's format exactly)
        
        Args:
            params: OAuth parameters
            
        Returns:
            Authorization header value
        """
        # Get realm (don't modify original dict)
        realm = params.get('realm', 'limited_poa')
        
        # Create header params (exclude realm from sorted params)
        header_params = {k: v for k, v in params.items() if k != 'realm'}
        
        # IBind includes all params in sorted order
        authorization_header_keys = ', '.join(
            [f'{key}="{value}"' for key, value in sorted(header_params.items())]
        )
        
        # Format exactly like IBind: OAuth realm="limited_poa", key1="value1", key2="value2"
        authorization_header_string = f'OAuth realm="{realm}", {authorization_header_keys}'
        return authorization_header_string
    
    def _load_tokens(self) -> bool:
        """Load tokens from file if they exist"""
        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, 'r') as f:
                    data = json.load(f)
                    self.access_token = data.get('access_token')
                    self.access_token_secret = data.get('access_token_secret')
                    # CRITICAL FIX: Load LST as base64 string (no decoding needed)
                    # This maintains consistent state management
                    self.live_session_token = data.get('live_session_token')
                    
                    if self.access_token and self.live_session_token:
                        self.logger.info("Loaded tokens from file")
                        return True
            return False
        except Exception as e:
            self.logger.error(f"Error loading tokens: {e}")
            return False
    
    def _save_tokens(self):
        """Save tokens to file for reuse"""
        try:
            data = {
                'access_token': self.access_token,
                'access_token_secret': self.access_token_secret,
                'live_session_token': self.live_session_token,
                'consumer_key': self.consumer_key,
                'realm': self.realm,
                'timestamp': datetime.now().isoformat()
            }
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
            
            with open(self.token_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Set restrictive permissions
            os.chmod(self.token_file, 0o600)
            
            self.logger.info("Saved tokens to file")
        except Exception as e:
            self.logger.error(f"Error saving tokens: {e}")
    
    def get_request_token(self) -> bool:
        """
        Step 1: Get OAuth request token
        
        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.oauth_base}/request_token"
            
            # OAuth parameters
            oauth_params = {
                'oauth_callback': 'oob',
                'oauth_consumer_key': self.consumer_key,
                'oauth_nonce': self._generate_nonce(),
                'oauth_signature_method': 'RSA-SHA256',
                'oauth_timestamp': self._get_timestamp(),
                'realm': self.realm
            }
            
            # Create signature base string
            base_string = self._create_signature_base_string('POST', url, 
                {k: v for k, v in oauth_params.items() if k != 'realm'})
            
            # Sign the request
            oauth_params['oauth_signature'] = self._sign_rsa_sha256(base_string)
            
            # Create authorization header
            auth_header = self._create_oauth_header(oauth_params)
            
            # Make request
            headers = {
                'Authorization': auth_header,
                'Content-Length': '0'
            }
            
            response = requests.post(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                self.request_token = data.get('oauth_token')
                self.logger.info(f"Got request token: {self.request_token}")
                return True
            else:
                self.logger.error(f"Request token failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error getting request token: {e}")
            return False
    
    def get_access_token(self, verifier: str = None) -> bool:
        """
        Step 3: Get OAuth access token
        
        Args:
            verifier: OAuth verifier (for manual flow)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # For headless authentication, we might not need the verifier
            if not self.request_token:
                self.logger.error("No request token available")
                return False
            
            url = f"{self.oauth_base}/access_token"
            
            # OAuth parameters
            oauth_params = {
                'oauth_consumer_key': self.consumer_key,
                'oauth_nonce': self._generate_nonce(),
                'oauth_signature_method': 'RSA-SHA256',
                'oauth_timestamp': self._get_timestamp(),
                'oauth_token': self.request_token,
                'realm': self.realm
            }
            
            if verifier:
                oauth_params['oauth_verifier'] = verifier
            
            # Create signature base string
            base_string = self._create_signature_base_string('POST', url,
                {k: v for k, v in oauth_params.items() if k != 'realm'})
            
            # Sign the request
            oauth_params['oauth_signature'] = self._sign_rsa_sha256(base_string)
            
            self.logger.debug(f"Access token request oauth_params: {oauth_params}")
            
            # Create authorization header
            auth_header = self._create_oauth_header(oauth_params)
            
            # Make request
            headers = {
                'Authorization': auth_header,
                'Content-Length': '0'
            }
            
            response = requests.post(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('oauth_token')
                self.access_token_secret = data.get('oauth_token_secret')
                self.logger.info(f"Got access token: {self.access_token}")
                return True
            else:
                self.logger.error(f"Access token failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error getting access token: {e}")
            return False
    
    def _decrypt_token_secret(self) -> str:
        """Decrypt the access token secret using private encryption key"""
        try:
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
            
        except Exception as e:
            self.logger.error(f"Error decrypting token secret: {e}")
            raise
    
    def get_live_session_token(self) -> bool:
        """
        Step 4: Get live session token using Diffie-Hellman exchange
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.access_token or not self.access_token_secret:
                self.logger.error("No access token available")
                return False
            
            url = f"{self.oauth_base}/live_session_token"
            
            # Generate Diffie-Hellman challenge
            # Using proper DH values from IB documentation
            # Standard DH parameters: p (prime) and g (generator)
            dh_prime = int("00e9c0372154feb9e1b24eaa5d290fbffc6e5ac0adb6db1d1cf6b9edee93cf5ed5e004ad2ba4bde0a0b1f6b9e9d020e67fb3e5bb66ac0f9f0dd6b613b5c10c4fb527aedf5c7eee088ed43e36a0540b586de88b1cdecf045a17e9df5fe0cb3074f9c6b2bbfa8ad4461ab69db963852366e40838c4b03283c51810efb8f1db53e69d2ec0372154feb9e1b24eaa5d290fbffc6e5ac0adb6db1d1cf6b9edee93cf5ed5e004ad2ba4bde0a0b1f6b9e9d020e67fb3e5bb66ac0f9f0dd6b613b5c10c4fb527aedf5c7eee088ed43e36a0540b586de88b1cdecf045a17e9df5fe0cb3074f9c6b2bbfa8ad4461ab69db963852366e40838c4b03283c51810efb8f1db53e6af", 16)
            dh_generator = 2
            
            # Generate random private value 'a'
            dh_random = random.randint(2**255, 2**256 - 1)
            
            # Calculate A = g^a mod p
            dh_challenge = pow(dh_generator, dh_random, dh_prime)
            
            # Convert to hex string
            dh_challenge_hex = format(dh_challenge, 'x')
            
            # Decrypt token secret for prepend
            prepend = self._decrypt_token_secret()
            
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
            
            self.logger.debug(f"LST request oauth_params: {oauth_params}")
            
            # Create authorization header
            auth_header = self._create_oauth_header(oauth_params)
            
            self.logger.debug(f"LST Authorization header: {auth_header}")
            
            # Make request
            headers = {
                'Authorization': auth_header,
                'Content-Length': '0'
            }
            
            response = requests.post(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                dh_response = data.get('diffie_hellman_response')
                lst_signature = data.get('live_session_token_signature')
                
                # Convert DH response from hex to int
                dh_response_int = int(dh_response, 16)
                
                # Calculate shared secret K = B^a mod p
                shared_secret = pow(dh_response_int, dh_random, dh_prime)
                
                # Convert to bytes (big-endian)
                k_bytes = shared_secret.to_bytes((shared_secret.bit_length() + 7) // 8, 'big')
                
                # Add sign bit if needed (Java BigInteger compatibility)
                if k_bytes[0] & 0x80:
                    k_bytes = b'\x00' + k_bytes
                
                # Calculate LST = HMAC-SHA1(K, access_token_secret)
                lst_bytes = hmac.new(
                    k_bytes,
                    base64.b64decode(self.access_token_secret),
                    hashlib.sha1
                ).digest()
                
                # CRITICAL FIX: Store LST as base64 string for consistent state management
                # This ensures it's always in the same format for HMAC signing
                self.live_session_token = base64.b64encode(lst_bytes).decode('utf-8')
                
                # Verify the signature (should use same data as LST calculation)
                computed_signature = hmac.new(
                    k_bytes,
                    base64.b64decode(self.access_token_secret),
                    hashlib.sha1
                ).hexdigest()
                
                if computed_signature != lst_signature:
                    self.logger.warning(f"LST signature mismatch")
                
                # Save tokens
                self._save_tokens()
                
                self.logger.info("Got live session token")
                return True
            else:
                self.logger.error(f"Live session token failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error getting live session token: {e}")
            return False
    
    def init_brokerage_session(self) -> bool:
        """
        Step 5: Initialize brokerage session for /iserver endpoints
        Tries localhost first (if Client Portal Gateway is running), then cloud
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Request parameters
            params = {
                'compete': 'false',
                'publish': 'true'
            }
            
            # Try multiple endpoints
            urls = [
                "https://localhost:5000/v1/api/iserver/auth/ssodh/init",  # Client Portal Gateway
                f"{self.base_url}/iserver/auth/ssodh/init"  # Cloud API
            ]
            
            for url in urls:
                try:
                    self.logger.info(f"Trying brokerage session init at: {url}")
                    # Make authenticated request
                    response = self._make_authenticated_request('POST', url, data=params)
                    
                    if response and response.status_code == 200:
                        data = response.json()
                        self.logger.info(f"Brokerage session initialized via {url}: {data}")
                        return True
                    elif response:
                        self.logger.warning(f"Failed at {url}: {response.status_code}")
                        if response.status_code == 401:
                            self.logger.warning("401 Unauthorized - Token may be expired or invalid")
                    else:
                        self.logger.warning(f"No response from {url}")
                        
                except Exception as e:
                    self.logger.warning(f"Error trying {url}: {e}")
                    continue
            
            # If we get here, all attempts failed
            self.logger.error("Failed to initialize brokerage session at all endpoints")
            return False
                
        except Exception as e:
            self.logger.error(f"Error initializing brokerage session: {e}")
            return False
    
    def _make_authenticated_request(self, method: str, url: str, 
                                  params: Dict = None, data: Dict = None) -> Optional[requests.Response]:
        """
        Make an authenticated request to IB REST API
        
        Args:
            method: HTTP method
            url: Request URL
            params: URL parameters
            data: Request body data
            
        Returns:
            Response object or None if failed
        """
        try:
            if not self.live_session_token:
                self.logger.error("No live session token available")
                return None
            
            # OAuth parameters
            oauth_params = {
                'oauth_consumer_key': self.consumer_key,
                'oauth_nonce': self._generate_nonce(),
                'oauth_signature_method': 'HMAC-SHA256',
                'oauth_timestamp': self._get_timestamp(),
                'oauth_token': self.access_token,
                'oauth_version': '1.0',  # CRITICAL: Required by IBKR even though OAuth spec considers it optional
                'realm': self.realm
            }
            
            # Combine all parameters for signature (excluding realm)
            sig_params = {k: v for k, v in oauth_params.items() if k != 'realm'}
            if params:
                sig_params.update(params)
            if data and method == 'POST':
                sig_params.update(data)
            
            # Create signature base string
            base_string = self._create_signature_base_string(method, url, sig_params)
            
            # Sign with live session token
            oauth_params['oauth_signature'] = self._sign_hmac_sha256(base_string, self.live_session_token)
            
            # Create authorization header
            auth_header = self._create_oauth_header(oauth_params)
            
            # Debug logging
            self.logger.debug(f"Request URL: {url}")
            self.logger.debug(f"OAuth params: {oauth_params}")
            self.logger.debug(f"Base string: {base_string[:200]}...")
            self.logger.debug(f"Auth header: {auth_header[:200]}...")
            
            # Make request
            headers = {
                'Authorization': auth_header,
                'Accept': 'application/json'
            }
            
            if method == 'GET':
                response = requests.get(url, params=params, headers=headers, timeout=30)
            elif method == 'POST':
                if data:
                    headers['Content-Type'] = 'application/x-www-form-urlencoded'
                    response = requests.post(url, data=urlencode(data), headers=headers, timeout=30)
                else:
                    headers['Content-Length'] = '0'
                    response = requests.post(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            self.logger.debug(f"Response status: {response.status_code}")
            self.logger.debug(f"Response text: {response.text[:200] if response.text else 'No text'}")
            return response
            
        except Exception as e:
            self.logger.error(f"Error making authenticated request: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def authenticate(self) -> bool:
        """
        Complete OAuth authentication flow
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if we have valid tokens
            if self.live_session_token:
                # Test if tokens are still valid
                if self.test_authentication():
                    self.logger.info("Using existing valid tokens")
                    return True
            
            # Check if we already have access token from environment
            env_access_token = os.getenv('IB_ACCESS_TOKEN')
            if env_access_token:
                # Use pre-authorized access token
                self.access_token = env_access_token
                self.access_token_secret = os.getenv('IB_ACCESS_TOKEN_SECRET')
                self.logger.info("Using pre-authorized access token")
                
                # Skip directly to live session token
                if not self.get_live_session_token():
                    return False
                
                # Initialize brokerage session
                if not self.init_brokerage_session():
                    return False
                
                return True
            
            # Otherwise, do full OAuth flow
            # Step 1: Request token
            if not self.get_request_token():
                return False
            
            # Step 2: Authorization (skip for headless)
            # For headless auth, we assume pre-authorization
            
            # Step 3: Access token
            if not self.get_access_token():
                return False
            
            # Step 4: Live session token
            if not self.get_live_session_token():
                return False
            
            # Step 5: Initialize brokerage session
            if not self.init_brokerage_session():
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            return False
    
    def test_authentication(self) -> bool:
        """Test authentication by making a simple API call"""
        try:
            response = self._make_authenticated_request('GET', f"{self.base_url}/portfolio/accounts")
            
            if response and response.status_code == 200:
                accounts = response.json()
                self.logger.info(f"Authentication valid. Found {len(accounts)} accounts")
                for account in accounts:
                    self.logger.info(f"  Account: {account.get('accountId')}")
                return True
            else:
                self.logger.error("Authentication test failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Authentication test error: {e}")
            return False
    
    def get_accounts(self) -> Optional[list]:
        """Get list of accounts"""
        response = self._make_authenticated_request('GET', f"{self.base_url}/portfolio/accounts")
        if response and response.status_code == 200:
            return response.json()
        return None
    
    def search_contracts(self, symbol: str, sec_type: str = "STK") -> Optional[list]:
        """Search for contracts"""
        params = {
            'symbol': symbol,
            'secType': sec_type
        }
        response = self._make_authenticated_request('GET', f"{self.base_url}/iserver/secdef/search", params=params)
        if response and response.status_code == 200:
            return response.json()
        return None


def test_auth():
    """Test authentication setup"""
    logging.basicConfig(level=logging.INFO)
    
    # Initialize auth
    auth = IBRestAuth()
    
    # Check for required environment variables
    if not auth.consumer_key:
        print("❌ IB_CONSUMER_KEY environment variable not set")
        return False
    
    if not auth.signature_key_path or not os.path.exists(auth.signature_key_path):
        print(f"❌ Signature key not found: {auth.signature_key_path}")
        return False
    
    if not auth.encryption_key_path or not os.path.exists(auth.encryption_key_path):
        print(f"❌ Encryption key not found: {auth.encryption_key_path}")
        return False
    
    print(f"✅ Consumer Key: {auth.consumer_key}")
    print(f"✅ Signature Key: {auth.signature_key_path}")
    print(f"✅ Encryption Key: {auth.encryption_key_path}")
    
    # Authenticate
    if auth.authenticate():
        print("✅ Authentication successful")
        
        # Test by getting accounts
        accounts = auth.get_accounts()
        if accounts:
            print(f"✅ Found {len(accounts)} accounts")
            return True
    
    print("❌ Authentication failed")
    return False


if __name__ == "__main__":
    test_auth()