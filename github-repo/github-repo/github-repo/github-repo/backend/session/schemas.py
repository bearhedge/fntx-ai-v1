"""
Session Management Schemas
Data models for trading sessions and state management.
"""

from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field
import uuid


class SessionStatus(str, Enum):
    """Trading session statuses."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    SUSPENDED = "suspended"
    CLOSING = "closing"
    CLOSED = "closed"
    ERROR = "error"


class SessionType(str, Enum):
    """Types of trading sessions."""
    REGULAR = "regular"
    EXTENDED_HOURS = "extended_hours"
    PAPER_TRADING = "paper_trading"
    BACKTEST = "backtest"
    MANUAL_OVERRIDE = "manual_override"


class AgentState(BaseModel):
    """State of an individual agent within a session."""
    agent_id: str = Field(..., description="Unique agent identifier")
    status: str = Field(..., description="Agent status (active/paused/error)")
    last_update: datetime = Field(default_factory=datetime.utcnow)
    
    # Agent-specific state
    internal_state: Dict[str, Any] = Field(
        default_factory=dict,
        description="Agent's internal state data"
    )
    
    # Performance within session
    actions_taken: int = Field(default=0, description="Number of actions in session")
    decisions_made: int = Field(default=0, description="Number of decisions made")
    errors_encountered: int = Field(default=0, description="Number of errors")
    
    # Resource usage
    memory_usage_mb: float = Field(default=0.0, description="Memory usage in MB")
    processing_time_ms: float = Field(default=0.0, description="Total processing time")


class MarketState(BaseModel):
    """Market state snapshot within a session."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Market data
    spy_price: float = Field(..., description="Current SPY price")
    vix_level: float = Field(..., description="Current VIX level")
    market_regime: str = Field(..., description="Current market regime")
    
    # Trading conditions
    market_open: bool = Field(..., description="Whether market is open")
    extended_hours: bool = Field(default=False, description="Extended hours trading")
    liquidity_status: str = Field(default="normal", description="Liquidity conditions")
    
    # Technical levels
    support_levels: List[float] = Field(default_factory=list)
    resistance_levels: List[float] = Field(default_factory=list)
    key_levels: Dict[str, float] = Field(default_factory=dict)


class TradingState(BaseModel):
    """Trading-specific state within a session."""
    # Positions
    open_positions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Currently open positions"
    )
    pending_orders: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Pending orders"
    )
    
    # Daily metrics
    trades_today: int = Field(default=0, description="Number of trades today")
    daily_pnl: float = Field(default=0.0, description="Daily P&L")
    daily_return: float = Field(default=0.0, description="Daily return percentage")
    
    # Risk tracking
    current_exposure: float = Field(default=0.0, description="Current market exposure")
    margin_used: float = Field(default=0.0, description="Margin in use")
    buying_power: float = Field(default=0.0, description="Available buying power")
    
    # Limits and controls
    max_daily_loss_remaining: float = Field(..., description="Remaining loss limit")
    position_limit_remaining: int = Field(..., description="Remaining position slots")
    trading_enabled: bool = Field(default=True, description="Whether trading is enabled")


class SessionCheckpoint(BaseModel):
    """Checkpoint for session state recovery."""
    checkpoint_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = Field(..., description="Parent session ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # State snapshots
    agent_states: Dict[str, AgentState] = Field(..., description="All agent states")
    market_state: MarketState = Field(..., description="Market state snapshot")
    trading_state: TradingState = Field(..., description="Trading state snapshot")
    
    # Metadata
    checkpoint_type: str = Field(default="periodic", description="Type of checkpoint")
    is_recovery_point: bool = Field(default=True, description="Can recover from this")
    compressed: bool = Field(default=False, description="Whether data is compressed")
    
    # Validation
    checksum: Optional[str] = Field(None, description="State checksum for validation")
    verified: bool = Field(default=False, description="Whether checkpoint is verified")


class SessionEvent(BaseModel):
    """Event that occurred during a session."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = Field(..., description="Session this event belongs to")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Event details
    event_type: str = Field(..., description="Type of event")
    event_category: str = Field(..., description="Event category")
    severity: str = Field(default="info", description="Event severity")
    
    # Event data
    source_agent: Optional[str] = Field(None, description="Agent that triggered event")
    description: str = Field(..., description="Event description")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event data")
    
    # Impact
    requires_action: bool = Field(default=False, description="Whether action required")
    action_taken: Optional[str] = Field(None, description="Action taken if any")
    impact_assessment: Optional[Dict[str, Any]] = Field(None, description="Impact analysis")


class SessionMetrics(BaseModel):
    """Metrics for a trading session."""
    session_id: str = Field(..., description="Session identifier")
    
    # Duration metrics
    start_time: datetime = Field(..., description="Session start time")
    end_time: Optional[datetime] = Field(None, description="Session end time")
    active_duration: timedelta = Field(default=timedelta(), description="Active trading time")
    pause_duration: timedelta = Field(default=timedelta(), description="Time paused")
    
    # Trading metrics
    total_trades: int = Field(default=0, description="Total trades executed")
    winning_trades: int = Field(default=0, description="Number of winning trades")
    losing_trades: int = Field(default=0, description="Number of losing trades")
    
    # Financial metrics
    gross_pnl: float = Field(default=0.0, description="Gross P&L")
    net_pnl: float = Field(default=0.0, description="Net P&L after costs")
    max_drawdown: float = Field(default=0.0, description="Maximum drawdown")
    
    # Efficiency metrics
    decision_latency_ms: float = Field(default=0.0, description="Average decision time")
    execution_slippage: float = Field(default=0.0, description="Average slippage")
    error_rate: float = Field(default=0.0, description="Error rate percentage")
    
    # Resource metrics
    peak_memory_mb: float = Field(default=0.0, description="Peak memory usage")
    total_api_calls: int = Field(default=0, description="Total API calls made")
    checkpoint_count: int = Field(default=0, description="Number of checkpoints")


class TradingSession(BaseModel):
    """Complete trading session with all state."""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_type: SessionType = Field(..., description="Type of session")
    status: SessionStatus = Field(default=SessionStatus.INITIALIZING)
    
    # Temporal bounds
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(None, description="When trading started")
    ended_at: Optional[datetime] = Field(None, description="When session ended")
    
    # Configuration
    config: Dict[str, Any] = Field(default_factory=dict, description="Session configuration")
    risk_parameters: Dict[str, float] = Field(..., description="Risk limits for session")
    enabled_strategies: List[str] = Field(..., description="Strategies enabled")
    
    # Current state
    agent_states: Dict[str, AgentState] = Field(
        default_factory=dict,
        description="Current state of all agents"
    )
    market_state: Optional[MarketState] = Field(None, description="Current market state")
    trading_state: Optional[TradingState] = Field(None, description="Current trading state")
    
    # History
    events: List[SessionEvent] = Field(default_factory=list, description="Session events")
    checkpoints: List[str] = Field(
        default_factory=list,
        description="Checkpoint IDs in order"
    )
    
    # Metrics
    metrics: Optional[SessionMetrics] = Field(None, description="Session metrics")
    
    # Recovery
    last_checkpoint_id: Optional[str] = Field(None, description="Latest checkpoint")
    recovery_data: Optional[Dict[str, Any]] = Field(None, description="Recovery metadata")
    
    # Hierarchy
    parent_session_id: Optional[str] = Field(None, description="Parent session if nested")
    child_session_ids: List[str] = Field(default_factory=list, description="Child sessions")


class SessionTransition(BaseModel):
    """Transition between session states."""
    transition_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = Field(..., description="Session being transitioned")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Transition details
    from_status: SessionStatus = Field(..., description="Previous status")
    to_status: SessionStatus = Field(..., description="New status")
    trigger: str = Field(..., description="What triggered the transition")
    
    # Validation
    pre_conditions_met: bool = Field(..., description="Whether preconditions were met")
    post_conditions_met: Optional[bool] = Field(None, description="Whether postconditions met")
    
    # State transfer
    state_preserved: bool = Field(default=True, description="Whether state was preserved")
    data_migrated: Dict[str, bool] = Field(
        default_factory=dict,
        description="What data was migrated"
    )
    
    # Issues
    warnings: List[str] = Field(default_factory=list, description="Transition warnings")
    errors: List[str] = Field(default_factory=list, description="Transition errors")


class SessionRecoveryPlan(BaseModel):
    """Plan for recovering a session."""
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = Field(..., description="Session to recover")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Recovery strategy
    recovery_type: str = Field(..., description="Type of recovery")
    checkpoint_id: Optional[str] = Field(None, description="Checkpoint to recover from")
    fallback_checkpoint_ids: List[str] = Field(
        default_factory=list,
        description="Fallback checkpoints"
    )
    
    # Recovery steps
    steps: List[Dict[str, Any]] = Field(..., description="Recovery steps in order")
    estimated_duration: timedelta = Field(..., description="Estimated recovery time")
    
    # Validation
    data_integrity_checks: List[Dict[str, Any]] = Field(
        ...,
        description="Integrity checks to perform"
    )
    rollback_points: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Points where rollback is possible"
    )
    
    # Risk assessment
    data_loss_risk: str = Field(..., description="Risk level of data loss")
    state_consistency_risk: str = Field(..., description="Risk of inconsistent state")
    recovery_confidence: float = Field(..., description="Confidence in recovery success")


class SessionTemplate(BaseModel):
    """Template for creating new sessions."""
    template_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    template_name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    
    # Configuration
    session_type: SessionType = Field(..., description="Type of sessions to create")
    default_config: Dict[str, Any] = Field(..., description="Default configuration")
    default_risk_parameters: Dict[str, float] = Field(..., description="Default risk limits")
    
    # Agents
    required_agents: List[str] = Field(..., description="Agents that must be present")
    optional_agents: List[str] = Field(default_factory=list, description="Optional agents")
    agent_configurations: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Per-agent configurations"
    )
    
    # Strategies
    enabled_strategies: List[str] = Field(..., description="Strategies to enable")
    strategy_parameters: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Strategy-specific parameters"
    )
    
    # Lifecycle
    auto_start_conditions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Conditions for auto-start"
    )
    auto_stop_conditions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Conditions for auto-stop"
    )
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = Field(None, description="Last time template was used")
    usage_count: int = Field(default=0, description="Number of times used")