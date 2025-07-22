"""
Configuration for Dynamic Strike Selection
Adjust these parameters to tune the strike selection behavior
"""

# Volatility-based scaling parameters
STRIKE_CONFIG = {
    # Standard deviation multiplier (2.5 captures ~98.76% of price moves)
    'stdev_multiplier': 2.5,
    
    # Minimum contracts per side (even on very calm days)
    'min_contracts_per_side': 5,
    
    # Maximum contracts per side (cap for extreme volatility)
    'max_contracts_per_side': 30,
    
    # Target contracts for normal volatility days
    'base_contracts': 7,
    
    # Strike increment for SPY
    'strike_increment': 1.0,
    
    # Trading hours per day (regular market)
    'trading_hours_per_day': 6.5,
    
    # Minimum volume bars for liquidity filter
    'min_volume_bars': 60,  # 60 bars * 5 min = 5 hours
    
    # Fallback strikes per side when IV unavailable
    'fallback_strikes_per_side': 15
}

# Volatility scenarios for reference
VOLATILITY_SCENARIOS = {
    'very_calm': {
        'iv_range': (0.00, 0.10),
        'expected_strikes': 5,
        'description': 'Very low volatility, minimal movement expected'
    },
    'calm': {
        'iv_range': (0.10, 0.15),
        'expected_strikes': 5-7,
        'description': 'Below average volatility'
    },
    'normal': {
        'iv_range': (0.15, 0.25),
        'expected_strikes': 7-12,
        'description': 'Typical market conditions'
    },
    'elevated': {
        'iv_range': (0.25, 0.35),
        'expected_strikes': 12-17,
        'description': 'Above average volatility, uncertainty in market'
    },
    'high': {
        'iv_range': (0.35, 0.50),
        'expected_strikes': 17-25,
        'description': 'High volatility, significant events or uncertainty'
    },
    'extreme': {
        'iv_range': (0.50, 1.00),
        'expected_strikes': 25-30,
        'description': 'Extreme volatility, major market events'
    }
}

# Example daily adjustments
def get_strike_estimate(iv: float) -> str:
    """Get estimated strikes for given IV level"""
    for scenario, config in VOLATILITY_SCENARIOS.items():
        min_iv, max_iv = config['iv_range']
        if min_iv <= iv < max_iv:
            return f"{scenario}: ~{config['expected_strikes']} strikes per side"
    return "extreme: 30 strikes per side (capped)"