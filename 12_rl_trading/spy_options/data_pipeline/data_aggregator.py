"""
Data aggregator for converting real-time streaming data to 5-minute bars
Maintains consistency with RL model training data
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np


class DataAggregator:
    """Aggregates real-time data into 5-minute OHLCV bars"""
    
    def __init__(self, interval_minutes: int = 5):
        self.interval_minutes = interval_minutes
        self.logger = logging.getLogger(__name__)
        
        # Current bar being built
        self.current_bar = None
        self.bar_start_time = None
        
        # Historical bars (for feature calculation)
        self.historical_bars = []  # List of completed bars
        self.max_bars = 100  # Keep last 100 bars
        
        # Price tracking for current bar
        self.prices_in_bar = []
        self.volumes_in_bar = []
        
    def update(self, price: float, volume: int = 0, timestamp: datetime = None) -> Optional[Dict]:
        """
        Update with new price tick
        Returns completed bar when interval ends, None otherwise
        """
        if timestamp is None:
            timestamp = datetime.now()
            
        # Check if we need to start a new bar
        if self._should_start_new_bar(timestamp):
            completed_bar = self._close_current_bar()
            self._start_new_bar(timestamp)
            
            # Add price to new bar
            self.prices_in_bar.append(price)
            self.volumes_in_bar.append(volume)
            
            return completed_bar
        else:
            # Add to current bar
            self.prices_in_bar.append(price)
            self.volumes_in_bar.append(volume)
            
            # Update current bar
            if self.current_bar:
                self.current_bar['high'] = max(self.current_bar['high'], price)
                self.current_bar['low'] = min(self.current_bar['low'], price)
                self.current_bar['close'] = price
                self.current_bar['volume'] += volume
                
            return None
            
    def _should_start_new_bar(self, timestamp: datetime) -> bool:
        """Check if we should start a new bar"""
        if self.bar_start_time is None:
            return True
            
        # Calculate bar end time
        bar_end_time = self.bar_start_time + timedelta(minutes=self.interval_minutes)
        return timestamp >= bar_end_time
        
    def _start_new_bar(self, timestamp: datetime):
        """Start a new bar"""
        # Round down to nearest interval
        minutes = timestamp.minute
        rounded_minutes = (minutes // self.interval_minutes) * self.interval_minutes
        
        self.bar_start_time = timestamp.replace(
            minute=rounded_minutes,
            second=0,
            microsecond=0
        )
        
        self.current_bar = {
            'timestamp': self.bar_start_time,
            'open': 0,
            'high': 0,
            'low': float('inf'),
            'close': 0,
            'volume': 0
        }
        
        self.prices_in_bar = []
        self.volumes_in_bar = []
        
    def _close_current_bar(self) -> Optional[Dict]:
        """Close current bar and return it"""
        if self.current_bar is None or not self.prices_in_bar:
            return None
            
        # Finalize bar
        self.current_bar['open'] = self.prices_in_bar[0]
        self.current_bar['close'] = self.prices_in_bar[-1]
        self.current_bar['high'] = max(self.prices_in_bar)
        self.current_bar['low'] = min(self.prices_in_bar)
        self.current_bar['volume'] = sum(self.volumes_in_bar)
        
        # Add to history
        self.historical_bars.append(self.current_bar)
        
        # Trim history
        if len(self.historical_bars) > self.max_bars:
            self.historical_bars = self.historical_bars[-self.max_bars:]
            
        self.logger.info(f"Completed 5-min bar: O={self.current_bar['open']:.2f} "
                        f"H={self.current_bar['high']:.2f} L={self.current_bar['low']:.2f} "
                        f"C={self.current_bar['close']:.2f} V={self.current_bar['volume']}")
        
        return self.current_bar
        
    def get_latest_bars(self, num_bars: int = 20) -> List[Dict]:
        """Get latest completed bars"""
        if not self.historical_bars:
            return []
            
        return self.historical_bars[-num_bars:]
        
    def calculate_features(self) -> Dict[str, float]:
        """Calculate features from aggregated data (matching RL model features)"""
        if len(self.historical_bars) < 2:
            return {}
            
        # Get recent bars
        recent_bars = self.get_latest_bars(20)
        
        if len(recent_bars) < 2:
            return {}
            
        # Calculate returns
        prices = [bar['close'] for bar in recent_bars]
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        
        # Calculate features
        features = {
            'price_return_5m': returns[-1] if returns else 0,
            'price_return_15m': sum(returns[-3:]) if len(returns) >= 3 else 0,
            'price_return_30m': sum(returns[-6:]) if len(returns) >= 6 else 0,
            'volume_ratio': self._calculate_volume_ratio(recent_bars),
            'momentum_5m': self._calculate_momentum(prices, 1),
            'momentum_15m': self._calculate_momentum(prices, 3),
            'volatility_5m': np.std(returns[-1:]) if len(returns) >= 1 else 0,
            'volatility_15m': np.std(returns[-3:]) if len(returns) >= 3 else 0,
        }
        
        return features
        
    def calculate_rl_features(self, current_time: datetime = None) -> List[float]:
        """Calculate the 8-feature vector expected by the RL model"""
        if current_time is None:
            current_time = datetime.now()
            
        # Feature 0: Time progress (0-1, market open to close)
        market_open = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = current_time.replace(hour=16, minute=0, second=0, microsecond=0)
        
        if current_time < market_open:
            time_progress = 0.0
        elif current_time > market_close:
            time_progress = 1.0
        else:
            total_seconds = (market_close - market_open).total_seconds()
            elapsed_seconds = (current_time - market_open).total_seconds()
            time_progress = elapsed_seconds / total_seconds
            
        # Get recent bars for calculations
        recent_bars = self.get_latest_bars(20)
        
        if len(recent_bars) < 2:
            # Return default features if insufficient data
            return [time_progress, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            
        prices = [bar['close'] for bar in recent_bars]
        volumes = [bar['volume'] for bar in recent_bars]
        
        # Calculate returns
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        
        # Feature 1: Recent price return (5-minute)
        price_return_5m = returns[-1] if returns else 0.0
        
        # Feature 2: Medium-term return (15-minute, last 3 bars)
        price_return_15m = sum(returns[-3:]) if len(returns) >= 3 else (returns[-1] if returns else 0.0)
        
        # Feature 3: Longer-term return (30-minute, last 6 bars)
        price_return_30m = sum(returns[-6:]) if len(returns) >= 6 else price_return_15m
        
        # Feature 4: Volume ratio (current vs average)
        avg_volume = np.mean(volumes[:-1]) if len(volumes) > 1 else volumes[-1]
        volume_ratio = volumes[-1] / avg_volume if avg_volume > 0 else 1.0
        
        # Feature 5: Short-term volatility
        volatility_5m = np.std(returns[-1:]) if len(returns) >= 1 else 0.0
        
        # Feature 6: Medium-term volatility
        volatility_15m = np.std(returns[-3:]) if len(returns) >= 3 else volatility_5m
        
        # Feature 7: Risk score (combination of volatility and time)
        # Higher risk during market open/close and high volatility periods
        time_risk = abs(time_progress - 0.5) * 2  # Higher at open/close
        vol_risk = min(volatility_15m * 10, 1.0)  # Cap at 1.0
        risk_score = (time_risk + vol_risk) / 2
        
        features = [
            time_progress,
            price_return_5m,
            price_return_15m, 
            price_return_30m,
            volume_ratio,
            volatility_5m,
            volatility_15m,
            risk_score
        ]
        
        return features
        
    def _calculate_volume_ratio(self, bars: List[Dict]) -> float:
        """Calculate volume ratio vs average"""
        if len(bars) < 2:
            return 1.0
            
        volumes = [bar['volume'] for bar in bars]
        avg_volume = np.mean(volumes[:-1]) if len(volumes) > 1 else volumes[0]
        
        if avg_volume > 0:
            return volumes[-1] / avg_volume
        return 1.0
        
    def _calculate_momentum(self, prices: List[float], periods: int) -> float:
        """Calculate price momentum"""
        if len(prices) < periods + 1:
            return 0
            
        return (prices[-1] - prices[-(periods+1)]) / prices[-(periods+1)]
        
    def get_current_price(self) -> float:
        """Get most recent price"""
        if self.prices_in_bar:
            return self.prices_in_bar[-1]
        elif self.historical_bars:
            return self.historical_bars[-1]['close']
        return 0
    
    def get_latest_bar(self) -> Optional[Dict]:
        """Get the most recent completed bar with JSON-serializable format"""
        if not self.historical_bars:
            return None
        
        # Get the latest bar and convert datetime to string
        latest_bar = self.historical_bars[-1].copy()
        
        # Convert timestamp to ISO format string for JSON serialization
        if 'timestamp' in latest_bar and isinstance(latest_bar['timestamp'], datetime):
            latest_bar['timestamp'] = latest_bar['timestamp'].isoformat()
        
        return latest_bar