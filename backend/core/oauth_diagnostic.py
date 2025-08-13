#!/usr/bin/env python3
"""
Enhanced OAuth Diagnostic Script for IB REST API
Shows exactly what's working and what's not with detailed error codes
"""

import os
import sys
import logging
import json
import requests
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.append('/home/info/fntx-ai-v1/backend')
from core.trading.ib_rest_auth import IBRestAuth

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_env_vars():
    """Load environment variables from .env file"""
    env_path = Path('/home/info/fntx-ai-v1/config/.env')
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    os.environ[key] = value
        logger.info("Loaded environment variables")

def test_endpoint_detailed(auth, method, endpoint, params=None, data=None, description=""):
    """Test an endpoint with detailed error reporting"""
    print(f"\n{'='*60}")
    print(f"Testing: {description or endpoint}")
    print(f"{'='*60}")
    
    url = f"{auth.base_url}{endpoint}"
    print(f"URL: {url}")
    print(f"Method: {method}")
    
    try:
        # Make the authenticated request
        response = auth._make_authenticated_request(method, url, params=params, data=data)
        
        if response is None:
            print("❌ Response is None - request failed internally")
            return False
            
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ SUCCESS")
            try:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)[:500]}")  # First 500 chars
            except:
                print(f"Response (text): {response.text[:500]}")
            return True
        else:
            print(f"❌ FAILED with status {response.status_code}")
            print(f"Response: {response.text[:500] if response.text else 'No response body'}")
            
            # Decode specific error codes
            if response.status_code == 401:
                print("→ 401 Unauthorized: Authentication failed or token expired")
            elif response.status_code == 403:
                print("→ 403 Forbidden: Account doesn't have permission for this endpoint")
            elif response.status_code == 404:
                print("→ 404 Not Found: Endpoint doesn't exist or not available")
            elif response.status_code == 500:
                print("→ 500 Server Error: IB server issue")
            elif response.status_code == 503:
                print("→ 503 Service Unavailable: Service temporarily unavailable")
                
            return False
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def main():
    """Run comprehensive diagnostics"""
    print("\n" + "="*70)
    print(" IB OAuth Enhanced Diagnostic ")
    print("="*70)
    print(f"Time: {datetime.now().isoformat()}")
    
    # Load environment
    load_env_vars()
    
    # Initialize auth
    auth = IBRestAuth()
    
    print(f"\nConfiguration:")
    print(f"  Consumer Key: {auth.consumer_key}")
    print(f"  Realm: {auth.realm}")
    print(f"  Base URL: {auth.base_url}")
    
    # Check if we have tokens
    if not auth.live_session_token:
        print("\n⚠️ No Live Session Token found, generating new one...")
        
        if not auth.access_token:
            print("❌ No access token available")
            return False
            
        # Try to generate LST
        if auth.get_live_session_token():
            print("✅ Generated new Live Session Token")
        else:
            print("❌ Failed to generate Live Session Token")
            return False
    else:
        print("✅ Using existing Live Session Token")
    
    # Test various endpoints
    results = {}
    
    # 1. Portfolio endpoints (should work with basic OAuth)
    results['portfolio'] = test_endpoint_detailed(
        auth, 'GET', '/portfolio/accounts',
        description="Portfolio Accounts (Basic OAuth endpoint)"
    )
    
    # 2. Simple test endpoint
    results['tickle'] = test_endpoint_detailed(
        auth, 'GET', '/tickle',
        description="Tickle (Session check endpoint)"
    )
    
    # 3. Market data endpoint (might need different permissions)
    results['marketdata'] = test_endpoint_detailed(
        auth, 'GET', '/md/snapshot',
        params={'conids': '265598', 'fields': 'Last'},
        description="Market Data Snapshot (SPY)"
    )
    
    # 4. The problematic SSODH endpoint
    results['ssodh'] = test_endpoint_detailed(
        auth, 'POST', '/iserver/auth/ssodh/init',
        data={'compete': False, 'publish': True},
        description="SSODH Init (Brokerage session initialization)"
    )
    
    # 5. Alternative authentication status
    results['auth_status'] = test_endpoint_detailed(
        auth, 'GET', '/iserver/auth/status',
        description="Authentication Status"
    )
    
    # 6. Account data endpoint
    results['account'] = test_endpoint_detailed(
        auth, 'GET', '/iserver/accounts',
        description="IServer Accounts"
    )
    
    # Summary
    print("\n" + "="*70)
    print(" SUMMARY ")
    print("="*70)
    
    for endpoint, success in results.items():
        status = "✅ Works" if success else "❌ Fails"
        print(f"{endpoint:20s}: {status}")
    
    # Analysis
    print("\n" + "="*70)
    print(" ANALYSIS ")
    print("="*70)
    
    if results['portfolio'] and not results['ssodh']:
        print("→ OAuth authentication works for portfolio endpoints")
        print("→ But /iserver endpoints are not accessible")
        print("→ This suggests account lacks cloud trading permissions")
        print("→ Client Portal Gateway may be required for /iserver endpoints")
    elif not results['portfolio']:
        print("→ Basic OAuth authentication is failing")
        print("→ Tokens may have expired or credentials are invalid")
    elif results['ssodh']:
        print("→ Full OAuth authentication is working!")
        print("→ You should be able to trade via API")
    
    return any(results.values())

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)