"""
Market Data Collector
Real-time market data collection and processing.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Callable
from datetime import datetime, timedelta
from collections import deque
import json

from ..mcp.context_manager import MCPContextManager
from ..mcp.schemas import MemorySlice, MemoryType, MemoryImportance
from ..services.ibkr_service import IBKRService
from .schemas import (
    MarketDataPoint, MarketSnapshot, TechnicalIndicators,
    MarketRegime, VolatilityRegime, RegimeAnalysis
)

logger = logging.getLogger(__name__)


class MarketDataCollector:
    """
    Collects and processes real-time market data.
    """
    
    def __init__(self, mcp_manager: MCPContextManager, ibkr_service: Optional[IBKRService] = None):
        self.mcp = mcp_manager
        self.ibkr = ibkr_service
        
        # Data storage
        self.market_data: Dict[str, deque] = {
            'SPY': deque(maxlen=10000),  # Store last 10k data points
            'VIX': deque(maxlen=10000),
            'DXY': deque(maxlen=10000),
            'TNX': deque(maxlen=10000),
            'GLD': deque(maxlen=10000)
        }
        
        # Technical indicators cache
        self.indicators_cache: Dict[str, TechnicalIndicators] = {}
        
        # Subscription tracking
        self.subscriptions: Set[str] = set()
        self.callbacks: Dict[str, List[Callable]] = {}
        
        # Processing state
        self.processing_interval = 1.0  # Process every second
        self._processing_task: Optional[asyncio.Task] = None
        self._collection_task: Optional[asyncio.Task] = None
        
        # Market hours tracking
        self.market_open = False
        self.extended_hours = False
        
    async def initialize(self) -> None:
        """Initialize the market data collector."""
        # Register with MCP
        await self.mcp.register_agent(
            "MarketDataCollector",
            ["market_data_collection", "technical_analysis", "real_time_processing"]
        )
        
        # Start collection and processing
        self._collection_task = asyncio.create_task(self._collect_market_data())
        self._processing_task = asyncio.create_task(self._process_market_data())
        
        logger.info("Market Data Collector initialized")
        
    async def shutdown(self) -> None:
        """Shutdown the collector."""
        # Cancel tasks
        if self._collection_task:
            self._collection_task.cancel()
        if self._processing_task:
            self._processing_task.cancel()
            
        # Wait for tasks to complete
        await asyncio.gather(
            self._collection_task,
            self._processing_task,
            return_exceptions=True
        )
        
        logger.info("Market Data Collector shut down")
        
    # Data Collection
    
    async def subscribe(self, symbol: str, callback: Optional[Callable] = None) -> bool:
        """
        Subscribe to real-time data for a symbol.
        
        Args:
            symbol: Symbol to subscribe to
            callback: Optional callback for data updates
            
        Returns:
            Success status
        """
        try:
            self.subscriptions.add(symbol)
            
            if callback:
                if symbol not in self.callbacks:
                    self.callbacks[symbol] = []
                self.callbacks[symbol].append(callback)
                
            # Initialize data storage if needed
            if symbol not in self.market_data:
                self.market_data[symbol] = deque(maxlen=10000)
                
            logger.info(f"Subscribed to {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe to {symbol}: {e}")
            return False
            
    async def unsubscribe(self, symbol: str) -> bool:
        """Unsubscribe from a symbol."""
        try:
            self.subscriptions.discard(symbol)
            self.callbacks.pop(symbol, None)
            
            logger.info(f"Unsubscribed from {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe from {symbol}: {e}")
            return False
            
    async def get_latest_data(self, symbol: str) -> Optional[MarketDataPoint]:
        """Get latest data for a symbol."""
        data_queue = self.market_data.get(symbol)
        if data_queue and len(data_queue) > 0:
            return data_queue[-1]
        return None
        
    async def get_market_snapshot(self) -> MarketSnapshot:
        """Get current market snapshot."""
        # Get latest data points
        spy_data = await self.get_latest_data('SPY')
        vix_data = await self.get_latest_data('VIX')
        
        if not spy_data or not vix_data:
            # Create dummy data if not available
            spy_data = MarketDataPoint(symbol='SPY', price=0.0)
            vix_data = MarketDataPoint(symbol='VIX', price=0.0)
            
        snapshot = MarketSnapshot(
            spy=spy_data,
            vix=vix_data,
            dxy=await self.get_latest_data('DXY'),
            tnx=await self.get_latest_data('TNX'),
            gld=await self.get_latest_data('GLD')
        )
        
        # Add market internals if available
        if self.ibkr:
            try:
                # Get market breadth data
                # This would be implemented with actual IBKR API calls
                pass
            except:
                pass
                
        return snapshot
        
    # Technical Analysis
    
    async def calculate_technical_indicators(self, symbol: str) -> Optional[TechnicalIndicators]:
        """
        Calculate technical indicators for a symbol.
        
        Args:
            symbol: Symbol to analyze
            
        Returns:
            Technical indicators if calculated
        """
        try:
            data_queue = self.market_data.get(symbol, deque())
            if len(data_queue) < 200:  # Need enough data for indicators
                return None
                
            # Convert to lists for calculation
            prices = [d.price for d in data_queue]
            volumes = [d.volume or 0 for d in data_queue]
            
            # Calculate indicators
            indicators = TechnicalIndicators(symbol=symbol)
            
            # Moving averages
            if len(prices) >= 20:
                indicators.sma_20 = sum(prices[-20:]) / 20
            if len(prices) >= 50:
                indicators.sma_50 = sum(prices[-50:]) / 50
            if len(prices) >= 200:
                indicators.sma_200 = sum(prices[-200:]) / 200
                
            # RSI calculation
            if len(prices) >= 14:
                indicators.rsi = self._calculate_rsi(prices, 14)
                
            # ATR calculation
            if len(data_queue) >= 14:
                indicators.atr = self._calculate_atr(data_queue, 14)
                
            # Bollinger Bands
            if len(prices) >= 20:
                bb_data = self._calculate_bollinger_bands(prices, 20, 2)
                indicators.bollinger_upper = bb_data['upper']
                indicators.bollinger_middle = bb_data['middle']
                indicators.bollinger_lower = bb_data['lower']
                
            # Support/Resistance
            if len(data_queue) >= 1:
                latest = data_queue[-1]
                pivot_data = self._calculate_pivot_points(latest)
                indicators.pivot_point = pivot_data['pivot']
                indicators.resistance_1 = pivot_data['r1']
                indicators.resistance_2 = pivot_data['r2']
                indicators.support_1 = pivot_data['s1']
                indicators.support_2 = pivot_data['s2']
                
            # Cache the result
            self.indicators_cache[symbol] = indicators
            
            return indicators
            
        except Exception as e:
            logger.error(f"Failed to calculate indicators for {symbol}: {e}")
            return None
            
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index."""
        if len(prices) < period + 1:
            return 50.0  # Neutral
            
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
                
        # Calculate initial averages
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        # Calculate subsequent averages
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
        if avg_loss == 0:
            return 100.0
            
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
        
    def _calculate_atr(self, data: deque, period: int = 14) -> float:
        """Calculate Average True Range."""
        if len(data) < period + 1:
            return 0.0
            
        true_ranges = []
        
        for i in range(1, len(data)):
            high = data[i].high or data[i].price
            low = data[i].low or data[i].price
            prev_close = data[i-1].close or data[i-1].price
            
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            
            true_ranges.append(max(tr1, tr2, tr3))
            
        if len(true_ranges) >= period:
            return sum(true_ranges[-period:]) / period
            
        return 0.0
        
    def _calculate_bollinger_bands(self, prices: List[float], period: int = 20, 
                                  std_dev: float = 2) -> Dict[str, float]:
        """Calculate Bollinger Bands."""
        if len(prices) < period:
            return {'upper': 0, 'middle': 0, 'lower': 0}
            
        # Calculate SMA
        sma = sum(prices[-period:]) / period
        
        # Calculate standard deviation
        variance = sum((p - sma) ** 2 for p in prices[-period:]) / period
        std = variance ** 0.5
        
        return {
            'upper': sma + (std_dev * std),
            'middle': sma,
            'lower': sma - (std_dev * std)
        }
        
    def _calculate_pivot_points(self, data: MarketDataPoint) -> Dict[str, float]:
        """Calculate pivot points."""
        high = data.high or data.price
        low = data.low or data.price
        close = data.close or data.price
        
        pivot = (high + low + close) / 3
        
        return {
            'pivot': pivot,
            'r1': 2 * pivot - low,
            'r2': pivot + (high - low),
            's1': 2 * pivot - high,
            's2': pivot - (high - low)
        }
        
    # Market State Analysis
    
    async def analyze_market_regime(self) -> RegimeAnalysis:
        """Analyze current market regime."""
        snapshot = await self.get_market_snapshot()
        
        # Get technical indicators
        spy_indicators = await self.calculate_technical_indicators('SPY')
        vix_indicators = await self.calculate_technical_indicators('VIX')
        
        # Determine market regime
        market_regime = await self._determine_market_regime(snapshot, spy_indicators)
        volatility_regime = self._determine_volatility_regime(snapshot.vix.price)
        trend_strength = await self._determine_trend_strength(spy_indicators)
        
        # Calculate confidence scores
        regime_confidence = await self._calculate_regime_confidence(
            snapshot, spy_indicators, market_regime
        )
        
        # Build analysis
        analysis = RegimeAnalysis(
            market_regime=market_regime,
            volatility_regime=volatility_regime,
            trend_strength=trend_strength,
            regime_confidence=regime_confidence,
            volatility_confidence=0.9 if snapshot.vix.price > 0 else 0.5,
            trend_confidence=0.8 if spy_indicators else 0.5,
            regime_stability=await self._calculate_regime_stability()
        )
        
        # Add trading implications
        analysis.recommended_strategies = self._get_recommended_strategies(
            market_regime, volatility_regime
        )
        
        analysis.position_sizing_factor = self._calculate_position_sizing_factor(
            volatility_regime, regime_confidence
        )
        
        return analysis
        
    async def _determine_market_regime(self, snapshot: MarketSnapshot, 
                                     indicators: Optional[TechnicalIndicators]) -> MarketRegime:
        """Determine current market regime."""
        if not indicators:
            return MarketRegime.UNKNOWN
            
        spy_price = snapshot.spy.price
        vix_level = snapshot.vix.price
        
        # Check for crash conditions
        if vix_level > 40:
            return MarketRegime.CRASH_CONDITIONS
            
        # Check for euphoria
        if indicators.rsi and indicators.rsi > 80 and vix_level < 12:
            return MarketRegime.EUPHORIA
            
        # Check trend
        if indicators.sma_50 and indicators.sma_200:
            if spy_price > indicators.sma_50 > indicators.sma_200:
                if vix_level < 20:
                    return MarketRegime.BULL_TRENDING
                else:
                    return MarketRegime.HIGH_VOLATILITY
            elif spy_price < indicators.sma_50 < indicators.sma_200:
                return MarketRegime.BEAR_TRENDING
                
        # Check for range bound
        if indicators.atr and spy_price > 0:
            atr_percentage = (indicators.atr / spy_price) * 100
            if atr_percentage < 1.0:
                return MarketRegime.RANGE_BOUND
                
        # Check volatility
        if vix_level > 25:
            return MarketRegime.HIGH_VOLATILITY
        elif vix_level < 15:
            return MarketRegime.LOW_VOLATILITY
            
        return MarketRegime.UNKNOWN
        
    def _determine_volatility_regime(self, vix_level: float) -> VolatilityRegime:
        """Determine volatility regime from VIX level."""
        if vix_level < 12:
            return VolatilityRegime.EXTREMELY_LOW
        elif vix_level < 16:
            return VolatilityRegime.LOW
        elif vix_level < 20:
            return VolatilityRegime.NORMAL
        elif vix_level < 25:
            return VolatilityRegime.ELEVATED
        elif vix_level < 30:
            return VolatilityRegime.HIGH
        elif vix_level < 40:
            return VolatilityRegime.VERY_HIGH
        else:
            return VolatilityRegime.EXTREME
            
    async def _determine_trend_strength(self, indicators: Optional[TechnicalIndicators]) -> TrendStrength:
        """Determine trend strength."""
        if not indicators:
            return TrendStrength.NEUTRAL
            
        # Use multiple indicators to determine trend
        signals = []
        
        # Moving average alignment
        if indicators.sma_20 and indicators.sma_50 and indicators.sma_200:
            if indicators.sma_20 > indicators.sma_50 > indicators.sma_200:
                signals.append(2)  # Strong up
            elif indicators.sma_20 > indicators.sma_50:
                signals.append(1)  # Moderate up
            elif indicators.sma_20 < indicators.sma_50 < indicators.sma_200:
                signals.append(-2)  # Strong down
            elif indicators.sma_20 < indicators.sma_50:
                signals.append(-1)  # Moderate down
            else:
                signals.append(0)  # Neutral
                
        # RSI
        if indicators.rsi:
            if indicators.rsi > 70:
                signals.append(2)
            elif indicators.rsi > 60:
                signals.append(1)
            elif indicators.rsi < 30:
                signals.append(-2)
            elif indicators.rsi < 40:
                signals.append(-1)
            else:
                signals.append(0)
                
        # Average signals
        if not signals:
            return TrendStrength.NEUTRAL
            
        avg_signal = sum(signals) / len(signals)
        
        if avg_signal >= 1.5:
            return TrendStrength.STRONG_UP
        elif avg_signal >= 0.5:
            return TrendStrength.MODERATE_UP
        elif avg_signal > 0:
            return TrendStrength.WEAK_UP
        elif avg_signal <= -1.5:
            return TrendStrength.STRONG_DOWN
        elif avg_signal <= -0.5:
            return TrendStrength.MODERATE_DOWN
        elif avg_signal < 0:
            return TrendStrength.WEAK_DOWN
        else:
            return TrendStrength.NEUTRAL
            
    async def _calculate_regime_confidence(self, snapshot: MarketSnapshot,
                                         indicators: Optional[TechnicalIndicators],
                                         regime: MarketRegime) -> float:
        """Calculate confidence in regime determination."""
        confidence_factors = []
        
        # Data quality
        if snapshot.spy.price > 0 and snapshot.vix.price > 0:
            confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.3)
            
        # Indicator availability
        if indicators:
            available_indicators = sum(1 for _, v in indicators.dict().items() if v is not None)
            total_indicators = len(indicators.dict())
            confidence_factors.append(available_indicators / total_indicators)
        else:
            confidence_factors.append(0.2)
            
        # Historical consistency
        # Check if regime has been stable
        stability = await self._calculate_regime_stability()
        confidence_factors.append(stability)
        
        # Average confidence
        return sum(confidence_factors) / len(confidence_factors)
        
    async def _calculate_regime_stability(self) -> float:
        """Calculate regime stability score."""
        # This would look at historical regime changes
        # For now, return a default value
        return 0.75
        
    def _get_recommended_strategies(self, market_regime: MarketRegime,
                                  volatility_regime: VolatilityRegime) -> List[str]:
        """Get recommended strategies for current regime."""
        strategies = []
        
        # Market regime strategies
        if market_regime == MarketRegime.BULL_TRENDING:
            strategies.extend(["Buy calls on dips", "Sell puts on support"])
        elif market_regime == MarketRegime.BEAR_TRENDING:
            strategies.extend(["Buy puts on rallies", "Avoid selling puts"])
        elif market_regime == MarketRegime.RANGE_BOUND:
            strategies.extend(["Iron condors", "Sell strangles at extremes"])
        elif market_regime == MarketRegime.HIGH_VOLATILITY:
            strategies.extend(["Reduce position size", "Buy protective puts"])
        elif market_regime == MarketRegime.LOW_VOLATILITY:
            strategies.extend(["Sell premium aggressively", "Increase position size"])
            
        # Volatility regime adjustments
        if volatility_regime in [VolatilityRegime.EXTREMELY_LOW, VolatilityRegime.LOW]:
            strategies.append("Focus on selling options")
        elif volatility_regime in [VolatilityRegime.HIGH, VolatilityRegime.VERY_HIGH]:
            strategies.append("Consider buying options")
            
        return strategies
        
    def _calculate_position_sizing_factor(self, volatility_regime: VolatilityRegime,
                                        confidence: float) -> float:
        """Calculate position sizing factor based on regime."""
        base_factor = 1.0
        
        # Adjust for volatility
        vol_factors = {
            VolatilityRegime.EXTREMELY_LOW: 1.5,
            VolatilityRegime.LOW: 1.2,
            VolatilityRegime.NORMAL: 1.0,
            VolatilityRegime.ELEVATED: 0.8,
            VolatilityRegime.HIGH: 0.6,
            VolatilityRegime.VERY_HIGH: 0.4,
            VolatilityRegime.EXTREME: 0.2
        }
        
        vol_factor = vol_factors.get(volatility_regime, 1.0)
        
        # Adjust for confidence
        confidence_factor = 0.5 + (confidence * 0.5)  # Range: 0.5 to 1.0
        
        return base_factor * vol_factor * confidence_factor
        
    # Background Tasks
    
    async def _collect_market_data(self) -> None:
        """Background task to collect market data."""
        while True:
            try:
                # Check market hours
                self.market_open = self._is_market_open()
                self.extended_hours = self._is_extended_hours()
                
                # Collect data for subscribed symbols
                for symbol in self.subscriptions:
                    data = await self._fetch_market_data(symbol)
                    if data:
                        # Store data
                        self.market_data[symbol].append(data)
                        
                        # Notify callbacks
                        callbacks = self.callbacks.get(symbol, [])
                        for callback in callbacks:
                            try:
                                await callback(data)
                            except Exception as e:
                                logger.error(f"Callback error for {symbol}: {e}")
                                
                # Wait before next collection
                await asyncio.sleep(1.0)  # Collect every second
                
            except Exception as e:
                logger.error(f"Market data collection error: {e}")
                await asyncio.sleep(5.0)  # Wait longer on error
                
    async def _process_market_data(self) -> None:
        """Background task to process market data."""
        while True:
            try:
                # Generate market snapshot
                snapshot = await self.get_market_snapshot()
                
                # Analyze regime
                regime_analysis = await self.analyze_market_regime()
                
                # Store in MCP
                await self.mcp.store_memory(
                    "MarketDataCollector",
                    MemorySlice(
                        memory_type=MemoryType.MARKET_OBSERVATION,
                        content={
                            'snapshot': snapshot.dict(),
                            'regime_analysis': regime_analysis.dict(),
                            'timestamp': datetime.utcnow().isoformat()
                        },
                        importance=MemoryImportance.MEDIUM
                    )
                )
                
                # Share with other agents
                await self.mcp.share_context(
                    "MarketDataCollector",
                    ["EnvironmentWatcherAgent", "StrategicPlannerAgent"],
                    {
                        'market_update': {
                            'spy_price': snapshot.spy.price,
                            'vix_level': snapshot.vix.price,
                            'market_regime': regime_analysis.market_regime.value,
                            'volatility_regime': regime_analysis.volatility_regime.value
                        }
                    }
                )
                
                # Wait before next processing
                await asyncio.sleep(self.processing_interval)
                
            except Exception as e:
                logger.error(f"Market data processing error: {e}")
                await asyncio.sleep(5.0)
                
    async def _fetch_market_data(self, symbol: str) -> Optional[MarketDataPoint]:
        """Fetch market data for a symbol."""
        try:
            if self.ibkr:
                # Use IBKR service to get real data
                data = await self.ibkr.get_market_data(symbol)
                if data:
                    return MarketDataPoint(
                        symbol=symbol,
                        price=data.get('last', 0),
                        bid=data.get('bid'),
                        ask=data.get('ask'),
                        volume=data.get('volume'),
                        high=data.get('high'),
                        low=data.get('low')
                    )
            else:
                # Simulate data for testing
                import random
                base_prices = {
                    'SPY': 445.0,
                    'VIX': 12.5,
                    'DXY': 102.0,
                    'TNX': 4.25,
                    'GLD': 195.0
                }
                
                base = base_prices.get(symbol, 100.0)
                price = base * (1 + random.gauss(0, 0.001))  # 0.1% volatility
                
                return MarketDataPoint(
                    symbol=symbol,
                    price=price,
                    bid=price - 0.01,
                    ask=price + 0.01,
                    volume=random.randint(1000000, 5000000),
                    high=price * 1.001,
                    low=price * 0.999
                )
                
        except Exception as e:
            logger.error(f"Failed to fetch data for {symbol}: {e}")
            return None
            
    def _is_market_open(self) -> bool:
        """Check if market is open."""
        now = datetime.utcnow()
        # NYSE hours: 9:30 AM - 4:00 PM ET (14:30 - 21:00 UTC)
        if now.weekday() < 5:  # Monday to Friday
            market_open = now.replace(hour=14, minute=30, second=0)
            market_close = now.replace(hour=21, minute=0, second=0)
            return market_open <= now <= market_close
        return False
        
    def _is_extended_hours(self) -> bool:
        """Check if in extended trading hours."""
        now = datetime.utcnow()
        if now.weekday() < 5:
            # Pre-market: 4:00 AM - 9:30 AM ET (09:00 - 14:30 UTC)
            # After-hours: 4:00 PM - 8:00 PM ET (21:00 - 01:00 UTC)
            pre_market_start = now.replace(hour=9, minute=0, second=0)
            pre_market_end = now.replace(hour=14, minute=30, second=0)
            after_hours_start = now.replace(hour=21, minute=0, second=0)
            
            if pre_market_start <= now <= pre_market_end:
                return True
            if now >= after_hours_start:
                return True
                
        return False