#!/usr/bin/env python3
"""
Get ARM 143 Call option quote for Aug 22 2025
Using IBKR REST API with OAuth - attempting direct market data access
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
    """Get ARM 143 call option expiring Aug 22 2025 using REST API"""
    
    # Initialize auth
    auth = IBRestAuth(
        consumer_key='BEARHEDGE',
        realm='limited_poa'
    )
    
    print("\n" + "="*60)
    print("ARM CALL OPTION - AUGUST 22, 2025 - $143 STRIKE")
    print("="*60)
    
    # First verify we're authenticated
    print("\n1. Checking authentication...")
    accounts_response = auth.make_authenticated_request('GET', '/iserver/accounts')
    
    if accounts_response and accounts_response.status_code == 200:
        accounts = accounts_response.json()
        print(f"✓ Authenticated - Accounts: {accounts}")
        
        # Now try to search for ARM contract
        print("\n2. Searching for ARM contract...")
        
        # Method 1: Try stock conid lookup first
        stock_response = auth.make_authenticated_request(
            'GET',
            '/trsrv/stocks',
            params={'symbols': 'ARM'}
        )
        
        if stock_response and stock_response.status_code == 200:
            stock_data = stock_response.json()
            print(f"Stock data: {json.dumps(stock_data, indent=2)[:500]}")
            
            if 'ARM' in stock_data:
                arm_conid = stock_data['ARM'].get('contracts', [{}])[0].get('conid')
                if arm_conid:
                    print(f"✓ Found ARM conid: {arm_conid}")
                    
                    # Now try to get option strikes
                    print("\n3. Getting option strikes for Aug 2025...")
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
                        print(f"Strikes data: {json.dumps(strikes_data, indent=2)[:500]}")
                        
                        # Check if 143 strike is available
                        if 'call' in strikes_data and 143 in strikes_data.get('call', []):
                            print(f"✓ 143 strike is available for calls")
                            
                            # Try to get market data snapshot
                            print("\n4. Getting market data for ARM 143C Aug25...")
                            
                            # We need the specific option conid
                            # Format: underlying_conid, expiry, strike, right
                            option_search_response = auth.make_authenticated_request(
                                'GET',
                                '/iserver/secdef/search',
                                params={
                                    'symbol': f'ARM  AUG 22 \'25 143 Call',
                                    'name': 'false',
                                    'sectype': 'OPT'
                                }
                            )
                            
                            if option_search_response and option_search_response.status_code == 200:
                                option_data = option_search_response.json()
                                print(f"Option search: {json.dumps(option_data, indent=2)[:500]}")
                                
                                if option_data and len(option_data) > 0:
                                    option_conid = option_data[0].get('conid')
                                    if option_conid:
                                        print(f"✓ Found option conid: {option_conid}")
                                        
                                        # Get market data
                                        print("\n5. Getting market data snapshot...")
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
                                            print("ARM $143 CALL - AUGUST 22, 2025 - QUOTE")
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
                                            print(f"Market data response: {market_response.status_code if market_response else 'No response'}")
                                            if market_response:
                                                print(f"Response: {market_response.text}")
                            else:
                                print(f"Option search response: {option_search_response.status_code if option_search_response else 'No response'}")
                                if option_search_response:
                                    print(f"Response: {option_search_response.text}")
                    else:
                        print(f"Strikes response: {strikes_response.status_code if strikes_response else 'No response'}")
                        if strikes_response:
                            print(f"Response: {strikes_response.text}")
        else:
            print(f"Stock lookup response: {stock_response.status_code if stock_response else 'No response'}")
            if stock_response:
                print(f"Response: {stock_response.text}")
    else:
        print(f"Accounts response: {accounts_response.status_code if accounts_response else 'No response'}")
        if accounts_response:
            print(f"Response: {accounts_response.text}")
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("The IBKR REST API requires Client Portal Gateway to be running")
    print("for market data and contract search endpoints to work properly.")
    print("")
    print("OAuth alone gives us:")
    print("✓ Portfolio/account access")
    print("✗ Market data endpoints (need gateway)")
    print("✗ Contract search (need gateway)")
    print("")
    print("For headless operation with full API access, you need:")
    print("1. OAuth for authentication (what we have)")
    print("2. Client Portal Gateway running (IBeam can automate this)")
    print("3. Or use IB Gateway + ib_insync (the traditional method)")

if __name__ == "__main__":
    get_arm_option_quote()