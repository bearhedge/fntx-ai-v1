# IB REST API Authentication Documentation

## Overview

This document provides comprehensive guidance for implementing Interactive Brokers REST API authentication for headless trading. The REST API eliminates the need for IB Gateway desktop application, allowing direct API-based trading with institutional accounts.

**Key Benefits**:
- No desktop application required (headless authentication)
- No daily manual login requirement
- No ghost connection issues
- Direct HTTP/REST communication
- Better suited for automated trading systems
- OAuth2-based secure authentication

## Table of Contents

1. [Authentication Components](#authentication-components)
2. [Key Generation](#key-generation)
3. [Access Token Management](#access-token-management)
4. [OAuth Implementation](#oauth-implementation)
5. [Security Best Practices](#security-best-practices)
6. [Migration Guide](#migration-guide)
7. [Quick Reference](#quick-reference)
8. [Troubleshooting](#troubleshooting)

## Authentication Components

### Required Keys and Parameters

1. **Public Signing Key**
   - Used for signing OAuth requests
   - RSA 2048-bit key
   - Path: `public_signature.pem`

2. **Public Encryption Key**
   - Used for encrypting sensitive data
   - RSA 2048-bit key
   - Path: `public_encryption.pem`

3. **Diffie-Hellman Parameters**
   - Used for secure key exchange
   - 2048-bit parameters
   - Path: `dhparams.pem`

4. **Access Token**
   - Consumer key for OAuth
   - Example: `8444def5466e38fb8b86`

5. **Access Token Secret**
   - Encrypted secret for OAuth
   - **NEVER SHARE OR COMMIT TO VERSION CONTROL**
   - Store securely in environment variables or secure vault

### Authentication Realms

- **Production**: `limited_poa` (Limited Power of Attorney for institutional accounts)
- **Testing**: `test_realm` (Used with TESTCONS consumer key)

## Key Generation

### Generate RSA Keys

```bash
# Generate private signing key
openssl genrsa -out private_signature.pem 2048

# Extract public signing key
openssl rsa -in private_signature.pem -outform PEM -pubout -out public_signature.pem

# Generate private encryption key
openssl genrsa -out private_encryption.pem 2048

# Extract public encryption key
openssl rsa -in private_encryption.pem -outform PEM -pubout -out public_encryption.pem

# Generate Diffie-Hellman parameters
openssl dhparam -outform PEM 2048 -out dhparam.pem
```

### Key Storage Structure

```
/home/info/fntx-ai-v1/
├── config/
│   ├── keys/
│   │   ├── private_signature.pem    # NEVER commit
│   │   ├── public_signature.pem     # Submit to IBKR
│   │   ├── private_encryption.pem   # NEVER commit
│   │   ├── public_encryption.pem    # Submit to IBKR
│   │   └── dhparam.pem             # Submit to IBKR
│   └── .env                        # Contains secrets
```

## Access Token Management

### Token Structure

```
Access Token: 8444def5466e38fb8b86
Access Token Secret: [Encrypted base64 string - DO NOT SHARE]
```

### Environment Variables

Add to `/home/info/fntx-ai-v1/config/.env`:

```bash
# IB REST API Configuration
IB_CONSUMER_KEY=8444def5466e38fb8b86
IB_ACCESS_TOKEN_SECRET="[Your encrypted token secret]"
IB_SIGNATURE_KEY_PATH=/home/info/fntx-ai-v1/config/keys/private_signature.pem
IB_ENCRYPTION_KEY_PATH=/home/info/fntx-ai-v1/config/keys/private_encryption.pem
IB_DH_PARAM_PATH=/home/info/fntx-ai-v1/config/keys/dhparam.pem
IB_REALM=limited_poa
IB_IS_LIVE=true
```

### Token Lifecycle

1. **Initial Token**: Valid until regenerated
2. **Token Rotation**: Can generate new tokens anytime via IBKR portal
3. **Live Session Token**: Generated dynamically, expires after 24 hours
4. **Automatic Refresh**: Implementation handles token refresh automatically

## OAuth Implementation

### OAuth Flow Overview

```
1. Request Token → 2. Authorization → 3. Access Token → 4. Live Session Token → 5. API Access
```

### 1. Request Token

```python
POST https://api.ibkr.com/v1/api/oauth/request_token

Headers:
Authorization: OAuth realm="limited_poa",
               oauth_callback="oob",
               oauth_consumer_key="8444def5466e38fb8b86",
               oauth_nonce="[random_nonce]",
               oauth_signature="[RSA-SHA256 signature]",
               oauth_signature_method="RSA-SHA256",
               oauth_timestamp="[unix_timestamp]"
```

### 2. Authorization (Skip for Headless)

For headless authentication with institutional accounts, this step is typically pre-authorized.

### 3. Access Token

```python
POST https://api.ibkr.com/v1/api/oauth/access_token

Headers:
Authorization: OAuth realm="limited_poa",
               oauth_consumer_key="8444def5466e38fb8b86",
               oauth_nonce="[random_nonce]",
               oauth_signature="[RSA-SHA256 signature]",
               oauth_signature_method="RSA-SHA256",
               oauth_timestamp="[unix_timestamp]",
               oauth_token="[request_token]",
               oauth_verifier="[verifier_token]"
```

### 4. Live Session Token

```python
POST https://api.ibkr.com/v1/api/oauth/live_session_token

Headers:
Authorization: OAuth realm="limited_poa",
               diffie_hellman_challenge="[DH challenge]",
               oauth_consumer_key="8444def5466e38fb8b86",
               oauth_nonce="[random_nonce]",
               oauth_signature="[RSA-SHA256 signature]",
               oauth_signature_method="RSA-SHA256",
               oauth_timestamp="[unix_timestamp]",
               oauth_token="[access_token]"
```

### 5. API Access

Once authenticated, access protected endpoints:

```python
GET https://api.ibkr.com/v1/api/portfolio/accounts

Headers:
Authorization: OAuth realm="limited_poa",
               oauth_consumer_key="8444def5466e38fb8b86",
               oauth_nonce="[random_nonce]",
               oauth_signature="[HMAC-SHA256 signature]",
               oauth_signature_method="HMAC-SHA256",
               oauth_timestamp="[unix_timestamp]",
               oauth_token="[access_token]"
```

## Security Best Practices

### 1. Key Management

```bash
# Set proper file permissions
chmod 600 /home/info/fntx-ai-v1/config/keys/private_*.pem
chmod 644 /home/info/fntx-ai-v1/config/keys/public_*.pem
chmod 644 /home/info/fntx-ai-v1/config/keys/dhparam.pem

# Ensure keys directory is not in git
echo "config/keys/" >> .gitignore
```

### 2. Environment Variables

```bash
# Never commit .env file
echo ".env" >> .gitignore

# Use system environment variables in production
export IB_CONSUMER_KEY="8444def5466e38fb8b86"
export IB_ACCESS_TOKEN_SECRET="[encrypted_secret]"
```

### 3. Token Storage

- Store tokens in encrypted format
- Use secure key management service in production
- Rotate tokens regularly
- Monitor token usage for anomalies

### 4. Network Security

- Always use HTTPS
- Implement request rate limiting
- Use IP whitelisting if possible
- Monitor for suspicious activity

## Migration Guide

### From IB Gateway/TWS to REST API

1. **Stop IB Gateway**
   ```bash
   pkill -f "java.*ibgateway"
   ```

2. **Update Trading Scripts**
   - Replace `execute_spy_trades.py` with `execute_spy_trades_rest.py`
   - Update import statements from `ib_insync` to REST client
   - Remove connection management code (no persistent connections)

3. **Benefits**
   - No ghost connections
   - No daily login requirement
   - Better error handling
   - Stateless requests

### Code Migration Example

**Before (ib_insync)**:
```python
from ib_insync import IB, Stock, Option

ib = IB()
ib.connect('127.0.0.1', 4001, clientId=1)
```

**After (REST API)**:
```python
from trading.ib_rest_client import IBRestClient

client = IBRestClient()
# No connection needed - stateless
```

## Quick Reference

### Essential Commands

```bash
# Generate new keys
./scripts/generate_ib_keys.sh

# Test authentication
python -m backend.core.trading.ib_rest_auth

# Execute trades
python backend/core/execute_spy_trades_rest.py --side both

# Check token validity
curl -H "Authorization: Bearer [token]" \
     https://api.ibkr.com/v1/api/portfolio/accounts
```

### Common API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/oauth/request_token` | POST | Get request token |
| `/oauth/access_token` | POST | Get access token |
| `/oauth/live_session_token` | POST | Get live session token |
| `/portfolio/accounts` | GET | List accounts |
| `/iserver/contract/search` | GET | Search contracts |
| `/iserver/account/{accountId}/orders` | POST | Place order |
| `/iserver/marketdata/snapshot` | GET | Get market data |

### Trading Workflow

1. **Authenticate** (automatic on first request)
2. **Search Contract**
   ```
   GET /iserver/contract/search?symbol=SPY&secType=OPT
   ```
3. **Place Order**
   ```
   POST /iserver/account/{accountId}/orders
   ```
4. **Monitor Order**
   ```
   GET /iserver/account/{accountId}/orders
   ```

## Troubleshooting

### Common Issues

1. **401 Unauthorized**
   - Check consumer key is correct
   - Verify signature calculation
   - Ensure timestamp is within 5 minutes

2. **Invalid Signature**
   - Verify private key matches public key
   - Check base string construction
   - Ensure proper URL encoding

3. **Token Expired**
   - Implement automatic token refresh
   - Check token expiry before requests
   - Handle refresh token properly

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Testing

1. **Test OAuth Flow**
   ```bash
   python -m backend.core.trading.test_ib_oauth
   ```

2. **Verify Keys**
   ```bash
   openssl rsa -in private_signature.pem -check
   openssl rsa -in public_signature.pem -pubin -text
   ```

3. **Check API Access**
   ```bash
   curl -v -H "Authorization: OAuth ..." \
        https://api.ibkr.com/v1/api/portfolio/accounts
   ```

## Implementation Status

### Completed
- [x] OAuth authentication module (`ib_rest_auth.py`)
- [x] Key generation instructions
- [x] Security best practices documentation

### TODO
- [ ] REST API client implementation
- [ ] SPY options trading functions
- [ ] Execute trades script (`execute_spy_trades_rest.py`)
- [ ] Integration testing
- [ ] Production deployment

## References

- [IBKR REST API Documentation](https://www.interactivebrokers.com/api/doc.html)
- [OAuth 1.0a Specification](https://oauth.net/core/1.0a/)
- [IBKR Self-Service Portal](https://www.interactivebrokers.com/sso/Login)

---

**Last Updated**: August 2025
**Document Version**: 1.0
**Maintained By**: FNTX Trading System Team