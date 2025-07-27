"""
Contract selector that maps RL model actions to specific option contracts
Selects optimal strikes based on Greeks, premium, and risk parameters
"""
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np
import pytz
from .statistical_analyzer import StatisticalAnalyzer


class ContractSelector:
    """Selects specific option contracts based on RL model decisions"""
    
    def __init__(self, 
                 target_delta: float = 0.20,
                 min_premium: float = 0.50,
                 max_spread_pct: float = 0.10,
                 max_pot: float = 0.35,
                 min_ev: float = 10.0):
        """
        Initialize contract selector
        
        Args:
            target_delta: Target delta for option selection (0.20 = 20 delta)
            min_premium: Minimum acceptable premium in dollars
            max_spread_pct: Maximum bid-ask spread as % of mid price
            max_pot: Maximum acceptable Probability of Touch (0.35 = 35%)
            min_ev: Minimum expected value per contract
        """
        self.target_delta = target_delta
        self.min_premium = min_premium
        self.max_spread_pct = max_spread_pct
        self.max_pot = max_pot
        self.min_ev = min_ev
        
        # Initialize statistical analyzer
        self.analyzer = StatisticalAnalyzer()
        
    def select_contract(self,
                       action: int,
                       options_chain: List[Dict],
                       spy_price: float,
                       vix: float = None) -> Optional[Dict]:
        """
        Select specific contract based on RL action
        
        Args:
            action: RL model action (0=HOLD, 1=SELL CALL, 2=SELL PUT)
            options_chain: List of option contracts with Greeks
            spy_price: Current SPY price
            vix: Current VIX value
            
        Returns:
            Selected contract dict with recommendation details or None
        """
        if action == 0:  # HOLD
            return None
            
        # Filter for calls or puts based on action
        option_type = 'C' if action == 1 else 'P'
        
        # Calculate time to expiry for 0DTE
        time_to_expiry = self.analyzer.calculate_time_to_expiry()
        
        # Filter options by type and basic criteria
        candidates = []
        for opt in options_chain:
            if opt.get('type') != option_type:
                continue
                
            # Check bid/ask validity
            bid = opt.get('bid', 0)
            ask = opt.get('ask', 0)
            if bid <= 0 or ask <= 0:
                continue
                
            # Check minimum premium
            mid_price = (bid + ask) / 2
            if mid_price < self.min_premium:
                continue
                
            # Check spread
            spread_pct = (ask - bid) / mid_price if mid_price > 0 else 1.0
            if spread_pct > self.max_spread_pct:
                continue
                
            # Get delta and IV
            delta = abs(opt.get('delta', 0))
            if delta <= 0:
                continue
                
            iv = opt.get('iv', 0.15)  # Default 15% if missing
            
            # Calculate statistical metrics
            pot = self.analyzer.calculate_probability_of_touch(
                spy_price=spy_price,
                strike=opt['strike'],
                volatility=iv,
                time_to_expiry=time_to_expiry,
                option_type=option_type
            )
            
            # Skip if PoT is too high
            if pot > self.max_pot:
                continue
                
            # Calculate expected value
            ev_stats = self.analyzer.calculate_expected_value(
                premium=mid_price,
                strike=opt['strike'],
                spy_price=spy_price,
                volatility=iv,
                time_to_expiry=time_to_expiry,
                option_type=option_type
            )
            
            # Skip if EV is too low
            if ev_stats['expected_value'] < self.min_ev:
                continue
                
            candidates.append({
                'option': opt,
                'mid_price': mid_price,
                'spread_pct': spread_pct,
                'delta': delta,
                'delta_diff': abs(delta - self.target_delta),
                'pot': pot,
                'ev': ev_stats['expected_value'],
                'ev_stats': ev_stats
            })
        
        if not candidates:
            return None
            
        # Sort by expected value (descending)
        candidates.sort(key=lambda x: x['ev'], reverse=True)
        
        # Select best candidate
        best = candidates[0]
        selected_option = best['option']
        
        # Build recommendation with statistical metrics
        recommendation = {
            'action': 'SELL CALL' if action == 1 else 'SELL PUT',
            'strike': selected_option['strike'],
            'type': selected_option['type'],
            'expiry': selected_option.get('expiry', '0DTE'),
            'bid': selected_option['bid'],
            'ask': selected_option['ask'],
            'mid_price': best['mid_price'],
            'delta': best['delta'],
            'gamma': selected_option.get('gamma', 0),
            'theta': selected_option.get('theta', 0),
            'vega': selected_option.get('vega', 0),
            'iv': selected_option.get('iv', 0),
            'spread_pct': best['spread_pct'],
            'position_size': 1,  # Fixed at 1 contract for now
            'probability_of_touch': best['pot'],
            'expected_value': best['ev'],
            'statistical_metrics': best['ev_stats'],
            'recommendation_text': self._format_recommendation(
                action, selected_option, best['mid_price'], spy_price, vix,
                best['pot'], best['ev']
            ),
            'risk_metrics': self._calculate_risk_metrics(
                selected_option, best['mid_price'], spy_price
            )
        }
        
        return recommendation
        
    def _format_recommendation(self, 
                             action: int,
                             option: Dict,
                             mid_price: float,
                             spy_price: float,
                             vix: Optional[float],
                             pot: float,
                             ev: float) -> str:
        """Format human-readable recommendation"""
        action_text = "SELL CALL" if action == 1 else "SELL PUT"
        strike = option['strike']
        delta = abs(option.get('delta', 0))
        
        # Calculate moneyness
        if action == 1:  # Call
            moneyness = strike / spy_price
            otm_pct = (strike - spy_price) / spy_price * 100
        else:  # Put
            moneyness = spy_price / strike
            otm_pct = (spy_price - strike) / spy_price * 100
            
        rec_text = (
            f"{action_text} {strike} @ ${mid_price:.2f}\n"
            f"Delta: {delta:.2f} ({abs(otm_pct):.1f}% OTM)\n"
            f"PoT: {pot:.1%} | EV: ${ev:.2f}\n"
            f"Position Size: 1 contract"
        )
        
        if vix:
            rec_text += f" | VIX: {vix:.1f}"
            
        return rec_text
        
    def _calculate_risk_metrics(self, 
                              option: Dict,
                              mid_price: float,
                              spy_price: float) -> Dict:
        """Calculate risk metrics for the position"""
        strike = option['strike']
        delta = abs(option.get('delta', 0))
        gamma = option.get('gamma', 0)
        
        # Calculate max loss (if SPY moves to strike)
        if option['type'] == 'C':
            move_to_strike = strike - spy_price
        else:
            move_to_strike = spy_price - strike
            
        # Estimate loss if SPY moves to strike
        # Simplified: Premium collected - intrinsic value at strike
        max_loss = 0 if move_to_strike <= 0 else move_to_strike - mid_price
        
        # Calculate breakeven
        if option['type'] == 'C':
            breakeven = strike + mid_price
        else:
            breakeven = strike - mid_price
            
        # Win rate estimate based on delta
        # Rough approximation: 1 - delta gives probability of expiring worthless
        win_rate = 1 - delta
        
        # Add position-specific metrics
        position_size = 1  # Fixed for now
        stop_loss_multiplier = 3.5  # Standard 3.5x
        
        return {
            'premium_collected': mid_price * 100 * position_size,
            'max_loss': max_loss * 100 * position_size if max_loss > 0 else 0,
            'stop_loss_price': mid_price * stop_loss_multiplier,
            'stop_loss_cost': mid_price * (stop_loss_multiplier - 1) * 100 * position_size,
            'breakeven': breakeven,
            'win_rate_estimate': win_rate,
            'delta_exposure': delta * 100 * position_size,
            'gamma_exposure': gamma * 100 * position_size,
            'risk_reward_ratio': abs(mid_price / max_loss) if max_loss > 0 else float('inf'),
            'position_size': position_size
        }
        
    def get_market_context(self, vix: float) -> Dict:
        """Get market context for decision making"""
        # VIX levels
        if vix < 12:
            vix_regime = "Very Low"
            vix_percentile = 10
        elif vix < 15:
            vix_regime = "Low"
            vix_percentile = 25
        elif vix < 20:
            vix_regime = "Normal"
            vix_percentile = 50
        elif vix < 25:
            vix_regime = "Elevated"
            vix_percentile = 75
        elif vix < 30:
            vix_regime = "High"
            vix_percentile = 90
        else:
            vix_regime = "Very High"
            vix_percentile = 95
            
        # Trading time context
        eastern = pytz.timezone('US/Eastern')
        now = datetime.now(eastern)
        hour = now.hour
        minute = now.minute
        
        if hour < 10:
            time_period = "Early Morning"
            time_characteristics = "Higher volatility, price discovery"
        elif hour < 11:
            time_period = "Mid Morning"
            time_characteristics = "Trending period"
        elif hour < 14:
            time_period = "Midday"
            time_characteristics = "Lower volatility, lunch lull"
        elif hour < 15:
            time_period = "Early Afternoon"
            time_characteristics = "Volatility pickup"
        else:
            time_period = "Late Day"
            time_characteristics = "Closing volatility, gamma risk"
            
        return {
            'vix_level': vix,
            'vix_regime': vix_regime,
            'vix_percentile': vix_percentile,
            'time_period': time_period,
            'time_characteristics': time_characteristics,
            'market_hours_remaining': self._calculate_hours_remaining(hour, minute)
        }
        
    def _calculate_hours_remaining(self, hour: int, minute: int) -> float:
        """Calculate hours remaining until market close"""
        # Market closes at 4 PM ET
        close_minutes = 16 * 60
        current_minutes = hour * 60 + minute
        
        if current_minutes >= close_minutes:
            return 0.0
            
        remaining_minutes = close_minutes - current_minutes
        return remaining_minutes / 60.0