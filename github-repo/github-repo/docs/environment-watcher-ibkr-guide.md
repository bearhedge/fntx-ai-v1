# 🔍 Enhanced EnvironmentWatcher Agent - IBKR Live Data Integration

## Overview

The EnvironmentWatcher agent has been completely refactored to use **Interactive Brokers (IBKR) as the exclusive data source** for live market analysis. This eliminates external API dependencies and provides direct access to real-time market data, options chains, and liquidity indicators.

## Key Enhancements

### ✅ **IBKR Live Data Integration**
- **SPY Real-time Data**: Live price, volume, bid/ask, high/low from IBKR
- **VIX Real-time Data**: Live volatility index data directly from CBOE via IBKR
- **Options Chain Analysis**: Real-time SPY options availability and expirations
- **Market Hours Detection**: Accurate trading session identification
- **Connection Management**: Robust IBKR connection handling with cleanup

### ✅ **Enhanced Market Regime Detection**
- **VIX-based Volatility Regime**: Low (<15), Normal (15-25), High (>25)
- **Trend Regime**: Bullish, Bearish, Neutral based on SPY price action
- **Volume Regime**: High, Normal, Low relative to typical SPY volume
- **Liquidity Regime**: Excellent, Good, Fair, Poor based on bid-ask spreads
- **Options Regime**: Active chains availability for 0DTE/1DTE trading
- **Intraday Opportunities**: Assessment of same-day/next-day option availability

### ✅ **Advanced Trading Signals**
- **Overall Regime Classification**:
  - `favorable_for_selling`: Low VIX + Bullish/Neutral + Good liquidity + Active options
  - `unfavorable_high_vol`: High VIX conditions
  - `risk_off`: High volume + Bearish trend
  - `illiquid_conditions`: Poor liquidity or inactive options
  - `neutral`: Standard market conditions

### ✅ **Real-time Monitoring**
- **Continuous Data Updates**: Configurable monitoring intervals
- **Regime Change Detection**: Automatic detection and logging of regime shifts
- **Alert Level Calculation**: Low, Medium, High alerts based on market conditions
- **Memory Persistence**: MCP-compatible JSON memory for historical analysis

## Configuration

### IBKR Connection Settings
```bash
# Environment Variables (.env file)
IBKR_HOST=127.0.0.1
IBKR_PORT=4001          # Live account port (4002 for paper)
IBKR_CLIENT_ID=2        # Unique client ID for EnvironmentWatcher

# Threshold Settings
VIX_LOW_THRESHOLD=15.0
VIX_HIGH_THRESHOLD=25.0
SPY_SUPPORT_THRESHOLD=0.02
VOLUME_SPIKE_THRESHOLD=1.5
```

### Prerequisites
1. **IBKR Account**: Live trading account (analysis only, no trades executed)
2. **TWS/Gateway**: IBKR Trader Workstation or Gateway running
3. **API Permissions**: Enable API access in IBKR account settings
4. **Port Configuration**: Ensure port 4001 is available and configured in TWS

## Key Methods

### Market Data Fetching
```python
def get_market_data(self) -> Dict[str, Any]:
    """Fetch comprehensive market data from IBKR"""
    # Returns: SPY, VIX, options chain data, market hours

def _fetch_spy_data_ibkr(self) -> Dict[str, Any]:
    """Live SPY data with bid/ask, volume, OHLC"""

def _fetch_vix_data_ibkr(self) -> Dict[str, Any]:
    """Live VIX level and daily change"""

def _fetch_spy_options_data(self) -> Dict[str, Any]:
    """SPY options chains for 0DTE/1DTE analysis"""
```

### Market Analysis
```python
def analyze_market_regime(self, market_data: Dict[str, Any]) -> Dict[str, str]:
    """Enhanced regime analysis with options and liquidity"""
    # Returns: Multi-dimensional regime classification

def generate_trading_recommendations(self, regime_indicators: Dict, market_data: Dict) -> Dict:
    """Generate trading signals based on current regime"""
    # Returns: Signal strength, strategy preference, position sizing
```

### Connection Management
```python
def _ensure_ibkr_connection(self) -> bool:
    """Establish and maintain IBKR connection"""

def cleanup(self):
    """Properly disconnect from IBKR"""
```

## Usage Examples

### Basic Market Analysis
```python
from environment_watcher import EnvironmentWatcherAgent

# Initialize agent
agent = EnvironmentWatcherAgent()

# Get live market data
market_data = agent.get_market_data()
print(f"SPY: ${market_data['spy']['price']}")
print(f"VIX: {market_data['vix']['level']}")

# Analyze market regime
regime = agent.analyze_market_regime(market_data)
print(f"Overall Regime: {regime['overall_regime']}")
print(f"VIX Regime: {regime['vix_regime']}")
print(f"Liquidity: {regime['liquidity_regime']}")
```

### Continuous Monitoring
```python
# Start continuous monitoring
agent.run()  # Monitors every 30 seconds by default

# Access regime changes
memory = agent.load_memory()
recent_changes = memory.get('regime_history', [])[-5:]  # Last 5 changes
```

## Data Output Structure

### Market Data
```json
{
  "timestamp": "2024-12-12T09:30:00.000Z",
  "market_hours": true,
  "trading_day": true,
  "spy": {
    "price": 447.85,
    "change": 2.35,
    "volume": 89000000,
    "high": 448.50,
    "low": 445.20,
    "bid": 447.84,
    "ask": 447.86
  },
  "vix": {
    "level": 12.45,
    "change": -0.87,
    "high": 13.20,
    "low": 12.30
  },
  "options": {
    "chains_available": 8,
    "expirations": ["20241212", "20241213"],
    "iv_summary": {},
    "put_call_ratio": 0.0
  }
}
```

### Regime Indicators
```json
{
  "vix_regime": "low_volatility",
  "trend_regime": "bullish",
  "volume_regime": "normal_volume",
  "liquidity_regime": "excellent",
  "options_regime": "active_chains",
  "intraday_opportunities": "available",
  "volatility_regime": "very_low",
  "overall_regime": "favorable_for_selling"
}
```

## Performance Optimizations

### Connection Efficiency
- **Persistent Connections**: Single IBKR connection maintained across monitoring cycles
- **Data Caching**: 2-second data refresh intervals to avoid API rate limits
- **Error Recovery**: Automatic reconnection on connection failures
- **Resource Cleanup**: Proper disconnection on shutdown

### Memory Management
- **Rolling History**: Keep last 50 regime changes to prevent memory bloat
- **Efficient Updates**: Only update shared context when regime changes occur
- **Structured Logging**: Comprehensive logging without excessive disk I/O

## Integration with Trading System

### Shared Context Updates
The EnvironmentWatcher automatically updates the shared context file used by other agents:
```json
{
  "market_regime": "favorable_for_selling",
  "vix_level": 12.45,
  "spy_price": 447.85,
  "trading_recommendations": {...},
  "regime_changes": [...],
  "market_hours": true,
  "environment_alert_level": "low"
}
```

### Signal Generation
Trading recommendations include:
- **Overall Signal**: bullish/bearish/neutral
- **Strategy Preference**: aggressive_selling/conservative/defensive
- **Position Sizing**: increased/normal/reduced
- **Timing Preference**: opportunistic/wait_for_open/very_patient
- **Specific Actions**: Array of actionable insights

## Benefits vs. External APIs

### ✅ **Advantages of IBKR Integration**
- **Single Data Source**: No external API dependencies or costs
- **Real-time Data**: Sub-second latency for market data
- **Options Integration**: Native access to options chains and Greeks
- **Execution Context**: Same data source as trade execution
- **Reliability**: Direct broker connection, no third-party API limits
- **Comprehensive Data**: Bid/ask, volume, all OHLC data included

### ⚠️ **Requirements**
- **IBKR Account**: Must have active account with API permissions
- **TWS/Gateway**: Must be running and configured
- **Network Stability**: Reliable connection to IBKR servers
- **Account Limits**: Respect IBKR data rate limits

## Next Steps

1. **IBKR Setup**: Configure TWS/Gateway with API permissions
2. **Environment Variables**: Set IBKR connection parameters
3. **Testing**: Run agent in paper trading mode first
4. **Live Integration**: Connect to live account for real-time analysis
5. **Strategy Integration**: Use regime signals for strategic planning

The enhanced EnvironmentWatcher provides institutional-grade market analysis using live IBKR data, enabling sophisticated options trading strategies with real-time regime detection and risk assessment.