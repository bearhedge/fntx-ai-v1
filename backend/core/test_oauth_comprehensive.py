#!/usr/bin/env python3
"""
Comprehensive OAuth Authentication Test for IB REST API
Tests the complete authentication flow and provides detailed diagnostics
"""

import os
import sys
import logging
import json
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.append('/home/info/fntx-ai-v1/backend')
from core.trading.ib_rest_auth import IBRestAuth

# Configure logging
logging.basicConfig(
    level=logging.INFO,
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
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    os.environ[key] = value
        logger.info("Loaded environment variables from .env")
    else:
        logger.warning(".env file not found")

def check_prerequisites():
    """Check if all required files and environment variables are present"""
    print("\n" + "="*60)
    print("PREREQUISITE CHECK")
    print("="*60)
    
    required_vars = [
        'IB_CONSUMER_KEY',
        'IB_SIGNATURE_KEY_PATH',
        'IB_ENCRYPTION_KEY_PATH',
        'IB_REALM'
    ]
    
    all_good = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            if 'PATH' in var:
                if os.path.exists(value):
                    print(f"✅ {var}: {value} (exists)")
                else:
                    print(f"❌ {var}: {value} (file not found)")
                    all_good = False
            else:
                # Don't show full secret values
                if 'SECRET' in var:
                    print(f"✅ {var}: ***{value[-10:] if len(value) > 10 else 'SET'}")
                else:
                    print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: NOT SET")
            all_good = False
    
    # Check optional access token
    access_token = os.getenv('IB_ACCESS_TOKEN')
    if access_token:
        print(f"ℹ️  IB_ACCESS_TOKEN: {access_token[:10]}... (pre-authorized)")
    else:
        print("ℹ️  IB_ACCESS_TOKEN: Not set (will need full OAuth flow)")
    
    return all_good

def test_existing_tokens(auth):
    """Test if existing tokens are still valid"""
    print("\n" + "="*60)
    print("TESTING EXISTING TOKENS")
    print("="*60)
    
    # Check if token file exists
    if os.path.exists(auth.token_file):
        print(f"Token file found: {auth.token_file}")
        with open(auth.token_file, 'r') as f:
            tokens = json.load(f)
            print(f"  Created: {tokens.get('timestamp', 'Unknown')}")
            print(f"  Consumer: {tokens.get('consumer_key', 'Unknown')}")
            print(f"  Has LST: {'Yes' if tokens.get('live_session_token') else 'No'}")
    else:
        print("No existing token file")
        return False
    
    # Test authentication with existing tokens
    print("\nTesting authentication with existing tokens...")
    if auth.test_authentication():
        print("✅ Existing tokens are valid!")
        return True
    else:
        print("❌ Existing tokens are invalid or expired")
        return False

def test_fresh_authentication(auth):
    """Perform fresh authentication"""
    print("\n" + "="*60)
    print("FRESH AUTHENTICATION")
    print("="*60)
    
    # Clear existing tokens
    auth.access_token = None
    auth.access_token_secret = None
    auth.live_session_token = None
    
    print("Starting fresh OAuth flow...")
    
    # Check if we have pre-authorized access token
    if os.getenv('IB_ACCESS_TOKEN'):
        print("Using pre-authorized access token...")
        auth.access_token = os.getenv('IB_ACCESS_TOKEN')
        auth.access_token_secret = os.getenv('IB_ACCESS_TOKEN_SECRET')
        
        # Step 4: Get Live Session Token
        print("\nStep 4: Getting Live Session Token...")
        if auth.get_live_session_token():
            print("✅ Got live session token")
            
            # Step 5: Initialize brokerage session
            print("\nStep 5: Initializing brokerage session...")
            if auth.init_brokerage_session():
                print("✅ Brokerage session initialized")
                return True
            else:
                print("❌ Failed to initialize brokerage session")
                return False
        else:
            print("❌ Failed to get live session token")
            return False
    else:
        print("No pre-authorized access token, would need full OAuth flow")
        print("This requires user interaction for authorization step")
        return False

def test_api_endpoints(auth):
    """Test various API endpoints"""
    print("\n" + "="*60)
    print("API ENDPOINT TESTS")
    print("="*60)
    
    # Test portfolio accounts
    print("\n1. Testing /portfolio/accounts...")
    accounts = auth.get_accounts()
    if accounts:
        print(f"✅ Found {len(accounts)} account(s):")
        for acc in accounts:
            print(f"   - {acc.get('accountId', 'Unknown')}")
    else:
        print("❌ Failed to get accounts")
        return False
    
    # Test market data search
    print("\n2. Testing /iserver/secdef/search...")
    contracts = auth.search_contracts("SPY", "STK")
    if contracts:
        print(f"✅ Found contracts for SPY")
        if len(contracts) > 0:
            print(f"   First result: {contracts[0].get('description', 'Unknown')}")
    else:
        print("❌ Failed to search contracts")
    
    return True

def main():
    """Main test function"""
    print("\n" + "="*70)
    print(" IB REST API OAuth Authentication Comprehensive Test ")
    print("="*70)
    print(f"Test Time: {datetime.now().isoformat()}")
    
    # Load environment variables
    load_env_vars()
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n⚠️  Some prerequisites are missing!")
        print("Please ensure all required files and environment variables are set.")
        return False
    
    # Initialize auth handler
    auth = IBRestAuth()
    print(f"\nAuth Configuration:")
    print(f"  Consumer Key: {auth.consumer_key}")
    print(f"  Realm: {auth.realm}")
    print(f"  Is Live: {auth.is_live}")
    
    # Test existing tokens
    if test_existing_tokens(auth):
        # If existing tokens work, test API endpoints
        test_api_endpoints(auth)
        print("\n✅ Authentication is working with existing tokens!")
        return True
    
    # If existing tokens don't work, try fresh authentication
    print("\nExisting tokens don't work, attempting fresh authentication...")
    if test_fresh_authentication(auth):
        # Test API endpoints with fresh tokens
        test_api_endpoints(auth)
        print("\n✅ Fresh authentication successful!")
        return True
    else:
        print("\n❌ Authentication failed")
        print("\nPossible issues:")
        print("1. Access token may have expired (tokens expire after 7 days)")
        print("2. Consumer key may not have proper permissions")
        print("3. Network/firewall issues")
        print("4. IB API server issues")
        print("\nNext steps:")
        print("1. Check if it's been more than 7 days since token creation")
        print("2. Verify consumer key permissions with IB")
        print("3. Consider using TESTCONS for testing")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)