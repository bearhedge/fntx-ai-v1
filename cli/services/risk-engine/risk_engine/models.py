"""
Risk models and limit definitions for FNTX AI trading

Implements multi-level risk controls:
- Position limits
- Loss limits
- Exposure limits
- Concentration limits
"""
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class RiskLevel(Enum):
    """Risk severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ViolationType(Enum):
    """Types of risk violations"""
    POSITION_LIMIT = "position_limit"
    LOSS_LIMIT = "loss_limit"
    EXPOSURE_LIMIT = "exposure_limit"
    CONCENTRATION_LIMIT = "concentration_limit"
    DRAWDOWN_LIMIT = "drawdown_limit"
    LEVERAGE_LIMIT = "leverage_limit"


class RiskLimits(BaseModel):
    """User/Agent risk limits configuration"""
    # Position limits
    max_position_size: float = Field(default=100000, description="Max USD per position")
    max_positions: int = Field(default=10, description="Max number of open positions")
    max_concentration: float = Field(default=0.25, description="Max % in single position")
    
    # Loss limits
    daily_loss_limit: float = Field(default=0.02, description="Max daily loss %")
    max_drawdown: float = Field(default=0.10, description="Max drawdown %")
    trailing_stop_loss: float = Field(default=0.05, description="Trailing stop %")
    
    # Exposure limits
    max_leverage: float = Field(default=2.0, description="Max leverage ratio")
    max_market_exposure: float = Field(default=0.80, description="Max % of capital exposed")
    max_sector_exposure: float = Field(default=0.30, description="Max % in one sector")
    
    # Options-specific limits
    max_theta_exposure: float = Field(default=-1000, description="Max daily theta decay")
    max_vega_exposure: float = Field(default=5000, description="Max vega exposure")
    max_gamma_exposure: float = Field(default=1000, description="Max gamma exposure")
    
    @validator('max_concentration', 'daily_loss_limit', 'max_drawdown', 
               'trailing_stop_loss', 'max_market_exposure', 'max_sector_exposure')
    def validate_percentages(cls, v):
        """Ensure percentage values are between 0 and 1"""
        if not 0 <= v <= 1:
            raise ValueError(f"Percentage must be between 0 and 1, got {v}")
        return v


class Position(BaseModel):
    """Trading position representation"""
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    position_type: str  # "long" or "short"
    entry_time: datetime
    sector: Optional[str] = None
    
    # Options-specific fields
    is_option: bool = False
    strike: Optional[float] = None
    expiry: Optional[datetime] = None
    option_type: Optional[str] = None  # "call" or "put"
    
    # Greeks (for options)
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    
    @property
    def market_value(self) -> float:
        """Calculate current market value"""
        return abs(self.quantity * self.current_price)
    
    @property
    def pnl(self) -> float:
        """Calculate profit/loss"""
        if self.position_type == "long":
            return self.quantity * (self.current_price - self.entry_price)
        else:  # short
            return self.quantity * (self.entry_price - self.current_price)
    
    @property
    def pnl_percentage(self) -> float:
        """Calculate P&L percentage"""
        return self.pnl / (self.quantity * self.entry_price)


class Portfolio(BaseModel):
    """Portfolio state and metrics"""
    user_id: str
    agent_id: Optional[str] = None
    positions: List[Position] = []
    cash_balance: float
    total_equity: float
    
    # Performance metrics
    daily_pnl: float = 0
    total_pnl: float = 0
    max_drawdown: float = 0
    high_water_mark: float = 0
    
    # Risk metrics
    total_exposure: float = 0
    leverage_ratio: float = 0
    concentration_ratio: float = 0
    
    # Greeks aggregation (for options portfolios)
    total_delta: float = 0
    total_gamma: float = 0
    total_theta: float = 0
    total_vega: float = 0
    
    def calculate_metrics(self):
        """Recalculate portfolio metrics"""
        # Calculate total exposure
        self.total_exposure = sum(pos.market_value for pos in self.positions)
        
        # Calculate leverage
        self.leverage_ratio = self.total_exposure / self.total_equity if self.total_equity > 0 else 0
        
        # Calculate concentration (largest position / total)
        if self.positions and self.total_exposure > 0:
            largest_position = max(pos.market_value for pos in self.positions)
            self.concentration_ratio = largest_position / self.total_exposure
        else:
            self.concentration_ratio = 0
        
        # Aggregate Greeks for options
        self.total_delta = sum(pos.delta or 0 for pos in self.positions if pos.is_option)
        self.total_gamma = sum(pos.gamma or 0 for pos in self.positions if pos.is_option)
        self.total_theta = sum(pos.theta or 0 for pos in self.positions if pos.is_option)
        self.total_vega = sum(pos.vega or 0 for pos in self.positions if pos.is_option)
        
        # Update drawdown
        if self.total_equity > self.high_water_mark:
            self.high_water_mark = self.total_equity
        
        if self.high_water_mark > 0:
            current_drawdown = (self.high_water_mark - self.total_equity) / self.high_water_mark
            self.max_drawdown = max(self.max_drawdown, current_drawdown)


class RiskCheck(BaseModel):
    """Risk check request"""
    portfolio: Portfolio
    proposed_trade: Optional[Dict[str, Any]] = None
    risk_limits: RiskLimits = RiskLimits()


class RiskViolation(BaseModel):
    """Risk limit violation details"""
    violation_type: ViolationType
    severity: RiskLevel
    message: str
    current_value: float
    limit_value: float
    recommended_action: str
    
    @property
    def is_blocking(self) -> bool:
        """Check if violation should block trading"""
        return self.severity in [RiskLevel.HIGH, RiskLevel.CRITICAL]


class RiskCheckResult(BaseModel):
    """Result of risk check"""
    passed: bool
    violations: List[RiskViolation] = []
    warnings: List[str] = []
    risk_score: float = Field(ge=0, le=100, description="Overall risk score 0-100")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Metrics snapshot
    portfolio_metrics: Dict[str, float] = {}
    
    def add_violation(self, violation: RiskViolation):
        """Add a risk violation"""
        self.violations.append(violation)
        if violation.is_blocking:
            self.passed = False
    
    @property
    def has_blocking_violations(self) -> bool:
        """Check if any violations are blocking"""
        return any(v.is_blocking for v in self.violations)


class RiskAlert(BaseModel):
    """Real-time risk alert"""
    alert_id: str
    user_id: str
    agent_id: Optional[str] = None
    severity: RiskLevel
    alert_type: ViolationType
    message: str
    details: Dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.now)
    acknowledged: bool = False
    
    
class CircuitBreakerConfig(BaseModel):
    """Configuration for service circuit breakers"""
    name: str
    failure_threshold: int = 5
    recovery_timeout: int = 60
    half_open_requests: int = 2
    error_types: List[str] = ["TimeoutError", "ConnectionError"]
    
    
class RiskEngineConfig(BaseModel):
    """Risk engine configuration"""
    # Circuit breaker configs for different services
    circuit_breakers: Dict[str, CircuitBreakerConfig] = {
        "market_data": CircuitBreakerConfig(
            name="market_data",
            failure_threshold=5,
            recovery_timeout=30,
            error_types=["TimeoutError", "ConnectionError", "DataUnavailable"]
        ),
        "trade_execution": CircuitBreakerConfig(
            name="trade_execution",
            failure_threshold=2,
            recovery_timeout=60,
            error_types=["TradeExecutionError", "BrokerUnavailable"]
        ),
        "risk_check": CircuitBreakerConfig(
            name="risk_check",
            failure_threshold=3,
            recovery_timeout=10,
            error_types=["ValidationError", "CalculationError"]
        )
    }
    
    # Risk calculation parameters
    risk_check_interval: int = Field(default=5, description="Seconds between risk checks")
    alert_cooldown: int = Field(default=300, description="Seconds before repeating same alert")
    
    # Emergency controls
    global_kill_switch: bool = Field(default=False, description="Emergency stop all trading")
    max_daily_trades: int = Field(default=100, description="Max trades per day per user")
    
    
class MarketConditions(BaseModel):
    """Current market conditions for risk adjustment"""
    vix_level: float = Field(description="Current VIX level")
    market_regime: str = Field(description="bull, bear, or sideways")
    intraday_volatility: float = Field(description="Current intraday volatility")
    volume_ratio: float = Field(description="Current vs average volume")
    
    @property
    def risk_multiplier(self) -> float:
        """Calculate risk adjustment multiplier based on conditions"""
        # Higher VIX = more conservative
        vix_factor = min(self.vix_level / 20, 2.0)  # Cap at 2x
        
        # Bear market = more conservative
        regime_factor = {
            "bull": 1.0,
            "sideways": 1.2,
            "bear": 1.5
        }.get(self.market_regime, 1.0)
        
        return vix_factor * regime_factor