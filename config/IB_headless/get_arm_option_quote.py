#!/usr/bin/env python3
"""
Get ARM option quote - 143 strike, Aug 22 2025 expiry
Using the IBKR REST API with OAuth authentication
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.IB_headless.ib_rest_auth_consolidated import IBRestAuth

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_arm_option_quote():
    """Get ARM 143 call option expiring Aug 22 2025"""
    
    # Initialize auth
    auth = IBRestAuth(
        consumer_key='BEARHEDGE',
        realm='limited_poa'
    )
    
    print("\n" + "="*60)
    print("ARM CALL OPTION - AUGUST 22, 2025 - $143 STRIKE")
    print("="*60)
    
    # ARM contract ID (from IBKR's database)
    # ARM Holdings (NASDAQ) typically has conid around 617085153
    # But let's search for it properly
    
    # Method 1: Try direct contract search with known ARM conid
    arm_conid = 617085153  # ARM Holdings ADR on NASDAQ
    
    print("\n1. Searching for ARM option chain...")
    
    # Try to get option chain info using secdef endpoint
    # Format: AUG25 for August 2025
    response = auth.make_authenticated_request(
        'GET',
        '/iserver/secdef/info',
        params={
            'conid': str(arm_conid),
            'sectype': 'OPT',
            'month': 'AUG25',
            'exchange': 'SMART',
            'strike': '143',
            'right': 'C'
        }
    )
    
    if response and response.status_code == 200:
        data = response.json()
        print(f"Option info: {json.dumps(data, indent=2)[:1000]}")
        
        # Extract the option conid
        if isinstance(data, list) and len(data) > 0:
            option_conid = data[0].get('conid')
            if option_conid:
                print(f"\n✓ Found ARM 143C Aug25 - Contract ID: {option_conid}")
                
                # Get market data
                print("\n2. Getting market data (15-min delayed)...")
                market_response = auth.make_authenticated_request(
                    'GET',
                    '/iserver/marketdata/snapshot',
                    params={
                        'conids': str(option_conid),
                        'fields': '31,84,85,86,87,88'  # Last, Bid, Ask, Volume, Open, Close
                    }
                )
                
                if market_response and market_response.status_code == 200:
                    market_data = market_response.json()
                    print("\n" + "="*60)
                    print("ARM $143 CALL - AUGUST 22, 2025")
                    print("="*60)
                    
                    if isinstance(market_data, list) and len(market_data) > 0:
                        quote = market_data[0]
                        print(f"Contract ID: {option_conid}")
                        print(f"Last Price: ${quote.get('31', 'N/A')}")
                        print(f"Bid: ${quote.get('84', 'N/A')}")
                        print(f"Ask: ${quote.get('85', 'N/A')}")
                        print(f"Volume: {quote.get('86', 'N/A')}")
                        print(f"Open: ${quote.get('87', 'N/A')}")
                        print(f"Previous Close: ${quote.get('88', 'N/A')}")
                        print("\nNote: Prices are 15-minute delayed without subscription")
                else:
                    print("Could not get market data")
    else:
        print(f"Could not find option info. Status: {response.status_code if response else 'No response'}")
        
        # Try alternative approach - get all strikes first
        print("\n3. Alternative: Getting all available strikes...")
        strikes_response = auth.make_authenticated_request(
            'GET',
            '/iserver/secdef/strikes',
            params={
                'conid': str(arm_conid),
                'sectype': 'OPT',
                'month': 'AUG25',
                'exchange': 'SMART'
            }
        )
        
        if strikes_response and strikes_response.status_code == 200:
            strikes_data = strikes_response.json()
            print(f"Available strikes: {json.dumps(strikes_data, indent=2)[:500]}")
            
            # Check if 143 is available
            if 'call' in strikes_data and 143 in strikes_data['call']:
                print(f"\n✓ 143 strike is available for calls")
                print("You may need to use the IBKR workstation to get the exact contract ID")

if __name__ == "__main__":
    get_arm_option_quote()