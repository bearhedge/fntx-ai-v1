"""
Reflection Framework Schemas
Data models for performance tracking, learning, and strategy refinement.
"""

from typing import Any, Dict, List, Optional, Set
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class PerformanceMetric(str, Enum):
    """Types of performance metrics tracked."""
    WIN_RATE = "win_rate"
    PROFIT_FACTOR = "profit_factor"
    SHARPE_RATIO = "sharpe_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    AVERAGE_RETURN = "average_return"
    RISK_ADJUSTED_RETURN = "risk_adjusted_return"
    CONSISTENCY_SCORE = "consistency_score"


class LearningType(str, Enum):
    """Types of learning mechanisms."""
    REINFORCEMENT = "reinforcement"
    SUPERVISED = "supervised"
    PATTERN_BASED = "pattern_based"
    RULE_BASED = "rule_based"
    COLLABORATIVE = "collaborative"


class InsightCategory(str, Enum):
    """Categories of insights generated."""
    STRATEGY_OPTIMIZATION = "strategy_optimization"
    RISK_MANAGEMENT = "risk_management"
    TIMING_IMPROVEMENT = "timing_improvement"
    MARKET_ADAPTATION = "market_adaptation"
    EXECUTION_EFFICIENCY = "execution_efficiency"
    PATTERN_RECOGNITION = "pattern_recognition"


class ReflectionPeriod(str, Enum):
    """Time periods for reflection cycles."""
    TRADE_LEVEL = "trade_level"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class TradeOutcome(BaseModel):
    """Detailed trade outcome for analysis."""
    trade_id: str = Field(..., description="Unique trade identifier")
    strategy: str = Field(..., description="Strategy used")
    entry_time: datetime = Field(..., description="Trade entry time")
    exit_time: Optional[datetime] = Field(None, description="Trade exit time")
    
    # Trade details
    symbol: str = Field(..., description="Traded symbol")
    position_type: str = Field(..., description="Long/Short/Option type")
    entry_price: float = Field(..., description="Entry price")
    exit_price: Optional[float] = Field(None, description="Exit price")
    quantity: int = Field(..., description="Position size")
    
    # Outcome metrics
    profit_loss: float = Field(..., description="P&L in dollars")
    return_percentage: float = Field(..., description="Return percentage")
    holding_period: Optional[float] = Field(None, description="Holding period in hours")
    max_favorable_excursion: Optional[float] = Field(None, description="Maximum profit during trade")
    max_adverse_excursion: Optional[float] = Field(None, description="Maximum loss during trade")
    
    # Context
    market_conditions: Dict[str, Any] = Field(..., description="Market conditions at entry")
    entry_reasoning: List[str] = Field(..., description="Reasons for entering trade")
    exit_reasoning: Optional[List[str]] = Field(None, description="Reasons for exit")
    
    # Analysis flags
    success: bool = Field(..., description="Whether trade was successful")
    followed_plan: bool = Field(..., description="Whether trade followed the plan")
    early_exit: bool = Field(default=False, description="Whether exited early")
    stop_hit: bool = Field(default=False, description="Whether stop loss was hit")


class PerformanceSnapshot(BaseModel):
    """Performance metrics for a specific period."""
    period_start: datetime = Field(..., description="Period start time")
    period_end: datetime = Field(..., description="Period end time")
    period_type: ReflectionPeriod = Field(..., description="Type of period")
    
    # Core metrics
    total_trades: int = Field(default=0, description="Total number of trades")
    winning_trades: int = Field(default=0, description="Number of winning trades")
    losing_trades: int = Field(default=0, description="Number of losing trades")
    
    # Financial metrics
    total_profit: float = Field(default=0.0, description="Total profit")
    total_loss: float = Field(default=0.0, description="Total loss")
    net_profit: float = Field(default=0.0, description="Net profit")
    
    # Calculated metrics
    win_rate: Optional[float] = Field(None, description="Win rate percentage")
    profit_factor: Optional[float] = Field(None, description="Profit factor")
    average_win: Optional[float] = Field(None, description="Average winning trade")
    average_loss: Optional[float] = Field(None, description="Average losing trade")
    expectancy: Optional[float] = Field(None, description="Trade expectancy")
    
    # Risk metrics
    max_drawdown: Optional[float] = Field(None, description="Maximum drawdown")
    sharpe_ratio: Optional[float] = Field(None, description="Sharpe ratio")
    sortino_ratio: Optional[float] = Field(None, description="Sortino ratio")
    calmar_ratio: Optional[float] = Field(None, description="Calmar ratio")
    
    # Strategy breakdown
    strategy_performance: Dict[str, Dict[str, float]] = Field(
        default_factory=dict, 
        description="Performance by strategy"
    )
    
    # Market regime performance
    regime_performance: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description="Performance by market regime"
    )


class LearningInsight(BaseModel):
    """An insight learned from performance analysis."""
    insight_id: str = Field(..., description="Unique insight identifier")
    category: InsightCategory = Field(..., description="Insight category")
    confidence: float = Field(..., description="Confidence in the insight (0-1)")
    
    # Insight details
    observation: str = Field(..., description="What was observed")
    conclusion: str = Field(..., description="Conclusion drawn")
    evidence: List[Dict[str, Any]] = Field(..., description="Supporting evidence")
    
    # Actionable recommendations
    recommendations: List[str] = Field(..., description="Recommended actions")
    expected_impact: Dict[str, float] = Field(
        ..., 
        description="Expected impact on metrics"
    )
    
    # Metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    based_on_trades: List[str] = Field(..., description="Trade IDs this insight is based on")
    learning_method: LearningType = Field(..., description="How this was learned")
    
    # Validation
    tested: bool = Field(default=False, description="Whether insight has been tested")
    test_results: Optional[Dict[str, Any]] = Field(None, description="Test results if tested")
    adoption_status: str = Field(default="pending", description="pending/adopted/rejected")


class StrategyAdjustment(BaseModel):
    """Proposed or implemented strategy adjustment."""
    adjustment_id: str = Field(..., description="Unique adjustment identifier")
    strategy_name: str = Field(..., description="Strategy being adjusted")
    adjustment_type: str = Field(..., description="Type of adjustment")
    
    # Changes
    parameter_changes: Dict[str, Dict[str, Any]] = Field(
        ..., 
        description="Parameter changes (param: {old, new})"
    )
    rule_changes: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Rule modifications"
    )
    
    # Rationale
    reasoning: List[str] = Field(..., description="Reasons for adjustment")
    based_on_insights: List[str] = Field(..., description="Insight IDs driving this")
    performance_trigger: Optional[Dict[str, Any]] = Field(
        None,
        description="Performance metrics that triggered adjustment"
    )
    
    # Testing
    backtest_results: Optional[Dict[str, float]] = Field(
        None,
        description="Backtest results if available"
    )
    paper_trade_results: Optional[Dict[str, float]] = Field(
        None,
        description="Paper trading results"
    )
    
    # Implementation
    proposed_at: datetime = Field(default_factory=datetime.utcnow)
    approved: bool = Field(default=False)
    implemented_at: Optional[datetime] = Field(None)
    rollback_plan: Optional[Dict[str, Any]] = Field(None, description="How to rollback if needed")


class ReflectionCycle(BaseModel):
    """A complete reflection cycle."""
    cycle_id: str = Field(..., description="Unique cycle identifier")
    period: ReflectionPeriod = Field(..., description="Reflection period type")
    start_time: datetime = Field(..., description="Cycle start time")
    end_time: datetime = Field(..., description="Cycle end time")
    
    # Performance analysis
    performance_snapshot: PerformanceSnapshot = Field(..., description="Performance metrics")
    trades_analyzed: List[str] = Field(..., description="Trade IDs analyzed")
    
    # Insights generated
    insights: List[LearningInsight] = Field(default_factory=list, description="Insights generated")
    patterns_identified: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Patterns found in trading behavior"
    )
    
    # Improvements
    strategy_adjustments: List[StrategyAdjustment] = Field(
        default_factory=list,
        description="Strategy adjustments proposed"
    )
    risk_adjustments: Dict[str, Any] = Field(
        default_factory=dict,
        description="Risk parameter adjustments"
    )
    
    # Cross-agent learning
    shared_learnings: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Learnings shared with other agents"
    )
    adopted_learnings: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Learnings adopted from other agents"
    )
    
    # Meta-analysis
    reflection_quality_score: float = Field(
        default=0.0,
        description="Quality score of this reflection"
    )
    actionable_items: int = Field(default=0, description="Number of actionable items generated")
    implemented_items: int = Field(default=0, description="Number of items implemented")


class LearningMemory(BaseModel):
    """Long-term learning memory storage."""
    memory_id: str = Field(..., description="Unique memory identifier")
    memory_type: str = Field(..., description="Type of memory")
    
    # Content
    learned_rules: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Trading rules learned"
    )
    successful_patterns: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Successful trading patterns"
    )
    failure_patterns: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Patterns that lead to failure"
    )
    
    # Market adaptations
    regime_strategies: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optimal strategies per market regime"
    )
    condition_responses: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Responses to specific conditions"
    )
    
    # Performance correlations
    factor_correlations: Dict[str, float] = Field(
        default_factory=dict,
        description="Factors correlated with success"
    )
    timing_patterns: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optimal timing patterns"
    )
    
    # Meta information
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    confidence_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Confidence in different learnings"
    )
    validation_status: Dict[str, bool] = Field(
        default_factory=dict,
        description="Which learnings have been validated"
    )


class CrossAgentLearning(BaseModel):
    """Learning shared between agents."""
    learning_id: str = Field(..., description="Unique learning identifier")
    source_agent: str = Field(..., description="Agent that generated the learning")
    target_agents: List[str] = Field(..., description="Agents to share with")
    
    # Learning content
    learning_type: str = Field(..., description="Type of learning")
    content: Dict[str, Any] = Field(..., description="Learning content")
    applicability: Dict[str, float] = Field(
        ...,
        description="Applicability score per agent"
    )
    
    # Evidence
    supporting_data: Dict[str, Any] = Field(..., description="Data supporting the learning")
    performance_improvement: Dict[str, float] = Field(
        ...,
        description="Expected performance improvement"
    )
    
    # Adoption tracking
    shared_at: datetime = Field(default_factory=datetime.utcnow)
    adoption_status: Dict[str, str] = Field(
        default_factory=dict,
        description="Adoption status per agent"
    )
    feedback: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Feedback from target agents"
    )


class PerformanceAlert(BaseModel):
    """Alert for significant performance deviations."""
    alert_id: str = Field(..., description="Unique alert identifier")
    alert_type: str = Field(..., description="Type of alert")
    severity: str = Field(..., description="Alert severity (info/warning/critical)")
    
    # Alert details
    metric: str = Field(..., description="Metric that triggered alert")
    current_value: float = Field(..., description="Current metric value")
    threshold_value: float = Field(..., description="Threshold that was crossed")
    deviation_percentage: float = Field(..., description="Percentage deviation")
    
    # Context
    period: str = Field(..., description="Time period for the metric")
    comparison_period: Optional[str] = Field(None, description="Comparison period if applicable")
    
    # Recommendations
    recommended_actions: List[str] = Field(..., description="Recommended actions")
    auto_adjustments: Optional[Dict[str, Any]] = Field(
        None,
        description="Automatic adjustments if enabled"
    )
    
    # Tracking
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged: bool = Field(default=False)
    resolved: bool = Field(default=False)
    resolution_notes: Optional[str] = Field(None)