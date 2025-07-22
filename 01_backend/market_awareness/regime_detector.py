"""
Market Regime Detector
Advanced regime detection and transition analysis.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque
import numpy as np

from ..mcp.context_manager import MCPContextManager
from ..mcp.schemas import MemorySlice, MemoryType, MemoryImportance
from .schemas import (
    MarketRegime, VolatilityRegime, TrendStrength, RegimeAnalysis,
    MarketSnapshot, TechnicalIndicators, MarketDataPoint
)
from .market_data_collector import MarketDataCollector

logger = logging.getLogger(__name__)


class RegimeTransition:
    """Represents a market regime transition."""
    def __init__(self, from_regime: MarketRegime, to_regime: MarketRegime,
                 timestamp: datetime, confidence: float):
        self.from_regime = from_regime
        self.to_regime = to_regime
        self.timestamp = timestamp
        self.confidence = confidence
        self.duration_in_previous = timedelta()
        self.transition_triggers = []
        
        
class MarketRegimeDetector:
    """
    Detects market regimes and analyzes transitions.
    """
    
    def __init__(self, mcp_manager: MCPContextManager, 
                 market_data_collector: MarketDataCollector):
        self.mcp = mcp_manager
        self.data_collector = market_data_collector
        
        # Regime tracking
        self.current_regime = MarketRegime.UNKNOWN
        self.current_volatility_regime = VolatilityRegime.NORMAL
        self.regime_history: deque = deque(maxlen=100)
        self.transition_history: List[RegimeTransition] = []
        
        # Analysis state
        self.regime_start_time = datetime.utcnow()
        self.regime_confidence = 0.5
        self.regime_stability_scores: deque = deque(maxlen=50)
        
        # Thresholds and parameters
        self.regime_change_threshold = 0.7
        self.minimum_regime_duration = timedelta(hours=4)
        
        # Background monitoring
        self._monitoring_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> None:
        """Initialize the regime detector."""
        # Register with MCP
        await self.mcp.register_agent(
            "MarketRegimeDetector",
            ["regime_detection", "market_analysis", "transition_prediction"]
        )
        
        # Load historical regime data
        await self._load_regime_history()
        
        # Start monitoring
        self._monitoring_task = asyncio.create_task(self._monitor_regime_changes())
        
        logger.info("Market Regime Detector initialized")
        
    async def shutdown(self) -> None:
        """Shutdown the detector."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            await asyncio.gather(self._monitoring_task, return_exceptions=True)
            
        # Save regime history
        await self._save_regime_history()
        
        logger.info("Market Regime Detector shut down")
        
    # Regime Detection
    
    async def detect_current_regime(self) -> RegimeAnalysis:
        """
        Detect the current market regime.
        
        Returns:
            Comprehensive regime analysis
        """
        # Get market snapshot
        snapshot = await self.data_collector.get_market_snapshot()
        
        # Get technical indicators
        spy_indicators = await self.data_collector.calculate_technical_indicators('SPY')
        vix_indicators = await self.data_collector.calculate_technical_indicators('VIX')
        
        # Multi-factor regime detection
        regime_signals = await self._collect_regime_signals(snapshot, spy_indicators, vix_indicators)
        
        # Determine regime with confidence
        market_regime, regime_confidence = await self._determine_regime_from_signals(regime_signals)
        
        # Detect volatility regime
        volatility_regime = self._classify_volatility_regime(snapshot.vix.price)
        vol_confidence = 0.95 if snapshot.vix.price > 0 else 0.5
        
        # Determine trend
        trend_strength, trend_confidence = await self._analyze_trend_strength(spy_indicators)
        
        # Calculate regime stability
        stability = await self._calculate_regime_stability(market_regime)
        
        # Build transition probabilities
        transition_probs = await self._calculate_transition_probabilities(market_regime)
        
        # Create analysis
        analysis = RegimeAnalysis(
            market_regime=market_regime,
            volatility_regime=volatility_regime,
            trend_strength=trend_strength,
            regime_confidence=regime_confidence,
            volatility_confidence=vol_confidence,
            trend_confidence=trend_confidence,
            regime_stability=stability,
            transition_probabilities=transition_probs
        )
        
        # Add supporting evidence
        analysis.supporting_indicators = self._get_supporting_indicators(regime_signals, market_regime)
        analysis.conflicting_indicators = self._get_conflicting_indicators(regime_signals, market_regime)
        
        # Add trading implications
        analysis.recommended_strategies = self._get_regime_strategies(market_regime, volatility_regime)
        analysis.risk_adjustments = self._get_risk_adjustments(market_regime, volatility_regime)
        analysis.position_sizing_factor = self._calculate_position_sizing(market_regime, volatility_regime, stability)
        
        # Check for regime change
        await self._check_regime_change(market_regime, regime_confidence)
        
        return analysis
        
    async def _collect_regime_signals(self, snapshot: MarketSnapshot,
                                    spy_indicators: Optional[TechnicalIndicators],
                                    vix_indicators: Optional[TechnicalIndicators]) -> Dict[str, Any]:
        """Collect signals from multiple sources for regime detection."""
        signals = {
            'price_level': {},
            'volatility': {},
            'trend': {},
            'breadth': {},
            'volume': {},
            'internals': {}
        }
        
        # Price level signals
        if spy_indicators:
            if spy_indicators.sma_200:
                signals['price_level']['above_200ma'] = snapshot.spy.price > spy_indicators.sma_200
            if spy_indicators.sma_50:
                signals['price_level']['above_50ma'] = snapshot.spy.price > spy_indicators.sma_50
            if spy_indicators.sma_20:
                signals['price_level']['above_20ma'] = snapshot.spy.price > spy_indicators.sma_20
                
        # Volatility signals
        vix_level = snapshot.vix.price
        signals['volatility']['vix_level'] = vix_level
        signals['volatility']['vix_regime'] = self._classify_volatility_regime(vix_level).value
        
        if vix_indicators and vix_indicators.sma_20:
            signals['volatility']['vix_above_ma'] = vix_level > vix_indicators.sma_20
            
        # Trend signals
        if spy_indicators:
            if spy_indicators.sma_20 and spy_indicators.sma_50 and spy_indicators.sma_200:
                # Moving average alignment
                ma_aligned_bull = spy_indicators.sma_20 > spy_indicators.sma_50 > spy_indicators.sma_200
                ma_aligned_bear = spy_indicators.sma_20 < spy_indicators.sma_50 < spy_indicators.sma_200
                signals['trend']['ma_aligned_bull'] = ma_aligned_bull
                signals['trend']['ma_aligned_bear'] = ma_aligned_bear
                
            if spy_indicators.rsi:
                signals['trend']['rsi'] = spy_indicators.rsi
                signals['trend']['rsi_overbought'] = spy_indicators.rsi > 70
                signals['trend']['rsi_oversold'] = spy_indicators.rsi < 30
                
        # Market breadth signals
        if snapshot.advance_decline_ratio:
            signals['breadth']['ad_ratio'] = snapshot.advance_decline_ratio
            signals['breadth']['broad_strength'] = snapshot.advance_decline_ratio > 1.5
            signals['breadth']['broad_weakness'] = snapshot.advance_decline_ratio < 0.67
            
        # Volume signals
        if snapshot.volume_ratio:
            signals['volume']['up_down_ratio'] = snapshot.volume_ratio
            signals['volume']['strong_buying'] = snapshot.volume_ratio > 1.5
            signals['volume']['strong_selling'] = snapshot.volume_ratio < 0.67
            
        # Options signals
        if snapshot.put_call_ratio:
            signals['internals']['put_call_ratio'] = snapshot.put_call_ratio
            signals['internals']['high_put_buying'] = snapshot.put_call_ratio > 1.2
            signals['internals']['high_call_buying'] = snapshot.put_call_ratio < 0.8
            
        return signals
        
    async def _determine_regime_from_signals(self, signals: Dict[str, Any]) -> Tuple[MarketRegime, float]:
        """Determine market regime from collected signals."""
        regime_scores = {
            MarketRegime.BULL_TRENDING: 0,
            MarketRegime.BEAR_TRENDING: 0,
            MarketRegime.RANGE_BOUND: 0,
            MarketRegime.HIGH_VOLATILITY: 0,
            MarketRegime.LOW_VOLATILITY: 0,
            MarketRegime.CRASH_CONDITIONS: 0,
            MarketRegime.EUPHORIA: 0,
            MarketRegime.ACCUMULATION: 0,
            MarketRegime.DISTRIBUTION: 0
        }
        
        # Score each regime based on signals
        
        # Bull trending signals
        if signals['price_level'].get('above_200ma', False):
            regime_scores[MarketRegime.BULL_TRENDING] += 2
        if signals['trend'].get('ma_aligned_bull', False):
            regime_scores[MarketRegime.BULL_TRENDING] += 3
        if signals['breadth'].get('broad_strength', False):
            regime_scores[MarketRegime.BULL_TRENDING] += 2
        if signals['volume'].get('strong_buying', False):
            regime_scores[MarketRegime.BULL_TRENDING] += 1
            
        # Bear trending signals
        if not signals['price_level'].get('above_200ma', True):
            regime_scores[MarketRegime.BEAR_TRENDING] += 2
        if signals['trend'].get('ma_aligned_bear', False):
            regime_scores[MarketRegime.BEAR_TRENDING] += 3
        if signals['breadth'].get('broad_weakness', False):
            regime_scores[MarketRegime.BEAR_TRENDING] += 2
        if signals['volume'].get('strong_selling', False):
            regime_scores[MarketRegime.BEAR_TRENDING] += 1
            
        # Volatility regimes
        vix_level = signals['volatility'].get('vix_level', 20)
        if vix_level > 30:
            regime_scores[MarketRegime.HIGH_VOLATILITY] += 4
            if vix_level > 40:
                regime_scores[MarketRegime.CRASH_CONDITIONS] += 5
        elif vix_level < 15:
            regime_scores[MarketRegime.LOW_VOLATILITY] += 3
            if vix_level < 12 and signals['trend'].get('rsi_overbought', False):
                regime_scores[MarketRegime.EUPHORIA] += 3
                
        # Range bound detection
        if abs(signals['trend'].get('ma_aligned_bull', False) - signals['trend'].get('ma_aligned_bear', False)) < 0.1:
            regime_scores[MarketRegime.RANGE_BOUND] += 2
            
        # Accumulation/Distribution
        if signals['volume'].get('strong_buying', False) and not signals['price_level'].get('above_50ma', True):
            regime_scores[MarketRegime.ACCUMULATION] += 2
        if signals['volume'].get('strong_selling', False) and signals['price_level'].get('above_50ma', False):
            regime_scores[MarketRegime.DISTRIBUTION] += 2
            
        # Find highest scoring regime
        best_regime = max(regime_scores.items(), key=lambda x: x[1])
        total_score = sum(regime_scores.values())
        
        if total_score > 0:
            confidence = best_regime[1] / total_score
        else:
            confidence = 0.5
            
        return best_regime[0], confidence
        
    def _classify_volatility_regime(self, vix_level: float) -> VolatilityRegime:
        """Classify volatility regime based on VIX level."""
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
            
    async def _analyze_trend_strength(self, indicators: Optional[TechnicalIndicators]) -> Tuple[TrendStrength, float]:
        """Analyze trend strength from indicators."""
        if not indicators:
            return TrendStrength.NEUTRAL, 0.5
            
        strength_score = 0
        confidence_factors = []
        
        # Moving average analysis
        if indicators.sma_20 and indicators.sma_50 and indicators.sma_200:
            # Calculate slopes
            # This is simplified - in practice would use historical data
            if indicators.sma_20 > indicators.sma_50 > indicators.sma_200:
                strength_score += 2
                confidence_factors.append(0.9)
            elif indicators.sma_20 < indicators.sma_50 < indicators.sma_200:
                strength_score -= 2
                confidence_factors.append(0.9)
            else:
                confidence_factors.append(0.6)
                
        # RSI analysis
        if indicators.rsi:
            if indicators.rsi > 70:
                strength_score += 1.5
            elif indicators.rsi > 60:
                strength_score += 0.5
            elif indicators.rsi < 30:
                strength_score -= 1.5
            elif indicators.rsi < 40:
                strength_score -= 0.5
            confidence_factors.append(0.8)
            
        # MACD analysis
        if indicators.macd and indicators.macd_signal:
            if indicators.macd > indicators.macd_signal:
                strength_score += 1
            else:
                strength_score -= 1
            confidence_factors.append(0.7)
            
        # Determine trend strength
        if strength_score >= 3:
            trend = TrendStrength.STRONG_UP
        elif strength_score >= 1.5:
            trend = TrendStrength.MODERATE_UP
        elif strength_score >= 0.5:
            trend = TrendStrength.WEAK_UP
        elif strength_score <= -3:
            trend = TrendStrength.STRONG_DOWN
        elif strength_score <= -1.5:
            trend = TrendStrength.MODERATE_DOWN
        elif strength_score <= -0.5:
            trend = TrendStrength.WEAK_DOWN
        else:
            trend = TrendStrength.NEUTRAL
            
        # Calculate confidence
        confidence = np.mean(confidence_factors) if confidence_factors else 0.5
        
        return trend, confidence
        
    async def _calculate_regime_stability(self, current_regime: MarketRegime) -> float:
        """Calculate stability of current regime."""
        if not self.regime_stability_scores:
            return 0.5
            
        # Calculate recent stability
        recent_scores = list(self.regime_stability_scores)[-20:]
        
        # Factors for stability
        stability_factors = []
        
        # Regime consistency
        if self.current_regime == current_regime:
            time_in_regime = datetime.utcnow() - self.regime_start_time
            if time_in_regime > timedelta(days=7):
                stability_factors.append(0.9)
            elif time_in_regime > timedelta(days=3):
                stability_factors.append(0.7)
            elif time_in_regime > timedelta(days=1):
                stability_factors.append(0.5)
            else:
                stability_factors.append(0.3)
        else:
            stability_factors.append(0.2)
            
        # Score consistency
        if len(recent_scores) > 5:
            score_std = np.std(recent_scores)
            if score_std < 0.1:
                stability_factors.append(0.9)
            elif score_std < 0.2:
                stability_factors.append(0.7)
            else:
                stability_factors.append(0.5)
                
        # Recent transitions
        recent_transitions = [t for t in self.transition_history 
                            if t.timestamp > datetime.utcnow() - timedelta(days=7)]
        if len(recent_transitions) == 0:
            stability_factors.append(0.9)
        elif len(recent_transitions) <= 2:
            stability_factors.append(0.6)
        else:
            stability_factors.append(0.3)
            
        return np.mean(stability_factors) if stability_factors else 0.5
        
    async def _calculate_transition_probabilities(self, current_regime: MarketRegime) -> Dict[str, float]:
        """Calculate probabilities of transitioning to other regimes."""
        probabilities = {}
        
        # Base probabilities (simplified - in practice would use historical data)
        regime_transitions = {
            MarketRegime.BULL_TRENDING: {
                MarketRegime.RANGE_BOUND: 0.3,
                MarketRegime.DISTRIBUTION: 0.2,
                MarketRegime.HIGH_VOLATILITY: 0.15,
                MarketRegime.BEAR_TRENDING: 0.1
            },
            MarketRegime.BEAR_TRENDING: {
                MarketRegime.RANGE_BOUND: 0.25,
                MarketRegime.ACCUMULATION: 0.2,
                MarketRegime.HIGH_VOLATILITY: 0.2,
                MarketRegime.CRASH_CONDITIONS: 0.15
            },
            MarketRegime.RANGE_BOUND: {
                MarketRegime.BULL_TRENDING: 0.3,
                MarketRegime.BEAR_TRENDING: 0.3,
                MarketRegime.LOW_VOLATILITY: 0.2
            },
            MarketRegime.HIGH_VOLATILITY: {
                MarketRegime.CRASH_CONDITIONS: 0.3,
                MarketRegime.BEAR_TRENDING: 0.25,
                MarketRegime.RANGE_BOUND: 0.2
            },
            MarketRegime.LOW_VOLATILITY: {
                MarketRegime.RANGE_BOUND: 0.3,
                MarketRegime.BULL_TRENDING: 0.25,
                MarketRegime.EUPHORIA: 0.15
            }
        }
        
        # Get base probabilities for current regime
        base_probs = regime_transitions.get(current_regime, {})
        
        # Adjust based on current conditions
        # This is simplified - would use more sophisticated modeling
        for regime, base_prob in base_probs.items():
            probabilities[regime.value] = base_prob
            
        # Normalize to ensure sum = 1
        total_prob = sum(probabilities.values())
        if total_prob > 0:
            probabilities = {k: v/total_prob for k, v in probabilities.items()}
            
        return probabilities
        
    async def _check_regime_change(self, detected_regime: MarketRegime, confidence: float) -> None:
        """Check if regime has changed and handle transition."""
        if detected_regime != self.current_regime and confidence > self.regime_change_threshold:
            # Check minimum duration
            time_in_regime = datetime.utcnow() - self.regime_start_time
            if time_in_regime < self.minimum_regime_duration:
                return
                
            # Create transition
            transition = RegimeTransition(
                from_regime=self.current_regime,
                to_regime=detected_regime,
                timestamp=datetime.utcnow(),
                confidence=confidence
            )
            transition.duration_in_previous = time_in_regime
            
            # Store transition
            self.transition_history.append(transition)
            
            # Update current regime
            previous_regime = self.current_regime
            self.current_regime = detected_regime
            self.regime_start_time = datetime.utcnow()
            self.regime_confidence = confidence
            
            # Store in MCP
            await self._store_regime_change(transition)
            
            # Notify other agents
            await self.mcp.share_context(
                "MarketRegimeDetector",
                ["EnvironmentWatcherAgent", "StrategicPlannerAgent", "RiskManagerAgent"],
                {
                    'regime_change': {
                        'from': previous_regime.value,
                        'to': detected_regime.value,
                        'confidence': confidence,
                        'timestamp': datetime.utcnow().isoformat(),
                        'implications': self._get_regime_change_implications(previous_regime, detected_regime)
                    }
                }
            )
            
            logger.info(f"Regime change detected: {previous_regime.value} → {detected_regime.value} (confidence: {confidence:.2f})")
            
    def _get_supporting_indicators(self, signals: Dict[str, Any], regime: MarketRegime) -> Dict[str, Any]:
        """Get indicators supporting the detected regime."""
        supporting = {}
        
        if regime == MarketRegime.BULL_TRENDING:
            if signals['price_level'].get('above_200ma'):
                supporting['price_above_200ma'] = True
            if signals['trend'].get('ma_aligned_bull'):
                supporting['moving_averages_aligned'] = True
            if signals['breadth'].get('broad_strength'):
                supporting['market_breadth_positive'] = True
                
        elif regime == MarketRegime.HIGH_VOLATILITY:
            if signals['volatility'].get('vix_level', 0) > 25:
                supporting['elevated_vix'] = signals['volatility']['vix_level']
            if signals['internals'].get('high_put_buying'):
                supporting['high_put_buying'] = True
                
        return supporting
        
    def _get_conflicting_indicators(self, signals: Dict[str, Any], regime: MarketRegime) -> Dict[str, Any]:
        """Get indicators conflicting with the detected regime."""
        conflicting = {}
        
        if regime == MarketRegime.BULL_TRENDING:
            if signals['trend'].get('rsi_overbought'):
                conflicting['rsi_overbought'] = signals['trend']['rsi']
            if signals['volume'].get('strong_selling'):
                conflicting['high_selling_volume'] = True
                
        elif regime == MarketRegime.LOW_VOLATILITY:
            if signals['breadth'].get('broad_weakness'):
                conflicting['weak_market_breadth'] = True
                
        return conflicting
        
    def _get_regime_strategies(self, market_regime: MarketRegime, 
                              volatility_regime: VolatilityRegime) -> List[str]:
        """Get recommended strategies for regime combination."""
        strategies = []
        
        # Market regime strategies
        regime_strategies = {
            MarketRegime.BULL_TRENDING: [
                "Sell puts on pullbacks",
                "Buy calls on dips",
                "Use bull put spreads"
            ],
            MarketRegime.BEAR_TRENDING: [
                "Buy puts on rallies",
                "Avoid selling puts",
                "Use bear call spreads"
            ],
            MarketRegime.RANGE_BOUND: [
                "Sell strangles at range extremes",
                "Iron condors",
                "Mean reversion trades"
            ],
            MarketRegime.HIGH_VOLATILITY: [
                "Reduce position sizes",
                "Buy protective puts",
                "Wait for volatility compression"
            ],
            MarketRegime.LOW_VOLATILITY: [
                "Aggressive premium selling",
                "Increase position sizes",
                "Sell closer to the money"
            ],
            MarketRegime.CRASH_CONDITIONS: [
                "Exit all positions",
                "Buy puts for protection",
                "Wait for stability"
            ],
            MarketRegime.EUPHORIA: [
                "Take profits",
                "Reduce exposure",
                "Buy protective puts"
            ]
        }
        
        strategies.extend(regime_strategies.get(market_regime, ["Monitor closely"]))
        
        # Adjust for volatility
        if volatility_regime in [VolatilityRegime.EXTREMELY_LOW, VolatilityRegime.LOW]:
            strategies.append("Focus on premium collection")
        elif volatility_regime in [VolatilityRegime.HIGH, VolatilityRegime.VERY_HIGH]:
            strategies.append("Consider long volatility plays")
            
        return strategies
        
    def _get_risk_adjustments(self, market_regime: MarketRegime,
                             volatility_regime: VolatilityRegime) -> Dict[str, float]:
        """Get risk parameter adjustments for regime."""
        adjustments = {
            'position_size_multiplier': 1.0,
            'stop_loss_multiplier': 1.0,
            'max_risk_multiplier': 1.0
        }
        
        # Market regime adjustments
        if market_regime in [MarketRegime.HIGH_VOLATILITY, MarketRegime.CRASH_CONDITIONS]:
            adjustments['position_size_multiplier'] = 0.5
            adjustments['stop_loss_multiplier'] = 0.8
            adjustments['max_risk_multiplier'] = 0.5
        elif market_regime == MarketRegime.LOW_VOLATILITY:
            adjustments['position_size_multiplier'] = 1.5
            adjustments['stop_loss_multiplier'] = 1.2
            
        # Volatility adjustments
        if volatility_regime == VolatilityRegime.EXTREME:
            adjustments['position_size_multiplier'] *= 0.3
        elif volatility_regime == VolatilityRegime.EXTREMELY_LOW:
            adjustments['position_size_multiplier'] *= 1.3
            
        return adjustments
        
    def _calculate_position_sizing(self, market_regime: MarketRegime,
                                 volatility_regime: VolatilityRegime,
                                 stability: float) -> float:
        """Calculate position sizing factor."""
        base_factor = 1.0
        
        # Market regime factor
        regime_factors = {
            MarketRegime.BULL_TRENDING: 1.2,
            MarketRegime.BEAR_TRENDING: 0.8,
            MarketRegime.RANGE_BOUND: 1.0,
            MarketRegime.HIGH_VOLATILITY: 0.6,
            MarketRegime.LOW_VOLATILITY: 1.4,
            MarketRegime.CRASH_CONDITIONS: 0.2,
            MarketRegime.EUPHORIA: 0.7,
            MarketRegime.ACCUMULATION: 0.9,
            MarketRegime.DISTRIBUTION: 0.8
        }
        
        regime_factor = regime_factors.get(market_regime, 1.0)
        
        # Volatility factor
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
        
        # Stability factor (0.5 to 1.5)
        stability_factor = 0.5 + stability
        
        return base_factor * regime_factor * vol_factor * stability_factor
        
    def _get_regime_change_implications(self, from_regime: MarketRegime, 
                                      to_regime: MarketRegime) -> Dict[str, Any]:
        """Get implications of regime change for trading."""
        implications = {
            'action_required': 'monitor',
            'position_adjustment': 'none',
            'risk_level_change': 'none',
            'strategy_change': False
        }
        
        # Critical transitions requiring immediate action
        critical_transitions = [
            (MarketRegime.LOW_VOLATILITY, MarketRegime.HIGH_VOLATILITY),
            (MarketRegime.BULL_TRENDING, MarketRegime.CRASH_CONDITIONS),
            (MarketRegime.RANGE_BOUND, MarketRegime.CRASH_CONDITIONS)
        ]
        
        if (from_regime, to_regime) in critical_transitions:
            implications['action_required'] = 'immediate'
            implications['position_adjustment'] = 'reduce_all'
            implications['risk_level_change'] = 'decrease'
            implications['strategy_change'] = True
            
        # Favorable transitions
        favorable_transitions = [
            (MarketRegime.HIGH_VOLATILITY, MarketRegime.LOW_VOLATILITY),
            (MarketRegime.BEAR_TRENDING, MarketRegime.BULL_TRENDING),
            (MarketRegime.ACCUMULATION, MarketRegime.BULL_TRENDING)
        ]
        
        if (from_regime, to_regime) in favorable_transitions:
            implications['action_required'] = 'review'
            implications['position_adjustment'] = 'consider_increase'
            implications['risk_level_change'] = 'increase'
            implications['strategy_change'] = True
            
        return implications
        
    # Background Monitoring
    
    async def _monitor_regime_changes(self) -> None:
        """Background task to monitor for regime changes."""
        while True:
            try:
                # Detect current regime
                analysis = await self.detect_current_regime()
                
                # Update stability score
                self.regime_stability_scores.append(analysis.regime_stability)
                
                # Store analysis
                await self.mcp.store_memory(
                    "MarketRegimeDetector",
                    MemorySlice(
                        memory_type=MemoryType.MARKET_OBSERVATION,
                        content={
                            'regime_analysis': analysis.dict(),
                            'timestamp': datetime.utcnow().isoformat()
                        },
                        importance=MemoryImportance.HIGH if analysis.regime_confidence > 0.8 else MemoryImportance.MEDIUM
                    )
                )
                
                # Sleep before next check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Regime monitoring error: {e}")
                await asyncio.sleep(60)
                
    async def _store_regime_change(self, transition: RegimeTransition) -> None:
        """Store regime change in MCP."""
        await self.mcp.store_memory(
            "MarketRegimeDetector",
            MemorySlice(
                memory_type=MemoryType.MARKET_OBSERVATION,
                content={
                    'regime_transition': {
                        'from': transition.from_regime.value,
                        'to': transition.to_regime.value,
                        'timestamp': transition.timestamp.isoformat(),
                        'confidence': transition.confidence,
                        'duration_in_previous': transition.duration_in_previous.total_seconds()
                    }
                },
                importance=MemoryImportance.CRITICAL
            )
        )
        
    async def _load_regime_history(self) -> None:
        """Load historical regime data from MCP."""
        memories = await self.mcp.semantic_search(
            "MarketRegimeDetector",
            "regime transition history market regime change",
            scope="own"
        )
        
        for memory in memories:
            if 'regime_transition' in memory.content:
                # Reconstruct transition
                data = memory.content['regime_transition']
                transition = RegimeTransition(
                    from_regime=MarketRegime(data['from']),
                    to_regime=MarketRegime(data['to']),
                    timestamp=datetime.fromisoformat(data['timestamp']),
                    confidence=data['confidence']
                )
                self.transition_history.append(transition)
                
    async def _save_regime_history(self) -> None:
        """Save regime history to MCP."""
        history_data = {
            'current_regime': self.current_regime.value,
            'regime_start_time': self.regime_start_time.isoformat(),
            'transition_count': len(self.transition_history),
            'recent_transitions': [
                {
                    'from': t.from_regime.value,
                    'to': t.to_regime.value,
                    'timestamp': t.timestamp.isoformat(),
                    'confidence': t.confidence
                }
                for t in self.transition_history[-10:]  # Last 10 transitions
            ]
        }
        
        await self.mcp.store_memory(
            "MarketRegimeDetector",
            MemorySlice(
                memory_type=MemoryType.EVALUATION,
                content={
                    'regime_history': history_data,
                    'timestamp': datetime.utcnow().isoformat()
                },
                importance=MemoryImportance.HIGH
            )
        )