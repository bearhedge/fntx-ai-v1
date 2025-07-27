"""
Risk Assessment Module
Calculates market risk levels using 5 technical indicators
"""
import numpy as np
import pandas as pd
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class RiskAssessment:
    """
    Calculates risk levels (LOW, MEDIUM, HIGH) based on technical indicators
    """
    
    def __init__(self):
        self.risk_thresholds = {
            'LOW': (0, 2),      # 0-2 risk points
            'MEDIUM': (3, 5),   # 3-5 risk points  
            'HIGH': (6, 10)     # 6+ risk points
        }
        
    def calculate_risk_level(self, market_data: Dict) -> Tuple[str, int, Dict]:
        """
        Calculate current market risk level
        
        Args:
            market_data: Dictionary containing market indicators
            
        Returns:
            Tuple of (risk_level, risk_score, indicators_detail)
        """
        risk_points = 0
        indicators_detail = {}
        
        # 1. ATR Ratio (volatility expansion)
        atr_ratio = market_data.get('atr', 0) / market_data.get('atr_20d_avg', 1)
        if atr_ratio > 1.5:
            risk_points += 2
            indicators_detail['atr_ratio'] = {'value': atr_ratio, 'triggered': True}
        else:
            indicators_detail['atr_ratio'] = {'value': atr_ratio, 'triggered': False}
            
        # 2. RSI (momentum extremes)
        rsi = market_data.get('rsi', 50)
        if rsi < 30 or rsi > 70:
            risk_points += 1
            indicators_detail['rsi'] = {'value': rsi, 'triggered': True}
        else:
            indicators_detail['rsi'] = {'value': rsi, 'triggered': False}
            
        # 3. Trend Strength (SMA divergence)
        sma10 = market_data.get('spy_sma_10', 400)
        sma30 = market_data.get('spy_sma_30', 400)
        trend_strength = abs(sma10 - sma30) / sma30 if sma30 > 0 else 0
        
        if trend_strength > 0.02:  # 2% divergence
            risk_points += 1
            indicators_detail['trend_strength'] = {'value': trend_strength, 'triggered': True}
        else:
            indicators_detail['trend_strength'] = {'value': trend_strength, 'triggered': False}
            
        # 4. Put/Call Ratio (market fear)
        put_call_ratio = market_data.get('put_call_ratio', 1.0)
        if put_call_ratio > 1.5:
            risk_points += 2
            indicators_detail['put_call_ratio'] = {'value': put_call_ratio, 'triggered': True}
        else:
            indicators_detail['put_call_ratio'] = {'value': put_call_ratio, 'triggered': False}
            
        # 5. VIX Level (overall fear gauge)
        vix = market_data.get('vix', 20)
        if vix > 25:
            risk_points += 2
            indicators_detail['vix'] = {'value': vix, 'triggered': True}
        else:
            indicators_detail['vix'] = {'value': vix, 'triggered': False}
            
        # Determine risk level
        risk_level = self._get_risk_level(risk_points)
        
        logger.info(f"Risk Assessment: {risk_level} (score: {risk_points})")
        
        return risk_level, risk_points, indicators_detail
        
    def _get_risk_level(self, risk_points: int) -> str:
        """Map risk points to risk level"""
        if risk_points <= 2:
            return 'LOW'
        elif risk_points <= 5:
            return 'MEDIUM'
        else:
            return 'HIGH'
            
    def calculate_technical_indicators(self, price_data: pd.DataFrame, 
                                     lookback_days: int = 30) -> Dict:
        """
        Calculate technical indicators from price data
        
        Args:
            price_data: DataFrame with OHLC data
            lookback_days: Days to look back for indicators
            
        Returns:
            Dictionary of calculated indicators
        """
        if len(price_data) < lookback_days:
            logger.warning(f"Insufficient data for {lookback_days} day lookback")
            return self._get_default_indicators()
            
        # Calculate ATR (Average True Range)
        high_low = price_data['high'] - price_data['low']
        high_close = abs(price_data['high'] - price_data['close'].shift(1))
        low_close = abs(price_data['low'] - price_data['close'].shift(1))
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=14).mean().iloc[-1]
        atr_20d = tr.rolling(window=20).mean().iloc[-1]
        
        # Calculate RSI
        close_prices = price_data['close']
        delta = close_prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        # Calculate SMAs
        sma_10 = close_prices.rolling(window=10).mean().iloc[-1]
        sma_30 = close_prices.rolling(window=30).mean().iloc[-1]
        
        # Current price
        current_price = close_prices.iloc[-1]
        
        return {
            'atr': atr,
            'atr_20d_avg': atr_20d,
            'rsi': rsi,
            'spy_sma_10': sma_10,
            'spy_sma_30': sma_30,
            'current_price': current_price
        }
        
    def _get_default_indicators(self) -> Dict:
        """Return default neutral indicators"""
        return {
            'atr': 2.0,
            'atr_20d_avg': 2.0,
            'rsi': 50.0,
            'spy_sma_10': 400.0,
            'spy_sma_30': 400.0,
            'current_price': 400.0
        }
        
    def get_risk_parameters(self, risk_level: str) -> Dict:
        """
        Get trading parameters based on risk level
        
        Returns:
            Dictionary with stop_multiple, wait_hours, max_position_pct
        """
        from config import RISK_LEVELS
        return RISK_LEVELS.get(risk_level, RISK_LEVELS['MEDIUM'])