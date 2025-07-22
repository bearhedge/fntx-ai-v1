#!/usr/bin/env python3
"""
Smart Strike Selector for 0DTE Options
Dynamically selects relevant strikes based on IV and liquidity
"""
import sys
import requests
import numpy as np
from datetime import datetime, time
from typing import List, Dict, Tuple, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

class SmartStrikeSelector:
    def __init__(self, base_url: str = "http://127.0.0.1:25510/v2/hist/option"):
        self.base_url = base_url
        # Liquidity thresholds
        self.min_volume = 50
        self.min_bid = 0.05
        self.min_open_interest = 100
        self.dead_zone_strikes = 3  # Consecutive strikes to confirm dead zone
        
        # IV calculation parameters
        self.sigma_multiplier = 2.5  # Standard deviations to capture
        self.min_range_pct = 0.015  # Minimum 1.5% of spot price
        self.high_iv_threshold = 0.30  # 30% IV is considered high
        self.high_iv_multiplier = 1.5  # Expand range by 50% in high IV
        
    def get_trading_hours_remaining(self, date: datetime) -> float:
        """Calculate trading hours remaining for 0DTE"""
        # Market hours: 9:30 AM - 4:00 PM ET (6.5 hours total)
        market_open = time(9, 30)
        market_close = time(16, 0)
        
        current_time = datetime.now().time()
        
        # If before market open, use full day
        if current_time < market_open:
            return 6.5
        
        # If after market close, use minimal time
        if current_time >= market_close:
            return 0.1  # Small non-zero value
        
        # Calculate hours remaining
        current_minutes = current_time.hour * 60 + current_time.minute
        close_minutes = 16 * 60  # 4:00 PM
        minutes_remaining = close_minutes - current_minutes
        
        return max(minutes_remaining / 60.0, 0.1)
    
    def get_atm_iv(self, exp_str: str, spot_price: float) -> Optional[Dict]:
        """Get ATM implied volatility by querying nearby strikes"""
        # Find ATM strike
        atm_strike = int(round(spot_price))
        
        # Query ATM and ±1 strikes for better average
        strikes_to_check = [atm_strike - 1, atm_strike, atm_strike + 1]
        
        iv_data = []
        
        for strike in strikes_to_check:
            for option_type in ['C', 'P']:
                params = {
                    'root': 'SPY',
                    'exp': exp_str,
                    'strike': strike * 1000,
                    'right': option_type,
                    'start_date': exp_str,
                    'end_date': exp_str,
                    'ivl': 3600000  # 1 hour intervals for quick check
                }
                
                try:
                    # Get IV data
                    r = requests.get(f"{self.base_url}/implied_volatility", 
                                   params=params, timeout=5)
                    
                    if r.status_code == 200:
                        data = r.json().get('response', [])
                        if data:
                            # Get most recent IV
                            latest = data[-1]
                            # IV is in different fields for calls vs puts
                            if option_type == 'C':
                                iv = latest[4] if latest[4] else None
                            else:
                                iv = latest[2] if latest[2] else None
                            
                            if iv and iv > 0:
                                iv_data.append({
                                    'strike': strike,
                                    'type': option_type,
                                    'iv': iv
                                })
                                
                except Exception as e:
                    print(f"Error getting IV for ${strike}{option_type}: {e}")
                    continue
        
        if not iv_data:
            return None
        
        # Calculate average IV
        avg_iv = np.mean([d['iv'] for d in iv_data])
        
        return {
            'atm_strike': atm_strike,
            'avg_iv': avg_iv,
            'samples': len(iv_data),
            'iv_data': iv_data
        }
    
    def calculate_dynamic_range(self, spot_price: float, iv: float, 
                               hours_remaining: float) -> Tuple[float, float]:
        """Calculate expected price range using IV"""
        # Convert annual IV to expected move for remaining hours
        # Formula: Expected Move = Spot × IV × sqrt(time_in_years)
        time_in_years = hours_remaining / (365 * 24)
        
        # Base expected move (1 standard deviation)
        one_sigma_move = spot_price * iv * np.sqrt(time_in_years)
        
        # Calculate range with sigma multiplier
        iv_based_range = one_sigma_move * self.sigma_multiplier
        
        # Apply minimum range constraint
        min_range = spot_price * self.min_range_pct
        base_range = max(iv_based_range, min_range)
        
        # Adjust for high volatility environments
        if iv > self.high_iv_threshold:
            base_range *= self.high_iv_multiplier
        
        lower_bound = spot_price - base_range
        upper_bound = spot_price + base_range
        
        return lower_bound, upper_bound
    
    def test_strike_liquidity(self, strike: int, exp_str: str) -> Dict:
        """Test if a strike has sufficient liquidity"""
        liquidity_score = 0
        details = {
            'strike': strike,
            'has_volume': False,
            'has_bid': False,
            'has_oi': False,
            'is_liquid': False
        }
        
        # Test both calls and puts
        for option_type in ['C', 'P']:
            params = {
                'root': 'SPY',
                'exp': exp_str,
                'strike': strike * 1000,
                'right': option_type,
                'start_date': exp_str,
                'end_date': exp_str,
                'ivl': 300000  # 5 minutes
            }
            
            try:
                # Check OHLC for volume and bid
                r = requests.get(f"{self.base_url}/ohlc", params=params, timeout=5)
                
                if r.status_code == 200:
                    data = r.json().get('response', [])
                    if data:
                        # Get last few bars
                        recent_bars = data[-12:]  # Last hour
                        
                        # Check volume
                        total_volume = sum(bar[5] for bar in recent_bars)
                        if total_volume >= self.min_volume:
                            details['has_volume'] = True
                            liquidity_score += 1
                        
                        # Check bid (use close price as proxy)
                        recent_prices = [bar[4] for bar in recent_bars if bar[4] > 0]
                        if recent_prices and min(recent_prices) >= self.min_bid:
                            details['has_bid'] = True
                            liquidity_score += 1
                
                # Check open interest (would need separate endpoint or database)
                # For now, use volume as proxy
                if details['has_volume']:
                    details['has_oi'] = True
                    liquidity_score += 1
                    
            except Exception as e:
                print(f"Error testing ${strike}{option_type}: {e}")
                continue
        
        # Strike is liquid if it passes any liquidity test
        details['is_liquid'] = liquidity_score > 0
        details['liquidity_score'] = liquidity_score
        
        return details
    
    def discover_relevant_strikes(self, exp_str: str, spot_price: float,
                                 iv_data: Optional[Dict] = None) -> List[int]:
        """Discover relevant strikes using liquidity cascade"""
        
        # Get IV data if not provided
        if not iv_data:
            iv_data = self.get_atm_iv(exp_str, spot_price)
        
        if not iv_data:
            # Fallback to fixed percentage if no IV available
            print("Warning: No IV data available, using 2% fixed range")
            lower_bound = spot_price * 0.98
            upper_bound = spot_price * 1.02
        else:
            # Calculate dynamic range
            hours_remaining = self.get_trading_hours_remaining(
                datetime.strptime(exp_str, '%Y%m%d')
            )
            
            lower_bound, upper_bound = self.calculate_dynamic_range(
                spot_price, iv_data['avg_iv'], hours_remaining
            )
            
            print(f"IV-based range: ${lower_bound:.0f} - ${upper_bound:.0f}")
            print(f"  ATM IV: {iv_data['avg_iv']:.1%}")
            print(f"  Hours remaining: {hours_remaining:.1f}")
        
        # Start with strikes in the calculated range
        atm_strike = int(round(spot_price))
        min_strike = int(lower_bound)
        max_strike = int(upper_bound)
        
        relevant_strikes = []
        
        # Expand from ATM outward
        # First, add all strikes within the calculated range
        for strike in range(min_strike, max_strike + 1):
            relevant_strikes.append(strike)
        
        # Then expand outward checking liquidity
        # Check downward
        consecutive_dead = 0
        strike = min_strike - 1
        
        while strike > spot_price * 0.8 and consecutive_dead < self.dead_zone_strikes:
            liquidity = self.test_strike_liquidity(strike, exp_str)
            
            if liquidity['is_liquid']:
                relevant_strikes.append(strike)
                consecutive_dead = 0
            else:
                consecutive_dead += 1
            
            strike -= 1
        
        # Check upward
        consecutive_dead = 0
        strike = max_strike + 1
        
        while strike < spot_price * 1.2 and consecutive_dead < self.dead_zone_strikes:
            liquidity = self.test_strike_liquidity(strike, exp_str)
            
            if liquidity['is_liquid']:
                relevant_strikes.append(strike)
                consecutive_dead = 0
            else:
                consecutive_dead += 1
            
            strike += 1
        
        # Sort and return unique strikes
        relevant_strikes = sorted(list(set(relevant_strikes)))
        
        print(f"Selected {len(relevant_strikes)} strikes: "
              f"${min(relevant_strikes)} - ${max(relevant_strikes)}")
        
        return relevant_strikes
    
    def get_strike_recommendation(self, date: datetime, spot_price: float) -> Dict:
        """Get complete strike recommendation for a given date"""
        exp_str = date.strftime('%Y%m%d')
        
        # Get IV data
        iv_data = self.get_atm_iv(exp_str, spot_price)
        
        # Discover relevant strikes
        strikes = self.discover_relevant_strikes(exp_str, spot_price, iv_data)
        
        # Calculate statistics
        atm_strike = int(round(spot_price))
        strikes_below_atm = len([s for s in strikes if s < atm_strike])
        strikes_above_atm = len([s for s in strikes if s > atm_strike])
        
        recommendation = {
            'date': date,
            'spot_price': spot_price,
            'atm_strike': atm_strike,
            'iv_data': iv_data,
            'recommended_strikes': strikes,
            'strike_count': len(strikes),
            'min_strike': min(strikes) if strikes else None,
            'max_strike': max(strikes) if strikes else None,
            'strikes_below_atm': strikes_below_atm,
            'strikes_above_atm': strikes_above_atm,
            'range_percentage': (max(strikes) - min(strikes)) / spot_price * 100 if strikes else 0
        }
        
        return recommendation


def test_smart_selector():
    """Test the smart strike selector with Jan 3, 2023 data"""
    selector = SmartStrikeSelector()
    
    # Test date: Jan 3, 2023
    test_date = datetime(2023, 1, 3)
    spot_price = 380.0  # Approximate SPY price
    
    print("="*80)
    print("TESTING SMART STRIKE SELECTOR")
    print("="*80)
    
    recommendation = selector.get_strike_recommendation(test_date, spot_price)
    
    print(f"\nRecommendation for {test_date.strftime('%Y-%m-%d')}:")
    print(f"  Spot price: ${recommendation['spot_price']}")
    print(f"  Strike count: {recommendation['strike_count']}")
    print(f"  Strike range: ${recommendation['min_strike']} - ${recommendation['max_strike']}")
    print(f"  Range as % of spot: {recommendation['range_percentage']:.1f}%")
    print(f"  Strikes below ATM: {recommendation['strikes_below_atm']}")
    print(f"  Strikes above ATM: {recommendation['strikes_above_atm']}")
    
    if recommendation['iv_data']:
        print(f"  ATM IV: {recommendation['iv_data']['avg_iv']:.1%}")
    
    # Compare with current system
    print(f"\nCurrent system: 80 strikes ($352-$392)")
    print(f"Smart selector: {recommendation['strike_count']} strikes "
          f"(${recommendation['min_strike']}-${recommendation['max_strike']})")
    print(f"Reduction: {(80 - recommendation['strike_count']) / 80 * 100:.0f}%")
    
    return recommendation


if __name__ == "__main__":
    test_smart_selector()