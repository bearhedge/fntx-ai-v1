# Market Awareness Engine (Phase 3) - Implementation Guide

## Overview

The Market Awareness Engine provides FNTX.ai with real-time market analysis capabilities, pattern recognition, and regime detection. This system forms the sensory layer of the trading agent, enabling informed decision-making based on current market conditions.

## Architecture

### Components

1. **Market Data Collector** (`market_data_collector.py`)
   - Real-time data collection from IBKR
   - Technical indicator calculation
   - Market snapshot generation
   - Data caching and streaming

2. **Pattern Recognition Engine** (`pattern_recognition.py`)
   - Technical pattern detection
   - Pattern validation and scoring
   - Historical pattern performance tracking
   - Signal generation from patterns

3. **Market Regime Detector** (`regime_detector.py`)
   - Multi-factor regime analysis
   - Regime transition detection
   - Stability assessment
   - Trading implications

4. **Market Awareness Manager** (`market_awareness_manager.py`)
   - Unified interface for all components
   - Trading recommendations
   - Alert management
   - Performance tracking

## Data Flow

```
IBKR API → Market Data Collector → [Pattern Recognition, Regime Detection]
                                           ↓
                              Market Awareness Manager
                                           ↓
                    [Trading Signals, Recommendations, Alerts]
                                           ↓
                              Other Agents (via MCP)
```

## Key Features

### 1. Real-Time Market Analysis

The system continuously monitors market conditions and provides:

- **Market Snapshots**: Current prices, volumes, and internals
- **Technical Indicators**: Moving averages, RSI, ATR, Bollinger Bands
- **Support/Resistance Levels**: Dynamic calculation of key levels
- **Market Breadth**: Advance/decline ratios and volume analysis

### 2. Pattern Recognition

Detects and analyzes various technical patterns:

- **Reversal Patterns**:
  - Double Top/Bottom
  - Head and Shoulders
  - Support Bounce
  - Resistance Rejection

- **Continuation Patterns**:
  - Flags and Pennants
  - Triangles (Symmetrical, Ascending, Descending)
  - Channels

- **Volume Patterns**:
  - Volume spikes
  - Accumulation/Distribution

### 3. Market Regime Detection

Sophisticated regime analysis including:

- **Market Regimes**:
  - Bull Trending
  - Bear Trending
  - Range Bound
  - High Volatility
  - Low Volatility
  - Crash Conditions
  - Euphoria
  - Accumulation
  - Distribution

- **Volatility Regimes**:
  - Extremely Low (VIX < 12)
  - Low (VIX 12-16)
  - Normal (VIX 16-20)
  - Elevated (VIX 20-25)
  - High (VIX 25-30)
  - Very High (VIX 30-40)
  - Extreme (VIX > 40)

### 4. Trading Recommendations

The system generates actionable trading recommendations based on:

- Market regime alignment
- Pattern confirmations
- Technical indicator signals
- Risk assessment
- Liquidity conditions

## Usage Examples

### Basic Usage

```python
from backend.mcp.context_manager import MCPContextManager
from backend.market_awareness import MarketAwarenessManager

# Initialize
mcp = MCPContextManager()
await mcp.initialize()

market_awareness = MarketAwarenessManager(mcp)
await market_awareness.initialize()

# Get comprehensive analysis
analysis = await market_awareness.get_comprehensive_analysis()

# Access components
print(f"Market Regime: {analysis['regime_analysis']['market_regime']}")
print(f"Trading Recommendation: {analysis['trading_recommendation']['action']}")
print(f"Active Patterns: {len(analysis['active_patterns'])}")
```

### Pattern Detection

```python
# Get trading signals based on patterns
signals = await market_awareness.get_trading_signals()

for signal in signals:
    print(f"Signal: {signal['type']} - Confidence: {signal['confidence']}")
    print(f"Pattern: {signal.get('pattern')}")
    print(f"Entry: {signal.get('entry_trigger')}")
```

### Trade Evaluation

```python
# Evaluate a specific trade setup
evaluation = await market_awareness.evaluate_trade_setup(
    strategy="SPY_PUT_SELL",
    strike=440.0,
    expiration="2024-12-15"
)

print(f"Recommendation: {evaluation['recommendation']}")
print(f"Market Alignment: {evaluation['market_alignment']}")
print(f"Risk Score: {evaluation['risk_score']}")
print(f"Warnings: {evaluation['warnings']}")
```

### Alert Management

```python
# Register custom alerts
alert_id = await market_awareness.register_alert(
    condition="VIX_ABOVE",
    threshold=25.0,
    callback=alert_handler
)

# Check active alerts
alerts = await market_awareness.get_active_alerts()
```

## Integration with MCP

The Market Awareness Engine integrates deeply with the MCP memory system:

### Memory Storage

- **Market Observations**: Snapshots, indicators, raw data
- **Pattern Detections**: Significant patterns and their outcomes
- **Regime Transitions**: Historical regime changes and triggers
- **Performance Data**: Pattern success rates, recommendation outcomes

### Context Sharing

The system shares context with other agents:

```python
# Automatic context sharing on significant events
await mcp.share_context(
    "MarketAwarenessManager",
    ["StrategicPlannerAgent", "TacticalExecutorAgent"],
    {
        'market_update': {
            'trading_recommendation': recommendation,
            'market_regime': regime,
            'warnings': warnings
        }
    }
)
```

## Configuration

### Environment Variables

```bash
# Market Data Collection
MARKET_DATA_INTERVAL=1.0  # Seconds between data collection
MARKET_ANALYSIS_INTERVAL=30  # Seconds between full analysis

# Pattern Recognition
PATTERN_MIN_CONFIDENCE=0.7  # Minimum confidence for pattern detection
PATTERN_LOOKBACK_PERIODS=100  # Historical data for pattern analysis

# Regime Detection
REGIME_CHANGE_THRESHOLD=0.7  # Confidence threshold for regime changes
REGIME_MIN_DURATION=14400  # Minimum regime duration (4 hours)
```

### Market Hours

The system automatically adjusts behavior based on market hours:

- **Regular Hours**: 9:30 AM - 4:00 PM ET
- **Extended Hours**: 
  - Pre-market: 4:00 AM - 9:30 AM ET
  - After-hours: 4:00 PM - 8:00 PM ET

## Performance Tracking

The system tracks its own performance:

```python
# Track recommendation outcomes
await market_awareness.track_recommendation_outcome(
    recommendation_id="rec_20241212_093045",
    outcome="SUCCESS",
    profit_loss=125.50
)

# Get performance metrics
metrics = await market_awareness.get_performance_metrics()
print(f"Success Rate: {metrics['success_rate']:.2%}")
print(f"Pattern Detection Stats: {metrics['pattern_detection_stats']}")
```

## Error Handling

The system includes robust error handling:

- **Degraded Mode**: Continues with reduced functionality if components fail
- **Data Validation**: Validates all incoming market data
- **Fallback Logic**: Uses cached data when real-time data unavailable
- **Alert on Failures**: Notifies other agents of degraded state

## Future Enhancements

### Phase 3.5 Improvements
- Machine learning for pattern recognition
- Sentiment analysis integration
- Options flow analysis
- Intermarket analysis

### Integration Points
- News sentiment feed
- Economic calendar events
- Options unusual activity
- Dark pool data

## Best Practices

1. **Resource Management**
   - Monitor memory usage with large data histories
   - Implement data retention policies
   - Use efficient data structures for streaming

2. **Pattern Validation**
   - Backtest patterns before relying on them
   - Track pattern performance over time
   - Adjust confidence thresholds based on results

3. **Regime Detection**
   - Allow sufficient time for regime confirmation
   - Consider multiple timeframes
   - Validate regime changes with multiple indicators

4. **Alert Configuration**
   - Set reasonable thresholds to avoid alert fatigue
   - Use callbacks for critical alerts only
   - Regularly review and update alert conditions

## Troubleshooting

### Common Issues

1. **No Market Data**
   - Check IBKR connection
   - Verify market hours
   - Check subscription status

2. **Pattern Detection Issues**
   - Ensure sufficient historical data
   - Verify pattern configuration
   - Check confidence thresholds

3. **Regime Instability**
   - Increase minimum regime duration
   - Adjust change threshold
   - Review regime indicators

## API Reference

### MarketAwarenessManager

```python
class MarketAwarenessManager:
    async def get_comprehensive_analysis() -> Dict[str, Any]
    async def get_trading_signals() -> List[Dict[str, Any]]
    async def evaluate_trade_setup(strategy: str, strike: float, expiration: str) -> Dict[str, Any]
    async def register_alert(condition: str, threshold: float, callback: Optional[Callable]) -> str
    async def track_recommendation_outcome(recommendation_id: str, outcome: str, profit_loss: float) -> None
    async def get_performance_metrics() -> Dict[str, Any]
```

### Pattern Types

```python
class PatternType(Enum):
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    HEAD_AND_SHOULDERS = "head_and_shoulders"
    SUPPORT_BOUNCE = "support_bounce"
    RESISTANCE_REJECTION = "resistance_rejection"
    FLAG = "flag"
    TRIANGLE = "triangle"
    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"
    VOLUME_SPIKE = "volume_spike"
```

### Market Regimes

```python
class MarketRegime(Enum):
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
```

## Conclusion

The Market Awareness Engine provides FNTX.ai with sophisticated market analysis capabilities, enabling the system to make informed trading decisions based on real-time market conditions. By combining pattern recognition, regime detection, and comprehensive analysis, the system can adapt to changing market environments and optimize trading strategies accordingly.