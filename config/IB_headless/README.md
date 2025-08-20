# IBKR REST API OAuth Implementation

This folder contains the consolidated Python implementation for IBKR REST API OAuth authentication, matching the behavior of the working web demo.

## Files

- `ib_rest_auth_consolidated.py` - Main OAuth implementation
- `test_bearhedge_auth.py` - Test script using BEARHEDGE consumer key
- `oauth_utils.py` - Reference implementation from IBKR
- `IB_demo/` - Working web demo files

## Key Features

### OAuth 1.0a Implementation
- **RSA-SHA256** for initial OAuth flow (request token, access token, LST)
- **HMAC-SHA256** for authenticated API calls after getting LST
- Proper URL encoding of signatures using `quote_plus()`
- Includes critical `oauth_version='1.0'` parameter

### Signature Methods

#### RSA-SHA256 (for OAuth flow)
```python
def _sign_rsa_sha256(self, base_string: str) -> str:
    signature = private_key.sign(base_string.encode('utf-8'), padding.PKCS1v15(), hashes.SHA256())
    signature_b64 = base64.b64encode(signature).decode('utf-8')
    return quote_plus(signature_b64)  # URL encode
```

#### HMAC-SHA256 (for API calls)
```python
def _sign_hmac_sha256(self, base_string: str, key: str) -> str:
    key_bytes = base64.b64decode(key)  # Decode LST from base64
    mac = hmac.new(key_bytes, base_string.encode('utf-8'), hashlib.sha256)
    signature_b64 = base64.b64encode(mac.digest()).decode('utf-8')
    return quote_plus(signature_b64)  # URL encode to match RSA
```

## Setup

### 1. Environment Variables
```bash
export IB_CONSUMER_KEY="BEARHEDGE"
export IB_REALM="limited_poa"
export IB_ACCESS_TOKEN="your_access_token"
export IB_ACCESS_TOKEN_SECRET="your_encrypted_access_token_secret"
export IB_SIGNATURE_KEY_PATH="/path/to/private_signature.pem"
export IB_ENCRYPTION_KEY_PATH="/path/to/private_encryption.pem"
export IB_DH_PARAM_PATH="/path/to/dhparam.pem"
```

### 2. Key Files Required
- `private_signature.pem` - RSA private key for signing
- `private_encryption.pem` - RSA private key for decryption
- `dhparam.pem` - Diffie-Hellman parameters

### 3. Extract DH Prime from dhparam.pem
```bash
openssl dhparam -in dhparam.pem -text -noout
```

## Usage

### Basic Authentication
```python
from ib_rest_auth_consolidated import IBRestAuth

# Initialize
auth = IBRestAuth(
    consumer_key='BEARHEDGE',
    realm='limited_poa'
)

# Authenticate
if auth.authenticate():
    print("Authentication successful")
    
    # Make API calls
    accounts = auth.get_accounts()
    print(f"Accounts: {accounts}")
```

### Making Authenticated Requests
```python
# GET request
response = auth.make_authenticated_request('GET', '/portfolio/accounts')

# POST request with data
response = auth.make_authenticated_request(
    'POST', 
    '/iserver/auth/ssodh/init',
    data={'compete': 'false', 'publish': 'true'}
)
```

## Testing

Run the test script:
```bash
cd /home/info/fntx-ai-v1/config/IB_headless
python3 test_bearhedge_auth.py
```

Expected output:
- Successfully gets Live Session Token
- Returns 200 OK on `/portfolio/accounts` endpoint
- Matches web demo behavior

## Common Issues & Solutions

### 1. 401 Unauthorized on API calls
- Ensure `oauth_version='1.0'` is included
- Verify signatures are URL-encoded with `quote_plus()`
- Check that LST is base64-decoded before using as HMAC key

### 2. Signature Mismatch
- RSA signatures must be URL-encoded
- HMAC signatures must also be URL-encoded to match
- Base string must exclude 'realm' parameter

### 3. DH Parameter Issues
- Extract prime using openssl command
- Ensure prime is in hex format without colons/spaces
- Generator is typically 2

## Web Demo Comparison

The Python implementation matches the web demo's behavior:
1. Same OAuth header format
2. Same signature encoding (URL-encoded base64)
3. Same parameter ordering (alphabetical)
4. Includes oauth_version for HMAC requests

## References

- [IBKR OAuth Documentation](https://www.interactivebrokers.com/api/doc.html)
- [OAuth 1.0a Specification](https://oauth.net/core/1.0a/)
- Web Demo: `IB_demo/oauth.web.demo/dist/index.htm`