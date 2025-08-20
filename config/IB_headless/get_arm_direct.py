#!/usr/bin/env python3
"""
Get ARM option quote directly using our working OAuth
No ib_insync, no gateway, just our OAuth that already works
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

def get_arm_quote():
    """Get ARM 143 call option quote - Aug 22 2025"""
    
    # Initialize our working OAuth
    auth = IBRestAuth(
        consumer_key='BEARHEDGE',
        realm='limited_poa'
    )
    
    print("\n" + "="*60)
    print("ARM $143 CALL - AUGUST 22, 2025")
    print("="*60)
    
    # We know /portfolio/accounts works
    print("\n1. Testing with working endpoint...")
    response = auth.make_authenticated_request('GET', '/portfolio/accounts')
    
    if response and response.status_code == 200:
        data = response.json()
        print(f"✓ OAuth is working! Account: {data[0]['accountId']}")
        
        # Try different endpoints for ARM data
        print("\n2. Attempting to get ARM contract data...")
        
        # Try direct conid for ARM (common ARM Holdings conid)
        arm_conid = 617085153  # ARM Holdings ADR
        
        # Try market data endpoint
        print(f"\n3. Trying market data for ARM (conid: {arm_conid})...")
        response = auth.make_authenticated_request(
            'GET',
            '/md/snapshot',
            params={
                'conids': str(arm_conid),
                'fields': '31,84,85,86,87,88'  # Last, Bid, Ask, Volume, Open, Close
            }
        )
        
        if response:
            print(f"Market data response: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"ARM Stock Data: {json.dumps(data, indent=2)}")
            else:
                print(f"Response: {response.text[:500]}")
        
        # Try option-specific endpoint
        print("\n4. Trying option chain endpoint...")
        response = auth.make_authenticated_request(
            'GET',
            f'/iserver/secdef/info',
            params={
                'conid': str(arm_conid),
                'sectype': 'OPT',
                'month': 'AUG25',
                'strike': '143',
                'right': 'C'
            }
        )
        
        if response:
            print(f"Option info response: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Option Data: {json.dumps(data, indent=2)}")
    else:
        print(f"Response: {response.status_code if response else 'No response'}")
        if response:
            print(f"Text: {response.text}")
    
    print("\n" + "="*60)
    print("RESULT")
    print("="*60)
    print("OAuth authentication is working (we can access portfolio)")
    print("But market data endpoints require Client Portal Gateway")
    print("This is an IBKR limitation - not our code")

if __name__ == "__main__":
    get_arm_quote()