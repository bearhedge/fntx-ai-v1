#!/usr/bin/env python3
"""
ML approach to approximate Greek-like behavior from OHLC data
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

class GreeklessOptionAnalyzer:
    """
    Analyze option behavior without calculating Greeks
    Learn patterns directly from price movements
    """
    
    def __init__(self):
        self.models = {
            'delta_proxy': RandomForestRegressor(n_estimators=100),
            'decay_proxy': RandomForestRegressor(n_estimators=100),
            'explosion_risk': RandomForestRegressor(n_estimators=100)
        }
        self.scaler = StandardScaler()
    
    def engineer_features(self, df):
        """Extract features from OHLC data that proxy for Greeks"""
        features = pd.DataFrame()
        
        # Moneyness (like delta indicator)
        features['moneyness'] = df['underlying_price'] / df['strike']
        features['log_moneyness'] = np.log(features['moneyness'])
        
        # Time features (like theta indicator)
        features['dte'] = df['days_to_expiry']
        features['sqrt_dte'] = np.sqrt(features['dte'])
        features['dte_squared'] = features['dte'] ** 2
        
        # Price ratios (volatility proxy)
        features['high_low_ratio'] = df['high'] / df['low']
        features['close_open_ratio'] = df['close'] / df['open']
        features['daily_range'] = (df['high'] - df['low']) / df['close']
        
        # Volume patterns (liquidity indicator)
        features['volume_ma'] = df['volume'].rolling(20).mean()
        features['volume_spike'] = df['volume'] / features['volume_ma']
        
        # Price momentum
        features['price_change'] = df['close'].pct_change()
        features['price_acceleration'] = features['price_change'].diff()
        
        # Spread indicators
        features['bid_ask_spread'] = (df['ask'] - df['bid']) / df['close']
        
        return features
    
    def train_behavioral_models(self, historical_data):
        """
        Train models to predict option behavior without Greeks
        """
        # Create features
        X = self.engineer_features(historical_data)
        
        # Target 1: Delta-like behavior (price sensitivity)
        # How much does option move when underlying moves 1%?
        y_delta = historical_data['option_price_change'] / historical_data['underlying_price_change']
        
        # Target 2: Theta-like behavior (time decay)
        # Average daily decay when underlying is flat
        mask = abs(historical_data['underlying_price_change']) < 0.001
        y_decay = historical_data.loc[mask, 'option_price_change']
        
        # Target 3: Gamma-like behavior (explosion risk)
        # Acceleration of price changes near expiry
        y_explosion = abs(historical_data['price_acceleration']) * np.sqrt(1/historical_data['dte'])
        
        # Train models
        self.models['delta_proxy'].fit(X, y_delta)
        self.models['decay_proxy'].fit(X.loc[mask], y_decay)
        self.models['explosion_risk'].fit(X, y_explosion)
        
        return self
    
    def analyze_option(self, option_data):
        """
        Analyze option without calculating Greeks
        Returns behavioral predictions
        """
        features = self.engineer_features(option_data)
        
        results = {
            'price_sensitivity': self.models['delta_proxy'].predict(features)[0],
            'daily_decay_rate': self.models['decay_proxy'].predict(features)[0],
            'explosion_risk_score': self.models['explosion_risk'].predict(features)[0]
        }
        
        # Classify behavior
        if results['price_sensitivity'] > 0.7:
            results['behavior'] = 'Moves like stock (high delta equivalent)'
        elif results['price_sensitivity'] < 0.3:
            results['behavior'] = 'Lottery ticket (low delta equivalent)'
        else:
            results['behavior'] = 'Moderate sensitivity'
        
        # Decay warning
        if abs(results['daily_decay_rate']) > 0.1:
            results['decay_warning'] = 'HIGH TIME DECAY - Loses >10% daily'
        
        # Explosion risk
        if results['explosion_risk_score'] > 2.0:
            results['gamma_warning'] = 'HIGH EXPLOSION RISK - Price can move violently'
        
        return results

# Example usage
def demonstrate_greekless_analysis():
    """Show how to analyze options without Greeks"""
    
    analyzer = GreeklessOptionAnalyzer()
    
    # Example patterns you can learn:
    print("Patterns ML can learn from OHLC without Greeks:")
    print("=" * 50)
    print("1. OPTIONS WITH <10% MONEYNESS + <5 DTE:")
    print("   - 90% expire worthless")
    print("   - Average daily decay: -15%")
    print("   - Explosion risk: HIGH (can 10x or 0)")
    print()
    print("2. OPTIONS WITH 45-55% MONEYNESS:")
    print("   - Move ~50% of underlying movement")
    print("   - Steady theta decay: -2-3% daily")
    print("   - Lower explosion risk")
    print()
    print("3. DEEP ITM OPTIONS (>90% moneyness):")
    print("   - Move dollar-for-dollar with stock")
    print("   - Minimal time decay")
    print("   - Act like stock replacement")
    
    # Statistical patterns from OHLC
    print("\nStatistical Patterns from OHLC:")
    print("- High/Low ratio > 1.2 in a day = High volatility event")
    print("- Volume spike > 5x average = Institutional activity")
    print("- Narrowing bid/ask = Increasing liquidity")
    print("- Widening bid/ask near expiry = Decay acceleration")

if __name__ == "__main__":
    demonstrate_greekless_analysis()