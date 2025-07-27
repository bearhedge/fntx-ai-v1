"""
Data filtering for options chain display
Focus on OTM options with adequate liquidity
"""
from typing import List, Dict, Optional
import numpy as np


class OTMFilter:
    """Filter options to show only OTM with good liquidity"""
    
    def __init__(self, 
                 min_bid: float = 0.00,  # Show all options, even penny options
                 min_volume: int = 0,    # Show even if no volume (common for 0DTE)
                 max_strikes_shown: int = 20):  # Show more strikes
        self.min_bid = min_bid
        self.min_volume = min_volume
        self.max_strikes_shown = max_strikes_shown
    
    def filter_options_chain(self, 
                           options_chain: List[Dict],
                           spy_price: float) -> Dict[str, List[Dict]]:
        """
        Filter options chain to OTM only with liquidity checks
        
        Returns:
            Dict with 'calls' and 'puts' lists
        """
        otm_calls = []
        otm_puts = []
        
        for option in options_chain:
            strike = option['strike']
            opt_type = option['type']
            bid = option.get('bid', 0)
            volume = option.get('volume', 0)
            
            # Skip if no liquidity (but be lenient for 0DTE)
            # Only skip if both bid and ask are 0
            if option.get('bid', 0) == 0 and option.get('ask', 0) == 0:
                continue
            
            # OTM calls: strike > spot
            if opt_type == 'C' and strike > spy_price:
                otm_calls.append(option)
            
            # OTM puts: strike < spot  
            elif opt_type == 'P' and strike < spy_price:
                otm_puts.append(option)
        
        # Sort calls ascending (nearest OTM first)
        otm_calls.sort(key=lambda x: x['strike'])
        
        # Sort puts descending (nearest OTM first)
        otm_puts.sort(key=lambda x: x['strike'], reverse=True)
        
        # Limit to max strikes shown
        return {
            'calls': otm_calls[:self.max_strikes_shown],
            'puts': otm_puts[:self.max_strikes_shown]
        }
    
    def get_tradeable_strikes(self,
                            options_chain: List[Dict],
                            spy_price: float,
                            option_type: str) -> List[float]:
        """Get list of tradeable strikes for given option type"""
        filtered = self.filter_options_chain(options_chain, spy_price)
        
        if option_type.upper() == 'C':
            return [opt['strike'] for opt in filtered['calls']]
        else:
            return [opt['strike'] for opt in filtered['puts']]
    
    def find_best_otm_option(self,
                           options_chain: List[Dict],
                           spy_price: float,
                           option_type: str,
                           target_delta: float = 0.15) -> Optional[Dict]:
        """
        Find best OTM option based on delta target
        
        Args:
            options_chain: Full options chain
            spy_price: Current SPY price
            option_type: 'C' or 'P'
            target_delta: Target delta (abs value)
            
        Returns:
            Best option dict or None
        """
        filtered = self.filter_options_chain(options_chain, spy_price)
        
        candidates = filtered['calls'] if option_type.upper() == 'C' else filtered['puts']
        
        if not candidates:
            return None
        
        # Find option closest to target delta
        best_option = None
        best_delta_diff = float('inf')
        
        for option in candidates:
            delta = abs(option.get('delta', 0))
            delta_diff = abs(delta - target_delta)
            
            if delta_diff < best_delta_diff:
                best_delta_diff = delta_diff
                best_option = option
        
        return best_option
    
    def calculate_spread_quality(self, option: Dict) -> float:
        """
        Calculate spread quality score (0-1)
        Higher is better
        """
        bid = option.get('bid', 0)
        ask = option.get('ask', float('inf'))
        
        if bid <= 0 or ask <= 0:
            return 0
        
        spread = ask - bid
        mid = (bid + ask) / 2
        
        # Spread as percentage of mid
        spread_pct = spread / mid if mid > 0 else 1
        
        # Quality score: 1 for tight spreads, 0 for wide
        # 0.05 (5%) spread = 0.9 quality
        # 0.20 (20%) spread = 0.6 quality
        quality = max(0, 1 - (spread_pct * 5))
        
        return quality
    
    def format_option_display(self, option: Dict) -> Dict[str, str]:
        """Format option data for display"""
        bid = option.get('bid', 0)
        ask = option.get('ask', 0)
        mid = (bid + ask) / 2
        spread = ask - bid
        volume = option.get('volume', 0)
        oi = option.get('open_interest', 0)
        iv = option.get('iv', 0)
        delta = option.get('delta', 0)
        
        # Calculate spread quality
        quality = self.calculate_spread_quality(option)
        
        # Color coding for spread quality
        if quality >= 0.8:
            spread_color = "green"
        elif quality >= 0.6:
            spread_color = "yellow"
        else:
            spread_color = "red"
        
        return {
            'strike': f"{option['strike']:.0f}",
            'bid': f"{bid:.2f}",
            'ask': f"{ask:.2f}",
            'mid': f"{mid:.2f}",
            'spread': f"{spread:.2f}",
            'spread_color': spread_color,
            'volume': f"{volume:,}",
            'oi': f"{oi:,}",
            'iv': f"{iv:.1%}",
            'delta': f"{delta:.3f}"
        }