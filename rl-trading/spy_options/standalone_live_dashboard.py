#!/usr/bin/env python3
"""Standalone live options dashboard using only requests"""
import requests
import json
import time
from datetime import datetime
import sys

class LiveOptionsDashboard:
    def __init__(self):
        self.base_url = "http://localhost:25510"
        self.running = True
        
    def get_spy_price(self):
        """Get SPY price from Theta Terminal"""
        try:
            response = requests.get(f"{self.base_url}/v2/snapshot/stock/quote?root=SPY")
            if response.status_code == 200:
                data = response.json()
                if data['response']:
                    quote = data['response'][0]
                    bid = quote[3]
                    ask = quote[7]
                    return (bid + ask) / 2
        except:
            pass
        return 0
    
    def get_yahoo_price(self):
        """Get real-time SPY price from Yahoo"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/SPY", headers=headers)
            if response.status_code == 200:
                data = response.json()
                return data['chart']['result'][0]['meta']['regularMarketPrice']
        except:
            pass
        return 0
    
    def get_options_chain(self, atm_strike, exp_date):
        """Get options chain around ATM"""
        options = {}
        
        # Get options for strikes around ATM
        for offset in range(-5, 6):
            strike = atm_strike + offset
            
            for right in ['C', 'P']:
                try:
                    url = f"{self.base_url}/v2/snapshot/option/quote?root=SPY&exp={exp_date}&strike={strike}000&right={right}"
                    response = requests.get(url)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data['response']:
                            quote = data['response'][0]
                            bid = quote[3] / 100  # Convert cents to dollars
                            ask = quote[7] / 100
                            
                            key = f"{strike}_{right}"
                            options[key] = {
                                'strike': strike,
                                'type': right,
                                'bid': bid,
                                'ask': ask,
                                'mid': (bid + ask) / 2
                            }
                except:
                    pass
        
        return options
    
    def run(self):
        """Run the dashboard"""
        print("Starting Live 0DTE Options Dashboard...")
        print("Fetching initial data...")
        
        while self.running:
            try:
                # Clear screen
                print("\033[2J\033[H")
                
                # Get prices
                spy_theta = self.get_spy_price()
                spy_yahoo = self.get_yahoo_price()
                
                # Header
                print("=" * 80)
                print("SPY 0DTE OPTIONS LIVE STREAMING")
                print("=" * 80)
                
                # Display prices
                print(f"\nSPY Price:")
                print(f"  Theta Terminal: ${spy_theta:.2f} (15-min delayed)")
                print(f"  Yahoo Finance:  ${spy_yahoo:.2f} (real-time)")
                print(f"  Difference:     ${spy_yahoo - spy_theta:.2f}")
                
                # Get today's date for 0DTE
                today = datetime.now().strftime('%Y%m%d')
                print(f"\nExpiration: {today} (0DTE)")
                
                # Get options chain
                if spy_yahoo > 0:
                    atm_strike = int(spy_yahoo)
                    options = self.get_options_chain(atm_strike, today)
                    
                    print(f"\nOptions Chain ({len(options)} contracts loaded)")
                    print(f"ATM Strike: {atm_strike}")
                    
                    # Display options table
                    print(f"\n{'Strike':>8} {'Call Bid':>10} {'Call Ask':>10} {'Call Mid':>10} |"
                          f"{'Put Bid':>10} {'Put Ask':>10} {'Put Mid':>10}")
                    print("-" * 80)
                    
                    for offset in range(-5, 6):
                        strike = atm_strike + offset
                        
                        # Get call and put data
                        call_key = f"{strike}_C"
                        put_key = f"{strike}_P"
                        
                        call = options.get(call_key, {})
                        put = options.get(put_key, {})
                        
                        # Highlight ATM
                        if strike == atm_strike:
                            prefix = " -> "
                        elif abs(strike - atm_strike) <= 2:
                            prefix = "  * "
                        else:
                            prefix = "    "
                        
                        # Display row
                        if call or put:
                            print(f"{prefix}{strike:>5} "
                                  f"${call.get('bid', 0):>9.2f} ${call.get('ask', 0):>9.2f} ${call.get('mid', 0):>9.2f} |"
                                  f"${put.get('bid', 0):>9.2f} ${put.get('ask', 0):>9.2f} ${put.get('mid', 0):>9.2f}")
                    
                    # Show liquid strikes
                    print(f"\nLiquid strikes (within $2 of ATM):")
                    liquid_calls = []
                    liquid_puts = []
                    
                    for key, opt in options.items():
                        if abs(opt['strike'] - atm_strike) <= 2 and opt['mid'] > 0.10:
                            if opt['type'] == 'C':
                                liquid_calls.append(opt)
                            else:
                                liquid_puts.append(opt)
                    
                    print(f"  Calls: {len(liquid_calls)} contracts")
                    print(f"  Puts:  {len(liquid_puts)} contracts")
                
                # Update info
                print(f"\nLast update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("Refreshing every 2 seconds... Press Ctrl+C to exit")
                
                # Wait
                time.sleep(2)
                
            except KeyboardInterrupt:
                print("\nShutting down...")
                self.running = False
                break
            except Exception as e:
                print(f"\nError: {e}")
                time.sleep(5)

if __name__ == "__main__":
    dashboard = LiveOptionsDashboard()
    dashboard.run()