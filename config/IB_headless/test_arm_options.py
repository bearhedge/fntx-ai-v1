#!/usr/bin/env python3
"""
Get ARM call option quote - 143 strike, Aug 22 2025 expiry
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
    
    # Load saved tokens
    if not auth.live_session_token:
        print("No LST found, attempting to authenticate...")
        if not auth.authenticate():
            print("Authentication failed")
            return
    
    print("\n" + "="*60)
    print("ARM CALL OPTION QUOTE")
    print("Strike: $143")
    print("Expiry: August 22, 2025")
    print("="*60)
    
    # Step 1: Search for ARM contract
    print("\n1. Searching for ARM contract...")
    
    # Make direct API call for ARM
    response = auth.make_authenticated_request(
        'GET', 
        '/iserver/secdef/search',
        params={'symbol': 'ARM'}
    )
    
    if response:
        print(f"Response status: {response.status_code}")
        if response.status_code == 200:
            arm_search = response.json()
            print(f"Found contracts: {json.dumps(arm_search, indent=2)[:1000]}...")
            
            # Get the main ARM stock conid
            arm_conid = None
            if isinstance(arm_search, list) and len(arm_search) > 0:
                for contract in arm_search:
                    if 'ARM' in contract.get('symbol', '') and contract.get('secType') == 'STK':
                        arm_conid = contract.get('conid')
                        print(f"\nARM Stock Contract ID: {arm_conid}")
                        break
            
            if not arm_conid:
                print("Could not find ARM stock contract in results")
                # Try first result anyway
                if arm_search and len(arm_search) > 0:
                    arm_conid = arm_search[0].get('conid')
                    print(f"Using first result conid: {arm_conid}")
        else:
            print(f"API error: {response.text}")
            return
    else:
        print("No response from API")
        return
    
    # Step 2: Get option chain for August 2025
    if arm_conid:
        print("\n2. Getting option chain for August 2025...")
        
        # Try to get option strikes
        option_data = auth.get_option_strikes(arm_conid)
        
        if option_data:
            print(f"Option data: {json.dumps(option_data, indent=2)[:1000]}...")
        
        # Step 3: Search for specific option contract
        # Format: ARM Aug2025 143 C
        print("\n3. Searching for specific option contract...")
        
        # Try different search formats
        searches = [
            "ARM 08/22/25 C143",
            "ARM 22AUG25 143 C",
            "ARM Aug2025 143 C",
            "ARM 143 C 08/22/2025"
        ]
        
        for search_term in searches:
            print(f"\nTrying: {search_term}")
            option_search = auth.search_contract(search_term)
            
            if option_search:
                print(f"Results: {json.dumps(option_search, indent=2)[:500]}...")
                
                # Look for the specific contract
                for contract in option_search if isinstance(option_search, list) else [option_search]:
                    if (contract.get('secType') == 'OPT' and 
                        '143' in str(contract.get('strike', '')) and
                        contract.get('right') == 'C'):
                        
                        option_conid = contract.get('conid')
                        print(f"\n✓ Found option contract ID: {option_conid}")
                        print(f"Contract details: {json.dumps(contract, indent=2)}")
                        
                        # Step 4: Get market data for the option
                        print("\n4. Getting market data (15-min delayed)...")
                        market_data = auth.get_market_data(
                            [option_conid],
                            fields="31,84,85,86,87,88"  # Last, Bid, Ask, Volume, Open, Close
                        )
                        
                        if market_data:
                            print("\n" + "="*60)
                            print("ARM $143 CALL - AUG 22 2025")
                            print("="*60)
                            
                            for item in market_data:
                                if item.get('conid') == option_conid:
                                    print(f"Contract ID: {option_conid}")
                                    print(f"Last Price: ${item.get('31', 'N/A')}")
                                    print(f"Bid: ${item.get('84', 'N/A')}")
                                    print(f"Ask: ${item.get('85', 'N/A')}")
                                    print(f"Volume: {item.get('86', 'N/A')}")
                                    print(f"Open: ${item.get('87', 'N/A')}")
                                    print(f"Previous Close: ${item.get('88', 'N/A')}")
                                    print("\nNote: Prices are 15-minute delayed")
                                    return
                        else:
                            print("Failed to get market data")
    
    print("\nCould not find exact option contract. The contract may not exist yet or have different formatting.")

if __name__ == "__main__":
    get_arm_option_quote()