"""
Feature engineering service that converts raw market data to model features
Maintains same feature structure as training data
"""
import numpy as np
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple
import logging


class PositionTracker:
    """Tracks current trading positions and P&L"""
    
    def __init__(self):
        self.positions = []
        self.entry_time = None
        self.entry_price = None
        self.position_type = None  # 'call' or 'put'
        self.contracts = 0
        self.strike = None
        
    def open_position(self, position_type: str, strike: float, 
                     contracts: int, entry_price: float):
        """Record new position"""
        self.position_type = position_type
        self.strike = strike
        self.contracts = contracts
        self.entry_price = entry_price
        self.entry_time = datetime.now()
        
        self.positions.append({
            'type': position_type,
            'strike': strike,
            'contracts': contracts,
            'entry_price': entry_price,
            'entry_time': self.entry_time
        })
        
    def close_position(self, exit_price: float):
        """Close current position"""
        if not self.has_position():
            return 0
            
        # Calculate P&L (for short options)
        pnl = (self.entry_price - exit_price) * 100 * self.contracts
        
        # Reset
        self.position_type = None
        self.strike = None
        self.contracts = 0
        self.entry_price = None
        self.entry_time = None
        
        return pnl
        
    def has_position(self) -> bool:
        """Check if currently in position"""
        return self.contracts > 0
        
    def get_current_pnl(self, current_price: float) -> float:
        """Calculate unrealized P&L"""
        if not self.has_position():
            return 0
            
        return (self.entry_price - current_price) * 100 * self.contracts
        
    def get_time_in_position(self) -> float:
        """Get minutes in current position"""
        if not self.entry_time:
            return 0
            
        return (datetime.now() - self.entry_time).seconds / 60
        
    def get_state(self) -> dict:
        """Get current position state"""
        return {
            'has_position': 1 if self.has_position() else 0,
            'pnl': self.get_current_pnl(0),  # Will be updated with real price
            'time_held': self.get_time_in_position(),
            'type': self.position_type,
            'strike': self.strike,
            'contracts': self.contracts
        }


class FeatureEngine:
    """Converts raw market data to AI model features"""
    
    def __init__(self, position_tracker: Optional[PositionTracker] = None):
        self.position_tracker = position_tracker or PositionTracker()
        
        # Market hours
        self.market_open = time(9, 30)
        self.market_close = time(16, 0)
        
        # Risk parameters (matching training)
        self.risk_thresholds = {
            'low': 0.2,
            'medium': 0.5,
            'high': 0.8
        }
        
        self.logger = logging.getLogger(__name__)
        
    def get_model_features(self, market_data: dict) -> np.ndarray:
        """
        Convert market data to 8-feature vector expected by model:
        0: minutes_since_open / 390
        1: spot_price / 1000
        2: atm_iv
        3: has_position
        4: position_pnl / 1000
        5: time_in_position / 390
        6: risk_score
        7: minutes_until_close / 390
        
        NOTE: Temporarily reverted to 8 features for model compatibility
        TODO: Retrain model with 12 features including moneyness for exercise prevention
        """
        # Time features
        now = datetime.now()
        minutes_since_open = self._calculate_minutes_since_open(now)
        minutes_until_close = 390 - minutes_since_open
        
        # Market features
        spy_price = market_data['spy_price']
        atm_iv = self._calculate_atm_iv(market_data['options_chain'], spy_price)
        
        # Position features
        position_state = self.position_tracker.get_state()
        
        # Update P&L with current option price if in position
        if position_state['has_position']:
            current_opt_price = self._get_current_option_price(
                market_data['options_chain'],
                position_state['strike'],
                position_state['type']
            )
            position_state['pnl'] = self.position_tracker.get_current_pnl(current_opt_price)
        
        # Risk score
        risk_score = self._calculate_risk_score(
            position_state,
            market_data,
            minutes_since_open
        )
        
        # Calculate moneyness (exercise risk indicator) - STILL CALCULATE BUT DON'T INCLUDE
        moneyness = 0.0
        if position_state['has_position'] and position_state['strike']:
            strike = position_state['strike']
            if position_state['type'] == 'call':
                # For calls: positive when ITM (spy > strike)
                moneyness = (spy_price - strike) / strike
            elif position_state['type'] == 'put':
                # For puts: positive when ITM (spy < strike)
                moneyness = (strike - spy_price) / strike
        
        # Store for exercise prevention logic (not in features yet)
        self._last_moneyness = moneyness
        self._hours_to_expiry = minutes_until_close / 60.0
        
        # Build feature vector (8 features only for compatibility)
        features = np.array([
            minutes_since_open / 390,
            spy_price / 1000,
            atm_iv,
            position_state['has_position'],
            position_state['pnl'] / 1000,
            position_state['time_held'] / 390,
            risk_score,
            minutes_until_close / 390
        ], dtype=np.float32)
        
        # Validate features
        features = self._validate_features(features)
        
        return features
        
    def _calculate_minutes_since_open(self, current_time: datetime) -> float:
        """Calculate minutes since market open"""
        market_open_today = current_time.replace(
            hour=self.market_open.hour,
            minute=self.market_open.minute,
            second=0,
            microsecond=0
        )
        
        if current_time < market_open_today:
            return 0
            
        minutes = (current_time - market_open_today).seconds / 60
        return min(minutes, 390)  # Cap at market hours
        
    def _calculate_atm_iv(self, options_chain: List[dict], spy_price: float = None) -> float:
        """Calculate at-the-money implied volatility"""
        if not options_chain:
            return 0.15  # Default IV
            
        # Group by strike
        strikes = {}
        for opt in options_chain:
            strike = opt['strike']
            if strike not in strikes:
                strikes[strike] = {}
            strikes[strike][opt['type']] = opt
            
        # Find ATM strike (closest to current price)
        if spy_price is None:
            # Estimate from strikes if not provided
            spy_price = sum(opt['strike'] for opt in options_chain) / len(options_chain) if options_chain else 500
        
        # For now, use the first complete strike pair
        for strike, opts in sorted(strikes.items()):
            if 'C' in opts and 'P' in opts:
                call_iv = opts['C']['iv']
                put_iv = opts['P']['iv']
                return (call_iv + put_iv) / 2
                
        return 0.15  # Default if no complete pairs
        
    def _get_current_option_price(self, options_chain: List[dict], 
                                 strike: float, opt_type: str) -> float:
        """Get current price for specific option"""
        for opt in options_chain:
            if opt['strike'] == strike and opt['type'] == opt_type.upper()[0]:
                # Use mid price
                return (opt['bid'] + opt['ask']) / 2
        return 0
        
    def _calculate_risk_score(self, position_state: dict, 
                            market_data: dict, 
                            minutes_since_open: float) -> float:
        """
        Calculate risk score (0-1) based on:
        - Position size
        - Time of day
        - Market volatility
        - P&L status
        """
        risk_factors = []
        
        # Position risk
        if position_state['has_position']:
            # Risk increases with position size
            contracts = position_state['contracts']
            if contracts >= 30:
                risk_factors.append(0.8)
            elif contracts >= 20:
                risk_factors.append(0.5)
            elif contracts >= 10:
                risk_factors.append(0.3)
            else:
                risk_factors.append(0.2)
                
            # Risk from P&L
            pnl = position_state['pnl']
            if pnl < -500:  # Large loss
                risk_factors.append(0.9)
            elif pnl < -200:
                risk_factors.append(0.6)
                
        # Time risk (avoid first/last 30 min)
        if minutes_since_open < 30 or minutes_since_open > 360:
            risk_factors.append(0.7)
            
        # Volatility risk (from IV)
        atm_iv = self._calculate_atm_iv(market_data['options_chain'])
        if atm_iv > 0.25:  # High IV
            risk_factors.append(0.6)
        elif atm_iv < 0.10:  # Very low IV
            risk_factors.append(0.4)
            
        # Average risk factors
        if risk_factors:
            risk_score = np.mean(risk_factors)
        else:
            risk_score = 0.2  # Base risk
            
        return np.clip(risk_score, 0, 1)
        
    def _validate_features(self, features: np.ndarray) -> np.ndarray:
        """Ensure features are in valid ranges"""
        # All features should be in [0, 1] except position_pnl
        features[0] = np.clip(features[0], 0, 1)  # time
        features[1] = np.clip(features[1], 0, 2)  # price (allow some room)
        features[2] = np.clip(features[2], 0, 1)  # IV
        features[3] = np.clip(features[3], 0, 1)  # has_position
        # features[4] is P&L, can be negative
        features[5] = np.clip(features[5], 0, 1)  # time in position
        features[6] = np.clip(features[6], 0, 1)  # risk
        features[7] = np.clip(features[7], 0, 1)  # time until close
        
        # Check for NaN
        if np.any(np.isnan(features)):
            self.logger.warning(f"NaN detected in features: {features}")
            features = np.nan_to_num(features, nan=0.5)
            
        return features
        
    def get_feature_names(self) -> List[str]:
        """Get feature names for debugging"""
        return [
            'minutes_since_open_norm',
            'spy_price_norm',
            'atm_iv',
            'has_position',
            'position_pnl_norm',
            'time_in_position_norm',
            'risk_score',
            'minutes_until_close_norm'
        ]
        
    def features_to_dict(self, features: np.ndarray) -> dict:
        """Convert feature vector to named dict for logging"""
        names = self.get_feature_names()
        return {name: float(features[i]) for i, name in enumerate(names)}
    
    def get_exercise_risk_metrics(self) -> dict:
        """Get exercise risk metrics (calculated but not in feature vector yet)"""
        return {
            'moneyness': getattr(self, '_last_moneyness', 0.0),
            'hours_to_expiry': getattr(self, '_hours_to_expiry', 6.5)
        }


# Example usage and testing
if __name__ == "__main__":
    # Create mock market data
    mock_market_data = {
        'spy_price': 628.50,
        'spy_bid': 628.45,
        'spy_ask': 628.55,
        'options_chain': [
            {
                'strike': 628,
                'type': 'C',
                'bid': 2.45,
                'ask': 2.55,
                'iv': 0.15
            },
            {
                'strike': 628,
                'type': 'P',
                'bid': 2.35,
                'ask': 2.45,
                'iv': 0.16
            }
        ]
    }
    
    # Test feature engineering
    engine = FeatureEngine()
    features = engine.get_model_features(mock_market_data)
    
    print("Feature vector:", features)
    print("\nNamed features:")
    for name, value in engine.features_to_dict(features).items():
        print(f"  {name}: {value:.4f}")