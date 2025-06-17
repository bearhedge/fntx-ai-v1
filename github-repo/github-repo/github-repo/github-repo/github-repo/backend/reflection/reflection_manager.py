"""
Reflection Manager
Orchestrates the entire reflection framework including performance tracking,
learning generation, and cross-agent sharing.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict
import json

from ..mcp.context_manager import MCPContextManager
from ..mcp.schemas import MemorySlice, MemoryType, MemoryImportance
from .schemas import (
    ReflectionCycle, ReflectionPeriod, TradeOutcome, PerformanceSnapshot,
    LearningInsight, StrategyAdjustment, PerformanceAlert
)
from .performance_tracker import PerformanceTracker
from .learning_engine import LearningEngine
from .cross_agent_learning import CrossAgentLearningHub

logger = logging.getLogger(__name__)


class ReflectionManager:
    """
    Manages the complete reflection process for continuous improvement.
    """
    
    def __init__(self, mcp_manager: MCPContextManager):
        self.mcp = mcp_manager
        
        # Initialize components
        self.performance_tracker = PerformanceTracker(mcp_manager)
        self.learning_engine = LearningEngine(mcp_manager, self.performance_tracker)
        self.cross_agent_hub = CrossAgentLearningHub(mcp_manager)
        
        # Reflection cycles
        self.active_cycles: Dict[ReflectionPeriod, ReflectionCycle] = {}
        self.completed_cycles: List[ReflectionCycle] = []
        
        # Improvement tracking
        self.implemented_adjustments: List[StrategyAdjustment] = []
        self.adjustment_outcomes: Dict[str, Dict[str, Any]] = {}
        
        # Configuration
        self.reflection_schedule = {
            ReflectionPeriod.TRADE_LEVEL: timedelta(minutes=0),  # Immediate
            ReflectionPeriod.DAILY: timedelta(hours=24),
            ReflectionPeriod.WEEKLY: timedelta(days=7),
            ReflectionPeriod.MONTHLY: timedelta(days=30)
        }
        
        # Background tasks
        self._reflection_task: Optional[asyncio.Task] = None
        self._implementation_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> None:
        """Initialize the reflection manager and all components."""
        logger.info("Initializing Reflection Manager")
        
        # Register with MCP
        await self.mcp.register_agent(
            "ReflectionManager",
            ["reflection_orchestration", "performance_analysis", "continuous_improvement"]
        )
        
        # Initialize components
        await self.performance_tracker.initialize()
        await self.learning_engine.initialize()
        await self.cross_agent_hub.initialize()
        
        # Register all agents with cross-agent hub
        await self._register_agents_with_hub()
        
        # Load historical cycles
        await self._load_historical_cycles()
        
        # Start background tasks
        self._reflection_task = asyncio.create_task(self._run_reflection_cycles())
        self._implementation_task = asyncio.create_task(self._implement_improvements())
        
        logger.info("Reflection Manager initialized successfully")
        
    async def shutdown(self) -> None:
        """Shutdown the reflection manager."""
        logger.info("Shutting down Reflection Manager")
        
        # Cancel background tasks
        if self._reflection_task:
            self._reflection_task.cancel()
        if self._implementation_task:
            self._implementation_task.cancel()
            
        await asyncio.gather(
            self._reflection_task,
            self._implementation_task,
            return_exceptions=True
        )
        
        # Shutdown components
        await self.performance_tracker.shutdown()
        await self.learning_engine.shutdown()
        await self.cross_agent_hub.shutdown()
        
        # Save current state
        await self._save_reflection_state()
        
        logger.info("Reflection Manager shut down")
        
    # Trade Recording
    
    async def record_trade_outcome(self, trade: TradeOutcome) -> None:
        """
        Record a trade outcome and trigger immediate reflection.
        
        Args:
            trade: Completed trade outcome
        """
        # Record in performance tracker
        await self.performance_tracker.record_trade(trade)
        
        # Trigger trade-level reflection
        await self._run_trade_reflection(trade)
        
        # Share with cross-agent hub if significant
        if abs(trade.profit_loss) > 500 or not trade.followed_plan:
            await self._share_trade_learning(trade)
            
    async def _run_trade_reflection(self, trade: TradeOutcome) -> None:
        """Run immediate reflection on a single trade."""
        # Create trade-level cycle
        cycle = ReflectionCycle(
            cycle_id=f"cycle_trade_{trade.trade_id}",
            period=ReflectionPeriod.TRADE_LEVEL,
            start_time=trade.entry_time,
            end_time=trade.exit_time or datetime.utcnow(),
            performance_snapshot=PerformanceSnapshot(
                period_start=trade.entry_time,
                period_end=trade.exit_time or datetime.utcnow(),
                period_type=ReflectionPeriod.TRADE_LEVEL,
                total_trades=1,
                winning_trades=1 if trade.success else 0,
                losing_trades=0 if trade.success else 1,
                net_profit=trade.profit_loss
            ),
            trades_analyzed=[trade.trade_id]
        )
        
        # Quick analysis for immediate learnings
        if not trade.success and trade.stop_hit:
            insight = LearningInsight(
                insight_id=f"insight_trade_{trade.trade_id}",
                category=InsightCategory.RISK_MANAGEMENT,
                confidence=0.9,
                observation=f"Stop loss hit on {trade.symbol} trade",
                conclusion="Stop may have been too tight or entry was poor",
                evidence=[{
                    'trade_id': trade.trade_id,
                    'max_favorable': trade.max_favorable_excursion,
                    'max_adverse': trade.max_adverse_excursion
                }],
                recommendations=["Review stop placement", "Check entry criteria"],
                expected_impact={'win_rate': 0.02},
                based_on_trades=[trade.trade_id],
                learning_method=LearningType.RULE_BASED
            )
            cycle.insights.append(insight)
            
        # Store cycle
        self.completed_cycles.append(cycle)
        
    # Reflection Cycles
    
    async def _run_reflection_cycles(self) -> None:
        """Background task to run scheduled reflection cycles."""
        while True:
            try:
                now = datetime.utcnow()
                
                # Check each reflection period
                for period, interval in self.reflection_schedule.items():
                    if period == ReflectionPeriod.TRADE_LEVEL:
                        continue  # Handled separately
                        
                    # Check if cycle is due
                    last_cycle = self._get_last_cycle(period)
                    if not last_cycle or (now - last_cycle.end_time) > interval:
                        await self._run_reflection_cycle(period)
                        
                # Wait before next check
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Reflection cycle error: {e}")
                await asyncio.sleep(600)
                
    async def _run_reflection_cycle(self, period: ReflectionPeriod) -> None:
        """Run a complete reflection cycle."""
        logger.info(f"Starting {period.value} reflection cycle")
        
        # Determine time range
        end_time = datetime.utcnow()
        if period == ReflectionPeriod.DAILY:
            start_time = end_time - timedelta(days=1)
        elif period == ReflectionPeriod.WEEKLY:
            start_time = end_time - timedelta(days=7)
        elif period == ReflectionPeriod.MONTHLY:
            start_time = end_time - timedelta(days=30)
        else:
            start_time = end_time - timedelta(days=90)  # Quarterly
            
        # Create cycle
        cycle = ReflectionCycle(
            cycle_id=f"cycle_{period.value}_{end_time.strftime('%Y%m%d_%H%M%S')}",
            period=period,
            start_time=start_time,
            end_time=end_time
        )
        
        # Get performance snapshot
        cycle.performance_snapshot = await self.performance_tracker.calculate_performance_snapshot(
            period, start_time, end_time
        )
        
        # Get trades for period
        period_trades = [
            t for t in self.performance_tracker.trades
            if start_time <= t.entry_time <= end_time
        ]
        cycle.trades_analyzed = [t.trade_id for t in period_trades]
        
        # Generate insights
        if period_trades:
            insights = await self.learning_engine.analyze_trades(period_trades, period)
            cycle.insights = insights
            
            # Generate strategy adjustments
            if insights:
                adjustments = await self.learning_engine.generate_strategy_adjustments(insights)
                cycle.strategy_adjustments = adjustments
                
        # Identify patterns
        cycle.patterns_identified = await self._identify_patterns(period_trades)
        
        # Cross-agent learning
        if cycle.insights:
            for insight in cycle.insights:
                if insight.confidence > 0.8:
                    learning_id = await self.cross_agent_hub.submit_learning(
                        "ReflectionManager",
                        self._map_insight_to_learning_type(insight),
                        {
                            'insight': insight.observation,
                            'recommendations': insight.recommendations
                        },
                        {
                            'evidence': insight.evidence,
                            'expected_impact': insight.expected_impact
                        }
                    )
                    
                    if learning_id:
                        cycle.shared_learnings.append({
                            'learning_id': learning_id,
                            'insight_id': insight.insight_id
                        })
                        
        # Calculate reflection quality
        cycle.reflection_quality_score = self._calculate_reflection_quality(cycle)
        cycle.actionable_items = len(cycle.insights) + len(cycle.strategy_adjustments)
        
        # Store cycle
        self.active_cycles[period] = cycle
        self.completed_cycles.append(cycle)
        
        # Store in MCP
        await self._store_reflection_cycle(cycle)
        
        # Share key findings
        await self._share_cycle_findings(cycle)
        
        logger.info(f"Completed {period.value} reflection cycle with {len(cycle.insights)} insights")
        
    async def _identify_patterns(self, trades: List[TradeOutcome]) -> List[Dict[str, Any]]:
        """Identify patterns in trading behavior."""
        patterns = []
        
        if len(trades) < 5:
            return patterns
            
        # Time-based patterns
        hour_performance = defaultdict(lambda: {'count': 0, 'success': 0})
        for trade in trades:
            hour = trade.entry_time.hour
            hour_performance[hour]['count'] += 1
            if trade.success:
                hour_performance[hour]['success'] += 1
                
        # Find significant hours
        for hour, stats in hour_performance.items():
            if stats['count'] >= 3:
                win_rate = stats['success'] / stats['count']
                if win_rate > 0.75 or win_rate < 0.25:
                    patterns.append({
                        'type': 'time_based',
                        'hour': hour,
                        'win_rate': win_rate,
                        'trade_count': stats['count']
                    })
                    
        # Strategy patterns
        strategy_performance = defaultdict(lambda: {'count': 0, 'profit': 0})
        for trade in trades:
            strategy_performance[trade.strategy]['count'] += 1
            strategy_performance[trade.strategy]['profit'] += trade.profit_loss
            
        for strategy, stats in strategy_performance.items():
            avg_profit = stats['profit'] / stats['count'] if stats['count'] > 0 else 0
            patterns.append({
                'type': 'strategy',
                'strategy': strategy,
                'avg_profit': avg_profit,
                'total_profit': stats['profit'],
                'trade_count': stats['count']
            })
            
        return patterns
        
    # Implementation
    
    async def _implement_improvements(self) -> None:
        """Background task to implement approved improvements."""
        while True:
            try:
                # Check for pending adjustments
                for cycle in self.active_cycles.values():
                    for adjustment in cycle.strategy_adjustments:
                        if not adjustment.approved and not adjustment.implemented_at:
                            # Auto-approve high confidence adjustments
                            if self._should_auto_approve(adjustment):
                                adjustment.approved = True
                                
                        if adjustment.approved and not adjustment.implemented_at:
                            await self._implement_adjustment(adjustment)
                            cycle.implemented_items += 1
                            
                # Monitor implemented adjustments
                await self._monitor_adjustments()
                
                # Wait before next check
                await asyncio.sleep(600)  # Check every 10 minutes
                
            except Exception as e:
                logger.error(f"Implementation error: {e}")
                await asyncio.sleep(1800)
                
    def _should_auto_approve(self, adjustment: StrategyAdjustment) -> bool:
        """Determine if an adjustment should be auto-approved."""
        # Auto-approve if:
        # 1. Based on high-confidence insights
        # 2. Risk-reducing adjustments
        # 3. Small parameter changes
        
        if 'risk' in adjustment.adjustment_type.lower():
            return True
            
        # Check parameter change magnitude
        for param, changes in adjustment.parameter_changes.items():
            old_val = changes.get('old')
            new_val = changes.get('new')
            
            if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
                change_pct = abs(new_val - old_val) / (abs(old_val) + 0.001)
                if change_pct > 0.2:  # More than 20% change
                    return False
                    
        return True
        
    async def _implement_adjustment(self, adjustment: StrategyAdjustment) -> None:
        """Implement a strategy adjustment."""
        logger.info(f"Implementing adjustment {adjustment.adjustment_id}")
        
        # Share adjustment with relevant agents
        target_agents = self._get_target_agents_for_adjustment(adjustment)
        
        await self.mcp.share_context(
            "ReflectionManager",
            target_agents,
            {
                'strategy_adjustment': {
                    'adjustment_id': adjustment.adjustment_id,
                    'strategy': adjustment.strategy_name,
                    'changes': adjustment.parameter_changes,
                    'reasoning': adjustment.reasoning
                }
            }
        )
        
        # Mark as implemented
        adjustment.implemented_at = datetime.utcnow()
        self.implemented_adjustments.append(adjustment)
        
        # Track for monitoring
        self.adjustment_outcomes[adjustment.adjustment_id] = {
            'implemented_at': adjustment.implemented_at,
            'baseline_metrics': await self.performance_tracker.get_current_metrics(),
            'target_metrics': adjustment.expected_impact
        }
        
    def _get_target_agents_for_adjustment(self, adjustment: StrategyAdjustment) -> List[str]:
        """Determine which agents should receive an adjustment."""
        if adjustment.strategy_name == "all_strategies":
            return ["StrategicPlannerAgent", "TacticalExecutorAgent", "RiskManagerAgent"]
        elif "risk" in adjustment.adjustment_type:
            return ["RiskManagerAgent", "TacticalExecutorAgent"]
        elif "timing" in adjustment.adjustment_type:
            return ["TacticalExecutorAgent", "EnvironmentWatcherAgent"]
        else:
            return ["StrategicPlannerAgent"]
            
    async def _monitor_adjustments(self) -> None:
        """Monitor the effectiveness of implemented adjustments."""
        for adj_id, outcome in self.adjustment_outcomes.items():
            if 'completed' in outcome:
                continue
                
            # Check if enough time has passed
            time_elapsed = datetime.utcnow() - outcome['implemented_at']
            if time_elapsed < timedelta(days=3):
                continue
                
            # Get current metrics
            current_metrics = await self.performance_tracker.get_current_metrics()
            baseline_metrics = outcome['baseline_metrics']
            
            # Calculate improvement
            improvements = {}
            for metric, baseline_value in baseline_metrics.items():
                if metric in current_metrics:
                    current_value = current_metrics[metric]
                    if isinstance(baseline_value, (int, float)) and isinstance(current_value, (int, float)):
                        improvement = current_value - baseline_value
                        improvements[metric] = improvement
                        
            # Mark as completed and store results
            outcome['completed'] = True
            outcome['actual_improvements'] = improvements
            
            # Validate adjustment
            if adj_id in [a.adjustment_id for a in self.implemented_adjustments]:
                adjustment = next(a for a in self.implemented_adjustments if a.adjustment_id == adj_id)
                
                # Compare actual vs expected
                success = self._evaluate_adjustment_success(improvements, adjustment.expected_impact)
                
                # Provide feedback to learning engine
                for insight_id in adjustment.based_on_insights:
                    await self.learning_engine.validate_insight(
                        insight_id,
                        {
                            'success': success,
                            'actual_impact': improvements
                        }
                    )
                    
    def _evaluate_adjustment_success(self, actual: Dict[str, float], 
                                   expected: Dict[str, float]) -> bool:
        """Evaluate if an adjustment was successful."""
        if not actual or not expected:
            return False
            
        # Check if improvements are in the right direction
        success_count = 0
        total_count = 0
        
        for metric, expected_value in expected.items():
            if metric in actual:
                actual_value = actual[metric]
                total_count += 1
                
                # Check if improvement is in the right direction
                if expected_value > 0 and actual_value > 0:
                    success_count += 1
                elif expected_value < 0 and actual_value < 0:
                    success_count += 1
                elif abs(actual_value) < 0.01:  # Negligible change
                    success_count += 0.5
                    
        return (success_count / total_count) > 0.5 if total_count > 0 else False
        
    # Helper Methods
    
    def _get_last_cycle(self, period: ReflectionPeriod) -> Optional[ReflectionCycle]:
        """Get the last completed cycle for a period."""
        period_cycles = [c for c in self.completed_cycles if c.period == period]
        return max(period_cycles, key=lambda c: c.end_time) if period_cycles else None
        
    def _calculate_reflection_quality(self, cycle: ReflectionCycle) -> float:
        """Calculate quality score for a reflection cycle."""
        score = 0.5  # Base score
        
        # More insights = better
        score += min(len(cycle.insights) * 0.1, 0.3)
        
        # High confidence insights
        high_conf_insights = [i for i in cycle.insights if i.confidence > 0.8]
        score += min(len(high_conf_insights) * 0.05, 0.1)
        
        # Actionable adjustments
        score += min(len(cycle.strategy_adjustments) * 0.05, 0.1)
        
        # Cross-agent sharing
        score += min(len(cycle.shared_learnings) * 0.05, 0.1)
        
        return min(score, 1.0)
        
    def _map_insight_to_learning_type(self, insight: LearningInsight) -> str:
        """Map insight category to learning type."""
        mapping = {
            InsightCategory.STRATEGY_OPTIMIZATION: "strategy_optimization",
            InsightCategory.RISK_MANAGEMENT: "risk_management",
            InsightCategory.TIMING_IMPROVEMENT: "timing_optimization",
            InsightCategory.MARKET_ADAPTATION: "market_analysis",
            InsightCategory.EXECUTION_EFFICIENCY: "execution_improvement",
            InsightCategory.PATTERN_RECOGNITION: "pattern_recognition"
        }
        
        return mapping.get(insight.category, "strategy_optimization")
        
    async def _share_trade_learning(self, trade: TradeOutcome) -> None:
        """Share significant trade learnings."""
        learning_type = "execution_improvement"
        if not trade.followed_plan:
            learning_type = "risk_management"
        elif trade.profit_loss > 1000:
            learning_type = "strategy_optimization"
            
        await self.cross_agent_hub.submit_learning(
            "ReflectionManager",
            learning_type,
            {
                'trade_id': trade.trade_id,
                'outcome': 'success' if trade.success else 'failure',
                'key_factors': trade.entry_reasoning
            },
            {
                'profit_loss': trade.profit_loss,
                'market_conditions': trade.market_conditions
            }
        )
        
    async def _share_cycle_findings(self, cycle: ReflectionCycle) -> None:
        """Share key findings from a reflection cycle."""
        # Share performance snapshot
        await self.mcp.share_context(
            "ReflectionManager",
            ["StrategicPlannerAgent", "TacticalExecutorAgent", "RiskManagerAgent"],
            {
                'reflection_summary': {
                    'period': cycle.period.value,
                    'performance': {
                        'win_rate': cycle.performance_snapshot.win_rate,
                        'net_profit': cycle.performance_snapshot.net_profit,
                        'sharpe_ratio': cycle.performance_snapshot.sharpe_ratio
                    },
                    'insights_count': len(cycle.insights),
                    'key_recommendations': [i.recommendations[0] for i in cycle.insights[:3]]
                }
            }
        )
        
    # Agent Registration
    
    async def _register_agents_with_hub(self) -> None:
        """Register all agents with the cross-agent learning hub."""
        agents = [
            ("StrategicPlannerAgent", ["strategy", "planning", "high_level"]),
            ("TacticalExecutorAgent", ["execution", "timing", "trading"]),
            ("EnvironmentWatcherAgent", ["market", "monitoring", "analysis"]),
            ("RiskManagerAgent", ["risk", "safety", "limits"]),
            ("EvaluatorAgent", ["evaluation", "performance", "metrics"]),
            ("RewardModelAgent", ["learning", "preferences", "optimization"])
        ]
        
        for agent_id, capabilities in agents:
            await self.cross_agent_hub.register_agent(agent_id, capabilities)
            
    # Data Persistence
    
    async def _store_reflection_cycle(self, cycle: ReflectionCycle) -> None:
        """Store reflection cycle in MCP."""
        await self.mcp.store_memory(
            "ReflectionManager",
            MemorySlice(
                memory_type=MemoryType.EVALUATION,
                content={
                    'reflection_cycle': cycle.dict(),
                    'timestamp': datetime.utcnow().isoformat()
                },
                importance=MemoryImportance.HIGH
            )
        )
        
    async def _load_historical_cycles(self) -> None:
        """Load historical reflection cycles."""
        memories = await self.mcp.semantic_search(
            "ReflectionManager",
            "reflection cycle performance insights",
            scope="own"
        )
        
        for memory in memories:
            if 'reflection_cycle' in memory.content:
                cycle_data = memory.content['reflection_cycle']
                cycle = ReflectionCycle(**cycle_data)
                self.completed_cycles.append(cycle)
                
        logger.info(f"Loaded {len(self.completed_cycles)} historical reflection cycles")
        
    async def _save_reflection_state(self) -> None:
        """Save current reflection state."""
        state = {
            'active_cycles': {k.value: v.dict() for k, v in self.active_cycles.items()},
            'completed_cycles_count': len(self.completed_cycles),
            'implemented_adjustments': len(self.implemented_adjustments),
            'cross_agent_performance': await self.cross_agent_hub.aggregate_cross_agent_performance()
        }
        
        await self.mcp.store_memory(
            "ReflectionManager",
            MemorySlice(
                memory_type=MemoryType.EVALUATION,
                content={
                    'reflection_state': state,
                    'timestamp': datetime.utcnow().isoformat()
                },
                importance=MemoryImportance.HIGH
            )
        )
        
    # Public API
    
    async def get_reflection_summary(self) -> Dict[str, Any]:
        """Get summary of reflection activities."""
        current_metrics = await self.performance_tracker.get_current_metrics()
        cross_agent_stats = await self.cross_agent_hub.aggregate_cross_agent_performance()
        
        summary = {
            'current_performance': current_metrics,
            'active_cycles': {k.value: v.cycle_id for k, v in self.active_cycles.items()},
            'recent_insights': [],
            'implemented_adjustments': len(self.implemented_adjustments),
            'cross_agent_learning': cross_agent_stats,
            'improvement_trends': {}
        }
        
        # Get recent insights
        recent_cycles = sorted(self.completed_cycles, key=lambda c: c.end_time, reverse=True)[:5]
        for cycle in recent_cycles:
            for insight in cycle.insights[:2]:  # Top 2 insights per cycle
                summary['recent_insights'].append({
                    'observation': insight.observation,
                    'confidence': insight.confidence,
                    'expected_impact': insight.expected_impact
                })
                
        # Calculate improvement trends
        if len(self.completed_cycles) >= 2:
            old_cycles = [c for c in self.completed_cycles if c.period == ReflectionPeriod.WEEKLY]
            if len(old_cycles) >= 2:
                old_cycle = old_cycles[-2]
                new_cycle = old_cycles[-1]
                
                if old_cycle.performance_snapshot.win_rate and new_cycle.performance_snapshot.win_rate:
                    summary['improvement_trends']['win_rate_change'] = (
                        new_cycle.performance_snapshot.win_rate - 
                        old_cycle.performance_snapshot.win_rate
                    )
                    
        return summary