#!/usr/bin/env python3
"""
Execute ARM $145 Call Option Order with Proper Session Initialization
Based on awiseib's implementation
"""

import sys
import time
import json
from datetime import datetime

sys.path.append('/home/info/fntx-ai-v1')
from config.IB_headless.ib_rest_auth_consolidated import IBRestAuth

def initialize_iserver_session(auth):
    """Initialize iserver session for trading"""
    
    print("Initializing iserver session...")
    
    # Step 1: Logout to clear any existing sessions
    print("1. Clearing existing sessions...")
    response = auth.make_authenticated_request('POST', '/logout')
    if response:
        print(f"   Logout status: {response.status_code}")
    
    # Step 2: Initialize SSO with publish and compete flags
    print("2. Initializing SSO/DH session...")
    init_data = {
        "publish": True,
        "compete": True
    }
    
    response = auth.make_authenticated_request(
        'POST',
        '/iserver/auth/ssodh/init',
        data=init_data
    )
    
    if response and response.status_code == 200:
        result = response.json()
        print(f"   SSO Init: {result}")
        
        # Check if authenticated
        if result.get('authenticated'):
            print("   ✓ Session authenticated!")
            return True
        else:
            print("   Session not yet authenticated")
    
    # Step 3: Tickle to get session token
    print("3. Getting session token...")
    response = auth.make_authenticated_request('POST', '/tickle')
    
    if response and response.status_code == 200:
        result = response.json()
        session_token = result.get('session')
        iserver_status = result.get('iserver', {})
        
        print(f"   Session token: {session_token}")
        print(f"   IServer authenticated: {iserver_status.get('authStatus', {}).get('authenticated', False)}")
        
        # Store session token if needed
        if session_token:
            auth.session_token = session_token
            
        return iserver_status.get('authStatus', {}).get('authenticated', False)
    
    return False

def execute_arm_145_call_order(auth):
    """Execute the ARM $145 call order"""
    
    print("\n" + "="*60)
    print("EXECUTING ARM $145 CALL ORDER")
    print("="*60)
    
    option_conid = 796812614  # ARM $145 Call Aug 22 2025
    account_id = 'U19860056'
    
    # Get current quote first
    print("\n1. Getting current market quote...")
    
    # Initialize market data
    response = auth.make_authenticated_request(
        'GET',
        '/iserver/marketdata/snapshot',
        params={
            'conids': str(option_conid),
            'fields': '31,84,85,86,87,88'
        }
    )
    
    time.sleep(1)
    
    # Get actual data
    response = auth.make_authenticated_request(
        'GET',
        '/iserver/marketdata/snapshot',
        params={
            'conids': str(option_conid),
            'fields': '31,84,85,86,87,88'
        }
    )
    
    if response and response.status_code == 200:
        data = response.json()
        if data and len(data) > 0:
            quote = data[0]
            print(f"   Last: ${quote.get('31', 'N/A')}")
            print(f"   Bid: ${quote.get('84', 'N/A')}")
            print(f"   Ask: ${quote.get('85', 'N/A')}")
    
    # Place the order using the correct structure from jcazelib's implementation
    print("\n2. Placing BUY order for 1 contract...")
    
    order_payload = {
        "orders": [
            {
                "side": "BUY",
                "quantity": 1,
                "conid": option_conid,
                "orderType": "LMT",
                "listingExchange": "SMART",
                "price": 1.15,
                "tif": "DAY",
                "outsideRTH": False
            }
        ]
    }
    
    print(f"   Order details:")
    print(f"   - Contract ID: {option_conid}")
    print(f"   - Action: BUY")
    print(f"   - Quantity: 1 contract")
    print(f"   - Order Type: LIMIT @ $1.15")
    print(f"   - Exchange: SMART")
    print(f"   - Time in Force: DAY")
    
    # Submit order
    response = auth.make_authenticated_request(
        'POST',
        f'/iserver/account/{account_id}/orders',
        data=order_payload
    )
    
    if response:
        print(f"\n3. Order Response:")
        print(f"   Status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            result = response.json()
            print("   ✓ Order submitted successfully!")
            
            # Handle response
            if isinstance(result, list) and len(result) > 0:
                order_data = result[0]
                
                # Check for reply ID (warnings/confirmations)
                if 'id' in order_data:
                    reply_id = order_data['id']
                    print(f"   Reply ID: {reply_id}")
                    
                    # Check for messages/warnings
                    if 'message' in order_data:
                        messages = order_data['message']
                        if isinstance(messages, list):
                            for msg in messages:
                                print(f"   Warning: {msg}")
                        else:
                            print(f"   Warning: {messages}")
                    
                    # Confirm the order
                    print("\n4. Confirming order...")
                    confirm_response = auth.make_authenticated_request(
                        'POST',
                        f'/iserver/reply/{reply_id}',
                        data={'confirmed': True}
                    )
                    
                    if confirm_response and confirm_response.status_code == 200:
                        confirm_result = confirm_response.json()
                        print("   ✓ Order confirmed!")
                        
                        if isinstance(confirm_result, list) and len(confirm_result) > 0:
                            if 'order_id' in confirm_result[0]:
                                print(f"   Order ID: {confirm_result[0]['order_id']}")
                            if 'order_status' in confirm_result[0]:
                                print(f"   Status: {confirm_result[0]['order_status']}")
                
                # Direct order acceptance
                elif 'order_id' in order_data:
                    print(f"   Order ID: {order_data['order_id']}")
                    print(f"   Status: {order_data.get('order_status', 'SUBMITTED')}")
                
                print("\nFull response:")
                print(json.dumps(result, indent=2))
                
        elif response.status_code == 400:
            error = response.json()
            print(f"   ❌ Order rejected:")
            print(json.dumps(error, indent=2))
            
        elif response.status_code == 401:
            print("   ❌ Authentication failed - session not properly initialized")
            
        else:
            print(f"   Unexpected response: {response.text}")
    else:
        print("   Failed to submit order - no response")
    
    # Check order status
    print("\n5. Checking open orders...")
    response = auth.make_authenticated_request('GET', '/iserver/account/orders')
    
    if response and response.status_code == 200:
        orders = response.json()
        if 'orders' in orders:
            print(f"   Open orders: {len(orders['orders'])}")
            for order in orders['orders'][:3]:  # Show first 3
                print(f"   - {order.get('ticker', 'N/A')}: {order.get('side')} {order.get('totalSize')} @ {order.get('price')}")

def main():
    """Main execution"""
    
    print("ARM $145 CALL ORDER EXECUTION")
    print("Contract: 1x ARM Aug 22 2025 $145 Call")
    print("-"*60)
    
    # Initialize OAuth
    auth = IBRestAuth(consumer_key='BEARHEDGE', realm='limited_poa')
    
    # Initialize iserver session
    if initialize_iserver_session(auth):
        print("\n✓ Session initialized successfully!")
        
        # Execute the order
        execute_arm_145_call_order(auth)
    else:
        print("\n❌ Failed to initialize iserver session")
        print("Note: Trading requires either:")
        print("  1. IB Gateway/Client Portal Gateway running")
        print("  2. Proper OAuth credentials with trading permissions")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()