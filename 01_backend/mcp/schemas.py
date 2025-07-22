"""
Pydantic schemas for MCP memory system.
Defines structured data models for all memory types.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, Union
from uuid import uuid4

from pydantic import BaseModel, Field, validator


class MemoryType(str, Enum):
    """Types of memories stored in the system."""
    MARKET_OBSERVATION = "market_observation"
    TRADE_DECISION = "trade_decision"
    EXECUTION_PLAN = "execution_plan"
    TRADE_OUTCOME = "trade_outcome"
    USER_PREFERENCE = "user_preference"
    REFLECTION = "reflection"
    CONSOLIDATED = "consolidated"
    ACTIVE_TRADE = "active_trade"
    MARKET_INTELLIGENCE = "market_intelligence"
    STRATEGY_OPTION = "strategy_option"
    

class MemoryImportance(int, Enum):
    """Importance levels for memory storage tiering."""
    CRITICAL = 10  # Mission-critical, keep in hot memory
    HIGH = 7       # Important for current session
    MEDIUM = 5     # Useful for context
    LOW = 3        # Archive candidate
    TRIVIAL = 1    # Can be discarded
    

class TradingSessionStatus(str, Enum):
    """Status of a trading session."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    

class ExecutionPlanStatus(str, Enum):
    """Status of an execution plan."""
    DRAFT = "draft"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    CONFIRMED = "confirmed"
    EXECUTING = "executing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class BaseMemory(BaseModel):
    """Base class for all memory types."""
    id: Optional[str] = Field(default_factory=lambda: str(uuid4()))
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = {}
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MemorySlice(BaseMemory):
    """
    Core memory unit in the MCP system.
    Represents a single piece of information from an agent or user interaction.
    """
    agent_id: str = Field(..., description="ID of the agent that created this memory")
    session_id: Optional[str] = Field(None, description="Trading session this memory belongs to")
    user_id: Optional[str] = Field(None, description="User associated with this memory")
    memory_type: MemoryType = Field(..., description="Type of memory for categorization")
    content: Dict[str, Any] = Field(..., description="Actual memory content")
    importance: MemoryImportance = Field(
        default=MemoryImportance.MEDIUM,
        description="Importance level for storage tiering"
    )
    embedding: Optional[List[float]] = Field(None, description="Vector embedding for semantic search")
    references: Optional[List[str]] = Field(default_factory=list, description="IDs of related memories")
    ttl_seconds: Optional[int] = Field(None, description="Time to live in seconds")
    archive: bool = Field(default=True, description="Whether to archive when consolidated")
    
    @validator('content')
    def validate_content(cls, v, values):
        """Ensure content matches expected schema for memory type."""
        memory_type = values.get('memory_type')
        
        # Add type-specific validation here
        if memory_type == MemoryType.TRADE_OUTCOME:
            required_fields = ['trade_id', 'outcome', 'profit_loss']
            for field in required_fields:
                if field not in v:
                    raise ValueError(f"Trade outcome must include {field}")
                    
        return v


class ExecutionPlan(BaseMemory):
    """
    Detailed plan for executing a trade, created through collaboration
    between user and AI agents.
    """
    plan_id: str = Field(default_factory=lambda: f"PLAN_{uuid4().hex[:8]}")
    session_id: str = Field(..., description="Trading session ID")
    user_id: str = Field(..., description="User who confirmed this plan")
    status: ExecutionPlanStatus = Field(default=ExecutionPlanStatus.DRAFT)
    
    # Strategy details
    strategy_type: str = Field(..., description="Type of strategy (e.g., 'spy_put_spread')")
    symbol: str = Field(default="SPY", description="Trading symbol")
    option_type: str = Field(..., description="PUT or CALL")
    
    # Trade parameters
    strike: float = Field(..., description="Option strike price")
    expiration: str = Field(..., description="Expiration date (YYYYMMDD)")
    contracts: int = Field(..., ge=1, description="Number of contracts")
    
    # Entry conditions
    entry_conditions: Dict[str, Any] = Field(
        ...,
        description="Conditions that must be met to enter trade"
    )
    
    # Risk management
    stop_loss: Optional[float] = Field(None, description="Stop loss price")
    take_profit: Optional[float] = Field(None, description="Take profit price")
    max_loss_dollars: Optional[float] = Field(None, description="Maximum loss in dollars")
    risk_score: float = Field(..., ge=0, le=10, description="Risk score 0-10")
    
    # Exit rules
    exit_rules: Dict[str, Any] = Field(
        default_factory=dict,
        description="Rules for exiting the position"
    )
    
    # AI analysis
    ai_confidence: float = Field(..., ge=0, le=1, description="AI confidence in this plan")
    ai_rationale: str = Field(..., description="AI explanation for this plan")
    market_context: Dict[str, Any] = Field(..., description="Market conditions at plan creation")
    
    # User interactions
    user_confirmations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="User confirmations and parameter choices"
    )
    modifications: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="User modifications to original AI suggestion"
    )
    
    # Execution tracking
    execution_start: Optional[datetime] = None
    execution_complete: Optional[datetime] = None
    actual_entry_price: Optional[float] = None
    actual_exit_price: Optional[float] = None
    

class TradeOutcome(BaseMemory):
    """
    Record of a completed trade with performance metrics and reflection.
    """
    trade_id: str = Field(..., description="Unique trade identifier")
    plan_id: Optional[str] = Field(None, description="Associated execution plan ID")
    session_id: str = Field(..., description="Trading session ID")
    user_id: str = Field(..., description="User who executed this trade")
    
    # Trade details
    strategy: Dict[str, Any] = Field(..., description="Strategy configuration used")
    entry_time: datetime = Field(..., description="When position was opened")
    exit_time: Optional[datetime] = Field(None, description="When position was closed")
    
    # Outcome
    status: str = Field(..., description="OPEN, CLOSED, EXPIRED, ASSIGNED")
    profit_loss: float = Field(..., description="Profit/loss in dollars")
    profit_loss_percent: float = Field(..., description="Profit/loss as percentage")
    
    # Performance metrics
    holding_period_minutes: Optional[int] = None
    max_profit_during_trade: Optional[float] = None
    max_loss_during_trade: Optional[float] = None
    volatility_during_trade: Optional[float] = None
    
    # Reflection
    reflection: Dict[str, Any] = Field(
        default_factory=dict,
        description="Post-trade analysis and learnings"
    )
    
    # Market context
    market_conditions_entry: Dict[str, Any] = Field(..., description="Market state at entry")
    market_conditions_exit: Optional[Dict[str, Any]] = None
    
    # Execution quality
    slippage: Optional[float] = Field(None, description="Execution slippage")
    fees: float = Field(default=0, description="Transaction fees")
    
    @property
    def was_profitable(self) -> bool:
        """Check if trade was profitable."""
        return self.profit_loss > 0
        

class AgentMemory(BaseMemory):
    """
    Structured memory for individual agents to maintain state and learnings.
    """
    agent_id: str = Field(..., description="Agent identifier")
    memory_version: int = Field(default=1, description="Schema version")
    
    # Agent state
    current_state: Dict[str, Any] = Field(
        default_factory=dict,
        description="Current operational state"
    )
    
    # Historical data
    performance_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Historical performance metrics"
    )
    
    # Learned parameters
    learned_parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters learned from experience"
    )
    
    # Preferences and patterns
    identified_patterns: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Patterns identified by the agent"
    )
    
    # Last significant events
    last_decision: Optional[Dict[str, Any]] = None
    last_reflection: Optional[Dict[str, Any]] = None
    last_error: Optional[Dict[str, Any]] = None
    

class MemoryQuery(BaseModel):
    """Query parameters for searching memories."""
    # Filter criteria
    agent_ids: Optional[List[str]] = None
    memory_types: Optional[List[MemoryType]] = None
    session_ids: Optional[List[str]] = None
    user_ids: Optional[List[str]] = None
    
    # Time range
    date_range: Optional[List[datetime]] = None
    
    # Importance filter
    importance_min: Optional[MemoryImportance] = None
    
    # Semantic search
    semantic_query: Optional[str] = None
    
    # Options
    include_hot_memory: bool = True
    include_archived: bool = False
    

class TradingSession(BaseMemory):
    """
    Represents a complete trading session with all associated context.
    """
    session_id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="User running this session")
    date: datetime = Field(..., description="Session date")
    status: TradingSessionStatus = Field(default=TradingSessionStatus.ACTIVE)
    
    # Market snapshot at open
    market_open_snapshot: Dict[str, Any] = Field(
        ...,
        description="Market conditions at session start"
    )
    
    # Plans and trades
    active_plans: List[str] = Field(
        default_factory=list,
        description="IDs of active execution plans"
    )
    completed_trades: List[str] = Field(
        default_factory=list,
        description="IDs of completed trades"
    )
    
    # Conversation and decisions
    conversation_summary: Optional[str] = None
    key_decisions: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Metrics
    session_metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Aggregate performance metrics"
    )
    
    # User state
    user_preferences: Dict[str, Any] = Field(
        default_factory=dict,
        description="User preferences for this session"
    )
    psychological_state: Dict[str, Any] = Field(
        default_factory=dict,
        description="Inferred psychological state"
    )


class MarketIntelligence(BaseMemory):
    """
    Aggregated market intelligence from various sources.
    """
    scan_date: datetime = Field(..., description="When this scan was performed")
    
    # Market sentiment
    headline_sentiment: Dict[str, Any] = Field(
        ...,
        description="Sentiment analysis of news headlines"
    )
    
    # Volatility analysis
    volatility_catalysts: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Identified volatility catalysts"
    )
    
    # Earnings impact
    earnings_impact: Dict[str, Any] = Field(
        default_factory=dict,
        description="Expected impact from earnings"
    )
    
    # Options flow
    unusual_options: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Unusual options activity detected"
    )
    
    # Risk events
    risk_events: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Upcoming risk events"
    )
    
    # Trading edge
    trading_edge: float = Field(
        ...,
        ge=0,
        le=1,
        description="Calculated edge score 0-1"
    )
    
    # Recommendations
    recommendations: List[str] = Field(
        default_factory=list,
        description="AI-generated recommendations"
    )