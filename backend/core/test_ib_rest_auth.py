#!/usr/bin/env python3
"""
Test IB REST API Authentication
Verifies OAuth flow and basic API functionality
"""

import os
import sys
import logging
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
project_root = Path(__file__).parent.parent.parent
env_path = project_root / 'config' / '.env'
load_dotenv(env_path)

sys.path.append('/home/info/fntx-ai-v1/backend')
from core.trading.ib_rest_auth import IBRestAuth
from core.trading.ib_rest_client import IBRestClient

# Set up logging with detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_environment():
    """Test environment setup and configuration"""
    print("\n" + "="*60)
    print("ENVIRONMENT VERIFICATION")
    print("="*60)
    
    # Check required environment variables
    required_vars = [
        'IB_CONSUMER_KEY',
        'IB_SIGNATURE_KEY_PATH',
        'IB_ENCRYPTION_KEY_PATH',
        'IB_DH_PARAM_PATH'
    ]
    
    all_present = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if 'KEY' in var and 'PATH' not in var:
                display_value = value[:6] + '...' + value[-4:] if len(value) > 10 else '***'
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
        else:
            print(f"❌ {var}: NOT SET")
            all_present = False
    
    # Check key files exist
    print("\n" + "-"*60)
    print("KEY FILE VERIFICATION")
    print("-"*60)
    
    key_files = {
        'Signature Key': os.getenv('IB_SIGNATURE_KEY_PATH'),
        'Encryption Key': os.getenv('IB_ENCRYPTION_KEY_PATH'),
        'DH Parameters': os.getenv('IB_DH_PARAM_PATH')
    }
    
    for name, path in key_files.items():
        if path and os.path.exists(path):
            stat = os.stat(path)
            print(f"✅ {name}: {path}")
            print(f"   Size: {stat.st_size} bytes")
            print(f"   Permissions: {oct(stat.st_mode)[-3:]}")
        else:
            print(f"❌ {name}: NOT FOUND at {path}")
            all_present = False
    
    return all_present

def test_oauth_flow():
    """Test OAuth authentication flow step by step"""
    print("\n" + "="*60)
    print("OAUTH AUTHENTICATION FLOW")
    print("="*60)
    
    try:
        # Initialize auth handler
        auth = IBRestAuth()
        print(f"✅ Initialized auth handler")
        print(f"   Consumer Key: {auth.consumer_key[:6]}...{auth.consumer_key[-4:]}")
        print(f"   Realm: {auth.realm}")
        print(f"   Base URL: {auth.base_url}")
        
        # Step 1: Request Token
        print("\n" + "-"*60)
        print("Step 1: Getting Request Token")
        print("-"*60)
        
        if auth.get_request_token():
            print(f"✅ Got request token: {auth.request_token}")
        else:
            print("❌ Failed to get request token")
            return False
        
        # Step 2: Access Token (skip authorization for headless)
        print("\n" + "-"*60)
        print("Step 2: Getting Access Token")
        print("-"*60)
        
        if auth.get_access_token():
            print(f"✅ Got access token: {auth.access_token}")
            print(f"✅ Got access token secret (encrypted)")
        else:
            print("❌ Failed to get access token")
            return False
        
        # Step 3: Live Session Token
        print("\n" + "-"*60)
        print("Step 3: Getting Live Session Token")
        print("-"*60)
        
        if auth.get_live_session_token():
            print(f"✅ Got live session token")
            print(f"   Token length: {len(auth.live_session_token)} bytes")
        else:
            print("❌ Failed to get live session token")
            return False
        
        # Step 4: Initialize Brokerage Session
        print("\n" + "-"*60)
        print("Step 4: Initializing Brokerage Session")
        print("-"*60)
        
        if auth.init_brokerage_session():
            print(f"✅ Brokerage session initialized")
        else:
            print("❌ Failed to initialize brokerage session")
            return False
        
        # Test API Access
        print("\n" + "-"*60)
        print("Step 5: Testing API Access")
        print("-"*60)
        
        accounts = auth.get_accounts()
        if accounts:
            print(f"✅ Successfully retrieved {len(accounts)} accounts:")
            for account in accounts:
                print(f"   Account ID: {account.get('accountId')}")
                print(f"   Type: {account.get('type')}")
                print(f"   Currency: {account.get('currency')}")
        else:
            print("❌ Failed to retrieve accounts")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"OAuth flow failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_trading_client():
    """Test high-level trading client"""
    print("\n" + "="*60)
    print("TRADING CLIENT TEST")
    print("="*60)
    
    try:
        # Initialize client
        client = IBRestClient()
        print("✅ Initialized trading client")
        
        # Connect (authenticate)
        print("\n" + "-"*60)
        print("Connecting to IB REST API")
        print("-"*60)
        
        if client.connect():
            print(f"✅ Connected successfully")
            print(f"   Primary Account: {client.account_id}")
        else:
            print("❌ Failed to connect")
            return False
        
        # Test contract search
        print("\n" + "-"*60)
        print("Testing Contract Search")
        print("-"*60)
        
        # Search for SPY stock first
        results = client.auth.search_contracts('SPY', 'STK')
        if results:
            print(f"✅ Found {len(results)} results for SPY stock")
            spy_conid = None
            for result in results[:3]:  # Show first 3
                print(f"   Symbol: {result.get('symbol')}, "
                      f"ConId: {result.get('conid')}, "
                      f"Exchange: {result.get('exchange')}")
                if result.get('symbol') == 'SPY':
                    spy_conid = result.get('conid')
        else:
            print("❌ No results for SPY")
        
        # Test option contract search
        print("\n" + "-"*60)
        print("Testing Option Contract Search")
        print("-"*60)
        
        from datetime import datetime
        expiry = datetime.now().strftime('%Y%m%d')
        
        contract = client.get_option_contract('SPY', 630, 'C', expiry)
        if contract:
            print(f"✅ Found option contract:")
            print(f"   Symbol: {contract.symbol}")
            print(f"   Strike: {contract.strike}")
            print(f"   Right: {contract.right}")
            print(f"   ConId: {contract.conid}")
            
            # Test market data
            print("\n" + "-"*60)
            print("Testing Market Data")
            print("-"*60)
            
            market_data = client.get_market_data(contract.conid)
            if market_data:
                print(f"✅ Got market data:")
                print(f"   Bid: ${market_data['bid']:.2f}")
                print(f"   Ask: ${market_data['ask']:.2f}")
                print(f"   Last: ${market_data['last']:.2f}")
            else:
                print("⚠️  No market data available (markets may be closed)")
        else:
            print("❌ Could not find option contract")
        
        # Test positions
        print("\n" + "-"*60)
        print("Testing Position Retrieval")
        print("-"*60)
        
        positions = client.get_positions()
        if positions is not None:
            print(f"✅ Retrieved positions: {len(positions)} total")
            spy_positions = [p for p in positions if p.get('ticker', '').startswith('SPY')]
            print(f"   SPY positions: {len(spy_positions)}")
            for pos in spy_positions[:5]:  # Show first 5
                print(f"   {pos.get('ticker')} - Qty: {pos.get('position')}")
        else:
            print("⚠️  Could not retrieve positions")
        
        # Test orders
        print("\n" + "-"*60)
        print("Testing Order Retrieval")
        print("-"*60)
        
        orders = client.get_orders()
        if orders is not None:
            print(f"✅ Retrieved orders: {len(orders)} total")
            for order in orders[:5]:  # Show first 5
                print(f"   Order {order.get('orderId')}: "
                      f"{order.get('side')} {order.get('quantity')} "
                      f"@ {order.get('orderType')}")
        else:
            print("⚠️  Could not retrieve orders")
        
        return True
        
    except Exception as e:
        logger.error(f"Trading client test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_trade_simulation():
    """Test trade simulation (without actually placing orders)"""
    print("\n" + "="*60)
    print("TRADE SIMULATION TEST")
    print("="*60)
    
    try:
        client = IBRestClient()
        
        if not client.connect():
            print("❌ Failed to connect")
            return False
        
        # Simulate selling a PUT
        print("\n" + "-"*60)
        print("Simulating SPY 629 Put Sale")
        print("-"*60)
        
        from datetime import datetime
        expiry = datetime.now().strftime('%Y%m%d')
        
        # Get contract
        contract = client.get_option_contract('SPY', 629, 'P', expiry)
        if contract:
            print(f"✅ Found contract: SPY {contract.strike}{contract.right}")
            
            # Get market data
            market_data = client.get_market_data(contract.conid)
            if market_data and market_data['bid'] > 0:
                bid = market_data['bid']
                stop_multiple = 5.0
                stop_price = bid * stop_multiple
                
                print(f"\n📊 Trade Simulation:")
                print(f"   Contract: SPY {contract.strike} Put")
                print(f"   Bid Price: ${bid:.2f}")
                print(f"   Quantity: 3 contracts")
                print(f"   Credit: ${bid * 100 * 3:.2f}")
                print(f"   Stop Loss: ${stop_price:.2f} ({stop_multiple}x)")
                print(f"   Max Risk: ${(stop_price - bid) * 100 * 3:.2f}")
                print(f"\n✅ Simulation successful - ready for live trading!")
            else:
                print("⚠️  No market data (markets may be closed)")
        else:
            print("❌ Could not find contract")
        
        return True
        
    except Exception as e:
        logger.error(f"Trade simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("IB REST API AUTHENTICATION TEST SUITE")
    print("="*60)
    print("Testing OAuth authentication and API functionality")
    
    # Test 1: Environment
    print("\nTest 1: Environment Setup")
    if not test_environment():
        print("\n❌ FAILED: Environment not properly configured")
        print("   Please check your .env file and key paths")
        return
    
    # Test 2: OAuth Flow
    print("\nTest 2: OAuth Authentication Flow")
    if not test_oauth_flow():
        print("\n❌ FAILED: OAuth authentication failed")
        print("   Check your consumer key and API credentials")
        return
    
    # Test 3: Trading Client
    print("\nTest 3: Trading Client")
    if not test_trading_client():
        print("\n❌ FAILED: Trading client test failed")
        return
    
    # Test 4: Trade Simulation
    print("\nTest 4: Trade Simulation")
    if not test_simple_trade_simulation():
        print("\n❌ FAILED: Trade simulation failed")
        return
    
    # All tests passed
    print("\n" + "="*60)
    print("ALL TESTS PASSED! ✅")
    print("="*60)
    print("\nThe IB REST API authentication is working correctly.")
    print("You can now run execute_spy_trades_rest.py to place real trades.")
    print("\nExample commands:")
    print("  python execute_spy_trades_rest.py --side both")
    print("  python execute_spy_trades_rest.py --side put --put-strike 628")
    print("  python execute_spy_trades_rest.py --side call --call-strike 632 --quantity 5")

if __name__ == "__main__":
    main()