"""
Statistical analyzer for option trading decisions
Calculates Probability of Touch (PoT) and Expected Value (EV)
Replaces vague confidence scores with real statistical metrics
"""
import numpy as np
from typing import Dict, Optional, Tuple
from datetime import datetime
import pytz
from scipy.stats import norm


class StatisticalAnalyzer:
    """Calculate real statistical metrics for option trading decisions"""
    
    def __init__(self, risk_free_rate: float = 0.05):
        """
        Initialize statistical analyzer
        
        Args:
            risk_free_rate: Annual risk-free rate for calculations
        """
        self.risk_free_rate = risk_free_rate
        self.eastern = pytz.timezone('US/Eastern')
        
    def calculate_probability_of_touch(self,
                                     spy_price: float,
                                     strike: float,
                                     volatility: float,
                                     time_to_expiry: float,
                                     option_type: str) -> float:
        """
        Calculate Probability of Touch using barrier option theory
        
        This is the probability that the underlying will touch the strike
        price at ANY point before expiration. For short option sellers,
        this is a critical risk metric.
        
        Args:
            spy_price: Current SPY price
            strike: Option strike price
            volatility: Implied volatility (annualized)
            time_to_expiry: Time to expiration in years
            option_type: 'C' for call, 'P' for put
            
        Returns:
            Probability of touch (0 to 1)
        """
        if time_to_expiry <= 0:
            return 0.0
            
        # Calculate parameters
        vol_sqrt_t = volatility * np.sqrt(time_to_expiry)
        drift = (self.risk_free_rate - 0.5 * volatility ** 2) * time_to_expiry
        
        if option_type == 'C':
            # For calls, we care about upward movement
            if strike <= spy_price:
                return 1.0  # Already ITM
            
            # For 0DTE, use simplified approach
            # Distance to strike as percentage
            distance_pct = (strike - spy_price) / spy_price
            
            # Standard deviations to strike
            std_devs = distance_pct / (volatility * np.sqrt(time_to_expiry))
            
            # Probability of touching is approximately 2 * (1 - N(std_devs))
            # This is because price can touch from above or below
            pot = 2 * (1 - norm.cdf(std_devs))
            
        else:  # Put
            # For puts, we care about downward movement
            if strike >= spy_price:
                return 1.0  # Already ITM
                
            # Distance to strike as percentage
            distance_pct = (spy_price - strike) / spy_price
            
            # Standard deviations to strike
            std_devs = distance_pct / (volatility * np.sqrt(time_to_expiry))
            
            # Probability of touching
            pot = 2 * (1 - norm.cdf(std_devs))
            
        return min(max(pot, 0.0), 1.0)  # Ensure [0, 1]
        
    def calculate_expected_value(self,
                               premium: float,
                               strike: float,
                               spy_price: float,
                               volatility: float,
                               time_to_expiry: float,
                               option_type: str,
                               position_size: int = 1,
                               stop_loss_multiplier: float = 3.5) -> Dict[str, float]:
        """
        Calculate Expected Value of the trade
        
        EV = P(Win) * Profit_on_Win - P(Loss) * Loss_on_Loss
        
        Args:
            premium: Option premium per contract
            strike: Option strike price
            spy_price: Current SPY price
            volatility: Implied volatility
            time_to_expiry: Time to expiration in years
            option_type: 'C' or 'P'
            position_size: Number of contracts
            stop_loss_multiplier: Stop loss as multiple of premium
            
        Returns:
            Dict with EV calculations and components
        """
        # Calculate PoT
        pot = self.calculate_probability_of_touch(
            spy_price, strike, volatility, time_to_expiry, option_type
        )
        
        # Win probability (option expires worthless)
        prob_win = 1 - pot
        
        # Profit on win (keep full premium)
        profit_on_win = premium * 100 * position_size
        
        # Loss scenarios
        # 1. Hit stop loss (most likely loss scenario)
        stop_loss_price = premium * stop_loss_multiplier
        loss_at_stop = (stop_loss_price - premium) * 100 * position_size
        
        # 2. Maximum theoretical loss (option goes deep ITM)
        # For practical purposes, cap at 2x stop loss
        max_loss = loss_at_stop * 2
        
        # Weighted average loss
        # Assume 80% of losses hit stop, 20% worse
        avg_loss_on_loss = 0.8 * loss_at_stop + 0.2 * max_loss
        
        # Calculate EV
        ev = prob_win * profit_on_win - pot * avg_loss_on_loss
        
        # Calculate other useful metrics
        risk_reward_ratio = profit_on_win / loss_at_stop
        
        # Kelly Criterion for position sizing
        # f = (p * b - q) / b
        # where p = prob_win, q = prob_loss, b = odds (profit/loss ratio)
        kelly_fraction = (prob_win * risk_reward_ratio - pot) / risk_reward_ratio
        kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Cap at 25%
        
        return {
            'expected_value': ev,
            'probability_of_touch': pot,
            'win_probability': prob_win,
            'profit_on_win': profit_on_win,
            'loss_at_stop': loss_at_stop,
            'avg_loss_on_loss': avg_loss_on_loss,
            'risk_reward_ratio': risk_reward_ratio,
            'kelly_fraction': kelly_fraction,
            'ev_per_dollar_risked': ev / loss_at_stop if loss_at_stop > 0 else 0
        }
        
    def calculate_time_to_expiry(self) -> float:
        """
        Calculate time to market close for 0DTE options
        
        Returns:
            Time to expiry in years (fraction of trading year)
        """
        now = datetime.now(self.eastern)
        
        # Market close at 4 PM ET
        close_time = now.replace(hour=16, minute=0, second=0, microsecond=0)
        
        if now >= close_time:
            return 0.0
            
        # Calculate hours remaining
        time_remaining = close_time - now
        hours_remaining = time_remaining.total_seconds() / 3600
        
        # Convert to fraction of year (252 trading days, 6.5 hours per day)
        years_remaining = hours_remaining / (252 * 6.5)
        
        return years_remaining
        
    def analyze_options_chain(self,
                            options_chain: list,
                            spy_price: float,
                            action: int,
                            target_delta: float = 0.20) -> list:
        """
        Analyze entire options chain and rank by EV
        
        Args:
            options_chain: List of option contracts
            spy_price: Current SPY price
            action: 1 for calls, 2 for puts
            target_delta: Target delta for filtering
            
        Returns:
            List of analyzed options sorted by EV
        """
        option_type = 'C' if action == 1 else 'P'
        time_to_expiry = self.calculate_time_to_expiry()
        
        analyzed_options = []
        
        for opt in options_chain:
            if opt.get('type') != option_type:
                continue
                
            # Basic filtering
            bid = opt.get('bid', 0)
            ask = opt.get('ask', 0)
            if bid <= 0 or ask <= 0:
                continue
                
            mid_price = (bid + ask) / 2
            if mid_price < 0.50:  # Min premium
                continue
                
            delta = abs(opt.get('delta', 0))
            iv = opt.get('iv', 0.15)  # Default 15% if missing
            
            # Calculate PoT and EV
            stats = self.calculate_expected_value(
                premium=mid_price,
                strike=opt['strike'],
                spy_price=spy_price,
                volatility=iv,
                time_to_expiry=time_to_expiry,
                option_type=option_type
            )
            
            # Add to results
            analyzed_options.append({
                'option': opt,
                'mid_price': mid_price,
                'delta': delta,
                'iv': iv,
                **stats
            })
            
        # Sort by EV (descending)
        analyzed_options.sort(key=lambda x: x['expected_value'], reverse=True)
        
        return analyzed_options
        
    def get_market_statistics(self, vix: float) -> Dict[str, any]:
        """
        Get current market statistics and regime
        
        Args:
            vix: Current VIX level
            
        Returns:
            Market statistics and regime information
        """
        # Historical VIX percentiles (approximate)
        vix_percentiles = {
            12: 10,
            15: 25,
            18: 50,
            22: 75,
            28: 90,
            35: 95,
            40: 99
        }
        
        # Find percentile
        percentile = 0
        for level, pct in sorted(vix_percentiles.items()):
            if vix <= level:
                percentile = pct
                break
        else:
            percentile = 99
            
        # Determine regime
        if vix < 15:
            regime = "Low Volatility"
            regime_description = "Favorable for premium selling"
        elif vix < 20:
            regime = "Normal"
            regime_description = "Standard market conditions"
        elif vix < 25:
            regime = "Elevated"
            regime_description = "Increased caution advised"
        elif vix < 30:
            regime = "High Volatility"
            regime_description = "Consider smaller positions"
        else:
            regime = "Extreme"
            regime_description = "Very high risk environment"
            
        # Time of day analysis
        now = datetime.now(self.eastern)
        hour = now.hour
        
        if hour < 10:
            time_period = "Opening Hour"
            time_notes = "Higher volatility, price discovery"
        elif hour < 11:
            time_period = "Mid-Morning"
            time_notes = "Trending period"
        elif hour < 14:
            time_period = "Midday"
            time_notes = "Often lower volatility"
        elif hour < 15:
            time_period = "Early Afternoon"
            time_notes = "Volatility may increase"
        else:
            time_period = "Final Hour"
            time_notes = "Gamma risk, closing volatility"
            
        return {
            'vix_level': vix,
            'vix_percentile': percentile,
            'volatility_regime': regime,
            'regime_description': regime_description,
            'time_period': time_period,
            'time_notes': time_notes,
            'hours_to_close': self.calculate_time_to_expiry() * 252 * 6.5
        }
        
    def calculate_portfolio_metrics(self, positions: list) -> Dict[str, float]:
        """
        Calculate portfolio-level risk metrics
        
        Args:
            positions: List of current positions
            
        Returns:
            Portfolio metrics
        """
        if not positions:
            return {
                'total_delta': 0,
                'total_gamma': 0,
                'total_theta': 0,
                'total_vega': 0,
                'max_loss': 0,
                'expected_portfolio_ev': 0
            }
            
        total_delta = sum(p.get('delta', 0) * p.get('quantity', 0) * 100 for p in positions)
        total_gamma = sum(p.get('gamma', 0) * p.get('quantity', 0) * 100 for p in positions)
        total_theta = sum(p.get('theta', 0) * p.get('quantity', 0) * 100 for p in positions)
        total_vega = sum(p.get('vega', 0) * p.get('quantity', 0) * 100 for p in positions)
        
        # Calculate max loss (sum of individual stop losses)
        max_loss = sum(
            p.get('premium', 0) * 3.5 * p.get('quantity', 0) * 100 
            for p in positions
        )
        
        # Sum individual EVs
        total_ev = sum(p.get('expected_value', 0) for p in positions)
        
        return {
            'total_delta': total_delta,
            'total_gamma': total_gamma,
            'total_theta': total_theta,
            'total_vega': total_vega,
            'max_loss': max_loss,
            'expected_portfolio_ev': total_ev,
            'net_greek_exposure': abs(total_delta) + abs(total_gamma) * 10
        }