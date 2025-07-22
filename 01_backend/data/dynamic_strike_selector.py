#!/usr/bin/env python3
"""
Dynamic Strike Selection based on Implied Volatility
Automatically adjusts number of strikes based on market volatility
"""
import numpy as np
import requests
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import logging
from strike_config import STRIKE_CONFIG

class DynamicStrikeSelector:
    """
    Selects option strikes dynamically based on implied volatility.
    Scales from minimum contracts on calm days to maximum on volatile days.
    """
    
    def __init__(self, base_url: str = "http://127.0.0.1:25510/v2/hist/option", config: dict = None):
        # API configuration
        self.base_url = base_url
        
        # Use provided config or default STRIKE_CONFIG
        self.config = config or STRIKE_CONFIG
        
        # Strike selection parameters from config
        self.stdev_multiplier = self.config['stdev_multiplier']
        self.min_contracts_per_side = self.config['min_contracts_per_side']
        self.max_contracts_per_side = self.config['max_contracts_per_side']
        self.base_contracts = self.config['base_contracts']
        
        # Market parameters from config
        self.strike_increment = self.config['strike_increment']
        self.trading_hours_per_day = self.config['trading_hours_per_day']
        
        # Liquidity parameters from config
        self.min_volume_bars = self.config['min_volume_bars']
        
        # Fallback parameters
        self.fallback_strikes_per_side = self.config['fallback_strikes_per_side']
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def get_atm_iv(self, exp_str: str, atm_strike: int) -> Optional[float]:
        """Get implied volatility for ATM options"""
        self.logger.info(f"Fetching ATM IV for strike ${atm_strike}")
        
        # Query ATM and adjacent strikes for better average
        strikes_to_check = [atm_strike - 1, atm_strike, atm_strike + 1]
        iv_values = []
        
        for strike in strikes_to_check:
            for option_type in ['C', 'P']:
                params = {
                    'root': 'SPY',
                    'exp': exp_str,
                    'strike': strike * 1000,
                    'right': option_type,
                    'start_date': exp_str,
                    'end_date': exp_str,
                    'ivl': 3600000  # 1 hour intervals
                }
                
                try:
                    r = requests.get(f"{self.base_url}/implied_volatility", 
                                   params=params, timeout=5)
                    
                    if r.status_code == 200:
                        data = r.json().get('response', [])
                        if data:
                            # Extract IV values
                            for bar in data[-5:]:  # Last 5 bars
                                if option_type == 'C' and len(bar) > 4 and bar[4]:
                                    iv_values.append(float(bar[4]))
                                elif option_type == 'P' and len(bar) > 2 and bar[2]:
                                    iv_values.append(float(bar[2]))
                except Exception as e:
                    self.logger.warning(f"Error fetching IV for ${strike}{option_type}: {e}")
        
        if iv_values:
            avg_iv = np.mean(iv_values)
            self.logger.info(f"ATM IV: {avg_iv:.1%} (from {len(iv_values)} samples)")
            return avg_iv
        
        self.logger.warning("Could not fetch ATM IV")
        return None
    
    def calculate_strike_count(self, spot_price: float, iv: float) -> int:
        """
        Calculate number of strikes to select based on volatility
        
        Formula:
        - Expected daily move = spot × iv × sqrt(hours/8760)
        - Strikes needed = (expected move × stdev multiplier) / strike increment
        """
        # Time to expiration for 0DTE
        time_in_years = self.trading_hours_per_day / (24 * 365)
        
        # Expected 1 standard deviation move
        daily_1sd_move = spot_price * iv * np.sqrt(time_in_years)
        
        # How many strikes fit in the expected move range
        strikes_per_sd = daily_1sd_move / self.strike_increment
        
        # Target strikes (2.5 standard deviations)
        target_strikes = int(strikes_per_sd * self.stdev_multiplier)
        
        # Apply bounds
        strike_count = max(self.min_contracts_per_side, 
                          min(target_strikes, self.max_contracts_per_side))
        
        self.logger.info(f"Volatility-based calculation:")
        self.logger.info(f"  Spot: ${spot_price:.2f}, IV: {iv:.1%}")
        self.logger.info(f"  1 SD move: ${daily_1sd_move:.2f}")
        self.logger.info(f"  Raw target: {target_strikes} strikes")
        self.logger.info(f"  Bounded result: {strike_count} strikes per side")
        
        return strike_count
    
    def get_strike_range(self, spot_price: float, trade_date: datetime) -> Dict:
        """
        Get dynamic strike range based on current volatility
        
        Returns:
            Dict with strike selection details
        """
        # Find ATM strike
        atm_strike = int(round(spot_price / self.strike_increment) * self.strike_increment)
        exp_str = trade_date.strftime('%Y%m%d')
        
        # Get ATM implied volatility
        iv = self.get_atm_iv(exp_str, atm_strike)
        
        if not iv:
            # Fallback to default range if IV unavailable
            self.logger.warning("IV unavailable, using fallback range")
            return self._get_fallback_range(spot_price, atm_strike)
        
        # Calculate dynamic strike count
        strikes_per_side = self.calculate_strike_count(spot_price, iv)
        
        # Generate strike lists
        min_strike = atm_strike - (strikes_per_side * int(self.strike_increment))
        max_strike = atm_strike + (strikes_per_side * int(self.strike_increment))
        
        all_strikes = list(range(min_strike, max_strike + 1, int(self.strike_increment)))
        
        return {
            'spot_price': spot_price,
            'atm_strike': atm_strike,
            'iv': iv,
            'strikes_per_side': strikes_per_side,
            'min_strike': min_strike,
            'max_strike': max_strike,
            'all_strikes': all_strikes,
            'total_strikes': len(all_strikes),
            'method': 'dynamic',
            'expected_contracts': len(all_strikes) * 2  # Calls + Puts
        }
    
    def _get_fallback_range(self, spot_price: float, atm_strike: int) -> Dict:
        """Fallback range when IV is unavailable"""
        # Use configured fallback range
        strikes_per_side = self.fallback_strikes_per_side
        min_strike = atm_strike - strikes_per_side
        max_strike = atm_strike + strikes_per_side
        
        all_strikes = list(range(min_strike, max_strike + 1))
        
        return {
            'spot_price': spot_price,
            'atm_strike': atm_strike,
            'iv': None,
            'strikes_per_side': strikes_per_side,
            'min_strike': min_strike,
            'max_strike': max_strike,
            'all_strikes': all_strikes,
            'total_strikes': len(all_strikes),
            'method': 'fallback',
            'expected_contracts': len(all_strikes) * 2
        }
    
    def test_volatility_scenarios(self):
        """Test strike selection across different volatility scenarios"""
        print("\n" + "="*60)
        print("Testing Dynamic Strike Selection Scenarios")
        print("="*60)
        
        spot_price = 400.0  # Example SPY price
        
        scenarios = [
            ("Very Calm", 0.08),
            ("Calm", 0.12),
            ("Normal", 0.20),
            ("Elevated", 0.30),
            ("High", 0.40),
            ("Very High", 0.60),
            ("Extreme", 0.80),
            ("Circuit Breaker", 1.00)
        ]
        
        for name, iv in scenarios:
            strikes = self.calculate_strike_count(spot_price, iv)
            daily_move = spot_price * iv * np.sqrt(self.trading_hours_per_day / (24 * 365))
            
            print(f"\n{name} Day (IV={iv:.0%}):")
            print(f"  Expected 1σ move: ${daily_move:.2f}")
            print(f"  Strikes per side: {strikes}")
            print(f"  Total contracts: {strikes * 2} (calls + puts)")
            print(f"  Strike range: ${int(spot_price - strikes)} - ${int(spot_price + strikes)}")


def main():
    """Test the dynamic strike selector"""
    selector = DynamicStrikeSelector()
    
    # Run test scenarios
    selector.test_volatility_scenarios()
    
    # Test with actual date
    print("\n" + "="*60)
    print("Testing with Jan 3, 2023")
    print("="*60)
    
    result = selector.get_strike_range(384.37, datetime(2023, 1, 3))
    
    print(f"\nDynamic Strike Selection Result:")
    print(f"  Spot: ${result['spot_price']:.2f}")
    print(f"  ATM: ${result['atm_strike']}")
    if result['iv']:
        print(f"  IV: {result['iv']:.1%}")
    print(f"  Method: {result['method']}")
    print(f"  Strikes per side: {result['strikes_per_side']}")
    print(f"  Strike range: ${result['min_strike']} - ${result['max_strike']}")
    print(f"  Total strikes: {result['total_strikes']}")
    print(f"  Expected contracts: {result['expected_contracts']}")


if __name__ == "__main__":
    main()