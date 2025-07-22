#!/usr/bin/env python3
"""Working dashboard with streaming data"""
import requests
import json
import time
from datetime import datetime
import threading
import queue

class StreamingDashboard:
    def __init__(self):
        self.base_url = "http://localhost:25510"
        self.running = True
        self.data_queue = queue.Queue()
        
    def fetch_data_worker(self):
        """Background worker to fetch data"""
        while self.running:
            try:
                data = {
                    'spy_price': self.get_spy_price(),
                    'spy_price_realtime': self.get_yahoo_price(),
                    'options_chain': self.get_options_chain(),
                    'timestamp': datetime.now()
                }
                self.data_queue.put(data)
                time.sleep(1)  # Update every second
            except Exception as e:
                print(f"Error fetching data: {e}")
                time.sleep(5)
    
    def get_spy_price(self):
        """Get SPY price from Theta Terminal"""
        try:
            response = requests.get(f"{self.base_url}/v2/snapshot/stock/quote?root=SPY", timeout=2)
            if response.status_code == 200:
                data = response.json()
                if data['response']:
                    quote = data['response'][0]
                    return (quote[3] + quote[7]) / 2
        except:
            pass
        return 0
    
    def get_yahoo_price(self):
        """Get real-time SPY price from Yahoo"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/SPY", 
                                  headers=headers, timeout=2)
            if response.status_code == 200:
                data = response.json()
                return data['chart']['result'][0]['meta']['regularMarketPrice']
        except:
            pass
        return 0
    
    def get_options_chain(self):
        """Get 0DTE options chain"""
        options = []
        try:
            # Get current price for ATM calculation
            spy_price = self.get_yahoo_price() or self.get_spy_price()
            if spy_price <= 0:
                return options
                
            atm_strike = int(spy_price)
            today = datetime.now().strftime('%Y%m%d')
            
            # Fetch liquid strikes (±5 from ATM)
            for offset in range(-5, 6):
                strike = atm_strike + offset
                
                for option_type in ['C', 'P']:
                    try:
                        url = f"{self.base_url}/v2/snapshot/option/quote?root=SPY&exp={today}&strike={strike}000&right={option_type}"
                        response = requests.get(url, timeout=1)
                        
                        if response.status_code == 200:
                            data = response.json()
                            if data['response']:
                                quote = data['response'][0]
                                bid = quote[3] / 100  # Convert cents to dollars
                                ask = quote[7] / 100
                                
                                # Only include liquid options
                                if bid > 0 or ask > 0:
                                    options.append({
                                        'strike': strike,
                                        'type': option_type,
                                        'bid': bid,
                                        'ask': ask,
                                        'mid': (bid + ask) / 2,
                                        'spread': ask - bid
                                    })
                    except:
                        pass
                        
        except Exception as e:
            print(f"Error fetching options: {e}")
            
        return options
    
    def display_dashboard(self):
        """Main display loop"""
        # Start data fetcher in background
        fetcher = threading.Thread(target=self.fetch_data_worker, daemon=True)
        fetcher.start()
        
        print("Starting Live Options Dashboard...")
        print("Fetching initial data...")
        time.sleep(2)
        
        last_data = None
        
        while self.running:
            try:
                # Get latest data
                try:
                    last_data = self.data_queue.get(timeout=0.1)
                except queue.Empty:
                    pass
                
                if not last_data:
                    time.sleep(0.5)
                    continue
                
                # Clear screen
                print("\033[2J\033[H")
                
                # Header
                print("=" * 100)
                print(" " * 35 + "SPY 0DTE OPTIONS LIVE STREAM")
                print("=" * 100)
                
                # Prices
                spy_theta = last_data['spy_price']
                spy_yahoo = last_data['spy_price_realtime']
                
                print(f"\nMARKET DATA:")
                print(f"  SPY Price (Theta/Delayed): ${spy_theta:>7.2f}")
                print(f"  SPY Price (Yahoo/Live):    ${spy_yahoo:>7.2f}")
                print(f"  Price Difference:          ${spy_yahoo - spy_theta:>7.2f}")
                print(f"  Update Time:               {last_data['timestamp'].strftime('%H:%M:%S')}")
                
                # Options chain
                options = last_data['options_chain']
                if options:
                    # Group by strike
                    strikes = {}
                    for opt in options:
                        strike = opt['strike']
                        if strike not in strikes:
                            strikes[strike] = {}
                        strikes[strike][opt['type']] = opt
                    
                    # Display options table
                    atm_strike = int(spy_yahoo) if spy_yahoo > 0 else int(spy_theta)
                    
                    print(f"\nOPTIONS CHAIN (0DTE - {datetime.now().strftime('%Y-%m-%d')}):")
                    print(f"ATM Strike: {atm_strike}")
                    
                    print(f"\n{'':>4} {'Strike':>8} {'|':^3} {'CALLS':^35} {'|':^3} {'PUTS':^35}")
                    print(f"{'':>4} {'':>8} {'|':^3} {'Bid':>10} {'Ask':>10} {'Mid':>10} {'|':^3} {'Bid':>10} {'Ask':>10} {'Mid':>10}")
                    print("-" * 100)
                    
                    # Sort strikes
                    sorted_strikes = sorted(strikes.keys())
                    
                    for strike in sorted_strikes:
                        if abs(strike - atm_strike) <= 5:  # Show ±5 strikes
                            call = strikes[strike].get('C', {})
                            put = strikes[strike].get('P', {})
                            
                            # Mark ATM and near-ATM
                            if strike == atm_strike:
                                marker = "ATM"
                            elif abs(strike - atm_strike) <= 2:
                                marker = " * "
                            else:
                                marker = "   "
                            
                            # Format row
                            call_bid = f"${call.get('bid', 0):.2f}" if call else "-"
                            call_ask = f"${call.get('ask', 0):.2f}" if call else "-"
                            call_mid = f"${call.get('mid', 0):.2f}" if call else "-"
                            
                            put_bid = f"${put.get('bid', 0):.2f}" if put else "-"
                            put_ask = f"${put.get('ask', 0):.2f}" if put else "-"
                            put_mid = f"${put.get('mid', 0):.2f}" if put else "-"
                            
                            print(f"{marker:>4} {strike:>8} {'|':^3} "
                                  f"{call_bid:>10} {call_ask:>10} {call_mid:>10} {'|':^3} "
                                  f"{put_bid:>10} {put_ask:>10} {put_mid:>10}")
                    
                    # Summary
                    liquid_options = [opt for opt in options if opt['bid'] > 0.05]
                    print(f"\nLiquid contracts (bid > $0.05): {len(liquid_options)}")
                    
                    # Show most liquid
                    if liquid_options:
                        liquid_sorted = sorted(liquid_options, key=lambda x: x['bid'], reverse=True)[:5]
                        print("\nMost liquid contracts:")
                        for opt in liquid_sorted:
                            print(f"  {opt['strike']} {opt['type']}: Bid=${opt['bid']:.2f} Ask=${opt['ask']:.2f}")
                else:
                    print("\nWaiting for options data...")
                
                print("\nPress Ctrl+C to exit")
                
                # Small delay for display
                time.sleep(0.1)
                
            except KeyboardInterrupt:
                print("\nShutting down...")
                self.running = False
                break
            except Exception as e:
                print(f"\nDisplay error: {e}")
                time.sleep(1)

def main():
    dashboard = StreamingDashboard()
    dashboard.display_dashboard()

if __name__ == "__main__":
    main()