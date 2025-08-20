#!/usr/bin/env python3
"""
IBKR REST API OAuth Authentication - Consolidated Implementation
Based on working web demo and reference implementations
Tested with BEARHEDGE consumer key
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
from urllib.parse import quote_plus, quote, urlencode
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

class IBRestAuth:
    """
    IBKR REST API OAuth 1.0a Authentication Handler
    Consolidated implementation matching web demo behavior
    """
    
    def __init__(self, 
                 consumer_key: str = None,
                 realm: str = None,
                 is_live: bool = True,
                 token_file: str = None):
        """
        Initialize IB REST API authentication
        
        Args:
            consumer_key: OAuth consumer key (BEARHEDGE for testing)
            realm: Authentication realm (limited_poa for institutional)
            is_live: Use live API (True) or paper trading (False)
            token_file: Path to store/retrieve tokens
        """
        self.consumer_key = consumer_key or os.getenv('IB_CONSUMER_KEY', 'BEARHEDGE')
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
        
        # Keys - default to BEARHEDGE test paths
        self.signature_key_path = os.getenv('IB_SIGNATURE_KEY_PATH', 
            '/home/info/fntx-ai-v1/config/keys/private_signature.pem')
        self.encryption_key_path = os.getenv('IB_ENCRYPTION_KEY_PATH',
            '/home/info/fntx-ai-v1/config/keys/private_encryption.pem')
        self.dh_param_path = os.getenv('IB_DH_PARAM_PATH',
            '/home/info/fntx-ai-v1/config/keys/dhparam.pem')
        
        # DH parameters
        self.dh_prime = None
        self.dh_generator = 2
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
        # Load existing tokens if available
        self._load_tokens()
        
        # Load DH parameters
        self._load_dh_params()
    
    def _load_dh_params(self):
        """Load Diffie-Hellman parameters from file"""
        try:
            # Use the correct DH prime value (extracted from dhparam.pem)
            self.dh_prime = "E07E73AA8A4EE468DC3748936F27F864754F73EA087EC5D0422D12915D3CB94C790FB6825FDEFD356453253B509CD693A793BBB484DD9632FBE6387530F0103D1FCE88C3B503A91DB4220AF9E8DFA39DF5ABB17C97C8E28005B299E841777AD5CE068BD01D037B6D584894863FF8418FD36FB18F22BC968662843ABB4D5E749DD24DD8890E4E7D032560FFC98CB685B0134BCB252C6A5A48D49C8B61A8761D52A64958351BE57242E61F2BC461BED325EEDF55976CE338230D12E12388A1F899FEE8D38E97C39C1225CAEBFD6CB4B50B75F5C2ACFCDB5B581857A3ABFC479B1066232FC2B9FB8C5E030CD5262B95AE923B6A0992B3A9EEC92435F39DB15D85C7"
            self.logger.info(f"Loaded DH prime: {self.dh_prime[:32]}...")
        except Exception as e:
            self.logger.error(f"Error loading DH parameters: {e}")
    
    def _generate_nonce(self, length: int = 32) -> str:
        """Generate a random nonce for OAuth"""
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))
    
    def _get_timestamp(self) -> str:
        """Get current Unix timestamp as string"""
        return str(int(time.time()))
    
    def _percent_encode(self, string: str) -> str:
        """
        Percent encode according to OAuth spec
        Uses quote with safe='~' to match OAuth requirements
        """
        return quote(str(string), safe='~')
    
    def _create_signature_base_string(self, method: str, url: str, params: Dict[str, str], 
                                    prepend: str = None) -> str:
        """
        Create OAuth signature base string
        Matches the format from working implementations
        """
        # Sort parameters alphabetically
        sorted_params = sorted(params.items())
        
        # Create parameter string
        param_string = '&'.join([f"{k}={self._percent_encode(v)}" for k, v in sorted_params])
        
        # Create base string
        base_string = f"{method.upper()}&{self._percent_encode(url)}&{self._percent_encode(param_string)}"
        
        # Add prepend if provided (for LST)
        if prepend:
            base_string = prepend + base_string
        
        # Fix double-encoding issues (matches JavaScript implementation)
        # These replacements are critical for IBKR API compatibility
        base_string = base_string.replace('%257C', '%7C')  # Fix double-encoded pipe |
        base_string = base_string.replace('%252C', '%2C')  # Fix double-encoded comma ,
        base_string = base_string.replace('%253A', '%3A')  # Fix double-encoded colon :
        
        return base_string
    
    def _sign_rsa_sha256(self, base_string: str) -> str:
        """
        Sign using RSA-SHA256 (for request token, access token, and LST)
        Returns base64-encoded signature (NOT URL-encoded)
        """
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
        
        # Base64 encode and return directly (no URL encoding)
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        # Return base64 signature directly (matches JavaScript implementation)
        return signature_b64
    
    def _sign_hmac_sha256(self, base_string: str, key: str) -> str:
        """
        Sign using HMAC-SHA256 (for API calls after getting LST)
        Matches reference implementation exactly
        
        Args:
            base_string: OAuth signature base string
            key: Live session token (base64 encoded)
            
        Returns:
            Base64-encoded signature (NOT URL-encoded)
        """
        # Decode the LST from base64 to use as HMAC key
        key_bytes = base64.b64decode(key)
        
        # Create HMAC
        mac = hmac.new(
            key_bytes,
            base_string.encode('utf-8'),
            hashlib.sha256
        )
        
        # Get digest and base64 encode
        signature_bytes = mac.digest()
        signature_b64 = base64.b64encode(signature_bytes).decode('utf-8')
        
        # Return base64 signature directly (matches JavaScript implementation)
        return signature_b64
    
    def _create_oauth_header(self, params: Dict[str, str]) -> str:
        """
        Create OAuth authorization header
        Format: OAuth realm="limited_poa", key1="value1", key2="value2"
        OAuth spec requires percent-encoding of parameter values
        """
        # Get realm
        realm = params.get('realm', self.realm)
        
        # Create header params (exclude realm from sorted params)
        header_params = {k: v for k, v in params.items() if k != 'realm'}
        
        # Sort and format parameters with percent-encoding for values
        param_strings = []
        for key, value in sorted(header_params.items()):
            # Percent-encode the value (especially important for oauth_signature)
            encoded_value = quote(value, safe='')
            param_strings.append(f'{key}="{encoded_value}"')
        
        # Format header
        authorization_header = f'OAuth realm="{realm}", {", ".join(param_strings)}'
        return authorization_header
    
    def _load_tokens(self) -> bool:
        """Load tokens from file if they exist"""
        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, 'r') as f:
                    data = json.load(f)
                    self.access_token = data.get('access_token')
                    self.access_token_secret = data.get('access_token_secret')
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
            os.makedirs(os.path.dirname(self.token_file) if os.path.dirname(self.token_file) else '.', exist_ok=True)
            
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
        Uses RSA-SHA256 signature
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
            
            # Create signature base string (exclude realm)
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
            
            self.logger.debug(f"Request token URL: {url}")
            self.logger.debug(f"Authorization: {auth_header}")
            
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
        Uses RSA-SHA256 signature
        """
        try:
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
            
            # Add verifier if provided
            if verifier:
                oauth_params['oauth_verifier'] = verifier
            
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
    
    def get_live_session_token(self) -> bool:
        """
        Step 4: Get live session token using Diffie-Hellman exchange
        Uses RSA-SHA256 signature with prepend
        """
        try:
            if not self.access_token or not self.access_token_secret:
                self.logger.error("No access token available")
                return False
            
            if not self.dh_prime:
                self.logger.error("DH parameters not loaded")
                return False
            
            url = f"{self.oauth_base}/live_session_token"
            
            # Generate DH challenge
            dh_random = random.getrandbits(256)
            dh_prime_int = int(self.dh_prime, 16)
            dh_challenge = pow(self.dh_generator, dh_random, dh_prime_int)
            dh_challenge_hex = format(dh_challenge, 'x')
            
            # Decrypt access token secret for prepend
            with open(self.encryption_key_path, 'rb') as f:
                from cryptography.hazmat.primitives.asymmetric import padding
                private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
                
                # Decrypt access token secret
                decrypted_secret = private_key.decrypt(
                    base64.b64decode(self.access_token_secret),
                    padding.PKCS1v15()
                )
                prepend = decrypted_secret.hex()
            
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
            
            response = requests.post(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                dh_response = data.get('diffie_hellman_response')
                
                # Calculate shared secret
                dh_response_int = int(dh_response, 16)
                shared_secret = pow(dh_response_int, dh_random, dh_prime_int)
                
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
                
                # Store LST as base64 string
                self.live_session_token = base64.b64encode(lst_bytes).decode('utf-8')
                
                # Save tokens
                self._save_tokens()
                
                self.logger.info("Got live session token")
                return True
            else:
                self.logger.error(f"Live session token failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error getting live session token: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def make_authenticated_request(self, method: str, endpoint: str, 
                                 params: Dict = None, data: Dict = None) -> Optional[requests.Response]:
        """
        Make an authenticated request to IB REST API
        Uses HMAC-SHA256 signature with LST
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., '/portfolio/accounts')
            params: URL parameters
            data: Request body data
            
        Returns:
            Response object or None if failed
        """
        try:
            if not self.live_session_token:
                self.logger.error("No live session token available")
                return None
            
            # Build full URL
            url = f"{self.base_url}{endpoint}"
            
            # OAuth parameters
            oauth_params = {
                'oauth_consumer_key': self.consumer_key,
                'oauth_nonce': self._generate_nonce(),
                'oauth_signature_method': 'HMAC-SHA256',
                'oauth_timestamp': self._get_timestamp(),
                'oauth_token': self.access_token,
                'oauth_version': '1.0',  # CRITICAL: Required for HMAC
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
            
            # Make request
            headers = {
                'Authorization': auth_header,
                'Accept': 'application/json'
            }
            
            self.logger.debug(f"Request: {method} {url}")
            self.logger.debug(f"Authorization: {auth_header}")
            
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
            
            self.logger.debug(f"Response: {response.status_code}")
            return response
            
        except Exception as e:
            self.logger.error(f"Error making authenticated request: {e}")
            return None
    
    def get_accounts(self) -> Optional[list]:
        """
        Get portfolio accounts
        Test endpoint that should return 200 OK with BEARHEDGE key
        """
        response = self.make_authenticated_request('GET', '/portfolio/accounts')
        if response and response.status_code == 200:
            return response.json()
        return None
    
    def authenticate(self) -> bool:
        """
        Complete OAuth authentication flow
        For BEARHEDGE testing, tokens are pre-configured
        """
        # Check if we already have tokens
        if self.live_session_token:
            self.logger.info("Using existing live session token")
            return True
        
        # For BEARHEDGE, we should have pre-configured tokens
        if self.consumer_key == 'BEARHEDGE':
            # Try to load from environment
            self.access_token = os.getenv('IB_ACCESS_TOKEN')
            self.access_token_secret = os.getenv('IB_ACCESS_TOKEN_SECRET')
            
            if self.access_token and self.access_token_secret:
                self.logger.info("Using BEARHEDGE pre-configured tokens")
                # Try to get LST
                return self.get_live_session_token()
        
        self.logger.error("Authentication failed - no valid tokens")
        return False
    
    # ==================== TRADING METHODS ====================
    
    def search_contract(self, symbol: str) -> Optional[Dict]:
        """
        Search for a contract by symbol
        
        Args:
            symbol: Stock or option symbol (e.g., 'SPY')
            
        Returns:
            Contract information or None
        """
        response = self.make_authenticated_request(
            'GET', 
            f'/trsrv/secdef/search',
            params={'symbol': symbol}
        )
        
        if response and response.status_code == 200:
            return response.json()
        return None
    
    def get_option_strikes(self, conid: int, exchange: str = 'SMART') -> Optional[Dict]:
        """
        Get available option strikes for an underlying
        
        Args:
            conid: Contract ID of the underlying
            exchange: Exchange (default SMART)
            
        Returns:
            Strike prices and expirations
        """
        response = self.make_authenticated_request(
            'GET',
            f'/iserver/secdef/strikes',
            params={
                'conid': conid,
                'sectype': 'OPT',
                'exchange': exchange
            }
        )
        
        if response and response.status_code == 200:
            return response.json()
        return None
    
    def get_market_data(self, conids: list, fields: str = "31,84,85,86,87,88") -> Optional[Dict]:
        """
        Get market data snapshot (15-min delayed without subscription)
        
        Args:
            conids: List of contract IDs
            fields: Comma-separated field IDs
                   31=Last, 84=Bid, 85=Ask, 86=Volume, 87=Open, 88=Close
                   
        Returns:
            Market data snapshot
        """
        conid_str = ','.join(str(c) for c in conids)
        response = self.make_authenticated_request(
            'GET',
            '/md/snapshot',
            params={
                'conids': conid_str,
                'fields': fields
            }
        )
        
        if response and response.status_code == 200:
            return response.json()
        return None
    
    def place_order(self, account_id: str, order: Dict) -> Optional[Dict]:
        """
        Place a trading order
        
        Args:
            account_id: Account ID (e.g., 'U19860056')
            order: Order details dict with:
                   - conid: Contract ID
                   - orderType: LMT, MKT, STP, etc.
                   - side: BUY or SELL
                   - quantity: Number of contracts
                   - price: Limit price (for LMT orders)
                   - tif: Time in force (DAY, GTC, etc.)
                   
        Returns:
            Order response with order ID
        """
        response = self.make_authenticated_request(
            'POST',
            f'/iserver/account/{account_id}/order',
            data=order
        )
        
        if response:
            result = response.json()
            
            # Handle order confirmation/warning
            if response.status_code == 200 and isinstance(result, list):
                # May need to confirm warnings
                if result[0].get('id'):
                    return self._confirm_order(result[0]['id'])
            
            return result
        return None
    
    def _confirm_order(self, reply_id: str) -> Optional[Dict]:
        """
        Confirm order after warnings
        
        Args:
            reply_id: Reply ID from initial order submission
            
        Returns:
            Final order response
        """
        response = self.make_authenticated_request(
            'POST',
            f'/iserver/reply/{reply_id}',
            data={'confirmed': True}
        )
        
        if response and response.status_code == 200:
            return response.json()
        return None
    
    def get_orders(self) -> Optional[list]:
        """
        Get all open orders
        
        Returns:
            List of open orders
        """
        response = self.make_authenticated_request('GET', '/iserver/account/orders')
        
        if response and response.status_code == 200:
            return response.json()
        return None
    
    def cancel_order(self, account_id: str, order_id: str) -> bool:
        """
        Cancel an open order
        
        Args:
            account_id: Account ID
            order_id: Order ID to cancel
            
        Returns:
            True if cancelled successfully
        """
        response = self.make_authenticated_request(
            'DELETE',
            f'/iserver/account/{account_id}/order/{order_id}'
        )
        
        return response and response.status_code in [200, 202]
    
    def get_trades(self) -> Optional[list]:
        """
        Get today's executed trades
        
        Returns:
            List of today's trades
        """
        response = self.make_authenticated_request('GET', '/iserver/account/trades')
        
        if response and response.status_code == 200:
            return response.json()
        return None
    
    def get_positions(self, account_id: str, page: int = 0) -> Optional[list]:
        """
        Get current positions
        
        Args:
            account_id: Account ID
            page: Page number for pagination
            
        Returns:
            List of positions
        """
        response = self.make_authenticated_request(
            'GET',
            f'/portfolio/{account_id}/positions/{page}'
        )
        
        if response and response.status_code == 200:
            return response.json()
        return None