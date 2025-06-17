"""
Performance Tracker
Tracks and analyzes trading performance across multiple dimensions.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
import numpy as np
import json

from ..mcp.context_manager import MCPContextManager
from ..mcp.schemas import MemorySlice, MemoryType, MemoryImportance
from .schemas import (
    TradeOutcome, PerformanceSnapshot, PerformanceMetric,
    ReflectionPeriod, PerformanceAlert
)

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """
    Tracks trading performance and generates metrics.
    """
    
    def __init__(self, mcp_manager: MCPContextManager):
        self.mcp = mcp_manager
        
        # Trade history
        self.trades: List[TradeOutcome] = []
        self.trade_index: Dict[str, TradeOutcome] = {}
        
        # Performance snapshots
        self.snapshots: Dict[ReflectionPeriod, List[PerformanceSnapshot]] = {
            period: [] for period in ReflectionPeriod
        }
        
        # Running metrics
        self.equity_curve: deque = deque(maxlen=10000)
        self.current_equity = 100000.0  # Starting capital
        self.high_water_mark = self.current_equity
        
        # Alert thresholds
        self.alert_thresholds = {
            'max_drawdown': 0.10,  # 10% drawdown
            'losing_streak': 5,     # 5 losses in a row
            'daily_loss': 0.02,     # 2% daily loss
            'win_rate_drop': 0.15   # 15% drop in win rate
        }
        
        # Performance cache
        self._metrics_cache: Dict[str, Any] = {}
        self._cache_expiry = datetime.utcnow()
        
        # Background tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> None:
        """Initialize the performance tracker."""
        # Register with MCP
        await self.mcp.register_agent(
            "PerformanceTracker",
            ["performance_tracking", "metrics_calculation", "trade_analysis"]
        )
        
        # Load historical trades
        await self._load_historical_trades()
        
        # Start monitoring
        self._monitoring_task = asyncio.create_task(self._monitor_performance())
        
        logger.info("Performance Tracker initialized")
        
    async def shutdown(self) -> None:
        """Shutdown the tracker."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            await asyncio.gather(self._monitoring_task, return_exceptions=True)
            
        # Save current state
        await self._save_performance_data()
        
        logger.info("Performance Tracker shut down")
        
    # Trade Recording
    
    async def record_trade(self, trade: TradeOutcome) -> None:
        """
        Record a completed trade.
        
        Args:
            trade: Trade outcome to record
        """
        # Add to history
        self.trades.append(trade)
        self.trade_index[trade.trade_id] = trade
        
        # Update equity
        self.current_equity += trade.profit_loss
        self.equity_curve.append({
            'timestamp': trade.exit_time or datetime.utcnow(),
            'equity': self.current_equity,
            'trade_id': trade.trade_id
        })
        
        # Update high water mark
        if self.current_equity > self.high_water_mark:
            self.high_water_mark = self.current_equity
            
        # Store in MCP
        await self._store_trade_in_mcp(trade)
        
        # Invalidate cache
        self._metrics_cache.clear()
        
        # Check for alerts
        await self._check_performance_alerts(trade)
        
        logger.info(f"Recorded trade {trade.trade_id}: P&L ${trade.profit_loss:.2f}")
        
    async def update_trade(self, trade_id: str, updates: Dict[str, Any]) -> None:
        """Update an existing trade."""
        if trade_id in self.trade_index:
            trade = self.trade_index[trade_id]
            for key, value in updates.items():
                if hasattr(trade, key):
                    setattr(trade, key, value)
                    
            # Recalculate metrics if needed
            if 'profit_loss' in updates:
                self._metrics_cache.clear()
                
    # Performance Calculation
    
    async def calculate_performance_snapshot(self, 
                                           period: ReflectionPeriod,
                                           start_time: datetime,
                                           end_time: datetime) -> PerformanceSnapshot:
        """
        Calculate performance metrics for a specific period.
        
        Args:
            period: Type of period
            start_time: Period start
            end_time: Period end
            
        Returns:
            Performance snapshot
        """
        # Filter trades for period
        period_trades = [
            t for t in self.trades
            if t.entry_time >= start_time and t.entry_time <= end_time
        ]
        
        if not period_trades:
            return PerformanceSnapshot(
                period_start=start_time,
                period_end=end_time,
                period_type=period
            )
            
        # Calculate basic metrics
        winning_trades = [t for t in period_trades if t.success]
        losing_trades = [t for t in period_trades if not t.success]
        
        total_profit = sum(t.profit_loss for t in winning_trades)
        total_loss = abs(sum(t.profit_loss for t in losing_trades))
        net_profit = total_profit - total_loss
        
        # Create snapshot
        snapshot = PerformanceSnapshot(
            period_start=start_time,
            period_end=end_time,
            period_type=period,
            total_trades=len(period_trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            total_profit=total_profit,
            total_loss=total_loss,
            net_profit=net_profit
        )
        
        # Calculate derived metrics
        if snapshot.total_trades > 0:
            snapshot.win_rate = (snapshot.winning_trades / snapshot.total_trades) * 100
            
        if snapshot.winning_trades > 0:
            snapshot.average_win = snapshot.total_profit / snapshot.winning_trades
            
        if snapshot.losing_trades > 0:
            snapshot.average_loss = snapshot.total_loss / snapshot.losing_trades
            
        if snapshot.total_loss > 0:
            snapshot.profit_factor = snapshot.total_profit / snapshot.total_loss
            
        # Calculate expectancy
        if snapshot.total_trades > 0 and snapshot.average_win and snapshot.average_loss:
            win_prob = snapshot.win_rate / 100
            loss_prob = 1 - win_prob
            snapshot.expectancy = (win_prob * snapshot.average_win) - (loss_prob * snapshot.average_loss)
            
        # Risk metrics
        snapshot.max_drawdown = await self._calculate_max_drawdown(period_trades)
        snapshot.sharpe_ratio = await self._calculate_sharpe_ratio(period_trades)
        snapshot.sortino_ratio = await self._calculate_sortino_ratio(period_trades)
        
        # Strategy breakdown
        snapshot.strategy_performance = await self._calculate_strategy_breakdown(period_trades)
        
        # Regime performance
        snapshot.regime_performance = await self._calculate_regime_breakdown(period_trades)
        
        # Store snapshot
        self.snapshots[period].append(snapshot)
        
        return snapshot
        
    async def get_current_metrics(self) -> Dict[str, float]:
        """
        Get current performance metrics.
        
        Returns:
            Dictionary of current metrics
        """
        # Check cache
        if self._metrics_cache and datetime.utcnow() < self._cache_expiry:
            return self._metrics_cache
            
        metrics = {}
        
        if not self.trades:
            return metrics
            
        # Overall metrics
        all_trades = self.trades
        winning_trades = [t for t in all_trades if t.success]
        losing_trades = [t for t in all_trades if not t.success]
        
        metrics['total_trades'] = len(all_trades)
        metrics['winning_trades'] = len(winning_trades)
        metrics['losing_trades'] = len(losing_trades)
        metrics['win_rate'] = (len(winning_trades) / len(all_trades) * 100) if all_trades else 0
        
        # P&L metrics
        metrics['total_pnl'] = sum(t.profit_loss for t in all_trades)
        metrics['average_pnl'] = metrics['total_pnl'] / len(all_trades) if all_trades else 0
        
        # Risk metrics
        metrics['current_drawdown'] = ((self.high_water_mark - self.current_equity) / 
                                     self.high_water_mark * 100) if self.high_water_mark > 0 else 0
        metrics['max_drawdown'] = await self._calculate_max_drawdown(all_trades)
        
        # Recent performance (last 20 trades)
        recent_trades = all_trades[-20:] if len(all_trades) >= 20 else all_trades
        recent_wins = [t for t in recent_trades if t.success]
        metrics['recent_win_rate'] = (len(recent_wins) / len(recent_trades) * 100) if recent_trades else 0
        
        # Streaks
        metrics['current_streak'] = self._calculate_current_streak()
        metrics['max_win_streak'] = self._calculate_max_streak(True)
        metrics['max_loss_streak'] = self._calculate_max_streak(False)
        
        # Cache results
        self._metrics_cache = metrics
        self._cache_expiry = datetime.utcnow() + timedelta(minutes=5)
        
        return metrics
        
    # Risk Metrics
    
    async def _calculate_max_drawdown(self, trades: List[TradeOutcome]) -> float:
        """Calculate maximum drawdown."""
        if not trades:
            return 0.0
            
        equity = self.current_equity
        peak = equity
        max_dd = 0.0
        
        # Reverse calculate equity curve
        for trade in reversed(trades):
            equity -= trade.profit_loss
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak if peak > 0 else 0
            max_dd = max(max_dd, drawdown)
            
        return max_dd * 100  # Return as percentage
        
    async def _calculate_sharpe_ratio(self, trades: List[TradeOutcome], 
                                    risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio."""
        if len(trades) < 2:
            return 0.0
            
        returns = [t.return_percentage / 100 for t in trades]
        
        if not returns:
            return 0.0
            
        # Annualize based on average holding period
        avg_holding_hours = np.mean([t.holding_period or 24 for t in trades])
        periods_per_year = (365 * 24) / avg_holding_hours
        
        avg_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
            
        annualized_return = avg_return * periods_per_year
        annualized_std = std_return * np.sqrt(periods_per_year)
        
        sharpe = (annualized_return - risk_free_rate) / annualized_std
        
        return sharpe
        
    async def _calculate_sortino_ratio(self, trades: List[TradeOutcome],
                                     target_return: float = 0.0) -> float:
        """Calculate Sortino ratio (downside deviation)."""
        if len(trades) < 2:
            return 0.0
            
        returns = [t.return_percentage / 100 for t in trades]
        
        if not returns:
            return 0.0
            
        # Calculate downside deviation
        downside_returns = [r for r in returns if r < target_return]
        
        if not downside_returns:
            return float('inf')  # No downside risk
            
        avg_return = np.mean(returns)
        downside_std = np.std(downside_returns)
        
        if downside_std == 0:
            return float('inf')
            
        sortino = (avg_return - target_return) / downside_std
        
        return sortino
        
    # Breakdown Analysis
    
    async def _calculate_strategy_breakdown(self, trades: List[TradeOutcome]) -> Dict[str, Dict[str, float]]:
        """Calculate performance breakdown by strategy."""
        strategy_metrics = defaultdict(lambda: {
            'trades': 0,
            'wins': 0,
            'total_pnl': 0.0,
            'win_rate': 0.0,
            'avg_pnl': 0.0
        })
        
        for trade in trades:
            strategy = trade.strategy
            strategy_metrics[strategy]['trades'] += 1
            strategy_metrics[strategy]['total_pnl'] += trade.profit_loss
            if trade.success:
                strategy_metrics[strategy]['wins'] += 1
                
        # Calculate derived metrics
        for strategy, metrics in strategy_metrics.items():
            if metrics['trades'] > 0:
                metrics['win_rate'] = (metrics['wins'] / metrics['trades']) * 100
                metrics['avg_pnl'] = metrics['total_pnl'] / metrics['trades']
                
        return dict(strategy_metrics)
        
    async def _calculate_regime_breakdown(self, trades: List[TradeOutcome]) -> Dict[str, Dict[str, float]]:
        """Calculate performance breakdown by market regime."""
        regime_metrics = defaultdict(lambda: {
            'trades': 0,
            'wins': 0,
            'total_pnl': 0.0,
            'win_rate': 0.0,
            'avg_pnl': 0.0
        })
        
        for trade in trades:
            regime = trade.market_conditions.get('market_regime', 'unknown')
            regime_metrics[regime]['trades'] += 1
            regime_metrics[regime]['total_pnl'] += trade.profit_loss
            if trade.success:
                regime_metrics[regime]['wins'] += 1
                
        # Calculate derived metrics
        for regime, metrics in regime_metrics.items():
            if metrics['trades'] > 0:
                metrics['win_rate'] = (metrics['wins'] / metrics['trades']) * 100
                metrics['avg_pnl'] = metrics['total_pnl'] / metrics['trades']
                
        return dict(regime_metrics)
        
    # Streak Calculations
    
    def _calculate_current_streak(self) -> int:
        """Calculate current win/loss streak."""
        if not self.trades:
            return 0
            
        streak = 0
        last_success = self.trades[-1].success
        
        for trade in reversed(self.trades):
            if trade.success == last_success:
                streak += 1 if last_success else -1
            else:
                break
                
        return streak
        
    def _calculate_max_streak(self, wins: bool) -> int:
        """Calculate maximum win or loss streak."""
        if not self.trades:
            return 0
            
        max_streak = 0
        current_streak = 0
        
        for trade in self.trades:
            if trade.success == wins:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
                
        return max_streak
        
    # Alert Management
    
    async def _check_performance_alerts(self, latest_trade: TradeOutcome) -> None:
        """Check for performance alerts after a trade."""
        alerts = []
        
        # Check drawdown
        current_metrics = await self.get_current_metrics()
        current_dd = current_metrics.get('current_drawdown', 0)
        
        if current_dd > self.alert_thresholds['max_drawdown'] * 100:
            alerts.append(PerformanceAlert(
                alert_id=f"alert_dd_{datetime.utcnow().timestamp()}",
                alert_type="MAX_DRAWDOWN",
                severity="critical",
                metric="drawdown",
                current_value=current_dd,
                threshold_value=self.alert_thresholds['max_drawdown'] * 100,
                deviation_percentage=current_dd - (self.alert_thresholds['max_drawdown'] * 100),
                period="current",
                recommended_actions=[
                    "Reduce position sizes",
                    "Review risk management",
                    "Consider pausing trading"
                ]
            ))
            
        # Check losing streak
        current_streak = self._calculate_current_streak()
        if current_streak <= -self.alert_thresholds['losing_streak']:
            alerts.append(PerformanceAlert(
                alert_id=f"alert_streak_{datetime.utcnow().timestamp()}",
                alert_type="LOSING_STREAK",
                severity="warning",
                metric="losing_streak",
                current_value=abs(current_streak),
                threshold_value=self.alert_thresholds['losing_streak'],
                deviation_percentage=0,
                period="current",
                recommended_actions=[
                    "Review recent trades",
                    "Check market conditions",
                    "Consider strategy adjustment"
                ]
            ))
            
        # Check daily loss
        today_trades = [t for t in self.trades 
                       if t.entry_time.date() == datetime.utcnow().date()]
        if today_trades:
            daily_pnl = sum(t.profit_loss for t in today_trades)
            daily_return = daily_pnl / self.current_equity if self.current_equity > 0 else 0
            
            if daily_return < -self.alert_thresholds['daily_loss']:
                alerts.append(PerformanceAlert(
                    alert_id=f"alert_daily_{datetime.utcnow().timestamp()}",
                    alert_type="DAILY_LOSS_LIMIT",
                    severity="critical",
                    metric="daily_loss",
                    current_value=daily_return * 100,
                    threshold_value=self.alert_thresholds['daily_loss'] * 100,
                    deviation_percentage=abs(daily_return) - self.alert_thresholds['daily_loss'],
                    period="daily",
                    recommended_actions=[
                        "Stop trading for today",
                        "Review today's trades",
                        "Analyze market conditions"
                    ]
                ))
                
        # Store and notify alerts
        for alert in alerts:
            await self._store_alert(alert)
            await self._notify_alert(alert)
            
    async def _store_alert(self, alert: PerformanceAlert) -> None:
        """Store performance alert."""
        await self.mcp.store_memory(
            "PerformanceTracker",
            MemorySlice(
                memory_type=MemoryType.EVALUATION,
                content={
                    'performance_alert': alert.dict(),
                    'timestamp': datetime.utcnow().isoformat()
                },
                importance=MemoryImportance.CRITICAL if alert.severity == "critical" else MemoryImportance.HIGH
            )
        )
        
    async def _notify_alert(self, alert: PerformanceAlert) -> None:
        """Notify other agents of performance alert."""
        await self.mcp.share_context(
            "PerformanceTracker",
            ["RiskManagerAgent", "TacticalExecutorAgent", "StrategicPlannerAgent"],
            {
                'performance_alert': {
                    'type': alert.alert_type,
                    'severity': alert.severity,
                    'metric': alert.metric,
                    'value': alert.current_value,
                    'actions': alert.recommended_actions
                }
            }
        )
        
    # Background Tasks
    
    async def _monitor_performance(self) -> None:
        """Background task to monitor performance."""
        while True:
            try:
                # Calculate periodic snapshots
                now = datetime.utcnow()
                
                # Daily snapshot at midnight
                if now.hour == 0 and now.minute < 1:
                    yesterday = now - timedelta(days=1)
                    await self.calculate_performance_snapshot(
                        ReflectionPeriod.DAILY,
                        yesterday.replace(hour=0, minute=0, second=0),
                        yesterday.replace(hour=23, minute=59, second=59)
                    )
                    
                # Weekly snapshot on Sundays
                if now.weekday() == 6 and now.hour == 0 and now.minute < 1:
                    week_ago = now - timedelta(days=7)
                    await self.calculate_performance_snapshot(
                        ReflectionPeriod.WEEKLY,
                        week_ago.replace(hour=0, minute=0, second=0),
                        now
                    )
                    
                # Check for performance degradation
                await self._check_performance_degradation()
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
                
    async def _check_performance_degradation(self) -> None:
        """Check for performance degradation patterns."""
        if len(self.trades) < 20:
            return
            
        # Compare recent performance to historical
        all_trades = self.trades
        recent_trades = all_trades[-20:]
        historical_trades = all_trades[:-20]
        
        if not historical_trades:
            return
            
        # Calculate win rates
        recent_win_rate = sum(1 for t in recent_trades if t.success) / len(recent_trades)
        historical_win_rate = sum(1 for t in historical_trades if t.success) / len(historical_trades)
        
        # Check for significant drop
        if historical_win_rate > 0 and recent_win_rate < historical_win_rate * (1 - self.alert_thresholds['win_rate_drop']):
            alert = PerformanceAlert(
                alert_id=f"alert_winrate_{datetime.utcnow().timestamp()}",
                alert_type="WIN_RATE_DEGRADATION",
                severity="warning",
                metric="win_rate",
                current_value=recent_win_rate * 100,
                threshold_value=historical_win_rate * 100,
                deviation_percentage=(historical_win_rate - recent_win_rate) * 100,
                period="recent_20_trades",
                comparison_period="historical",
                recommended_actions=[
                    "Review recent strategy changes",
                    "Analyze market regime shifts",
                    "Consider reverting to previous parameters"
                ]
            )
            
            await self._store_alert(alert)
            await self._notify_alert(alert)
            
    # Data Persistence
    
    async def _store_trade_in_mcp(self, trade: TradeOutcome) -> None:
        """Store trade in MCP memory."""
        await self.mcp.store_memory(
            "PerformanceTracker",
            MemorySlice(
                memory_type=MemoryType.EXECUTION,
                content={
                    'trade_outcome': trade.dict(),
                    'equity_after': self.current_equity,
                    'timestamp': datetime.utcnow().isoformat()
                },
                importance=MemoryImportance.HIGH if abs(trade.profit_loss) > 1000 else MemoryImportance.MEDIUM
            )
        )
        
    async def _load_historical_trades(self) -> None:
        """Load historical trades from MCP."""
        memories = await self.mcp.semantic_search(
            "PerformanceTracker",
            "trade outcome execution history",
            scope="own"
        )
        
        for memory in memories:
            if 'trade_outcome' in memory.content:
                trade_data = memory.content['trade_outcome']
                trade = TradeOutcome(**trade_data)
                self.trades.append(trade)
                self.trade_index[trade.trade_id] = trade
                
        # Sort by entry time
        self.trades.sort(key=lambda t: t.entry_time)
        
        logger.info(f"Loaded {len(self.trades)} historical trades")
        
    async def _save_performance_data(self) -> None:
        """Save current performance data."""
        performance_data = {
            'total_trades': len(self.trades),
            'current_equity': self.current_equity,
            'high_water_mark': self.high_water_mark,
            'metrics': await self.get_current_metrics(),
            'last_snapshot': self.snapshots[ReflectionPeriod.DAILY][-1].dict() if self.snapshots[ReflectionPeriod.DAILY] else None
        }
        
        await self.mcp.store_memory(
            "PerformanceTracker",
            MemorySlice(
                memory_type=MemoryType.EVALUATION,
                content={
                    'performance_summary': performance_data,
                    'timestamp': datetime.utcnow().isoformat()
                },
                importance=MemoryImportance.HIGH
            )
        )