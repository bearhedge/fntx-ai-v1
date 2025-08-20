#!/usr/bin/env python3
"""
Test various IBKR REST API endpoints to understand capabilities
"""

import os
import sys
import json
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.IB_headless.ib_rest_auth_consolidated import IBRestAuth

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_endpoints():
    """Test various IBKR REST API endpoints"""
    
    # Initialize auth
    auth = IBRestAuth(
        consumer_key='BEARHEDGE',
        realm='limited_poa'
    )
    
    # Set tokens from environment
    auth.access_token = os.getenv('IB_ACCESS_TOKEN', '8444def5466e38fb8b86')
    auth.access_token_secret = os.getenv('IB_ACCESS_TOKEN_SECRET')
    
    print("\n" + "="*60)
    print("IBKR REST API Endpoint Exploration")
    print("="*60)
    
    endpoints_to_test = [
        # Portfolio endpoints
        ("GET", "/portfolio/accounts", "List all accounts"),
        ("GET", "/portfolio/U19860056/meta", "Account metadata"),
        ("GET", "/portfolio/U19860056/summary", "Account summary"),
        ("GET", "/portfolio/U19860056/ledger", "Account ledger"),
        ("GET", "/portfolio/U19860056/positions/0", "Current positions"),
        ("GET", "/portfolio/U19860056/allocation", "Account allocation"),
        
        # Market Data endpoints
        ("GET", "/md/snapshot?conids=756733&fields=31,84,85,86,87,88", "Market snapshot for SPY"),
        ("GET", "/trsrv/secdef/search?symbol=SPY", "Search for SPY contract"),
        
        # Trading endpoints
        ("GET", "/iserver/accounts", "IServer accounts"),
        ("GET", "/iserver/marketdata/history?conid=756733&period=1d&bar=1min", "Historical data"),
        
        # Scanner endpoints
        ("GET", "/iserver/scanner/params", "Scanner parameters"),
        
        # Orders endpoints
        ("GET", "/iserver/account/orders", "Open orders"),
        ("GET", "/iserver/account/trades", "Today's trades"),
    ]
    
    # Get LST if needed
    if not auth.live_session_token:
        print("\nGetting Live Session Token...")
        if auth.get_live_session_token():
            print("✓ Got LST")
        else:
            print("✗ Failed to get LST")
            return
    
    results = {}
    
    for method, endpoint, description in endpoints_to_test:
        print(f"\n{'-'*50}")
        print(f"Testing: {description}")
        print(f"Endpoint: {method} {endpoint}")
        print("-"*50)
        
        try:
            response = auth.make_authenticated_request(method, endpoint)
            if response:
                print(f"Status: {response.status_code}")
                if response.status_code == 200:
                    print("✓ SUCCESS")
                    try:
                        data = response.json()
                        print(f"Response: {json.dumps(data, indent=2)[:500]}...")
                        results[endpoint] = {
                            "status": "success",
                            "description": description,
                            "sample_data": data
                        }
                    except:
                        print(f"Response: {response.text[:500]}...")
                        results[endpoint] = {
                            "status": "success",
                            "description": description,
                            "sample_data": response.text
                        }
                else:
                    print(f"✗ Failed: {response.status_code}")
                    print(f"Response: {response.text[:200]}...")
                    results[endpoint] = {
                        "status": f"failed_{response.status_code}",
                        "description": description,
                        "error": response.text
                    }
            else:
                print("✗ No response")
                results[endpoint] = {
                    "status": "no_response",
                    "description": description
                }
        except Exception as e:
            print(f"✗ Error: {e}")
            results[endpoint] = {
                "status": "error",
                "description": description,
                "error": str(e)
            }
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY OF ENDPOINT CAPABILITIES")
    print("="*60)
    
    working_endpoints = []
    failed_endpoints = []
    
    for endpoint, result in results.items():
        if result["status"] == "success":
            working_endpoints.append(f"✓ {result['description']}: {endpoint}")
        else:
            failed_endpoints.append(f"✗ {result['description']}: {endpoint} ({result['status']})")
    
    print("\n✅ WORKING ENDPOINTS:")
    for ep in working_endpoints:
        print(f"  {ep}")
    
    print("\n❌ FAILED ENDPOINTS:")
    for ep in failed_endpoints:
        print(f"  {ep}")
    
    # Save results
    with open("endpoint_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n📁 Full results saved to endpoint_test_results.json")
    
    return results

def compare_with_old_setup():
    """Compare REST API with the old ib_insync setup"""
    
    print("\n" + "="*60)
    print("COMPARISON: REST API vs ib_insync (Old Setup)")
    print("="*60)
    
    comparison = """
    OLD SETUP (ib_insync + IB Gateway):
    ------------------------------------
    ✗ Requires IB Gateway or TWS running locally
    ✗ Needs VNC/GUI for Gateway management
    ✗ Connection can drop, needs reconnection handling
    ✗ Limited to one connection per Gateway instance
    ✓ Real-time streaming data
    ✓ Full trading capabilities
    ✓ Synchronous/async operations
    
    NEW SETUP (REST API):
    ------------------------------------
    ✓ No Gateway/TWS needed - pure HTTP/REST
    ✓ Stateless - no connection management
    ✓ Can run from anywhere (cloud, serverless)
    ✓ Multiple concurrent requests possible
    ✓ OAuth authentication - more secure
    ✗ No real-time streaming (polling required)
    ✗ Some endpoints may have limitations
    
    KEY DIFFERENCES FOR TRADING:
    ------------------------------------
    1. Order Placement:
       - Old: ib.placeOrder(contract, order)
       - New: POST /iserver/account/{accountId}/orders
    
    2. Position Monitoring:
       - Old: ib.positions() with real-time updates
       - New: GET /portfolio/{accountId}/positions (polling)
    
    3. Market Data:
       - Old: ib.reqMktData() for streaming
       - New: GET /md/snapshot (polling) or websocket
    
    4. Authentication:
       - Old: Gateway handles auth
       - New: OAuth flow with LST
    
    WHAT YOU CAN DO WITH REST API:
    ------------------------------------
    ✓ Place/modify/cancel orders
    ✓ Get account info and positions
    ✓ Retrieve market data (snapshot/historical)
    ✓ Search for contracts
    ✓ Get order status and fills
    ✓ Access portfolio analytics
    ✓ Run scanners
    ✓ Get news and fundamentals
    
    ADVANTAGES FOR YOUR USE CASE:
    ------------------------------------
    1. No more Gateway crashes or connection issues
    2. Can run trades from cloud functions
    3. Better for scheduled/automated trading
    4. Easier deployment and scaling
    5. No VNC/GUI management needed
    """
    
    print(comparison)
    
    return comparison

if __name__ == "__main__":
    # Test endpoints
    results = test_endpoints()
    
    # Show comparison
    compare_with_old_setup()
    
    print("\n" + "="*60)
    print("RECOMMENDATION")
    print("="*60)
    print("""
    For your SPY options trading:
    1. REST API is BETTER for scheduled trades (no Gateway needed)
    2. You can place orders, check positions, get fills - all via REST
    3. No more connection management headaches
    4. Can run from cloud/cron without GUI
    
    Main limitation: No real-time streaming (but you can poll)
    """)