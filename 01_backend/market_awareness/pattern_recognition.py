"""
Pattern Recognition Engine
Identifies and tracks market patterns for trading opportunities.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from collections import deque
import numpy as np
from dataclasses import dataclass

from ..mcp.context_manager import MCPContextManager
from ..mcp.schemas import MemorySlice, MemoryType, MemoryImportance
from .schemas import (
    MarketDataPoint, MarketPattern, PatternType, TechnicalIndicators,
    MarketSnapshot, MarketEvent
)

logger = logging.getLogger(__name__)


@dataclass
class PatternDetectionConfig:
    """Configuration for pattern detection."""
    min_data_points: int = 50
    lookback_periods: int = 100
    confidence_threshold: float = 0.7
    volume_confirmation: bool = True
    min_pattern_duration: int = 5  # bars
    max_pattern_duration: int = 50  # bars


class PatternRecognitionEngine:
    """
    Detects and analyzes technical patterns in market data.
    """
    
    def __init__(self, mcp_manager: MCPContextManager):
        self.mcp = mcp_manager
        self.config = PatternDetectionConfig()
        
        # Pattern storage
        self.active_patterns: Dict[str, List[MarketPattern]] = {}
        self.completed_patterns: Dict[str, List[MarketPattern]] = {}
        self.pattern_performance: Dict[str, Dict[str, float]] = {}
        
        # Detection state
        self._detection_cache: Dict[str, Dict[str, Any]] = {}
        self._pattern_id_counter = 0
        
        # Background tasks
        self._pattern_validation_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> None:
        """Initialize the pattern recognition engine."""
        # Register with MCP
        await self.mcp.register_agent(
            "PatternRecognitionEngine",
            ["pattern_detection", "technical_analysis", "trading_signals"]
        )
        
        # Load historical pattern performance
        await self._load_pattern_performance()
        
        # Start validation task
        self._pattern_validation_task = asyncio.create_task(
            self._validate_patterns_background()
        )
        
        logger.info("Pattern Recognition Engine initialized")
        
    async def shutdown(self) -> None:
        """Shutdown the engine."""
        if self._pattern_validation_task:
            self._pattern_validation_task.cancel()
            await asyncio.gather(self._pattern_validation_task, return_exceptions=True)
            
        # Save pattern performance
        await self._save_pattern_performance()
        
        logger.info("Pattern Recognition Engine shut down")
        
    # Pattern Detection
    
    async def detect_patterns(self, symbol: str, data: List[MarketDataPoint],
                            indicators: Optional[TechnicalIndicators] = None) -> List[MarketPattern]:
        """
        Detect patterns in market data.
        
        Args:
            symbol: Symbol to analyze
            data: Historical data points
            indicators: Optional technical indicators
            
        Returns:
            List of detected patterns
        """
        if len(data) < self.config.min_data_points:
            return []
            
        patterns = []
        
        # Detect various pattern types
        patterns.extend(await self._detect_reversal_patterns(symbol, data, indicators))
        patterns.extend(await self._detect_continuation_patterns(symbol, data, indicators))
        patterns.extend(await self._detect_support_resistance(symbol, data, indicators))
        patterns.extend(await self._detect_volume_patterns(symbol, data))
        
        # Filter by confidence
        patterns = [p for p in patterns if p.confidence >= self.config.confidence_threshold]
        
        # Update active patterns
        self.active_patterns[symbol] = patterns
        
        # Store significant patterns in MCP
        for pattern in patterns:
            if pattern.confidence >= 0.8:  # High confidence patterns
                await self._store_pattern_in_mcp(pattern)
                
        return patterns
        
    async def _detect_reversal_patterns(self, symbol: str, data: List[MarketDataPoint],
                                      indicators: Optional[TechnicalIndicators]) -> List[MarketPattern]:
        """Detect reversal patterns."""
        patterns = []
        
        # Double Top/Bottom
        double_patterns = await self._detect_double_patterns(symbol, data)
        patterns.extend(double_patterns)
        
        # Head and Shoulders
        hs_patterns = await self._detect_head_shoulders(symbol, data)
        patterns.extend(hs_patterns)
        
        return patterns
        
    async def _detect_double_patterns(self, symbol: str, 
                                    data: List[MarketDataPoint]) -> List[MarketPattern]:
        """Detect double top and double bottom patterns."""
        patterns = []
        
        if len(data) < 20:
            return patterns
            
        prices = [d.price for d in data]
        highs = [d.high or d.price for d in data]
        lows = [d.low or d.price for d in data]
        
        # Look for double tops
        for i in range(10, len(prices) - 10):
            # Find first peak
            if highs[i] > max(highs[i-5:i]) and highs[i] > max(highs[i+1:i+6]):
                first_peak = i
                first_peak_price = highs[i]
                
                # Look for second peak
                for j in range(i + 5, min(i + 30, len(prices) - 5)):
                    if highs[j] > max(highs[j-5:j]) and highs[j] > max(highs[j+1:j+6]):
                        second_peak = j
                        second_peak_price = highs[j]
                        
                        # Check if peaks are similar (within 2%)
                        if abs(first_peak_price - second_peak_price) / first_peak_price < 0.02:
                            # Find trough between peaks
                            trough_idx = np.argmin(lows[first_peak:second_peak]) + first_peak
                            trough_price = lows[trough_idx]
                            
                            # Calculate pattern metrics
                            pattern_height = first_peak_price - trough_price
                            target_price = trough_price - pattern_height
                            
                            pattern = MarketPattern(
                                pattern_id=self._generate_pattern_id(),
                                pattern_type=PatternType.DOUBLE_TOP,
                                symbol=symbol,
                                start_time=data[first_peak].timestamp,
                                end_time=data[second_peak].timestamp,
                                confidence=self._calculate_double_pattern_confidence(
                                    first_peak_price, second_peak_price, trough_price
                                ),
                                key_levels=[first_peak_price, trough_price, second_peak_price],
                                bullish_bias=False,
                                target_price=target_price,
                                stop_loss=max(first_peak_price, second_peak_price) * 1.01,
                                invalidation_level=max(first_peak_price, second_peak_price),
                                detection_method="double_pattern_detection"
                            )
                            
                            patterns.append(pattern)
                            break
                            
        # Look for double bottoms (similar logic, inverted)
        for i in range(10, len(prices) - 10):
            if lows[i] < min(lows[i-5:i]) and lows[i] < min(lows[i+1:i+6]):
                first_trough = i
                first_trough_price = lows[i]
                
                for j in range(i + 5, min(i + 30, len(prices) - 5)):
                    if lows[j] < min(lows[j-5:j]) and lows[j] < min(lows[j+1:j+6]):
                        second_trough = j
                        second_trough_price = lows[j]
                        
                        if abs(first_trough_price - second_trough_price) / first_trough_price < 0.02:
                            peak_idx = np.argmax(highs[first_trough:second_trough]) + first_trough
                            peak_price = highs[peak_idx]
                            
                            pattern_height = peak_price - first_trough_price
                            target_price = peak_price + pattern_height
                            
                            pattern = MarketPattern(
                                pattern_id=self._generate_pattern_id(),
                                pattern_type=PatternType.DOUBLE_BOTTOM,
                                symbol=symbol,
                                start_time=data[first_trough].timestamp,
                                end_time=data[second_trough].timestamp,
                                confidence=self._calculate_double_pattern_confidence(
                                    first_trough_price, second_trough_price, peak_price
                                ),
                                key_levels=[first_trough_price, peak_price, second_trough_price],
                                bullish_bias=True,
                                target_price=target_price,
                                stop_loss=min(first_trough_price, second_trough_price) * 0.99,
                                invalidation_level=min(first_trough_price, second_trough_price),
                                detection_method="double_pattern_detection"
                            )
                            
                            patterns.append(pattern)
                            break
                            
        return patterns
        
    async def _detect_head_shoulders(self, symbol: str,
                                   data: List[MarketDataPoint]) -> List[MarketPattern]:
        """Detect head and shoulders patterns."""
        patterns = []
        
        if len(data) < 30:
            return patterns
            
        highs = [d.high or d.price for d in data]
        lows = [d.low or d.price for d in data]
        
        # Look for head and shoulders top
        for i in range(15, len(highs) - 15):
            # Find potential head (highest point)
            if highs[i] == max(highs[i-10:i+11]):
                head_idx = i
                head_price = highs[i]
                
                # Look for left shoulder
                left_range = highs[max(0, i-20):i-5]
                if left_range:
                    left_shoulder_idx = np.argmax(left_range) + max(0, i-20)
                    left_shoulder_price = highs[left_shoulder_idx]
                    
                    # Look for right shoulder
                    right_range = highs[i+5:min(len(highs), i+20)]
                    if right_range:
                        right_shoulder_idx = np.argmax(right_range) + i + 5
                        right_shoulder_price = highs[right_shoulder_idx]
                        
                        # Check if shoulders are roughly equal (within 3%)
                        shoulder_diff = abs(left_shoulder_price - right_shoulder_price)
                        avg_shoulder = (left_shoulder_price + right_shoulder_price) / 2
                        
                        if shoulder_diff / avg_shoulder < 0.03 and avg_shoulder < head_price:
                            # Find neckline
                            left_trough_idx = np.argmin(lows[left_shoulder_idx:head_idx]) + left_shoulder_idx
                            right_trough_idx = np.argmin(lows[head_idx:right_shoulder_idx]) + head_idx
                            neckline = (lows[left_trough_idx] + lows[right_trough_idx]) / 2
                            
                            # Calculate target
                            pattern_height = head_price - neckline
                            target_price = neckline - pattern_height
                            
                            pattern = MarketPattern(
                                pattern_id=self._generate_pattern_id(),
                                pattern_type=PatternType.HEAD_AND_SHOULDERS,
                                symbol=symbol,
                                start_time=data[left_shoulder_idx].timestamp,
                                end_time=data[right_shoulder_idx].timestamp,
                                confidence=self._calculate_hs_confidence(
                                    left_shoulder_price, head_price, right_shoulder_price, neckline
                                ),
                                key_levels=[left_shoulder_price, head_price, right_shoulder_price, neckline],
                                bullish_bias=False,
                                target_price=target_price,
                                stop_loss=head_price * 1.01,
                                invalidation_level=head_price,
                                detection_method="head_shoulders_detection"
                            )
                            
                            patterns.append(pattern)
                            
        return patterns
        
    async def _detect_continuation_patterns(self, symbol: str, data: List[MarketDataPoint],
                                          indicators: Optional[TechnicalIndicators]) -> List[MarketPattern]:
        """Detect continuation patterns."""
        patterns = []
        
        # Flag patterns
        flag_patterns = await self._detect_flag_patterns(symbol, data)
        patterns.extend(flag_patterns)
        
        # Triangle patterns
        triangle_patterns = await self._detect_triangle_patterns(symbol, data)
        patterns.extend(triangle_patterns)
        
        return patterns
        
    async def _detect_flag_patterns(self, symbol: str,
                                  data: List[MarketDataPoint]) -> List[MarketPattern]:
        """Detect flag and pennant patterns."""
        patterns = []
        
        if len(data) < 20:
            return patterns
            
        prices = [d.price for d in data]
        volumes = [d.volume or 0 for d in data]
        
        # Look for strong moves followed by consolidation
        for i in range(10, len(prices) - 10):
            # Check for strong initial move (pole)
            pole_start = i - 10
            pole_end = i
            price_change = (prices[pole_end] - prices[pole_start]) / prices[pole_start]
            
            # Significant move (> 3%)
            if abs(price_change) > 0.03:
                # Check for consolidation (flag)
                flag_prices = prices[i:i+10]
                flag_high = max(flag_prices)
                flag_low = min(flag_prices)
                flag_range = (flag_high - flag_low) / prices[i]
                
                # Tight consolidation (< 2% range)
                if flag_range < 0.02:
                    # Volume should decrease during flag
                    pole_avg_volume = np.mean(volumes[pole_start:pole_end]) if volumes[pole_start:pole_end] else 0
                    flag_avg_volume = np.mean(volumes[i:i+10]) if volumes[i:i+10] else 0
                    
                    volume_decrease = flag_avg_volume < pole_avg_volume * 0.7 if pole_avg_volume > 0 else True
                    
                    if volume_decrease:
                        # Calculate target
                        pole_height = abs(prices[pole_end] - prices[pole_start])
                        if price_change > 0:  # Bullish flag
                            target_price = flag_high + pole_height
                            pattern_type = PatternType.FLAG
                            bullish = True
                            stop = flag_low * 0.99
                        else:  # Bearish flag
                            target_price = flag_low - pole_height
                            pattern_type = PatternType.FLAG
                            bullish = False
                            stop = flag_high * 1.01
                            
                        pattern = MarketPattern(
                            pattern_id=self._generate_pattern_id(),
                            pattern_type=pattern_type,
                            symbol=symbol,
                            start_time=data[pole_start].timestamp,
                            end_time=data[i+9].timestamp,
                            confidence=0.75,
                            key_levels=[prices[pole_start], prices[pole_end], flag_high, flag_low],
                            bullish_bias=bullish,
                            target_price=target_price,
                            stop_loss=stop,
                            invalidation_level=flag_low if bullish else flag_high,
                            detection_method="flag_pattern_detection",
                            volume_profile="decreasing"
                        )
                        
                        patterns.append(pattern)
                        
        return patterns
        
    async def _detect_triangle_patterns(self, symbol: str,
                                      data: List[MarketDataPoint]) -> List[MarketPattern]:
        """Detect triangle patterns."""
        patterns = []
        
        if len(data) < 30:
            return patterns
            
        highs = [d.high or d.price for d in data]
        lows = [d.low or d.price for d in data]
        
        # Look for converging trendlines
        for i in range(20, len(data) - 10):
            window = 20
            
            # Get highs and lows in window
            window_highs = highs[i-window:i]
            window_lows = lows[i-window:i]
            
            # Find peaks and troughs
            peaks = []
            troughs = []
            
            for j in range(2, len(window_highs) - 2):
                if window_highs[j] > max(window_highs[j-2:j]) and window_highs[j] > max(window_highs[j+1:j+3]):
                    peaks.append((j, window_highs[j]))
                if window_lows[j] < min(window_lows[j-2:j]) and window_lows[j] < min(window_lows[j+1:j+3]):
                    troughs.append((j, window_lows[j]))
                    
            # Need at least 2 peaks and 2 troughs
            if len(peaks) >= 2 and len(troughs) >= 2:
                # Check if forming triangle (converging)
                upper_slope = (peaks[-1][1] - peaks[0][1]) / (peaks[-1][0] - peaks[0][0])
                lower_slope = (troughs[-1][1] - troughs[0][1]) / (troughs[-1][0] - troughs[0][0])
                
                # Symmetrical triangle: both lines converging
                if upper_slope < 0 and lower_slope > 0:
                    # Calculate apex
                    current_upper = peaks[-1][1]
                    current_lower = troughs[-1][1]
                    current_range = current_upper - current_lower
                    
                    if current_range > 0:
                        pattern = MarketPattern(
                            pattern_id=self._generate_pattern_id(),
                            pattern_type=PatternType.TRIANGLE,
                            symbol=symbol,
                            start_time=data[i-window].timestamp,
                            end_time=data[i].timestamp,
                            confidence=0.7,
                            key_levels=[peaks[0][1], troughs[0][1], current_upper, current_lower],
                            bullish_bias=True,  # Neutral, depends on breakout
                            target_price=None,  # Set on breakout
                            stop_loss=None,
                            invalidation_level=current_lower,
                            detection_method="triangle_pattern_detection"
                        )
                        
                        patterns.append(pattern)
                        
        return patterns
        
    async def _detect_support_resistance(self, symbol: str, data: List[MarketDataPoint],
                                       indicators: Optional[TechnicalIndicators]) -> List[MarketPattern]:
        """Detect support and resistance interactions."""
        patterns = []
        
        if not indicators or len(data) < 10:
            return patterns
            
        current_price = data[-1].price
        recent_high = max(d.high or d.price for d in data[-10:])
        recent_low = min(d.low or d.price for d in data[-10:])
        
        # Check support bounce
        if indicators.support_1 and indicators.support_2:
            if recent_low <= indicators.support_1 * 1.005 and current_price > indicators.support_1:
                pattern = MarketPattern(
                    pattern_id=self._generate_pattern_id(),
                    pattern_type=PatternType.SUPPORT_BOUNCE,
                    symbol=symbol,
                    start_time=data[-10].timestamp,
                    end_time=data[-1].timestamp,
                    confidence=0.8,
                    key_levels=[indicators.support_1, indicators.support_2],
                    bullish_bias=True,
                    target_price=indicators.pivot_point,
                    stop_loss=indicators.support_1 * 0.99,
                    invalidation_level=indicators.support_1 * 0.995,
                    detection_method="support_resistance_detection"
                )
                patterns.append(pattern)
                
        # Check resistance rejection
        if indicators.resistance_1 and indicators.resistance_2:
            if recent_high >= indicators.resistance_1 * 0.995 and current_price < indicators.resistance_1:
                pattern = MarketPattern(
                    pattern_id=self._generate_pattern_id(),
                    pattern_type=PatternType.RESISTANCE_REJECTION,
                    symbol=symbol,
                    start_time=data[-10].timestamp,
                    end_time=data[-1].timestamp,
                    confidence=0.8,
                    key_levels=[indicators.resistance_1, indicators.resistance_2],
                    bullish_bias=False,
                    target_price=indicators.pivot_point,
                    stop_loss=indicators.resistance_1 * 1.01,
                    invalidation_level=indicators.resistance_1 * 1.005,
                    detection_method="support_resistance_detection"
                )
                patterns.append(pattern)
                
        return patterns
        
    async def _detect_volume_patterns(self, symbol: str,
                                    data: List[MarketDataPoint]) -> List[MarketPattern]:
        """Detect volume-based patterns."""
        patterns = []
        
        if len(data) < 20:
            return patterns
            
        volumes = [d.volume or 0 for d in data]
        prices = [d.price for d in data]
        
        # Calculate average volume
        avg_volume = np.mean(volumes[-20:]) if volumes[-20:] else 0
        
        if avg_volume > 0:
            # Look for volume spikes
            for i in range(len(volumes) - 5, len(volumes)):
                if volumes[i] > avg_volume * 2.5:  # 150% above average
                    price_change = (prices[i] - prices[i-1]) / prices[i-1] if i > 0 else 0
                    
                    pattern = MarketPattern(
                        pattern_id=self._generate_pattern_id(),
                        pattern_type=PatternType.VOLUME_SPIKE,
                        symbol=symbol,
                        start_time=data[i].timestamp,
                        end_time=data[i].timestamp,
                        confidence=0.9,
                        key_levels=[prices[i]],
                        bullish_bias=price_change > 0,
                        target_price=None,
                        stop_loss=None,
                        invalidation_level=None,
                        detection_method="volume_pattern_detection",
                        volume_profile=f"spike_{volumes[i]/avg_volume:.1f}x"
                    )
                    patterns.append(pattern)
                    
        return patterns
        
    # Pattern Analysis
    
    async def analyze_pattern_strength(self, pattern: MarketPattern,
                                     current_data: MarketDataPoint) -> Dict[str, Any]:
        """
        Analyze the strength and validity of a pattern.
        
        Args:
            pattern: Pattern to analyze
            current_data: Current market data
            
        Returns:
            Analysis results
        """
        analysis = {
            'pattern_id': pattern.pattern_id,
            'still_valid': True,
            'completion_percentage': 0.0,
            'price_action_confirmation': False,
            'volume_confirmation': False,
            'risk_reward_ratio': 0.0,
            'entry_timing': 'wait'
        }
        
        # Check if pattern is still valid
        if pattern.invalidation_level:
            if pattern.bullish_bias and current_data.price < pattern.invalidation_level:
                analysis['still_valid'] = False
            elif not pattern.bullish_bias and current_data.price > pattern.invalidation_level:
                analysis['still_valid'] = False
                
        # Calculate completion percentage
        if pattern.target_price and pattern.key_levels:
            start_price = pattern.key_levels[0]
            total_move = abs(pattern.target_price - start_price)
            current_move = abs(current_data.price - start_price)
            analysis['completion_percentage'] = min(current_move / total_move * 100, 100) if total_move > 0 else 0
            
        # Check confirmations
        if pattern.pattern_type in [PatternType.BREAKOUT, PatternType.BREAKDOWN]:
            analysis['price_action_confirmation'] = True
            
        # Calculate risk/reward
        if pattern.target_price and pattern.stop_loss:
            potential_profit = abs(pattern.target_price - current_data.price)
            potential_loss = abs(current_data.price - pattern.stop_loss)
            if potential_loss > 0:
                analysis['risk_reward_ratio'] = potential_profit / potential_loss
                
        # Entry timing
        if analysis['still_valid'] and analysis['risk_reward_ratio'] > 2.0:
            analysis['entry_timing'] = 'good'
        elif analysis['still_valid'] and analysis['risk_reward_ratio'] > 1.5:
            analysis['entry_timing'] = 'moderate'
            
        return analysis
        
    async def get_pattern_statistics(self, pattern_type: Optional[PatternType] = None) -> Dict[str, Any]:
        """
        Get performance statistics for patterns.
        
        Args:
            pattern_type: Optional specific pattern type
            
        Returns:
            Statistics dictionary
        """
        stats = {
            'total_patterns_detected': 0,
            'successful_patterns': 0,
            'failed_patterns': 0,
            'average_profit': 0.0,
            'average_loss': 0.0,
            'win_rate': 0.0,
            'best_performing_pattern': None,
            'worst_performing_pattern': None
        }
        
        # Filter by pattern type if specified
        patterns_to_analyze = []
        for symbol_patterns in self.completed_patterns.values():
            for pattern in symbol_patterns:
                if pattern_type is None or pattern.pattern_type == pattern_type:
                    patterns_to_analyze.append(pattern)
                    
        stats['total_patterns_detected'] = len(patterns_to_analyze)
        
        # Calculate performance metrics
        profits = []
        losses = []
        
        for pattern in patterns_to_analyze:
            performance = self.pattern_performance.get(pattern.pattern_id, {})
            if 'result' in performance:
                if performance['result'] > 0:
                    stats['successful_patterns'] += 1
                    profits.append(performance['result'])
                else:
                    stats['failed_patterns'] += 1
                    losses.append(abs(performance['result']))
                    
        # Calculate averages
        if profits:
            stats['average_profit'] = np.mean(profits)
        if losses:
            stats['average_loss'] = np.mean(losses)
        if stats['total_patterns_detected'] > 0:
            stats['win_rate'] = stats['successful_patterns'] / stats['total_patterns_detected']
            
        # Find best/worst patterns
        pattern_types_performance = {}
        for pattern_type_key in PatternType:
            type_patterns = [p for p in patterns_to_analyze if p.pattern_type == pattern_type_key]
            if type_patterns:
                type_wins = sum(1 for p in type_patterns if self.pattern_performance.get(p.pattern_id, {}).get('result', 0) > 0)
                type_win_rate = type_wins / len(type_patterns)
                pattern_types_performance[pattern_type_key.value] = type_win_rate
                
        if pattern_types_performance:
            stats['best_performing_pattern'] = max(pattern_types_performance.items(), key=lambda x: x[1])
            stats['worst_performing_pattern'] = min(pattern_types_performance.items(), key=lambda x: x[1])
            
        return stats
        
    # Helper Methods
    
    def _generate_pattern_id(self) -> str:
        """Generate unique pattern ID."""
        self._pattern_id_counter += 1
        return f"pattern_{datetime.utcnow().strftime('%Y%m%d')}_{self._pattern_id_counter}"
        
    def _calculate_double_pattern_confidence(self, peak1: float, peak2: float, trough: float) -> float:
        """Calculate confidence for double top/bottom patterns."""
        # Base confidence
        confidence = 0.7
        
        # Adjust for peak similarity
        peak_diff = abs(peak1 - peak2) / max(peak1, peak2)
        if peak_diff < 0.01:  # Very similar peaks
            confidence += 0.1
        elif peak_diff > 0.03:  # Dissimilar peaks
            confidence -= 0.1
            
        # Adjust for pattern depth
        pattern_depth = abs(max(peak1, peak2) - trough) / max(peak1, peak2)
        if pattern_depth > 0.05:  # Deep pattern
            confidence += 0.1
        elif pattern_depth < 0.02:  # Shallow pattern
            confidence -= 0.1
            
        return max(0.0, min(1.0, confidence))
        
    def _calculate_hs_confidence(self, left_shoulder: float, head: float,
                               right_shoulder: float, neckline: float) -> float:
        """Calculate confidence for head and shoulders pattern."""
        confidence = 0.75
        
        # Check shoulder symmetry
        shoulder_diff = abs(left_shoulder - right_shoulder) / max(left_shoulder, right_shoulder)
        if shoulder_diff < 0.02:
            confidence += 0.1
        elif shoulder_diff > 0.05:
            confidence -= 0.1
            
        # Check head prominence
        head_prominence = (head - max(left_shoulder, right_shoulder)) / head
        if head_prominence > 0.03:
            confidence += 0.05
            
        return max(0.0, min(1.0, confidence))
        
    async def _store_pattern_in_mcp(self, pattern: MarketPattern) -> None:
        """Store significant pattern in MCP."""
        await self.mcp.store_memory(
            "PatternRecognitionEngine",
            MemorySlice(
                memory_type=MemoryType.MARKET_OBSERVATION,
                content={
                    'pattern': pattern.dict(),
                    'detection_time': datetime.utcnow().isoformat(),
                    'significance': 'high' if pattern.confidence > 0.9 else 'medium'
                },
                importance=MemoryImportance.HIGH if pattern.confidence > 0.9 else MemoryImportance.MEDIUM
            )
        )
        
    async def _validate_patterns_background(self) -> None:
        """Background task to validate active patterns."""
        while True:
            try:
                # Validate each active pattern
                for symbol, patterns in self.active_patterns.items():
                    for pattern in patterns[:]:  # Copy to allow modification
                        # Check if pattern has completed or failed
                        if pattern.end_time and datetime.utcnow() > pattern.end_time + timedelta(hours=24):
                            # Move to completed
                            if symbol not in self.completed_patterns:
                                self.completed_patterns[symbol] = []
                            self.completed_patterns[symbol].append(pattern)
                            patterns.remove(pattern)
                            
                # Sleep before next validation
                await asyncio.sleep(60)  # Validate every minute
                
            except Exception as e:
                logger.error(f"Pattern validation error: {e}")
                await asyncio.sleep(60)
                
    async def _load_pattern_performance(self) -> None:
        """Load historical pattern performance from MCP."""
        # Query MCP for pattern performance data
        memories = await self.mcp.semantic_search(
            "PatternRecognitionEngine",
            "pattern performance results statistics",
            scope="own"
        )
        
        for memory in memories:
            if 'pattern_performance' in memory.content:
                self.pattern_performance.update(memory.content['pattern_performance'])
                
    async def _save_pattern_performance(self) -> None:
        """Save pattern performance to MCP."""
        await self.mcp.store_memory(
            "PatternRecognitionEngine",
            MemorySlice(
                memory_type=MemoryType.EVALUATION,
                content={
                    'pattern_performance': self.pattern_performance,
                    'statistics': await self.get_pattern_statistics(),
                    'timestamp': datetime.utcnow().isoformat()
                },
                importance=MemoryImportance.HIGH
            )
        )