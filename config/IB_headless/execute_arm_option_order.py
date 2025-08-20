#!/usr/bin/env python3
"""
Execute ARM $145 Call Option Order - Aug 22 2025
One contract, using OAuth headless implementation
"""

import sys
import time
import json
from datetime import datetime

sys.path.append('/home/info/fntx-ai-v1')
from config.IB_headless.ib_rest_auth_consolidated import IBRestAuth

def execute_arm_145_call():
    """Execute order for ARM $145 Call expiring Aug 22 2025"""
    
    # Initialize OAuth
    auth = IBRestAuth(consumer_key='BEARHEDGE', realm='limited_poa')
    
    print("="*60)
    print("EXECUTING ARM $145 CALL ORDER - AUG 22 2025")
    print("="*60)
    
    # Known contract ID for ARM $145 Call Aug 22 2025
    option_conid = 796812614  # We already found this
    account_id = 'U19860056'  # BEAR HEDGE FINTEX LIMITED account
    
    # Step 1: Get current quote first
    print("\n1. Getting current market quote...")
    
    # First request to initialize
    response = auth.make_authenticated_request(
        'GET',
        '/iserver/marketdata/snapshot',
        params={
            'conids': str(option_conid),
            'fields': '31,84,85,86,87,88'  # Last, Bid, Ask, Volume, Open, Close
        }
    )
    
    # Second request for actual data
    time.sleep(1)
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
            last_price = quote.get('31', 'N/A')
            bid_price = quote.get('84', 'N/A')
            ask_price = quote.get('85', 'N/A')
            
            print(f"   Last: ${last_price}")
            print(f"   Bid: ${bid_price}")
            print(f"   Ask: ${ask_price}")
    
    # Step 2: Place the order
    print("\n2. Placing BUY order for 1 contract...")
    
    # Build order payload
    order = {
        'conid': option_conid,
        'orderType': 'LMT',  # Limit order
        'price': 1.15,  # Limit price (between last $1.10 and potential ask)
        'side': 'BUY',
        'quantity': 1,
        'tif': 'DAY',  # Day order
        'secType': 'OPT'
    }
    
    print(f"   Order details:")
    print(f"   - Contract ID: {option_conid}")
    print(f"   - Action: BUY")
    print(f"   - Quantity: 1 contract")
    print(f"   - Order Type: LIMIT")
    print(f"   - Limit Price: $1.15")
    print(f"   - Time in Force: DAY")
    
    # Submit order
    response = auth.make_authenticated_request(
        'POST',
        f'/iserver/account/{account_id}/order',
        data=order
    )
    
    if response:
        print(f"\n3. Order Response Status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            result = response.json()
            print("   Order submitted successfully!")
            
            # Check if we need to confirm warnings
            if isinstance(result, list) and len(result) > 0:
                if 'id' in result[0]:
                    reply_id = result[0]['id']
                    print(f"   Reply ID: {reply_id}")
                    
                    # Check for warnings/messages
                    if 'message' in result[0]:
                        print(f"   Warning: {result[0]['message']}")
                        
                        # Confirm the order
                        print("\n4. Confirming order...")
                        confirm_response = auth.make_authenticated_request(
                            'POST',
                            f'/iserver/reply/{reply_id}',
                            data={'confirmed': True}
                        )
                        
                        if confirm_response and confirm_response.status_code == 200:
                            confirm_result = confirm_response.json()
                            print("   Order confirmed!")
                            
                            # Extract order ID if available
                            if isinstance(confirm_result, list) and len(confirm_result) > 0:
                                if 'order_id' in confirm_result[0]:
                                    print(f"   Order ID: {confirm_result[0]['order_id']}")
                                    
                                    # Get order status
                                    print("\n5. Checking order status...")
                                    status_response = auth.make_authenticated_request(
                                        'GET',
                                        '/iserver/account/orders'
                                    )
                                    
                                    if status_response and status_response.status_code == 200:
                                        orders = status_response.json()
                                        print(f"   Open orders: {len(orders.get('orders', []))}")
                            
                            print(json.dumps(confirm_result, indent=2))
                        else:
                            print(f"   Confirmation failed: {confirm_response.status_code if confirm_response else 'No response'}")
                    else:
                        # Direct fill without warnings
                        print("   Order accepted without warnings")
                        if 'order_id' in result[0]:
                            print(f"   Order ID: {result[0]['order_id']}")
                
                print("\nFull response:")
                print(json.dumps(result, indent=2))
            else:
                print("   Unexpected response format")
                print(json.dumps(result, indent=2))
                
        elif response.status_code == 400:
            error = response.json()
            print(f"   Order rejected: {error}")
            
            # Common issues
            if 'error' in error:
                if 'market hours' in str(error).lower():
                    print("\n   ⚠️ Market is closed. Orders can only be placed during market hours.")
                elif 'insufficient' in str(error).lower():
                    print("\n   ⚠️ Insufficient buying power for this order.")
                elif 'permission' in str(error).lower():
                    print("\n   ⚠️ Account doesn't have options trading permission.")
        else:
            print(f"   Unexpected response: {response.text}")
    else:
        print("   Failed to submit order - no response")
    
    # Step 3: Check current positions
    print("\n6. Checking current positions...")
    response = auth.make_authenticated_request(
        'GET',
        f'/portfolio/{account_id}/positions/0'
    )
    
    if response and response.status_code == 200:
        positions = response.json()
        print(f"   Total positions: {len(positions)}")
        
        # Look for ARM options
        for pos in positions:
            if 'ARM' in str(pos.get('contractDesc', '')):
                print(f"   Found ARM position: {pos.get('contractDesc')}")
                print(f"   Quantity: {pos.get('position')}")

if __name__ == "__main__":
    print("Starting ARM $145 Call order execution...")
    print("Contract: 1x ARM Aug 22 2025 $145 Call")
    print("-"*60)
    
    try:
        execute_arm_145_call()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("Order execution attempt complete")