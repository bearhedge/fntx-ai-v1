#!/usr/bin/env python3
"""Live options streaming dashboard"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add to path
sys.path.append(str(Path(__file__).parent))

from data_pipeline.streaming_theta_connector import LocalThetaConnector
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SimpleOptionsDashboard:
    def __init__(self):
        self.connector = LocalThetaConnector()
        self.running = True
        
    async def run(self):
        """Run the dashboard"""
        try:
            print("Starting Options Dashboard...")
            await self.connector.start()
            
            # Give it time to fetch initial data
            await asyncio.sleep(3)
            
            while self.running:
                # Clear screen
                print("\033[2J\033[H")
                
                # Get current data
                snapshot = self.connector.get_current_snapshot()
                
                # Header
                print("=" * 80)
                print("SPY OPTIONS LIVE STREAMING DASHBOARD")
                print("=" * 80)
                
                # Prices
                spy_theta = snapshot.get('spy_price', 0)
                spy_yahoo = snapshot.get('spy_price_realtime', 0)
                
                print(f"\nSPY Price:")
                print(f"  Theta Terminal: ${spy_theta:.2f} (15-min delayed)")
                print(f"  Yahoo Finance:  ${spy_yahoo:.2f} (real-time)")
                print(f"  Difference:     ${spy_yahoo - spy_theta:.2f}")
                
                # VIX estimate
                vix = snapshot.get('vix', 0)
                print(f"\nImplied Volatility (VIX estimate): {vix:.1f}%")
                
                # Options chain
                options = snapshot.get('options_chain', [])
                print(f"\nOptions Chain ({len(options)} contracts):")
                
                if options:
                    # Sort by strike
                    sorted_options = sorted(options, key=lambda x: (x['strike'], x['type']))
                    
                    # Group by strike
                    strikes = {}
                    for opt in sorted_options:
                        strike = opt['strike']
                        if strike not in strikes:
                            strikes[strike] = {}
                        strikes[strike][opt['type']] = opt
                    
                    # Display ATM options
                    if spy_yahoo > 0:
                        atm_strike = int(spy_yahoo)
                        print(f"\nNear ATM Options (Strike range: {atm_strike-3} to {atm_strike+3}):")
                        print(f"\n{'Strike':>8} {'Call Bid':>10} {'Call Ask':>10} {'Call Mid':>10} |"
                              f"{'Put Bid':>10} {'Put Ask':>10} {'Put Mid':>10}")
                        print("-" * 80)
                        
                        for strike in range(atm_strike-3, atm_strike+4):
                            if strike in strikes:
                                call = strikes[strike].get('C', {})
                                put = strikes[strike].get('P', {})
                                
                                call_bid = call.get('bid', 0)
                                call_ask = call.get('ask', 0)
                                call_mid = (call_bid + call_ask) / 2 if call else 0
                                
                                put_bid = put.get('bid', 0)
                                put_ask = put.get('ask', 0)
                                put_mid = (put_bid + put_ask) / 2 if put else 0
                                
                                # Highlight ATM
                                prefix = " -> " if strike == atm_strike else "    "
                                
                                print(f"{prefix}{strike:>5} "
                                      f"${call_bid:>9.2f} ${call_ask:>9.2f} ${call_mid:>9.2f} |"
                                      f"${put_bid:>9.2f} ${put_ask:>9.2f} ${put_mid:>9.2f}")
                else:
                    print("\nWaiting for options data...")
                
                # Update timestamp
                print(f"\nLast update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("\nPress Ctrl+C to exit")
                
                # Wait before next update
                await asyncio.sleep(2)
                
        except KeyboardInterrupt:
            print("\nShutting down...")
            self.running = False
        finally:
            await self.connector.stop()

async def main():
    dashboard = SimpleOptionsDashboard()
    await dashboard.run()

if __name__ == "__main__":
    asyncio.run(main())