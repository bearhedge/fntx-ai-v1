#!/usr/bin/env python3
"""
Validate Theta Terminal data integration
Tests Greeks, volume, open interest, and position pricing
"""
import asyncio
import sys
from datetime import datetime
from typing import Dict, List
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from data_pipeline.rest_theta_connector import RESTThetaConnector
from data_pipeline.database_position_tracker import DatabasePositionTracker


class ThetaDataValidator:
    """Validate data from Theta Terminal"""
    
    def __init__(self):
        self.connector = RESTThetaConnector()
        self.db_tracker = DatabasePositionTracker()
        self.validation_results = {
            'greeks': {'passed': 0, 'failed': 0, 'issues': []},
            'volume': {'passed': 0, 'failed': 0, 'issues': []},
            'open_interest': {'passed': 0, 'failed': 0, 'issues': []},
            'positions': {'passed': 0, 'failed': 0, 'issues': []}
        }
    
    async def run_validation(self):
        """Run complete validation suite"""
        print("=" * 60)
        print("Theta Terminal Data Validation")
        print("=" * 60)
        
        # Start connector
        await self.connector.start()
        await asyncio.sleep(3)  # Let it fetch initial data
        
        # Get market snapshot
        snapshot = self.connector.get_current_snapshot()
        options_chain = snapshot.get('options_chain', [])
        spy_price = snapshot.get('spy_price_realtime', snapshot.get('spy_price', 0))
        
        print(f"\nMarket Data:")
        print(f"  SPY Price: ${spy_price:.2f}")
        print(f"  Options Found: {len(options_chain)}")
        
        # Validate Greeks
        print("\n1. Validating Greeks Data...")
        self._validate_greeks(options_chain, spy_price)
        
        # Validate Volume
        print("\n2. Validating Volume Data...")
        self._validate_volume(options_chain)
        
        # Validate Open Interest
        print("\n3. Validating Open Interest...")
        self._validate_open_interest(options_chain)
        
        # Validate Position Pricing
        print("\n4. Validating Position Pricing...")
        await self._validate_position_pricing(options_chain)
        
        # Summary
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)
        
        for category, results in self.validation_results.items():
            total = results['passed'] + results['failed']
            if total > 0:
                pass_rate = (results['passed'] / total) * 100
                status = "✅ PASS" if results['failed'] == 0 else "❌ FAIL"
                print(f"\n{category.upper()}: {status}")
                print(f"  Passed: {results['passed']}/{total} ({pass_rate:.1f}%)")
                
                if results['issues']:
                    print(f"  Issues found:")
                    for issue in results['issues'][:5]:  # Show first 5 issues
                        print(f"    - {issue}")
                    if len(results['issues']) > 5:
                        print(f"    ... and {len(results['issues']) - 5} more")
        
        await self.connector.stop()
    
    def _validate_greeks(self, options_chain: List[Dict], spy_price: float):
        """Validate Greeks data ranges and consistency"""
        atm_strike = int(spy_price)
        
        for option in options_chain:
            strike = option['strike']
            opt_type = option['type']
            delta = option.get('delta', 0)
            iv = option.get('iv', 0)
            
            # Skip far OTM options
            if abs(strike - atm_strike) > 20:
                continue
            
            # Validate delta ranges
            if opt_type == 'C':
                if 0 <= delta <= 1:
                    self.validation_results['greeks']['passed'] += 1
                else:
                    self.validation_results['greeks']['failed'] += 1
                    self.validation_results['greeks']['issues'].append(
                        f"{strike}C: Delta {delta:.3f} out of range (should be 0-1)"
                    )
            else:  # Put
                if -1 <= delta <= 0:
                    self.validation_results['greeks']['passed'] += 1
                else:
                    self.validation_results['greeks']['failed'] += 1
                    self.validation_results['greeks']['issues'].append(
                        f"{strike}P: Delta {delta:.3f} out of range (should be -1-0)"
                    )
            
            # Validate IV
            if iv > 0:
                self.validation_results['greeks']['passed'] += 1
            else:
                self.validation_results['greeks']['failed'] += 1
                self.validation_results['greeks']['issues'].append(
                    f"{strike}{opt_type}: IV {iv:.1%} is not positive"
                )
            
            # Check delta consistency with moneyness
            moneyness = "ATM" if strike == atm_strike else ("ITM" if (
                (opt_type == 'C' and strike < spy_price) or 
                (opt_type == 'P' and strike > spy_price)
            ) else "OTM")
            
            # Basic moneyness checks
            if opt_type == 'C':
                if moneyness == "ITM" and delta < 0.5:
                    self.validation_results['greeks']['issues'].append(
                        f"{strike}C: ITM call with low delta {delta:.3f}"
                    )
                elif moneyness == "OTM" and delta > 0.5:
                    self.validation_results['greeks']['issues'].append(
                        f"{strike}C: OTM call with high delta {delta:.3f}"
                    )
    
    def _validate_volume(self, options_chain: List[Dict]):
        """Validate volume data"""
        total_with_volume = 0
        total_zero_volume = 0
        
        for option in options_chain:
            volume = option.get('volume', 0)
            
            if volume > 0:
                total_with_volume += 1
                self.validation_results['volume']['passed'] += 1
            else:
                total_zero_volume += 1
                # Zero volume is acceptable for illiquid strikes
                self.validation_results['volume']['passed'] += 1
            
            # Check for unrealistic volumes
            if volume > 1000000:
                self.validation_results['volume']['failed'] += 1
                self.validation_results['volume']['issues'].append(
                    f"{option['strike']}{option['type']}: Unrealistic volume {volume}"
                )
        
        # Summary check - at least some options should have volume
        if total_with_volume == 0 and len(options_chain) > 10:
            self.validation_results['volume']['issues'].append(
                "No options have volume data - possible data issue"
            )
    
    def _validate_open_interest(self, options_chain: List[Dict]):
        """Validate open interest data"""
        total_with_oi = 0
        
        for option in options_chain:
            oi = option.get('open_interest', 0)
            
            if oi > 0:
                total_with_oi += 1
                self.validation_results['open_interest']['passed'] += 1
            else:
                # Zero OI is acceptable for new strikes
                self.validation_results['open_interest']['passed'] += 1
            
            # OI should generally be >= volume
            volume = option.get('volume', 0)
            if volume > 0 and oi < volume:
                self.validation_results['open_interest']['issues'].append(
                    f"{option['strike']}{option['type']}: OI {oi} < Volume {volume}"
                )
        
        # Summary check
        if total_with_oi == 0 and len(options_chain) > 10:
            self.validation_results['open_interest']['issues'].append(
                "No options have open interest data - possible data issue"
            )
    
    async def _validate_position_pricing(self, options_chain: List[Dict]):
        """Validate position pricing functionality"""
        # Connect to database
        if not self.db_tracker.connect():
            self.validation_results['positions']['issues'].append(
                "Could not connect to database"
            )
            return
        
        # Get current positions
        positions = self.db_tracker.get_current_positions()
        
        if not positions:
            print("  No active positions to validate")
            return
        
        # Check each position
        for pos in positions:
            strike = pos['strike']
            opt_type = pos['type']
            entry_price = pos['entry_price']
            
            # Find current price
            current_price = self.db_tracker._find_option_price(
                options_chain, strike, opt_type
            )
            
            if current_price is not None and current_price > 0:
                self.validation_results['positions']['passed'] += 1
                print(f"  {strike}{opt_type}: Entry ${entry_price:.2f} → Current ${current_price:.2f}")
                
                # Calculate P&L
                pnl_data = self.db_tracker.calculate_position_pnl(pos, current_price)
                print(f"    P&L: ${pnl_data['total_pnl']:.2f} ({pnl_data['pnl_percentage']:.1f}%)")
            else:
                self.validation_results['positions']['failed'] += 1
                self.validation_results['positions']['issues'].append(
                    f"{strike}{opt_type}: Could not find current price"
                )


async def main():
    """Run validation"""
    validator = ThetaDataValidator()
    await validator.run_validation()


if __name__ == "__main__":
    asyncio.run(main())