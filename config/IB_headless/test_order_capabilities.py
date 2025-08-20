#!/usr/bin/env python3
"""
Test what order capabilities are available with OAuth
"""

import sys
import json

sys.path.append('/home/info/fntx-ai-v1')
from config.IB_headless.ib_rest_auth_consolidated import IBRestAuth

def test_order_capabilities():
    """Test various order-related endpoints"""
    
    auth = IBRestAuth(consumer_key='BEARHEDGE', realm='limited_poa')
    
    print("TESTING ORDER CAPABILITIES WITH OAUTH")
    print("="*60)
    
    # Test 1: Account capabilities
    print("\n1. Account Trading Permissions:")
    response = auth.make_authenticated_request('GET', '/iserver/account/U19860056/meta')
    if response:
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
    
    # Test 2: Trading permissions
    print("\n2. Trading Features:")
    response = auth.make_authenticated_request('GET', '/iserver/account/features')
    if response:
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
    
    # Test 3: Market rules
    print("\n3. Market Rules for Options:")
    response = auth.make_authenticated_request(
        'GET', 
        '/iserver/marketdata/conid/rules',
        params={'conid': '796812614', 'exchange': 'NASDAQ'}
    )
    if response:
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
    
    # Test 4: Check if we can get order defaults
    print("\n4. Order Defaults:")
    response = auth.make_authenticated_request(
        'GET',
        '/iserver/account/order/defaults'
    )
    if response:
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
    
    # Test 5: Check trading schedule
    print("\n5. Trading Schedule:")
    response = auth.make_authenticated_request(
        'GET',
        '/iserver/marketdata/schedule',
        params={'exchange': 'NASDAQ'}
    )
    if response:
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
    
    # Test 6: Try order preview (doesn't place, just validates)
    print("\n6. Order Preview/Validation:")
    preview_order = {
        "conid": 796812614,
        "orderType": "LMT",
        "price": 1.15,
        "side": "BUY",
        "quantity": 1,
        "tif": "DAY"
    }
    
    response = auth.make_authenticated_request(
        'POST',
        '/iserver/account/U19860056/order/whatif',
        data=preview_order
    )
    if response:
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
    
    # Test 7: Check if SSO/session is the issue
    print("\n7. Session/SSO Status:")
    response = auth.make_authenticated_request('GET', '/sso/validate')
    if response:
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
    
    # Test 8: Try tickle to keep session alive
    print("\n8. Tickle Session:")
    response = auth.make_authenticated_request('POST', '/tickle')
    if response:
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")

if __name__ == "__main__":
    test_order_capabilities()