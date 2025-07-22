"""
Market Awareness Schemas
Data models for market intelligence and pattern recognition.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum
from pydantic import BaseModel, Field, validator
import numpy as np


class MarketRegime(str, Enum):
    """Market regime classifications."""
    BULL_TRENDING = "bull_trending"
    BEAR_TRENDING = "bear_trending"
    RANGE_BOUND = "range_bound"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    CRASH_CONDITIONS = "crash_conditions"
    EUPHORIA = "euphoria"
    ACCUMULATION = "accumulation"
    DISTRIBUTION = "distribution"
    UNKNOWN = "unknown"


class VolatilityRegime(str, Enum):
    """Volatility regime classifications."""
    EXTREMELY_LOW = "extremely_low"      # VIX < 12
    LOW = "low"                          # VIX 12-16
    NORMAL = "normal"                    # VIX 16-20
    ELEVATED = "elevated"                # VIX 20-25
    HIGH = "high"                        # VIX 25-30
    VERY_HIGH = "very_high"              # VIX 30-40
    EXTREME = "extreme"                  # VIX > 40


class TrendStrength(str, Enum):
    """Trend strength classifications."""
    STRONG_UP = "strong_up"
    MODERATE_UP = "moderate_up"
    WEAK_UP = "weak_up"
    NEUTRAL = "neutral"
    WEAK_DOWN = "weak_down"
    MODERATE_DOWN = "moderate_down"
    STRONG_DOWN = "strong_down"


class PatternType(str, Enum):
    """Technical pattern types."""
    # Reversal Patterns
    HEAD_AND_SHOULDERS = "head_and_shoulders"
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    TRIPLE_TOP = "triple_top"
    TRIPLE_BOTTOM = "triple_bottom"
    
    # Continuation Patterns
    FLAG = "flag"
    PENNANT = "pennant"
    WEDGE = "wedge"
    TRIANGLE = "triangle"
    
    # Support/Resistance
    SUPPORT_BOUNCE = "support_bounce"
    RESISTANCE_REJECTION = "resistance_rejection"
    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"
    
    # Volume Patterns
    VOLUME_SPIKE = "volume_spike"
    VOLUME_DRY_UP = "volume_dry_up"
    ACCUMULATION = "accumulation"
    DISTRIBUTION = "distribution"


class EventType(str, Enum):
    """Market event types."""
    ECONOMIC_DATA = "economic_data"
    EARNINGS = "earnings"
    FED_ANNOUNCEMENT = "fed_announcement"
    GEOPOLITICAL = "geopolitical"
    OPTIONS_EXPIRY = "options_expiry"
    MARKET_OPEN = "market_open"
    MARKET_CLOSE = "market_close"
    CIRCUIT_BREAKER = "circuit_breaker"


class MarketDataPoint(BaseModel):
    """Single market data observation."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    symbol: str = Field(..., description="Market symbol")
    
    # Price data
    price: float = Field(..., description="Current price")
    open: Optional[float] = Field(None, description="Open price")
    high: Optional[float] = Field(None, description="High price")
    low: Optional[float] = Field(None, description="Low price")
    close: Optional[float] = Field(None, description="Close price")
    
    # Volume data
    volume: Optional[int] = Field(None, description="Trading volume")
    avg_volume: Optional[float] = Field(None, description="Average volume")
    
    # Market internals
    bid: Optional[float] = Field(None, description="Best bid")
    ask: Optional[float] = Field(None, description="Best ask")
    bid_size: Optional[int] = Field(None, description="Bid size")
    ask_size: Optional[int] = Field(None, description="Ask size")
    
    # Derived metrics
    spread: Optional[float] = Field(None, description="Bid-ask spread")
    spread_percentage: Optional[float] = Field(None, description="Spread as percentage")
    
    @validator('spread', always=True)
    def calculate_spread(cls, v, values):
        """Calculate spread from bid/ask."""
        if v is None and 'bid' in values and 'ask' in values:
            bid = values.get('bid')
            ask = values.get('ask')
            if bid and ask:
                return ask - bid
        return v
        
    @validator('spread_percentage', always=True)
    def calculate_spread_percentage(cls, v, values):
        """Calculate spread percentage."""
        if v is None and 'spread' in values and 'price' in values:
            spread = values.get('spread')
            price = values.get('price')
            if spread and price and price > 0:
                return (spread / price) * 100
        return v


class MarketSnapshot(BaseModel):
    """Complete market snapshot at a point in time."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Primary indicators
    spy: MarketDataPoint = Field(..., description="SPY data")
    vix: MarketDataPoint = Field(..., description="VIX data")
    
    # Secondary indicators
    dxy: Optional[MarketDataPoint] = Field(None, description="Dollar index")
    tnx: Optional[MarketDataPoint] = Field(None, description="10-year yield")
    gld: Optional[MarketDataPoint] = Field(None, description="Gold")
    
    # Market internals
    advances: Optional[int] = Field(None, description="Advancing stocks")
    declines: Optional[int] = Field(None, description="Declining stocks")
    unchanged: Optional[int] = Field(None, description="Unchanged stocks")
    
    # Breadth indicators
    advance_decline_ratio: Optional[float] = Field(None)
    new_highs: Optional[int] = Field(None)
    new_lows: Optional[int] = Field(None)
    
    # Volume metrics
    up_volume: Optional[int] = Field(None)
    down_volume: Optional[int] = Field(None)
    volume_ratio: Optional[float] = Field(None)
    
    # Options metrics
    put_call_ratio: Optional[float] = Field(None)
    options_volume: Optional[int] = Field(None)
    
    @validator('advance_decline_ratio', always=True)
    def calculate_ad_ratio(cls, v, values):
        """Calculate advance/decline ratio."""
        if v is None:
            advances = values.get('advances')
            declines = values.get('declines')
            if advances and declines and declines > 0:
                return advances / declines
        return v


class TechnicalIndicators(BaseModel):
    """Technical analysis indicators."""
    symbol: str = Field(..., description="Symbol analyzed")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Moving averages
    sma_20: Optional[float] = Field(None, description="20-period SMA")
    sma_50: Optional[float] = Field(None, description="50-period SMA")
    sma_200: Optional[float] = Field(None, description="200-period SMA")
    ema_9: Optional[float] = Field(None, description="9-period EMA")
    ema_21: Optional[float] = Field(None, description="21-period EMA")
    
    # Momentum indicators
    rsi: Optional[float] = Field(None, description="Relative Strength Index")
    macd: Optional[float] = Field(None, description="MACD value")
    macd_signal: Optional[float] = Field(None, description="MACD signal line")
    macd_histogram: Optional[float] = Field(None, description="MACD histogram")
    stochastic_k: Optional[float] = Field(None, description="Stochastic %K")
    stochastic_d: Optional[float] = Field(None, description="Stochastic %D")
    
    # Volatility indicators
    atr: Optional[float] = Field(None, description="Average True Range")
    bollinger_upper: Optional[float] = Field(None, description="Upper Bollinger Band")
    bollinger_middle: Optional[float] = Field(None, description="Middle Bollinger Band")
    bollinger_lower: Optional[float] = Field(None, description="Lower Bollinger Band")
    
    # Volume indicators
    obv: Optional[float] = Field(None, description="On Balance Volume")
    volume_sma: Optional[float] = Field(None, description="Volume SMA")
    
    # Support/Resistance
    pivot_point: Optional[float] = Field(None)
    resistance_1: Optional[float] = Field(None)
    resistance_2: Optional[float] = Field(None)
    support_1: Optional[float] = Field(None)
    support_2: Optional[float] = Field(None)


class MarketPattern(BaseModel):
    """Detected market pattern."""
    pattern_id: str = Field(..., description="Unique pattern ID")
    pattern_type: PatternType = Field(..., description="Type of pattern")
    symbol: str = Field(..., description="Symbol where pattern detected")
    
    # Pattern details
    start_time: datetime = Field(..., description="Pattern start time")
    end_time: Optional[datetime] = Field(None, description="Pattern end time")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    
    # Pattern specifics
    key_levels: List[float] = Field(default_factory=list, description="Important price levels")
    volume_profile: Optional[str] = Field(None, description="Volume characteristics")
    
    # Trading implications
    bullish_bias: bool = Field(..., description="Bullish or bearish pattern")
    target_price: Optional[float] = Field(None, description="Pattern target")
    stop_loss: Optional[float] = Field(None, description="Suggested stop loss")
    
    # Validation
    confirmed: bool = Field(default=False, description="Pattern confirmed")
    invalidation_level: Optional[float] = Field(None, description="Level that invalidates pattern")
    
    # Metadata
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    detection_method: str = Field(..., description="Method used for detection")


class MarketEvent(BaseModel):
    """Market event that may impact trading."""
    event_id: str = Field(..., description="Unique event ID")
    event_type: EventType = Field(..., description="Type of event")
    
    # Event details
    scheduled_time: datetime = Field(..., description="When event occurs")
    actual_time: Optional[datetime] = Field(None, description="Actual occurrence time")
    
    # Event specifics
    title: str = Field(..., description="Event title")
    description: str = Field(..., description="Event description")
    importance: str = Field(..., description="High/Medium/Low")
    
    # Market impact
    expected_volatility: Optional[str] = Field(None, description="Expected vol impact")
    affected_instruments: List[str] = Field(default_factory=list)
    
    # Historical context
    previous_occurrences: List[Dict[str, Any]] = Field(default_factory=list)
    average_move: Optional[float] = Field(None, description="Average market move %")
    
    # Post-event analysis
    actual_impact: Optional[Dict[str, Any]] = Field(None)
    market_reaction: Optional[str] = Field(None)


class RegimeAnalysis(BaseModel):
    """Market regime analysis results."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Current regimes
    market_regime: MarketRegime = Field(..., description="Overall market regime")
    volatility_regime: VolatilityRegime = Field(..., description="Volatility regime")
    trend_strength: TrendStrength = Field(..., description="Trend strength")
    
    # Confidence scores
    regime_confidence: float = Field(..., ge=0.0, le=1.0)
    volatility_confidence: float = Field(..., ge=0.0, le=1.0)
    trend_confidence: float = Field(..., ge=0.0, le=1.0)
    
    # Supporting evidence
    supporting_indicators: Dict[str, Any] = Field(default_factory=dict)
    conflicting_indicators: Dict[str, Any] = Field(default_factory=dict)
    
    # Regime characteristics
    regime_duration: Optional[int] = Field(None, description="Days in current regime")
    regime_stability: float = Field(..., ge=0.0, le=1.0, description="Regime stability score")
    
    # Transition probabilities
    transition_probabilities: Dict[str, float] = Field(
        default_factory=dict,
        description="Probability of transitioning to other regimes"
    )
    
    # Trading implications
    recommended_strategies: List[str] = Field(default_factory=list)
    risk_adjustments: Dict[str, float] = Field(default_factory=dict)
    position_sizing_factor: float = Field(default=1.0)


class MarketForecast(BaseModel):
    """Market forecast and predictions."""
    forecast_id: str = Field(..., description="Unique forecast ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Forecast target
    symbol: str = Field(..., description="Symbol being forecasted")
    forecast_horizon: str = Field(..., description="Time horizon (e.g., '1D', '1W')")
    
    # Price predictions
    expected_price: float = Field(..., description="Expected price")
    upper_bound: float = Field(..., description="Upper price bound")
    lower_bound: float = Field(..., description="Lower price bound")
    confidence_interval: float = Field(default=0.95, description="Confidence level")
    
    # Directional probabilities
    prob_up: float = Field(..., ge=0.0, le=1.0, description="Probability of increase")
    prob_down: float = Field(..., ge=0.0, le=1.0, description="Probability of decrease")
    prob_flat: float = Field(..., ge=0.0, le=1.0, description="Probability of flat")
    
    # Volatility forecast
    expected_volatility: float = Field(..., description="Expected volatility")
    volatility_percentile: float = Field(..., description="Vol percentile vs history")
    
    # Model details
    model_name: str = Field(..., description="Forecasting model used")
    model_confidence: float = Field(..., ge=0.0, le=1.0)
    feature_importance: Dict[str, float] = Field(default_factory=dict)
    
    # Validation
    backtest_accuracy: Optional[float] = Field(None, description="Historical accuracy")
    last_error: Optional[float] = Field(None, description="Last forecast error")
    
    @validator('prob_up')
    def validate_probabilities(cls, v, values):
        """Ensure probabilities sum to 1."""
        # This is a simplified check - in practice would check all three
        return v


class MarketAnomalyAlert(BaseModel):
    """Alert for detected market anomalies."""
    alert_id: str = Field(..., description="Unique alert ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Anomaly details
    anomaly_type: str = Field(..., description="Type of anomaly detected")
    severity: str = Field(..., description="Critical/High/Medium/Low")
    
    # Detection details
    affected_symbols: List[str] = Field(default_factory=list)
    anomaly_score: float = Field(..., description="Anomaly score (higher = more unusual)")
    
    # Description
    description: str = Field(..., description="Human-readable description")
    technical_details: Dict[str, Any] = Field(default_factory=dict)
    
    # Context
    normal_range: Dict[str, Tuple[float, float]] = Field(
        default_factory=dict,
        description="Normal ranges for affected metrics"
    )
    observed_values: Dict[str, float] = Field(default_factory=dict)
    
    # Actions
    recommended_actions: List[str] = Field(default_factory=list)
    auto_triggered_actions: List[str] = Field(default_factory=list)
    
    # Resolution
    resolved: bool = Field(default=False)
    resolved_at: Optional[datetime] = Field(None)
    resolution_notes: Optional[str] = Field(None)


class MarketIntelligenceReport(BaseModel):
    """Comprehensive market intelligence report."""
    report_id: str = Field(..., description="Unique report ID")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    report_type: str = Field(..., description="Daily/Weekly/Event-driven")
    
    # Market state
    market_snapshot: MarketSnapshot = Field(..., description="Current market state")
    regime_analysis: RegimeAnalysis = Field(..., description="Regime analysis")
    technical_indicators: Dict[str, TechnicalIndicators] = Field(default_factory=dict)
    
    # Detected patterns
    active_patterns: List[MarketPattern] = Field(default_factory=list)
    pattern_success_rate: float = Field(default=0.0, description="Recent pattern accuracy")
    
    # Events and alerts
    upcoming_events: List[MarketEvent] = Field(default_factory=list)
    active_alerts: List[MarketAnomalyAlert] = Field(default_factory=list)
    
    # Forecasts
    short_term_forecast: Optional[MarketForecast] = Field(None)
    medium_term_forecast: Optional[MarketForecast] = Field(None)
    
    # Trading recommendations
    overall_bias: str = Field(..., description="Bullish/Bearish/Neutral")
    confidence_level: float = Field(..., ge=0.0, le=1.0)
    key_levels: Dict[str, List[float]] = Field(
        default_factory=dict,
        description="Key support/resistance levels"
    )
    
    # Risk assessment
    market_risk_score: float = Field(..., ge=0.0, le=10.0)
    volatility_forecast: str = Field(..., description="Expected volatility")
    risk_factors: List[str] = Field(default_factory=list)
    
    # Executive summary
    executive_summary: str = Field(..., description="Key takeaways")
    detailed_analysis: Optional[str] = Field(None, description="Detailed analysis")