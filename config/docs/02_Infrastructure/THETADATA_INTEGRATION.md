# ThetaData Terminal Integration Guide

## Overview

ThetaData Terminal is a professional-grade market data provider that delivers real-time and historical options data. This system uses ThetaData for all market data needs while IB Gateway handles trade execution.

**Cost**: ~$600/month for full options data access

## Architecture

```
┌─────────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  ThetaData Terminal │────▶│  Local REST API  │────▶│ Trading Systems │
│  (Java Application) │     │ (localhost:25510)│     │ (Python Clients)│
└─────────────────────┘     └──────────────────┘     └─────────────────┘
         │                                                      │
         │                                                      ▼
         ▼                                            ┌─────────────────┐
┌─────────────────────┐                              │   IB Gateway    │
│  ThetaData Cloud   │                               │ (Trade Execution)│
│  (Market Data)     │                               └─────────────────┘
└─────────────────────┘
```

## Key Components

### 1. ThetaData Terminal
- **Location**: Running on VNC desktop (port 5901)
- **API Port**: 25510 (HTTP REST API)
- **WebSocket Port**: 25520 (streaming data)
- **Process**: `ThetaTerminal.jar`

### 2. Data Types Available
- **Real-time quotes**: SPY stock and all options chains
- **Greeks**: Delta, Gamma, Theta, Vega, Rho
- **Options chains**: All strikes and expirations
- **Historical data**: Tick, minute, daily bars
- **Market statistics**: Volume, open interest, IV

### 3. API Endpoints

#### Stock Quotes
```
GET http://localhost:25510/v2/bulk_snapshot/stock/quote?root=SPY
```

#### Options Chain
```
GET http://localhost:25510/v2/bulk_snapshot/option/ohlc?root=SPY&exp=0
```
Note: `exp=0` returns today's expiring options (0DTE)

#### Greeks
```
GET http://localhost:25510/v2/bulk_snapshot/option/quote?root=SPY&exp=0&use_greek=true
```

## Integration Pattern

### Data Flow Architecture
```
Market Data Flow:
ThetaData Terminal → Real-time prices → Trading Systems → Decision Making
                  ↓                                    ↓
           Historical Data                      IB Gateway API
                                               (Execute Trades)

Position Data Flow:
IB Gateway → Position queries (scheduled) → Risk Assessment
         ↓
    Trade Execution
```

### Best Practices

1. **Use ThetaData for ALL market data**:
   - Real-time SPY prices
   - Options chains and quotes
   - Greeks calculations
   - Historical data analysis

2. **Use IB Gateway ONLY for**:
   - Position queries (scheduled, not streaming)
   - Trade execution
   - Account information
   - Order management

3. **Scheduled Position Checks**:
   - Every 30 minutes: General position sync
   - Every 15 minutes: When positions exist
   - Every 5 minutes: Last 30 minutes before close
   - Every 1 minute: Last 5 minutes before close

## Python Integration

### LocalThetaConnector
Located at: `/home/info/fntx-ai-v1/rl-trading/spy_options/data_pipeline/local_theta_connector.py`

```python
from data_pipeline.local_theta_connector import LocalThetaConnector

# Initialize connector
theta = LocalThetaConnector()
await theta.start()

# Get market data
market_data = theta.market_data
spy_price = market_data['spy_price']
options_chain = market_data['options_chain']
```

### Key Features
- Automatic reconnection on failure
- 1-second update intervals for real-time data
- Caching to reduce API calls
- Asynchronous operation for performance

## Common Use Cases

### 1. Get Current SPY Price
```python
async def get_spy_price():
    theta = LocalThetaConnector()
    await theta.start()
    return theta.market_data['spy_price']
```

### 2. Monitor Options Greeks
```python
async def get_option_greeks(strike, right):
    theta = LocalThetaConnector()
    await theta.start()
    
    for option in theta.market_data['options_chain']:
        if option['strike'] == strike and option['right'] == right:
            return {
                'delta': option['delta'],
                'gamma': option['gamma'],
                'theta': option['theta'],
                'vega': option['vega']
            }
```

### 3. Calculate Moneyness
```python
def calculate_moneyness(spy_price, strike, right):
    if right == 'C':  # Call
        return (spy_price - strike) / strike
    else:  # Put
        return (strike - spy_price) / strike
```

## Performance Optimization

### 1. Connection Management
- Keep single connection alive for entire session
- Use connection pooling for multiple clients
- Implement exponential backoff for reconnects

### 2. Data Caching
- Cache static data (strikes, expirations)
- Update dynamic data (prices, greeks) every second
- Use local calculations when possible

### 3. Rate Limiting
- ThetaData allows unlimited requests on localhost
- Still implement reasonable delays to prevent overload
- Batch requests when fetching multiple contracts

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Check ThetaTerminal is running: `ps aux | grep ThetaTerminal`
   - Verify port 25510 is listening: `ss -tlnp | grep 25510`
   - Restart ThetaTerminal if needed

2. **No Data Returned**
   - Check market hours (9:30 AM - 4:00 PM ET)
   - Verify subscription is active
   - Check ThetaTerminal logs

3. **Slow Response**
   - Reduce update frequency
   - Check system resources
   - Restart ThetaTerminal

### Log Locations
```
~/ThetaTerminal/logs/        # Main application logs
~/theta_terminal.log         # Startup logs
/var/log/cleanup-manager/    # Cleanup manager logs
```

## Cost Justification

At $600/month, ThetaData provides:
- Professional-grade data quality
- Real-time options chains with Greeks
- Historical data for backtesting
- 99.9% uptime SLA
- No data caps or throttling

This eliminates the need for:
- IBKR market data subscriptions
- Complex data management
- Missing data during critical moments
- Inaccurate Greeks calculations

## Security Considerations

1. **Local Access Only**
   - API binds to localhost only
   - No external network access required
   - Firewall ports 25510/25520 if needed

2. **Authentication**
   - No auth required for localhost
   - API key stored in ThetaTerminal config
   - Credentials never exposed in code

3. **Data Privacy**
   - All data stays on local machine
   - No cloud storage of trading data
   - Encrypted connection to ThetaData servers

## Future Enhancements

1. **WebSocket Streaming**
   - Implement WebSocket connector for sub-second updates
   - Reduce latency for high-frequency strategies

2. **Data Recording**
   - Record all market data for replay
   - Build local historical database

3. **Redundancy**
   - Fallback to IB Gateway data if ThetaData fails
   - Multiple ThetaTerminal instances for failover

## Conclusion

ThetaData Terminal provides professional market data infrastructure that's essential for reliable options trading. By separating market data (ThetaData) from execution (IB Gateway), the system achieves:

- Better performance through specialized services
- Higher reliability with redundant data sources  
- Cost efficiency by using the right tool for each job
- Scalability for future trading strategies