"""
Learning Engine
Analyzes performance data to generate insights and strategy improvements.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import json

from ..mcp.context_manager import MCPContextManager
from ..mcp.schemas import MemorySlice, MemoryType, MemoryImportance
from .schemas import (
    TradeOutcome, PerformanceSnapshot, LearningInsight, StrategyAdjustment,
    InsightCategory, LearningType, ReflectionPeriod
)
from .performance_tracker import PerformanceTracker

logger = logging.getLogger(__name__)


class LearningEngine:
    """
    Generates insights and learns from trading performance.
    """
    
    def __init__(self, mcp_manager: MCPContextManager, performance_tracker: PerformanceTracker):
        self.mcp = mcp_manager
        self.performance_tracker = performance_tracker
        
        # Insight storage
        self.insights: List[LearningInsight] = []
        self.insight_index: Dict[str, LearningInsight] = {}
        
        # Pattern detection
        self.success_patterns: List[Dict[str, Any]] = []
        self.failure_patterns: List[Dict[str, Any]] = []
        
        # Learning state
        self.learning_confidence: Dict[str, float] = defaultdict(float)
        self.validated_insights: Set[str] = set()
        
        # Configuration
        self.min_trades_for_insight = 10
        self.confidence_threshold = 0.7
        self.pattern_similarity_threshold = 0.8
        
        # Background tasks
        self._analysis_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> None:
        """Initialize the learning engine."""
        # Register with MCP
        await self.mcp.register_agent(
            "LearningEngine",
            ["performance_analysis", "insight_generation", "strategy_optimization"]
        )
        
        # Load historical insights
        await self._load_historical_insights()
        
        # Start analysis task
        self._analysis_task = asyncio.create_task(self._continuous_learning())
        
        logger.info("Learning Engine initialized")
        
    async def shutdown(self) -> None:
        """Shutdown the engine."""
        if self._analysis_task:
            self._analysis_task.cancel()
            await asyncio.gather(self._analysis_task, return_exceptions=True)
            
        # Save current insights
        await self._save_insights()
        
        logger.info("Learning Engine shut down")
        
    # Insight Generation
    
    async def analyze_trades(self, trades: List[TradeOutcome], 
                           period: Optional[ReflectionPeriod] = None) -> List[LearningInsight]:
        """
        Analyze trades to generate insights.
        
        Args:
            trades: Trades to analyze
            period: Optional period specification
            
        Returns:
            List of generated insights
        """
        if len(trades) < self.min_trades_for_insight:
            return []
            
        insights = []
        
        # Analyze win/loss patterns
        pattern_insights = await self._analyze_patterns(trades)
        insights.extend(pattern_insights)
        
        # Analyze market conditions
        market_insights = await self._analyze_market_conditions(trades)
        insights.extend(market_insights)
        
        # Analyze timing
        timing_insights = await self._analyze_timing(trades)
        insights.extend(timing_insights)
        
        # Analyze risk management
        risk_insights = await self._analyze_risk_management(trades)
        insights.extend(risk_insights)
        
        # Analyze strategy performance
        strategy_insights = await self._analyze_strategy_performance(trades)
        insights.extend(strategy_insights)
        
        # Filter by confidence
        high_confidence_insights = [i for i in insights if i.confidence >= self.confidence_threshold]
        
        # Store insights
        for insight in high_confidence_insights:
            self.insights.append(insight)
            self.insight_index[insight.insight_id] = insight
            await self._store_insight(insight)
            
        return high_confidence_insights
        
    async def _analyze_patterns(self, trades: List[TradeOutcome]) -> List[LearningInsight]:
        """Analyze patterns in winning and losing trades."""
        insights = []
        
        # Separate wins and losses
        wins = [t for t in trades if t.success]
        losses = [t for t in trades if not t.success]
        
        # Find common patterns in wins
        if len(wins) >= 5:
            win_patterns = self._extract_trade_patterns(wins)
            
            for pattern in win_patterns:
                if pattern['frequency'] > 0.6:  # Pattern appears in >60% of wins
                    insight = LearningInsight(
                        insight_id=f"insight_pattern_win_{datetime.utcnow().timestamp()}",
                        category=InsightCategory.PATTERN_RECOGNITION,
                        confidence=pattern['frequency'],
                        observation=f"Winning trades often have: {pattern['description']}",
                        conclusion="This pattern is associated with successful trades",
                        evidence=[{
                            'pattern': pattern['pattern'],
                            'frequency': pattern['frequency'],
                            'sample_trades': pattern['trades'][:5]
                        }],
                        recommendations=[
                            f"Prioritize trades with {pattern['description']}",
                            "Increase position size when this pattern is present"
                        ],
                        expected_impact={
                            'win_rate': pattern['frequency'] * 0.1,
                            'profit_factor': 0.05
                        },
                        based_on_trades=[t.trade_id for t in wins],
                        learning_method=LearningType.PATTERN_BASED
                    )
                    insights.append(insight)
                    
        # Find common patterns in losses
        if len(losses) >= 5:
            loss_patterns = self._extract_trade_patterns(losses)
            
            for pattern in loss_patterns:
                if pattern['frequency'] > 0.6:
                    insight = LearningInsight(
                        insight_id=f"insight_pattern_loss_{datetime.utcnow().timestamp()}",
                        category=InsightCategory.RISK_MANAGEMENT,
                        confidence=pattern['frequency'],
                        observation=f"Losing trades often have: {pattern['description']}",
                        conclusion="This pattern is associated with failed trades",
                        evidence=[{
                            'pattern': pattern['pattern'],
                            'frequency': pattern['frequency'],
                            'sample_trades': pattern['trades'][:5]
                        }],
                        recommendations=[
                            f"Avoid trades with {pattern['description']}",
                            "Reduce position size when this pattern is present",
                            "Tighten stop loss in these conditions"
                        ],
                        expected_impact={
                            'win_rate': pattern['frequency'] * 0.15,
                            'max_drawdown': -0.1
                        },
                        based_on_trades=[t.trade_id for t in losses],
                        learning_method=LearningType.PATTERN_BASED
                    )
                    insights.append(insight)
                    
        return insights
        
    async def _analyze_market_conditions(self, trades: List[TradeOutcome]) -> List[LearningInsight]:
        """Analyze performance in different market conditions."""
        insights = []
        
        # Group trades by market regime
        regime_groups = defaultdict(list)
        for trade in trades:
            regime = trade.market_conditions.get('market_regime', 'unknown')
            regime_groups[regime].append(trade)
            
        # Analyze each regime
        for regime, regime_trades in regime_groups.items():
            if len(regime_trades) >= 5:
                wins = sum(1 for t in regime_trades if t.success)
                win_rate = wins / len(regime_trades)
                avg_return = np.mean([t.return_percentage for t in regime_trades])
                
                # Check if performance differs significantly from overall
                overall_win_rate = sum(1 for t in trades if t.success) / len(trades)
                
                if abs(win_rate - overall_win_rate) > 0.15:  # 15% difference
                    insight = LearningInsight(
                        insight_id=f"insight_regime_{regime}_{datetime.utcnow().timestamp()}",
                        category=InsightCategory.MARKET_ADAPTATION,
                        confidence=min(0.9, len(regime_trades) / 20),  # More trades = higher confidence
                        observation=f"Performance in {regime} regime: {win_rate:.1%} win rate",
                        conclusion=f"Strategy performs {'better' if win_rate > overall_win_rate else 'worse'} in {regime} conditions",
                        evidence=[{
                            'regime': regime,
                            'trades': len(regime_trades),
                            'win_rate': win_rate,
                            'avg_return': avg_return,
                            'overall_win_rate': overall_win_rate
                        }],
                        recommendations=self._get_regime_recommendations(regime, win_rate, overall_win_rate),
                        expected_impact={
                            'win_rate': (win_rate - overall_win_rate) * 0.5,
                            'sharpe_ratio': 0.1 if win_rate > overall_win_rate else -0.1
                        },
                        based_on_trades=[t.trade_id for t in regime_trades],
                        learning_method=LearningType.PATTERN_BASED
                    )
                    insights.append(insight)
                    
        return insights
        
    async def _analyze_timing(self, trades: List[TradeOutcome]) -> List[LearningInsight]:
        """Analyze timing patterns in trades."""
        insights = []
        
        # Analyze by hour of day
        hour_performance = defaultdict(lambda: {'trades': 0, 'wins': 0, 'total_return': 0})
        
        for trade in trades:
            hour = trade.entry_time.hour
            hour_performance[hour]['trades'] += 1
            hour_performance[hour]['total_return'] += trade.return_percentage
            if trade.success:
                hour_performance[hour]['wins'] += 1
                
        # Find best and worst hours
        best_hours = []
        worst_hours = []
        
        for hour, perf in hour_performance.items():
            if perf['trades'] >= 3:  # Minimum trades to consider
                win_rate = perf['wins'] / perf['trades']
                avg_return = perf['total_return'] / perf['trades']
                
                if win_rate > 0.7 and avg_return > 0:
                    best_hours.append((hour, win_rate, avg_return))
                elif win_rate < 0.3 or avg_return < -1:
                    worst_hours.append((hour, win_rate, avg_return))
                    
        # Generate insights for timing
        if best_hours:
            insight = LearningInsight(
                insight_id=f"insight_timing_best_{datetime.utcnow().timestamp()}",
                category=InsightCategory.TIMING_IMPROVEMENT,
                confidence=0.8,
                observation=f"Best trading hours: {[h[0] for h in best_hours]}",
                conclusion="Certain hours show consistently better performance",
                evidence=[{
                    'best_hours': best_hours,
                    'performance_data': dict(hour_performance)
                }],
                recommendations=[
                    f"Focus trading during hours: {[h[0] for h in best_hours]}",
                    "Increase position sizes during optimal hours",
                    "Consider automated trading during these periods"
                ],
                expected_impact={
                    'win_rate': 0.1,
                    'average_return': 0.5
                },
                based_on_trades=[t.trade_id for t in trades],
                learning_method=LearningType.PATTERN_BASED
            )
            insights.append(insight)
            
        if worst_hours:
            insight = LearningInsight(
                insight_id=f"insight_timing_worst_{datetime.utcnow().timestamp()}",
                category=InsightCategory.TIMING_IMPROVEMENT,
                confidence=0.8,
                observation=f"Worst trading hours: {[h[0] for h in worst_hours]}",
                conclusion="Certain hours show consistently poor performance",
                evidence=[{
                    'worst_hours': worst_hours,
                    'performance_data': dict(hour_performance)
                }],
                recommendations=[
                    f"Avoid trading during hours: {[h[0] for h in worst_hours]}",
                    "Reduce position sizes if trading during these hours",
                    "Require higher confidence signals during these periods"
                ],
                expected_impact={
                    'win_rate': 0.15,
                    'max_drawdown': -0.05
                },
                based_on_trades=[t.trade_id for t in trades],
                learning_method=LearningType.PATTERN_BASED
            )
            insights.append(insight)
            
        return insights
        
    async def _analyze_risk_management(self, trades: List[TradeOutcome]) -> List[LearningInsight]:
        """Analyze risk management effectiveness."""
        insights = []
        
        # Analyze stop loss effectiveness
        stop_hit_trades = [t for t in trades if t.stop_hit]
        if len(stop_hit_trades) >= 5:
            # Check if stops are too tight
            stop_to_target_ratios = []
            for trade in stop_hit_trades:
                if trade.max_favorable_excursion and trade.max_adverse_excursion:
                    ratio = abs(trade.max_favorable_excursion / trade.max_adverse_excursion)
                    stop_to_target_ratios.append(ratio)
                    
            if stop_to_target_ratios:
                avg_ratio = np.mean(stop_to_target_ratios)
                if avg_ratio > 2.0:  # Favorable move was 2x the adverse move
                    insight = LearningInsight(
                        insight_id=f"insight_risk_stops_{datetime.utcnow().timestamp()}",
                        category=InsightCategory.RISK_MANAGEMENT,
                        confidence=0.85,
                        observation=f"Stops being hit despite favorable price action (avg ratio: {avg_ratio:.2f})",
                        conclusion="Stop losses may be too tight",
                        evidence=[{
                            'stop_hit_count': len(stop_hit_trades),
                            'avg_favorable_ratio': avg_ratio,
                            'sample_trades': [t.trade_id for t in stop_hit_trades[:5]]
                        }],
                        recommendations=[
                            "Widen stop losses by 20-30%",
                            "Use volatility-based stops instead of fixed",
                            "Consider trailing stops after favorable movement"
                        ],
                        expected_impact={
                            'win_rate': 0.1,
                            'average_return': 0.3
                        },
                        based_on_trades=[t.trade_id for t in stop_hit_trades],
                        learning_method=LearningType.RULE_BASED
                    )
                    insights.append(insight)
                    
        # Analyze position sizing impact
        trades_by_size = defaultdict(list)
        for trade in trades:
            size_category = 'small' if trade.quantity <= 5 else ('medium' if trade.quantity <= 10 else 'large')
            trades_by_size[size_category].append(trade)
            
        size_performance = {}
        for size, size_trades in trades_by_size.items():
            if len(size_trades) >= 5:
                win_rate = sum(1 for t in size_trades if t.success) / len(size_trades)
                avg_return = np.mean([t.return_percentage for t in size_trades])
                size_performance[size] = {'win_rate': win_rate, 'avg_return': avg_return}
                
        # Check if smaller sizes perform better (indicating overconfidence in sizing)
        if len(size_performance) >= 2:
            if 'small' in size_performance and 'large' in size_performance:
                small_perf = size_performance['small']
                large_perf = size_performance['large']
                
                if small_perf['win_rate'] > large_perf['win_rate'] + 0.1:
                    insight = LearningInsight(
                        insight_id=f"insight_risk_sizing_{datetime.utcnow().timestamp()}",
                        category=InsightCategory.RISK_MANAGEMENT,
                        confidence=0.75,
                        observation="Smaller positions have higher win rates",
                        conclusion="May be oversizing positions on lower confidence trades",
                        evidence=[{
                            'size_performance': size_performance,
                            'trade_counts': {k: len(v) for k, v in trades_by_size.items()}
                        }],
                        recommendations=[
                            "Reduce default position sizes by 20%",
                            "Scale position size with confidence level",
                            "Implement Kelly Criterion for optimal sizing"
                        ],
                        expected_impact={
                            'win_rate': 0.05,
                            'risk_adjusted_return': 0.15
                        },
                        based_on_trades=[t.trade_id for t in trades],
                        learning_method=LearningType.PATTERN_BASED
                    )
                    insights.append(insight)
                    
        return insights
        
    async def _analyze_strategy_performance(self, trades: List[TradeOutcome]) -> List[LearningInsight]:
        """Analyze performance by strategy."""
        insights = []
        
        # Group by strategy
        strategy_groups = defaultdict(list)
        for trade in trades:
            strategy_groups[trade.strategy].append(trade)
            
        # Analyze each strategy
        strategy_performance = {}
        for strategy, strat_trades in strategy_groups.items():
            if len(strat_trades) >= 5:
                wins = sum(1 for t in strat_trades if t.success)
                win_rate = wins / len(strat_trades)
                avg_return = np.mean([t.return_percentage for t in strat_trades])
                profit_factor = self._calculate_profit_factor(strat_trades)
                
                strategy_performance[strategy] = {
                    'trades': len(strat_trades),
                    'win_rate': win_rate,
                    'avg_return': avg_return,
                    'profit_factor': profit_factor
                }
                
        # Find best performing strategy
        if len(strategy_performance) >= 2:
            best_strategy = max(strategy_performance.items(), 
                              key=lambda x: x[1]['win_rate'] * x[1]['profit_factor'])
            worst_strategy = min(strategy_performance.items(),
                               key=lambda x: x[1]['win_rate'] * x[1]['profit_factor'])
            
            if best_strategy[1]['win_rate'] > 0.6 and best_strategy[1]['profit_factor'] > 1.5:
                insight = LearningInsight(
                    insight_id=f"insight_strategy_best_{datetime.utcnow().timestamp()}",
                    category=InsightCategory.STRATEGY_OPTIMIZATION,
                    confidence=0.9,
                    observation=f"{best_strategy[0]} is the best performing strategy",
                    conclusion="Focus on this strategy for consistent profits",
                    evidence=[{
                        'strategy_performance': strategy_performance,
                        'best_metrics': best_strategy[1]
                    }],
                    recommendations=[
                        f"Increase allocation to {best_strategy[0]}",
                        f"Study successful {best_strategy[0]} trades for patterns",
                        "Consider automating this strategy"
                    ],
                    expected_impact={
                        'win_rate': 0.1,
                        'profit_factor': 0.2
                    },
                    based_on_trades=[t.trade_id for t in strategy_groups[best_strategy[0]]],
                    learning_method=LearningType.PATTERN_BASED
                )
                insights.append(insight)
                
            # Check for underperforming strategies
            if worst_strategy[1]['win_rate'] < 0.4 or worst_strategy[1]['profit_factor'] < 0.8:
                insight = LearningInsight(
                    insight_id=f"insight_strategy_worst_{datetime.utcnow().timestamp()}",
                    category=InsightCategory.STRATEGY_OPTIMIZATION,
                    confidence=0.85,
                    observation=f"{worst_strategy[0]} is underperforming",
                    conclusion="This strategy needs improvement or should be discontinued",
                    evidence=[{
                        'strategy_performance': strategy_performance,
                        'worst_metrics': worst_strategy[1]
                    }],
                    recommendations=[
                        f"Review and adjust {worst_strategy[0]} parameters",
                        "Reduce allocation to this strategy",
                        "Backtest modifications before live trading"
                    ],
                    expected_impact={
                        'win_rate': 0.05,
                        'max_drawdown': -0.1
                    },
                    based_on_trades=[t.trade_id for t in strategy_groups[worst_strategy[0]]],
                    learning_method=LearningType.PATTERN_BASED
                )
                insights.append(insight)
                
        return insights
        
    # Strategy Adjustment Generation
    
    async def generate_strategy_adjustments(self, insights: List[LearningInsight]) -> List[StrategyAdjustment]:
        """
        Generate strategy adjustments based on insights.
        
        Args:
            insights: Recent insights to base adjustments on
            
        Returns:
            List of proposed adjustments
        """
        adjustments = []
        
        # Group insights by category
        insights_by_category = defaultdict(list)
        for insight in insights:
            insights_by_category[insight.category].append(insight)
            
        # Generate adjustments for each category
        for category, cat_insights in insights_by_category.items():
            if category == InsightCategory.RISK_MANAGEMENT:
                risk_adjustments = await self._generate_risk_adjustments(cat_insights)
                adjustments.extend(risk_adjustments)
                
            elif category == InsightCategory.TIMING_IMPROVEMENT:
                timing_adjustments = await self._generate_timing_adjustments(cat_insights)
                adjustments.extend(timing_adjustments)
                
            elif category == InsightCategory.STRATEGY_OPTIMIZATION:
                strategy_adjustments = await self._generate_strategy_adjustments(cat_insights)
                adjustments.extend(strategy_adjustments)
                
        return adjustments
        
    async def _generate_risk_adjustments(self, insights: List[LearningInsight]) -> List[StrategyAdjustment]:
        """Generate risk management adjustments."""
        adjustments = []
        
        for insight in insights:
            if 'stop' in insight.observation.lower():
                adjustment = StrategyAdjustment(
                    adjustment_id=f"adj_risk_{datetime.utcnow().timestamp()}",
                    strategy_name="all_strategies",
                    adjustment_type="risk_parameters",
                    parameter_changes={
                        'stop_loss_multiplier': {'old': 3.0, 'new': 3.5},
                        'use_volatility_stops': {'old': False, 'new': True}
                    },
                    reasoning=insight.recommendations,
                    based_on_insights=[insight.insight_id],
                    performance_trigger={'metric': 'stop_hit_rate', 'value': 0.3}
                )
                adjustments.append(adjustment)
                
            elif 'sizing' in insight.observation.lower():
                adjustment = StrategyAdjustment(
                    adjustment_id=f"adj_sizing_{datetime.utcnow().timestamp()}",
                    strategy_name="all_strategies",
                    adjustment_type="position_sizing",
                    parameter_changes={
                        'base_position_size': {'old': 10, 'new': 8},
                        'confidence_scaling': {'old': False, 'new': True}
                    },
                    reasoning=insight.recommendations,
                    based_on_insights=[insight.insight_id],
                    performance_trigger={'metric': 'size_performance_gap', 'value': 0.1}
                )
                adjustments.append(adjustment)
                
        return adjustments
        
    async def _generate_timing_adjustments(self, insights: List[LearningInsight]) -> List[StrategyAdjustment]:
        """Generate timing adjustments."""
        adjustments = []
        
        for insight in insights:
            if 'best trading hours' in insight.observation:
                # Extract best hours from evidence
                best_hours = insight.evidence[0].get('best_hours', [])
                if best_hours:
                    adjustment = StrategyAdjustment(
                        adjustment_id=f"adj_timing_{datetime.utcnow().timestamp()}",
                        strategy_name="all_strategies",
                        adjustment_type="trading_hours",
                        parameter_changes={
                            'allowed_hours': {'old': list(range(9, 16)), 'new': [h[0] for h in best_hours]},
                            'hour_confidence_boost': {'old': {}, 'new': {h[0]: 0.1 for h in best_hours}}
                        },
                        reasoning=insight.recommendations,
                        based_on_insights=[insight.insight_id],
                        performance_trigger={'metric': 'hour_performance', 'value': best_hours}
                    )
                    adjustments.append(adjustment)
                    
        return adjustments
        
    async def _generate_strategy_adjustments(self, insights: List[LearningInsight]) -> List[StrategyAdjustment]:
        """Generate strategy-specific adjustments."""
        adjustments = []
        
        for insight in insights:
            if 'best performing strategy' in insight.observation:
                strategy_name = insight.observation.split(' ')[0]  # Extract strategy name
                adjustment = StrategyAdjustment(
                    adjustment_id=f"adj_strat_alloc_{datetime.utcnow().timestamp()}",
                    strategy_name="portfolio_allocation",
                    adjustment_type="allocation",
                    parameter_changes={
                        f'{strategy_name}_weight': {'old': 0.33, 'new': 0.5},
                        'rebalance_frequency': {'old': 'weekly', 'new': 'daily'}
                    },
                    reasoning=insight.recommendations,
                    based_on_insights=[insight.insight_id],
                    performance_trigger={'metric': 'strategy_performance', 'value': insight.evidence[0]}
                )
                adjustments.append(adjustment)
                
        return adjustments
        
    # Insight Validation
    
    async def validate_insight(self, insight_id: str, test_results: Dict[str, Any]) -> None:
        """
        Validate an insight with test results.
        
        Args:
            insight_id: ID of insight to validate
            test_results: Results from testing the insight
        """
        if insight_id in self.insight_index:
            insight = self.insight_index[insight_id]
            insight.tested = True
            insight.test_results = test_results
            
            # Update adoption status based on results
            if test_results.get('success', False):
                insight.adoption_status = 'adopted'
                self.validated_insights.add(insight_id)
            else:
                insight.adoption_status = 'rejected'
                
            # Update confidence based on validation
            actual_impact = test_results.get('actual_impact', {})
            expected_impact = insight.expected_impact
            
            # Calculate accuracy of prediction
            accuracy_scores = []
            for metric, expected_value in expected_impact.items():
                if metric in actual_impact:
                    actual_value = actual_impact[metric]
                    accuracy = 1 - abs(actual_value - expected_value) / (abs(expected_value) + 0.001)
                    accuracy_scores.append(max(0, accuracy))
                    
            if accuracy_scores:
                avg_accuracy = np.mean(accuracy_scores)
                self.learning_confidence[insight.category] = (
                    self.learning_confidence[insight.category] * 0.8 + avg_accuracy * 0.2
                )
                
            # Store updated insight
            await self._store_insight(insight)
            
    # Pattern Extraction
    
    def _extract_trade_patterns(self, trades: List[TradeOutcome]) -> List[Dict[str, Any]]:
        """Extract common patterns from trades."""
        patterns = []
        
        # Extract features from each trade
        features = []
        for trade in trades:
            trade_features = {
                'vix_level': trade.market_conditions.get('vix_level', 0),
                'distance_from_support': trade.market_conditions.get('distance_from_support', 0),
                'rsi': trade.market_conditions.get('rsi', 50),
                'trend_strength': trade.market_conditions.get('trend_strength', 0),
                'volume_ratio': trade.market_conditions.get('volume_ratio', 1.0),
                'time_of_day': trade.entry_time.hour,
                'holding_period': trade.holding_period or 0
            }
            features.append(trade_features)
            
        # Find clusters of similar trades
        if len(features) >= 3:
            # Convert to matrix
            feature_names = list(features[0].keys())
            feature_matrix = np.array([[f.get(k, 0) for k in feature_names] for f in features])
            
            # Normalize features
            scaler = StandardScaler()
            normalized_features = scaler.fit_transform(feature_matrix)
            
            # Cluster trades
            n_clusters = min(3, len(trades) // 3)  # Ensure enough trades per cluster
            if n_clusters > 0:
                kmeans = KMeans(n_clusters=n_clusters, random_state=42)
                clusters = kmeans.fit_predict(normalized_features)
                
                # Analyze each cluster
                for cluster_id in range(n_clusters):
                    cluster_indices = [i for i, c in enumerate(clusters) if c == cluster_id]
                    if len(cluster_indices) >= 2:
                        cluster_trades = [trades[i] for i in cluster_indices]
                        
                        # Get cluster characteristics
                        cluster_features = feature_matrix[cluster_indices]
                        avg_features = np.mean(cluster_features, axis=0)
                        
                        # Create pattern description
                        pattern_desc = []
                        for i, feature_name in enumerate(feature_names):
                            avg_val = avg_features[i]
                            if feature_name == 'vix_level' and avg_val < 15:
                                pattern_desc.append("low volatility")
                            elif feature_name == 'rsi' and avg_val > 70:
                                pattern_desc.append("overbought conditions")
                            elif feature_name == 'trend_strength' and avg_val > 0.5:
                                pattern_desc.append("strong trend")
                                
                        if pattern_desc:
                            pattern = {
                                'pattern': {fname: avg_features[i] for i, fname in enumerate(feature_names)},
                                'description': ' and '.join(pattern_desc),
                                'frequency': len(cluster_indices) / len(trades),
                                'trades': [t.trade_id for t in cluster_trades]
                            }
                            patterns.append(pattern)
                            
        return patterns
        
    def _calculate_profit_factor(self, trades: List[TradeOutcome]) -> float:
        """Calculate profit factor for a set of trades."""
        gross_profit = sum(t.profit_loss for t in trades if t.profit_loss > 0)
        gross_loss = abs(sum(t.profit_loss for t in trades if t.profit_loss < 0))
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0
            
        return gross_profit / gross_loss
        
    def _get_regime_recommendations(self, regime: str, win_rate: float, overall_win_rate: float) -> List[str]:
        """Get recommendations for a specific market regime."""
        recommendations = []
        
        if win_rate > overall_win_rate:
            recommendations.extend([
                f"Increase trading frequency in {regime} conditions",
                f"Allocate more capital during {regime} regime",
                f"Loosen entry criteria in {regime} markets"
            ])
        else:
            recommendations.extend([
                f"Reduce trading in {regime} conditions",
                f"Tighten entry criteria during {regime} regime",
                f"Consider alternative strategies for {regime} markets"
            ])
            
        return recommendations
        
    # Background Tasks
    
    async def _continuous_learning(self) -> None:
        """Continuously analyze performance and generate insights."""
        while True:
            try:
                # Get recent trades
                recent_trades = self.performance_tracker.trades[-50:]  # Last 50 trades
                
                if len(recent_trades) >= self.min_trades_for_insight:
                    # Generate insights
                    insights = await self.analyze_trades(recent_trades, ReflectionPeriod.DAILY)
                    
                    if insights:
                        # Generate adjustments
                        adjustments = await self.generate_strategy_adjustments(insights)
                        
                        # Share insights with other agents
                        await self._share_insights(insights)
                        
                        logger.info(f"Generated {len(insights)} insights and {len(adjustments)} adjustments")
                        
                # Wait before next analysis
                await asyncio.sleep(3600)  # Analyze every hour
                
            except Exception as e:
                logger.error(f"Continuous learning error: {e}")
                await asyncio.sleep(1800)  # Wait 30 minutes on error
                
    async def _share_insights(self, insights: List[LearningInsight]) -> None:
        """Share insights with other agents."""
        for insight in insights:
            await self.mcp.share_context(
                "LearningEngine",
                ["StrategicPlannerAgent", "TacticalExecutorAgent", "RiskManagerAgent"],
                {
                    'learning_insight': {
                        'category': insight.category.value,
                        'observation': insight.observation,
                        'recommendations': insight.recommendations,
                        'expected_impact': insight.expected_impact,
                        'confidence': insight.confidence
                    }
                }
            )
            
    # Data Persistence
    
    async def _store_insight(self, insight: LearningInsight) -> None:
        """Store insight in MCP."""
        await self.mcp.store_memory(
            "LearningEngine",
            MemorySlice(
                memory_type=MemoryType.EVALUATION,
                content={
                    'learning_insight': insight.dict(),
                    'timestamp': datetime.utcnow().isoformat()
                },
                importance=MemoryImportance.CRITICAL if insight.confidence > 0.9 else MemoryImportance.HIGH
            )
        )
        
    async def _load_historical_insights(self) -> None:
        """Load historical insights from MCP."""
        memories = await self.mcp.semantic_search(
            "LearningEngine",
            "learning insight strategy improvement",
            scope="own"
        )
        
        for memory in memories:
            if 'learning_insight' in memory.content:
                insight_data = memory.content['learning_insight']
                insight = LearningInsight(**insight_data)
                self.insights.append(insight)
                self.insight_index[insight.insight_id] = insight
                
        logger.info(f"Loaded {len(self.insights)} historical insights")
        
    async def _save_insights(self) -> None:
        """Save current insights summary."""
        insights_summary = {
            'total_insights': len(self.insights),
            'validated_insights': len(self.validated_insights),
            'insights_by_category': defaultdict(int),
            'learning_confidence': dict(self.learning_confidence),
            'top_insights': []
        }
        
        # Count by category
        for insight in self.insights:
            insights_summary['insights_by_category'][insight.category.value] += 1
            
        # Get top insights
        top_insights = sorted(self.insights, key=lambda i: i.confidence, reverse=True)[:5]
        insights_summary['top_insights'] = [i.dict() for i in top_insights]
        
        await self.mcp.store_memory(
            "LearningEngine",
            MemorySlice(
                memory_type=MemoryType.EVALUATION,
                content={
                    'insights_summary': insights_summary,
                    'timestamp': datetime.utcnow().isoformat()
                },
                importance=MemoryImportance.HIGH
            )
        )