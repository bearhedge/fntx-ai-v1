#!/usr/bin/env python3
"""
Execute ARM $145 Call Option Order - FINAL VERSION
Using correct OAuth endpoint and order format from debug.txt
"""

import sys
import time
import json

sys.path.append('/home/info/fntx-ai-v1')
from config.IB_headless.ib_rest_auth_consolidated import IBRestAuth

def execute_arm_145_call():
    """Execute ARM $145 Call Option Order"""
    
    # Initialize OAuth
    auth = IBRestAuth(consumer_key='BEARHEDGE', realm='limited_poa')
    
    print("="*60)
    print("EXECUTING ARM $145 CALL ORDER - OAUTH DIRECT")
    print("="*60)
    
    # ARM $145 Call Aug 22 2025 - Contract ID we already found
    option_conid = 796812614
    account_id = 'U19860056'
    
    # Step 1: Get current quote
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
    
    # Get actual data (second request pattern)
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
    
    # Step 2: Place the order using correct format from debug.txt
    print("\n2. Placing BUY order for 1 contract...")
    
    # Using exact format from debug.txt line 101-115
    order_payload = {
        "orders": [
            {
                "side": "BUY",
                "quantity": 1,
                "conid": option_conid,
                "orderType": "LMT",
                "listingExchange": "SMART",
                "price": 1.15,  # Float, not string (as per line 22 in debug.txt)
                "tif": "DAY",
                "outsideRTH": False
            }
        ]
    }
    
    print(f"   Order details:")
    print(f"   - Contract ID: {option_conid}")
    print(f"   - Symbol: ARM $145 Call Aug 22 2025")
    print(f"   - Action: BUY")
    print(f"   - Quantity: 1 contract")
    print(f"   - Order Type: LIMIT @ $1.15")
    print(f"   - Exchange: SMART")
    print(f"   - Time in Force: DAY")
    
    # Submit order to OAuth endpoint (line 79 in debug.txt)
    print("\n3. Submitting order to OAuth endpoint...")
    response = auth.make_authenticated_request(
        'POST',
        f'/iserver/account/{account_id}/orders',
        data=order_payload
    )
    
    if response:
        print(f"   Status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            result = response.json()
            print("   ✅ Order submission received!")
            
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
                                print(f"   Message: {msg}")
                        else:
                            print(f"   Message: {messages}")
                    
                    # Confirm the order if needed
                    print("\n4. Confirming order...")
                    confirm_response = auth.make_authenticated_request(
                        'POST',
                        f'/iserver/reply/{reply_id}',
                        data={'confirmed': True}
                    )
                    
                    if confirm_response and confirm_response.status_code == 200:
                        confirm_result = confirm_response.json()
                        print("   ✅ Order confirmed!")
                        
                        if isinstance(confirm_result, list) and len(confirm_result) > 0:
                            if 'order_id' in confirm_result[0]:
                                print(f"   Order ID: {confirm_result[0]['order_id']}")
                            if 'order_status' in confirm_result[0]:
                                print(f"   Status: {confirm_result[0]['order_status']}")
                        
                        print("\nFull confirmation response:")
                        print(json.dumps(confirm_result, indent=2))
                    else:
                        print(f"   Confirmation status: {confirm_response.status_code if confirm_response else 'No response'}")
                        if confirm_response:
                            print(f"   Response: {confirm_response.text}")
                
                # Direct order acceptance
                elif 'order_id' in order_data:
                    print(f"   Order ID: {order_data['order_id']}")
                    print(f"   Status: {order_data.get('order_status', 'SUBMITTED')}")
                    print("   ✅ Order accepted directly!")
                
                print("\nFull order response:")
                print(json.dumps(result, indent=2))
                
        elif response.status_code == 400:
            error = response.json() if response.text else {"error": "Unknown"}
            print(f"   ❌ Order rejected:")
            print(json.dumps(error, indent=2))
            
            # Common error messages from debug.txt line 14-21
            if 'error' in error:
                error_msg = str(error['error']).lower()
                if 'missing order parameters' in error_msg:
                    print("\n   Issue: Missing required order parameters")
                    print("   Check: Ensure all required fields are present")
                elif 'market hours' in error_msg:
                    print("\n   Issue: Market is closed")
                    print("   Solution: Place order during market hours")
                elif 'permission' in error_msg:
                    print("\n   Issue: Account lacks options trading permission")
                elif 'authenticated' in error_msg:
                    print("\n   Issue: Authentication required")
                    print("   Note: OAuth alone may need gateway for trading")
                    
        elif response.status_code == 401:
            print("   ❌ Authentication failed")
            print("   Note: Trading may require CP Gateway even with OAuth")
            print(f"   Response: {response.text}")
            
        else:
            print(f"   Unexpected response:")
            print(f"   {response.text}")
    else:
        print("   No response from server")
    
    # Step 5: Check order status
    print("\n5. Checking order status...")
    response = auth.make_authenticated_request('GET', '/iserver/account/orders')
    
    if response and response.status_code == 200:
        orders = response.json()
        if 'orders' in orders and orders['orders']:
            print(f"   Open orders found: {len(orders['orders'])}")
            for order in orders['orders'][:3]:  # Show first 3
                print(f"   - {order.get('ticker', 'N/A')}: {order.get('side')} {order.get('totalSize')} @ ${order.get('price')}")
        else:
            print("   No open orders found")
    elif response:
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")

if __name__ == "__main__":
    print("ARM $145 CALL ORDER EXECUTION - FINAL ATTEMPT")
    print("Using OAuth direct endpoint from debug.txt")
    print("-"*60)
    
    try:
        execute_arm_145_call()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("Order execution complete")
    print("\nNOTE: If authentication fails, it confirms IBKR's statement")
    print("that OAuth is an 'alternative' to CP Gateway means OAuth")
    print("handles authentication but still needs gateway for trading.")