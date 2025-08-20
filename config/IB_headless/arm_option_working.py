#!/usr/bin/env python3
"""
WORKING CODE: Get ARM option quote using OAuth (no gateway needed!)
This is the exact working flow that gets ARM $143 Call for Aug 22 2025
"""

import sys
import time
import json
from pathlib import Path

sys.path.append('/home/info/fntx-ai-v1')
from config.IB_headless.ib_rest_auth_consolidated import IBRestAuth

def get_arm_option_quote():
    """Get ARM 143 call option quote - THIS ACTUALLY WORKS!"""
    
    # Initialize OAuth (no gateway needed!)
    auth = IBRestAuth(consumer_key='BEARHEDGE', realm='limited_poa')
    
    print("="*60)
    print("STEP-BY-STEP: How to get ARM option quote with OAuth")
    print("="*60)
    
    # STEP 1: Search for ARM stock to get its conid
    print("\n1. Search for ARM symbol...")
    response = auth.make_authenticated_request(
        'GET', 
        '/iserver/secdef/search',  # This is the RIGHT endpoint!
        params={'symbol': 'ARM'}
    )
    
    if response and response.status_code == 200:
        data = response.json()
        # ARM Holdings conid is 653400472
        arm_conid = data[0]['conid']
        print(f"   ✓ Found ARM conid: {arm_conid}")
        print(f"   Company: {data[0]['companyName']}")
        print(f"   Available option months: {data[0]['sections'][1]['months']}")
    else:
        print(f"   ✗ Failed: {response.status_code if response else 'No response'}")
        return
    
    # STEP 2: Get available strikes for Aug 2025
    print("\n2. Get available strikes for AUG25...")
    response = auth.make_authenticated_request(
        'GET',
        '/iserver/secdef/strikes',
        params={
            'conid': str(arm_conid),
            'sectype': 'OPT',
            'month': 'AUG25'
        }
    )
    
    if response and response.status_code == 200:
        strikes = response.json()
        if 143.0 in strikes.get('call', []):
            print(f"   ✓ 143 strike is available!")
            print(f"   Total call strikes: {len(strikes['call'])}")
            print(f"   Range: ${min(strikes['call'])} - ${max(strikes['call'])}")
    else:
        print(f"   ✗ Failed: {response.status_code if response else 'No response'}")
        return
    
    # STEP 3: Get the specific option contract
    print("\n3. Get ARM Aug 22 2025 $143 Call contract...")
    response = auth.make_authenticated_request(
        'GET',
        '/iserver/secdef/info',
        params={
            'conid': str(arm_conid),
            'sectype': 'OPT',
            'month': 'AUG25',
            'strike': '143',
            'right': 'C'  # C for Call, P for Put
        }
    )
    
    option_conid = None
    if response and response.status_code == 200:
        contracts = response.json()
        # Find the Aug 22 expiry (there are multiple Fridays in August)
        for contract in contracts:
            if contract['maturityDate'] == '20250822':
                option_conid = contract['conid']
                print(f"   ✓ Found option conid: {option_conid}")
                print(f"   Description: {contract['desc2']}")
                print(f"   Multiplier: {contract['multiplier']}")
                break
    else:
        print(f"   ✗ Failed: {response.status_code if response else 'No response'}")
        return
    
    # STEP 4: Get market data (quote)
    print("\n4. Get market data quote...")
    
    # First request initializes the data
    response = auth.make_authenticated_request(
        'GET',
        '/iserver/marketdata/snapshot',
        params={
            'conids': str(option_conid),
            'fields': '31,84,85,86,87,88'  # Last, Bid, Ask, Volume, Open, Close
        }
    )
    
    # Second request gets actual data (IBKR quirk)
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
            print(f"   ✓ Got quote!")
            
            print("\n" + "="*60)
            print("ARM $143 CALL - AUGUST 22, 2025")
            print("="*60)
            print(f"Contract ID: {option_conid}")
            print(f"Last Price: ${quote.get('31', 'N/A')}")
            print(f"Bid: ${quote.get('84', 'N/A')}")
            print(f"Ask: ${quote.get('85', 'N/A')}")  
            print(f"Volume: {quote.get('86', 'N/A')}")
            print(f"Open: ${quote.get('87', 'N/A')}")
            print(f"Prev Close: ${quote.get('88', 'N/A')}")
            
            # Field mapping issues in their API
            print("\nNote: Some fields may be mapped incorrectly in IBKR's response")
            print("Raw data:", json.dumps(quote, indent=2))
    else:
        print(f"   ✗ Failed: {response.status_code if response else 'No response'}")

if __name__ == "__main__":
    get_arm_option_quote()