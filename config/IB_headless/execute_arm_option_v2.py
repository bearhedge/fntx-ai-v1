#!/usr/bin/env python3
"""
Execute ARM $145 Call Option Order - Version 2
Using different order endpoints
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
    print("ARM $145 CALL ORDER - ATTEMPTING DIFFERENT ENDPOINTS")
    print("="*60)
    
    option_conid = 796812614  # ARM $145 Call
    account_id = 'U19860056'
    
    # Try method 1: /iserver/account/orders endpoint
    print("\n1. Trying /iserver/account/orders endpoint...")
    
    order_payload = {
        "orders": [{
            "conid": option_conid,
            "orderType": "LMT",
            "price": 1.15,
            "side": "BUY", 
            "quantity": 1,
            "tif": "DAY",
            "acctId": account_id
        }]
    }
    
    response = auth.make_authenticated_request(
        'POST',
        '/iserver/account/orders',
        data=order_payload
    )
    
    if response:
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
    else:
        print("   No response")
    
    # Try method 2: Check if we need to create a session first
    print("\n2. Checking session status...")
    
    response = auth.make_authenticated_request(
        'GET',
        '/iserver/auth/status'
    )
    
    if response:
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Authenticated: {data.get('authenticated', False)}")
            print(f"   Connected: {data.get('connected', False)}")
    
    # Try method 3: Initialize session
    print("\n3. Trying to initialize session...")
    
    response = auth.make_authenticated_request(
        'POST',
        '/iserver/auth/ssodh/init',
        data={}
    )
    
    if response:
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
    
    # Try method 4: Contract validation first
    print("\n4. Validating contract details...")
    
    response = auth.make_authenticated_request(
        'GET',
        f'/iserver/contract/{option_conid}/info'
    )
    
    if response and response.status_code == 200:
        data = response.json()
        print(f"   Contract valid: {data.get('symbol', 'Unknown')}")
        print(f"   Exchange: {data.get('exchange', 'Unknown')}")
        print(f"   Currency: {data.get('currency', 'Unknown')}")
    
    # Try method 5: Place order with different structure
    print("\n5. Trying simplified order structure...")
    
    simple_order = {
        "conid": option_conid,
        "secType": "OPT",
        "orderType": "LMT",
        "limitPrice": 1.15,
        "side": "BUY",
        "quantity": 1,
        "tif": "DAY"
    }
    
    response = auth.make_authenticated_request(
        'POST',
        f'/iserver/account/{account_id}/orders',
        data=simple_order
    )
    
    if response:
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
    
    # Try method 6: Check what orders endpoint expects
    print("\n6. Getting orders (to see structure)...")
    
    response = auth.make_authenticated_request(
        'GET',
        '/iserver/account/orders'
    )
    
    if response:
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Orders structure: {json.dumps(data, indent=2)[:500]}...")

if __name__ == "__main__":
    try:
        execute_arm_145_call()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()