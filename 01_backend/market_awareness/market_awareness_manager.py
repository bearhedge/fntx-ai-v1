"""
Market Awareness Manager
High-level interface that integrates all market awareness components.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json

from ..mcp.context_manager import MCPContextManager
from ..mcp.schemas import MemorySlice, MemoryType, MemoryImportance
from ..services.ibkr_service import IBKRService
from .schemas import (
    MarketSnapshot, MarketDataPoint, MarketPattern, PatternType,
    MarketRegime, VolatilityRegime, RegimeAnalysis, TrendStrength,
    TechnicalIndicators, MarketEvent, EventType, EventPriority
)
from .market_data_collector import MarketDataCollector
from .pattern_recognition import PatternRecognitionEngine
from .regime_detector import MarketRegimeDetector

logger = logging.getLogger(__name__)


class MarketAwarenessState(Enum):
    """Market awareness system states."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    DEGRADED = "degraded"
    SUSPENDED = "suspended"
    SHUTDOWN = "shutdown"


class TradingRecommendation:
    """Trading recommendation based on market analysis."""
    
    def __init__(self):
        self.action = "WAIT"  # BUY, SELL, WAIT
        self.confidence = 0.0
        self.strategy = None
        self.timing = "immediate"
        self.risk_adjustments = {}
        self.reasoning = []
        self.warnings = []
        

class MarketAwarenessManager:
    """
    Unified interface for market awareness capabilities.
    Integrates data collection, pattern recognition, and regime detection.
    """
    
    def __init__(self, mcp_manager: MCPContextManager, ibkr_service: Optional[IBKRService] = None):
        self.mcp = mcp_manager
        self.ibkr = ibkr_service
        
        # Initialize components
        self.data_collector = MarketDataCollector(mcp_manager, ibkr_service)
        self.pattern_engine = PatternRecognitionEngine(mcp_manager)
        self.regime_detector = MarketRegimeDetector(mcp_manager, self.data_collector)
        
        # State management
        self.state = MarketAwarenessState.INITIALIZING
        self.last_analysis_time = None
        self.analysis_interval = 30  # seconds
        
        # Alert management
        self.active_alerts: List[MarketEvent] = []
        self.alert_history: List[MarketEvent] = []
        
        # Performance tracking
        self.recommendation_history: List[Dict[str, Any]] = []
        self.accuracy_metrics = {
            'recommendations_made': 0,
            'successful_recommendations': 0,
            'failed_recommendations': 0
        }
        
        # Background tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._alert_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> None:
        """Initialize the market awareness system."""
        try:
            logger.info("Initializing Market Awareness Manager")
            
            # Register with MCP
            await self.mcp.register_agent(
                "MarketAwarenessManager",
                ["market_analysis", "pattern_detection", "regime_analysis", "trading_signals"]
            )
            
            # Initialize components
            await self.data_collector.initialize()
            await self.pattern_engine.initialize()
            await self.regime_detector.initialize()
            
            # Subscribe to key symbols
            await self.data_collector.subscribe("SPY")
            await self.data_collector.subscribe("VIX")
            await self.data_collector.subscribe("DXY")
            await self.data_collector.subscribe("TNX")
            
            # Start background tasks
            self._monitoring_task = asyncio.create_task(self._monitor_markets())
            self._alert_task = asyncio.create_task(self._process_alerts())
            
            self.state = MarketAwarenessState.ACTIVE
            logger.info("Market Awareness Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Market Awareness Manager: {e}")
            self.state = MarketAwarenessState.DEGRADED
            raise
            
    async def shutdown(self) -> None:
        """Shutdown the market awareness system."""
        logger.info("Shutting down Market Awareness Manager")
        self.state = MarketAwarenessState.SHUTDOWN
        
        # Cancel background tasks
        if self._monitoring_task:
            self._monitoring_task.cancel()
        if self._alert_task:
            self._alert_task.cancel()
            
        # Wait for tasks to complete
        await asyncio.gather(
            self._monitoring_task,
            self._alert_task,
            return_exceptions=True
        )
        
        # Shutdown components
        await self.data_collector.shutdown()
        await self.pattern_engine.shutdown()
        await self.regime_detector.shutdown()
        
        logger.info("Market Awareness Manager shut down")
        
    # Core Analysis Methods
    
    async def get_comprehensive_analysis(self) -> Dict[str, Any]:
        """
        Get comprehensive market analysis combining all components.
        
        Returns:
            Complete market analysis with snapshot, patterns, regime, and recommendations
        """
        # Get market snapshot
        snapshot = await self.data_collector.get_market_snapshot()
        
        # Get technical indicators
        spy_indicators = await self.data_collector.calculate_technical_indicators("SPY")
        vix_indicators = await self.data_collector.calculate_technical_indicators("VIX")
        
        # Get regime analysis
        regime_analysis = await self.regime_detector.detect_current_regime()
        
        # Get patterns
        spy_data = list(self.data_collector.market_data.get("SPY", []))
        patterns = await self.pattern_engine.detect_patterns("SPY", spy_data, spy_indicators)
        
        # Generate trading recommendation
        recommendation = await self._generate_trading_recommendation(
            snapshot, regime_analysis, patterns, spy_indicators
        )
        
        # Check for alerts
        alerts = await self._check_for_alerts(snapshot, regime_analysis, patterns)
        
        # Compile analysis
        analysis = {
            'timestamp': datetime.utcnow().isoformat(),
            'state': self.state.value,
            'market_snapshot': snapshot.dict(),
            'technical_indicators': {
                'SPY': spy_indicators.dict() if spy_indicators else None,
                'VIX': vix_indicators.dict() if vix_indicators else None
            },
            'regime_analysis': regime_analysis.dict(),
            'active_patterns': [p.dict() for p in patterns],
            'trading_recommendation': {
                'action': recommendation.action,
                'confidence': recommendation.confidence,
                'strategy': recommendation.strategy,
                'timing': recommendation.timing,
                'risk_adjustments': recommendation.risk_adjustments,
                'reasoning': recommendation.reasoning,
                'warnings': recommendation.warnings
            },
            'active_alerts': [a.dict() for a in alerts],
            'market_conditions': {
                'market_open': self.data_collector.market_open,
                'extended_hours': self.data_collector.extended_hours,
                'liquidity_assessment': await self._assess_liquidity(snapshot)
            }
        }
        
        # Store analysis in MCP
        await self._store_analysis(analysis)
        
        # Update last analysis time
        self.last_analysis_time = datetime.utcnow()
        
        return analysis
        
    async def get_trading_signals(self) -> List[Dict[str, Any]]:
        """
        Get actionable trading signals based on current market conditions.
        
        Returns:
            List of trading signals with entry/exit points
        """
        signals = []
        
        # Get current analysis
        analysis = await self.get_comprehensive_analysis()
        
        # Extract patterns with high confidence
        patterns = analysis['active_patterns']
        high_confidence_patterns = [p for p in patterns if p['confidence'] >= 0.8]
        
        # Generate signals from patterns
        for pattern in high_confidence_patterns:
            signal = await self._pattern_to_signal(pattern, analysis)
            if signal:
                signals.append(signal)
                
        # Add regime-based signals
        regime_signals = await self._get_regime_signals(analysis['regime_analysis'])
        signals.extend(regime_signals)
        
        # Filter and prioritize signals
        signals = self._prioritize_signals(signals)
        
        return signals
        
    async def evaluate_trade_setup(self, strategy: str, strike: float, 
                                 expiration: str) -> Dict[str, Any]:
        """
        Evaluate a specific trade setup.
        
        Args:
            strategy: Trading strategy (e.g., "SPY_PUT_SELL")
            strike: Strike price
            expiration: Expiration date
            
        Returns:
            Evaluation results with risk assessment
        """
        # Get current market analysis
        analysis = await self.get_comprehensive_analysis()
        
        evaluation = {
            'strategy': strategy,
            'strike': strike,
            'expiration': expiration,
            'timestamp': datetime.utcnow().isoformat(),
            'market_alignment': 0.0,
            'risk_score': 0.0,
            'opportunity_score': 0.0,
            'warnings': [],
            'supportive_factors': [],
            'risk_factors': []
        }
        
        # Check market regime alignment
        regime = analysis['regime_analysis']['market_regime']
        if strategy == "SPY_PUT_SELL":
            if regime in ['BULL_TRENDING', 'LOW_VOLATILITY', 'RANGE_BOUND']:
                evaluation['market_alignment'] = 0.8
                evaluation['supportive_factors'].append(f"Market regime ({regime}) favorable for put selling")
            elif regime in ['BEAR_TRENDING', 'HIGH_VOLATILITY', 'CRASH_CONDITIONS']:
                evaluation['market_alignment'] = 0.2
                evaluation['risk_factors'].append(f"Market regime ({regime}) unfavorable for put selling")
            else:
                evaluation['market_alignment'] = 0.5
                
        # Check technical levels
        spy_price = analysis['market_snapshot']['spy']['price']
        if spy_price > 0:
            distance_percentage = ((spy_price - strike) / spy_price) * 100
            
            if distance_percentage < 1:
                evaluation['risk_factors'].append("Strike very close to current price")
                evaluation['risk_score'] += 0.3
            elif distance_percentage > 5:
                evaluation['supportive_factors'].append("Strike has good distance from current price")
                evaluation['opportunity_score'] += 0.2
                
        # Check volatility conditions
        vix_level = analysis['market_snapshot']['vix']['price']
        vol_regime = analysis['regime_analysis']['volatility_regime']
        
        if vol_regime in ['EXTREMELY_LOW', 'LOW']:
            evaluation['warnings'].append("Low volatility may result in small premiums")
        elif vol_regime in ['HIGH', 'VERY_HIGH', 'EXTREME']:
            evaluation['warnings'].append("High volatility increases risk")
            evaluation['risk_score'] += 0.2
            
        # Check patterns
        for pattern in analysis['active_patterns']:
            if pattern['pattern_type'] == 'SUPPORT_BOUNCE' and pattern['bullish_bias']:
                evaluation['supportive_factors'].append("Support bounce pattern detected")
                evaluation['opportunity_score'] += 0.1
            elif pattern['pattern_type'] == 'RESISTANCE_REJECTION' and not pattern['bullish_bias']:
                evaluation['risk_factors'].append("Resistance rejection pattern detected")
                evaluation['risk_score'] += 0.1
                
        # Calculate final scores
        evaluation['opportunity_score'] = min(evaluation['opportunity_score'], 1.0)
        evaluation['risk_score'] = min(evaluation['risk_score'], 1.0)
        
        # Generate recommendation
        if evaluation['opportunity_score'] > 0.7 and evaluation['risk_score'] < 0.3:
            evaluation['recommendation'] = "PROCEED"
        elif evaluation['risk_score'] > 0.7:
            evaluation['recommendation'] = "AVOID"
        else:
            evaluation['recommendation'] = "PROCEED_WITH_CAUTION"
            
        return evaluation
        
    # Alert Management
    
    async def register_alert(self, condition: str, threshold: float, 
                           callback: Optional[Callable] = None) -> str:
        """
        Register a custom alert condition.
        
        Args:
            condition: Alert condition (e.g., "VIX_ABOVE", "SPY_SUPPORT_BREAK")
            threshold: Threshold value
            callback: Optional callback when alert triggers
            
        Returns:
            Alert ID
        """
        alert_id = f"alert_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{len(self.active_alerts)}"
        
        alert = MarketEvent(
            event_type=EventType.ALERT,
            symbol="MARKET",
            description=f"{condition} threshold: {threshold}",
            priority=EventPriority.HIGH,
            data={
                'alert_id': alert_id,
                'condition': condition,
                'threshold': threshold,
                'callback': callback,
                'created_at': datetime.utcnow().isoformat()
            }
        )
        
        self.active_alerts.append(alert)
        
        logger.info(f"Registered alert: {alert_id} for {condition}")
        return alert_id
        
    async def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts."""
        return [
            {
                'alert_id': a.data.get('alert_id'),
                'condition': a.data.get('condition'),
                'threshold': a.data.get('threshold'),
                'created_at': a.data.get('created_at'),
                'triggered': a.data.get('triggered', False)
            }
            for a in self.active_alerts
        ]
        
    # Performance Tracking
    
    async def track_recommendation_outcome(self, recommendation_id: str, 
                                         outcome: str, profit_loss: float) -> None:
        """
        Track the outcome of a recommendation.
        
        Args:
            recommendation_id: ID of the recommendation
            outcome: "SUCCESS", "FAILURE", or "NEUTRAL"
            profit_loss: Profit or loss amount
        """
        # Find recommendation
        recommendation = None
        for rec in self.recommendation_history:
            if rec.get('id') == recommendation_id:
                recommendation = rec
                break
                
        if recommendation:
            recommendation['outcome'] = outcome
            recommendation['profit_loss'] = profit_loss
            recommendation['resolved_at'] = datetime.utcnow().isoformat()
            
            # Update metrics
            self.accuracy_metrics['recommendations_made'] += 1
            if outcome == "SUCCESS":
                self.accuracy_metrics['successful_recommendations'] += 1
            elif outcome == "FAILURE":
                self.accuracy_metrics['failed_recommendations'] += 1
                
            # Store in MCP
            await self.mcp.store_memory(
                "MarketAwarenessManager",
                MemorySlice(
                    memory_type=MemoryType.EVALUATION,
                    content={
                        'recommendation_outcome': recommendation,
                        'accuracy_metrics': self.accuracy_metrics
                    },
                    importance=MemoryImportance.HIGH
                )
            )
            
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the market awareness system."""
        total = self.accuracy_metrics['recommendations_made']
        success = self.accuracy_metrics['successful_recommendations']
        
        metrics = {
            'total_recommendations': total,
            'successful_recommendations': success,
            'failed_recommendations': self.accuracy_metrics['failed_recommendations'],
            'success_rate': success / total if total > 0 else 0,
            'pattern_detection_stats': await self.pattern_engine.get_pattern_statistics(),
            'regime_detection_accuracy': await self._calculate_regime_accuracy(),
            'alert_statistics': {
                'total_alerts': len(self.alert_history),
                'active_alerts': len(self.active_alerts),
                'false_positive_rate': await self._calculate_alert_false_positive_rate()
            }
        }
        
        return metrics
        
    # Private Helper Methods
    
    async def _generate_trading_recommendation(self, snapshot: MarketSnapshot,
                                             regime: RegimeAnalysis,
                                             patterns: List[MarketPattern],
                                             indicators: Optional[TechnicalIndicators]) -> TradingRecommendation:
        """Generate trading recommendation based on all inputs."""
        recommendation = TradingRecommendation()
        
        # Check market hours first
        if not self.data_collector.market_open and not self.data_collector.extended_hours:
            recommendation.action = "WAIT"
            recommendation.timing = "wait_for_open"
            recommendation.reasoning.append("Market is closed")
            return recommendation
            
        # Analyze regime
        if regime.market_regime == MarketRegime.CRASH_CONDITIONS:
            recommendation.action = "WAIT"
            recommendation.confidence = 0.9
            recommendation.warnings.append("Crash conditions detected - avoid trading")
            recommendation.reasoning.append("Market in crash conditions")
            return recommendation
            
        # Score different factors
        regime_score = self._score_regime_for_trading(regime)
        pattern_score = self._score_patterns_for_trading(patterns)
        technical_score = self._score_technicals_for_trading(indicators)
        
        # Combine scores
        total_score = (regime_score * 0.4 + pattern_score * 0.3 + technical_score * 0.3)
        
        # Generate recommendation
        if total_score > 0.7:
            recommendation.action = "SELL"  # Sell premium
            recommendation.confidence = total_score
            recommendation.strategy = "SPY_PUT_SELL"
            recommendation.reasoning.append(f"High confidence score: {total_score:.2f}")
            
            # Add specific reasoning
            if regime_score > 0.7:
                recommendation.reasoning.append(f"Favorable market regime: {regime.market_regime.value}")
            if pattern_score > 0.7:
                recommendation.reasoning.append("Supportive technical patterns detected")
            if technical_score > 0.7:
                recommendation.reasoning.append("Technical indicators favorable")
                
        elif total_score < 0.3:
            recommendation.action = "WAIT"
            recommendation.confidence = 1 - total_score
            recommendation.reasoning.append(f"Low confidence score: {total_score:.2f}")
            recommendation.warnings.append("Unfavorable market conditions")
        else:
            recommendation.action = "WAIT"
            recommendation.confidence = 0.5
            recommendation.timing = "monitor"
            recommendation.reasoning.append("Mixed signals - continue monitoring")
            
        # Add risk adjustments
        recommendation.risk_adjustments = {
            'position_size_multiplier': regime.position_sizing_factor,
            'stop_loss_adjustment': regime.risk_adjustments.get('stop_loss_multiplier', 1.0),
            'take_profit_adjustment': 1.0
        }
        
        return recommendation
        
    def _score_regime_for_trading(self, regime: RegimeAnalysis) -> float:
        """Score regime favorability for trading."""
        # Favorable regimes for selling options
        favorable_regimes = {
            MarketRegime.BULL_TRENDING: 0.8,
            MarketRegime.LOW_VOLATILITY: 0.9,
            MarketRegime.RANGE_BOUND: 0.7,
            MarketRegime.ACCUMULATION: 0.6
        }
        
        # Unfavorable regimes
        unfavorable_regimes = {
            MarketRegime.CRASH_CONDITIONS: 0.0,
            MarketRegime.HIGH_VOLATILITY: 0.2,
            MarketRegime.BEAR_TRENDING: 0.3,
            MarketRegime.DISTRIBUTION: 0.4
        }
        
        base_score = favorable_regimes.get(
            regime.market_regime,
            unfavorable_regimes.get(regime.market_regime, 0.5)
        )
        
        # Adjust for confidence and stability
        score = base_score * regime.regime_confidence * regime.regime_stability
        
        return score
        
    def _score_patterns_for_trading(self, patterns: List[MarketPattern]) -> float:
        """Score patterns for trading opportunity."""
        if not patterns:
            return 0.5  # Neutral
            
        positive_patterns = 0
        negative_patterns = 0
        
        for pattern in patterns:
            if pattern.pattern_type == PatternType.SUPPORT_BOUNCE and pattern.bullish_bias:
                positive_patterns += pattern.confidence
            elif pattern.pattern_type == PatternType.DOUBLE_BOTTOM and pattern.bullish_bias:
                positive_patterns += pattern.confidence * 0.8
            elif pattern.pattern_type == PatternType.FLAG and pattern.bullish_bias:
                positive_patterns += pattern.confidence * 0.6
            elif pattern.pattern_type == PatternType.RESISTANCE_REJECTION and not pattern.bullish_bias:
                negative_patterns += pattern.confidence
            elif pattern.pattern_type == PatternType.DOUBLE_TOP and not pattern.bullish_bias:
                negative_patterns += pattern.confidence * 0.8
                
        # Calculate net score
        net_score = positive_patterns - negative_patterns
        
        # Normalize to 0-1 range
        max_possible = len(patterns)
        normalized_score = (net_score + max_possible) / (2 * max_possible)
        
        return max(0.0, min(1.0, normalized_score))
        
    def _score_technicals_for_trading(self, indicators: Optional[TechnicalIndicators]) -> float:
        """Score technical indicators for trading."""
        if not indicators:
            return 0.5  # Neutral
            
        score = 0.5  # Start neutral
        factors = 0
        
        # RSI
        if indicators.rsi:
            factors += 1
            if 30 < indicators.rsi < 70:
                score += 0.1  # Neutral range good for selling
            elif indicators.rsi < 30:
                score += 0.2  # Oversold - potential bounce
            else:
                score -= 0.1  # Overbought - be cautious
                
        # Moving averages
        if indicators.sma_20 and indicators.sma_50 and indicators.sma_200:
            factors += 1
            if indicators.sma_20 > indicators.sma_50 > indicators.sma_200:
                score += 0.2  # Bullish alignment
            elif indicators.sma_20 < indicators.sma_50 < indicators.sma_200:
                score -= 0.2  # Bearish alignment
                
        # Bollinger Bands
        if indicators.bollinger_upper and indicators.bollinger_lower:
            factors += 1
            # Check if price is not at extremes
            # This would need current price passed in
            score += 0.1  # Assume neutral for now
            
        # Normalize
        if factors > 0:
            score = score / (1 + factors * 0.2)  # Normalize based on factors considered
            
        return max(0.0, min(1.0, score))
        
    async def _pattern_to_signal(self, pattern: Dict[str, Any], 
                               analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert a pattern to a trading signal."""
        if pattern['pattern_type'] in ['SUPPORT_BOUNCE', 'DOUBLE_BOTTOM'] and pattern['bullish_bias']:
            signal = {
                'type': 'SELL_PUT',
                'symbol': pattern['symbol'],
                'entry_trigger': pattern['key_levels'][0] if pattern['key_levels'] else None,
                'stop_loss': pattern['stop_loss'],
                'target': pattern['target_price'],
                'confidence': pattern['confidence'],
                'pattern': pattern['pattern_type'],
                'timing': 'immediate' if pattern['confidence'] > 0.85 else 'wait_confirmation'
            }
            return signal
            
        return None
        
    async def _get_regime_signals(self, regime_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate signals based on regime analysis."""
        signals = []
        
        regime = regime_analysis['market_regime']
        volatility = regime_analysis['volatility_regime']
        
        if regime == 'LOW_VOLATILITY' and volatility in ['EXTREMELY_LOW', 'LOW']:
            signals.append({
                'type': 'INCREASE_SIZING',
                'confidence': regime_analysis['regime_confidence'],
                'reasoning': 'Low volatility regime favorable for selling premium',
                'adjustment': regime_analysis['position_sizing_factor']
            })
            
        return signals
        
    def _prioritize_signals(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize and filter signals."""
        # Sort by confidence
        signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        # Take top 3
        return signals[:3]
        
    async def _check_for_alerts(self, snapshot: MarketSnapshot,
                              regime: RegimeAnalysis,
                              patterns: List[MarketPattern]) -> List[MarketEvent]:
        """Check for alert conditions."""
        triggered_alerts = []
        
        for alert in self.active_alerts:
            if alert.data.get('triggered'):
                continue
                
            condition = alert.data.get('condition')
            threshold = alert.data.get('threshold')
            
            triggered = False
            
            if condition == "VIX_ABOVE" and snapshot.vix.price > threshold:
                triggered = True
            elif condition == "VIX_BELOW" and snapshot.vix.price < threshold:
                triggered = True
            elif condition == "SPY_ABOVE" and snapshot.spy.price > threshold:
                triggered = True
            elif condition == "SPY_BELOW" and snapshot.spy.price < threshold:
                triggered = True
            elif condition == "REGIME_CHANGE" and regime.market_regime.value != alert.data.get('last_regime'):
                triggered = True
                alert.data['last_regime'] = regime.market_regime.value
                
            if triggered:
                alert.data['triggered'] = True
                alert.data['triggered_at'] = datetime.utcnow().isoformat()
                triggered_alerts.append(alert)
                
                # Execute callback if provided
                callback = alert.data.get('callback')
                if callback:
                    try:
                        await callback(alert)
                    except Exception as e:
                        logger.error(f"Alert callback error: {e}")
                        
        return triggered_alerts
        
    async def _assess_liquidity(self, snapshot: MarketSnapshot) -> str:
        """Assess market liquidity conditions."""
        # Simple liquidity assessment based on time and volatility
        if not self.data_collector.market_open:
            return "POOR"
            
        if snapshot.vix.price > 30:
            return "STRESSED"
        elif snapshot.vix.price < 15:
            return "EXCELLENT"
        else:
            return "NORMAL"
            
    async def _store_analysis(self, analysis: Dict[str, Any]) -> None:
        """Store analysis in MCP."""
        # Store full analysis
        await self.mcp.store_memory(
            "MarketAwarenessManager",
            MemorySlice(
                memory_type=MemoryType.MARKET_OBSERVATION,
                content={
                    'comprehensive_analysis': analysis,
                    'timestamp': datetime.utcnow().isoformat()
                },
                importance=MemoryImportance.HIGH
            )
        )
        
        # Share key insights with other agents
        await self.mcp.share_context(
            "MarketAwarenessManager",
            ["StrategicPlannerAgent", "TacticalExecutorAgent", "RiskManagerAgent"],
            {
                'market_update': {
                    'trading_recommendation': analysis['trading_recommendation']['action'],
                    'confidence': analysis['trading_recommendation']['confidence'],
                    'market_regime': analysis['regime_analysis']['market_regime'],
                    'active_patterns': len(analysis['active_patterns']),
                    'warnings': analysis['trading_recommendation']['warnings']
                }
            }
        )
        
        # Track recommendation
        if analysis['trading_recommendation']['action'] != "WAIT":
            recommendation_record = {
                'id': f"rec_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                'timestamp': analysis['timestamp'],
                'action': analysis['trading_recommendation']['action'],
                'confidence': analysis['trading_recommendation']['confidence'],
                'market_conditions': {
                    'regime': analysis['regime_analysis']['market_regime'],
                    'spy_price': analysis['market_snapshot']['spy']['price'],
                    'vix_level': analysis['market_snapshot']['vix']['price']
                }
            }
            self.recommendation_history.append(recommendation_record)
            
    # Background Tasks
    
    async def _monitor_markets(self) -> None:
        """Background task to monitor markets."""
        while self.state != MarketAwarenessState.SHUTDOWN:
            try:
                if self.state == MarketAwarenessState.ACTIVE:
                    # Check if analysis needed
                    if (self.last_analysis_time is None or 
                        datetime.utcnow() - self.last_analysis_time > timedelta(seconds=self.analysis_interval)):
                        
                        # Run comprehensive analysis
                        await self.get_comprehensive_analysis()
                        
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Market monitoring error: {e}")
                if self.state == MarketAwarenessState.ACTIVE:
                    self.state = MarketAwarenessState.DEGRADED
                await asyncio.sleep(10)
                
    async def _process_alerts(self) -> None:
        """Background task to process alerts."""
        while self.state != MarketAwarenessState.SHUTDOWN:
            try:
                # Check alerts
                snapshot = await self.data_collector.get_market_snapshot()
                regime = await self.regime_detector.detect_current_regime()
                patterns = []  # Would get from pattern engine
                
                triggered = await self._check_for_alerts(snapshot, regime, patterns)
                
                # Move triggered alerts to history
                for alert in triggered:
                    self.alert_history.append(alert)
                    self.active_alerts.remove(alert)
                    
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Alert processing error: {e}")
                await asyncio.sleep(30)
                
    async def _calculate_regime_accuracy(self) -> float:
        """Calculate regime detection accuracy."""
        # This would analyze historical regime predictions vs actual outcomes
        # For now, return a placeholder
        return 0.85
        
    async def _calculate_alert_false_positive_rate(self) -> float:
        """Calculate alert false positive rate."""
        if not self.alert_history:
            return 0.0
            
        # This would analyze alert outcomes
        # For now, return a placeholder
        return 0.15