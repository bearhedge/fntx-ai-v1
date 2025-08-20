# IBKR OAuth Headless - WORKING GUIDE
**Last Updated: August 18, 2025**

## ✅ CONFIRMED WORKING: OAuth Without Gateway

This guide documents the **WORKING** method to get market data and execute trades using IBKR OAuth without any gateway running.

## Key Discovery

**YOU DON'T NEED IB GATEWAY OR CLIENT PORTAL GATEWAY!** 

OAuth alone works for:
- ✅ Account/Portfolio data
- ✅ Market data quotes
- ✅ Option chains
- ✅ Contract search
- ✅ Trading (to be tested)

## Critical Endpoints (Use These!)

### Working Endpoints
```python
/iserver/accounts              # Get accounts
/iserver/secdef/search         # Search symbols
/iserver/secdef/strikes        # Get option strikes
/iserver/secdef/info           # Get specific contracts
/iserver/marketdata/snapshot   # Get market quotes
```

### DON'T Use These (Return 404/400)
```python
/trsrv/secdef/search   # ❌ Returns 404
/md/snapshot           # ❌ Doesn't work properly
```

## Complete Working Example

### Step 1: Search for Symbol
```python
from config.IB_headless.ib_rest_auth_consolidated import IBRestAuth

auth = IBRestAuth(consumer_key='BEARHEDGE', realm='limited_poa')

# Search for ARM
response = auth.make_authenticated_request(
    'GET', 
    '/iserver/secdef/search',
    params={'symbol': 'ARM'}
)
# Returns: conid 653400472 for ARM Holdings
```

### Step 2: Get Option Strikes
```python
response = auth.make_authenticated_request(
    'GET',
    '/iserver/secdef/strikes',
    params={
        'conid': '653400472',
        'sectype': 'OPT',
        'month': 'AUG25'  # Format: MMMYY
    }
)
# Returns: Available strikes including 143, 145, etc.
```

### Step 3: Get Specific Option Contract
```python
response = auth.make_authenticated_request(
    'GET',
    '/iserver/secdef/info',
    params={
        'conid': '653400472',
        'sectype': 'OPT',
        'month': 'AUG25',
        'strike': '143',
        'right': 'C'  # C=Call, P=Put
    }
)
# Returns contracts with different expiry dates
# Aug 22 2025 143 Call: conid 804155360
```

### Step 4: Get Market Quote
```python
import time

# IMPORTANT: Two requests needed (IBKR quirk)
# First request initializes
response = auth.make_authenticated_request(
    'GET',
    '/iserver/marketdata/snapshot',
    params={
        'conids': '804155360',
        'fields': '31,84,85,86,87,88'  # Last,Bid,Ask,Volume,Open,Close
    }
)

# Wait and make second request for actual data
time.sleep(1)
response = auth.make_authenticated_request(
    'GET',
    '/iserver/marketdata/snapshot',
    params={
        'conids': '804155360',
        'fields': '31,84,85,86,87,88'
    }
)
# Returns actual quote data
```

## Known Contract IDs

### ARM Stock
- **Symbol:** ARM
- **ConID:** 653400472
- **Exchange:** NASDAQ

### ARM Options (Aug 22 2025 Expiry)
| Strike | Type | ConID | Last Price (Aug 18) |
|--------|------|--------|---------------------|
| $143 | Call | 804155360 | $1.60 |
| $145 | Call | 796812614 | $1.10 |

## Market Data Field Codes
- **31:** Last Price
- **84:** Bid Price  
- **85:** Ask Price
- **86:** Volume
- **87:** Open
- **88:** Previous Close

## Known Issues

1. **Field Mapping Errors:** Ask price sometimes shows incorrectly (e.g., 598 instead of 1.65)
2. **Two-Request Pattern:** Market data requires two requests - first initializes, second returns data
3. **Response Format:** Some fields come as strings, need parsing

## Authentication Setup

### Required Files
1. `/home/info/fntx-ai-v1/config/keys/private_signature.pem` - RSA signing key
2. `/home/info/fntx-ai-v1/config/keys/private_encryption.pem` - Encryption key
3. `/home/info/fntx-ai-v1/config/keys/dhparam.pem` - DH parameters
4. `/home/info/fntx-ai-v1/config/.env` - Environment variables

### Environment Variables
```bash
IB_CONSUMER_KEY=BEARHEDGE
IB_ACCESS_TOKEN=8444def5466e38fb8b86
IB_ACCESS_TOKEN_SECRET=[encrypted_secret]
IB_SIGNATURE_KEY_PATH=/home/info/fntx-ai-v1/config/keys/private_signature.pem
IB_ENCRYPTION_KEY_PATH=/home/info/fntx-ai-v1/config/keys/private_encryption.pem
IB_DH_PARAM_PATH=/home/info/fntx-ai-v1/config/keys/dhparam.pem
IB_REALM=limited_poa
IB_IS_LIVE=true
```

## Quick Test Script

```python
#!/usr/bin/env python3
# Save as test_oauth.py

import sys
sys.path.append('/home/info/fntx-ai-v1')
from config.IB_headless.ib_rest_auth_consolidated import IBRestAuth

auth = IBRestAuth(consumer_key='BEARHEDGE', realm='limited_poa')

# Test authentication
response = auth.make_authenticated_request('GET', '/iserver/accounts')
if response and response.status_code == 200:
    print("✅ OAuth is working!")
    print(f"Account: {response.json()}")
else:
    print("❌ OAuth failed")
```

## Trading Endpoints (To Be Tested)

```python
/iserver/account/{accountId}/orders  # Place orders
/iserver/account/{accountId}/order/{orderId}  # Modify/cancel orders
/iserver/account/orders  # Get open orders
/iserver/account/trades  # Get executed trades
```

## Key Insights

1. **No Gateway Required:** Pure OAuth headless operation works!
2. **Use /iserver/ endpoints:** These are the correct REST API endpoints
3. **Avoid /trsrv/ endpoints:** These don't work with OAuth alone
4. **Two-step market data:** Always make two requests for market data
5. **Field mapping issues:** Some response fields are incorrectly mapped

## Files in This Directory

- `ib_rest_auth_consolidated.py` - Main OAuth implementation with all fixes
- `arm_option_working.py` - Complete working example for getting option quotes
- `test_api_basic.py` - API endpoint tester
- `OAUTH_SETUP.md` - Original OAuth setup documentation
- `OAUTH_WORKING_GUIDE.md` - This file