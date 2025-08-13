# Theta Terminal Integration Documentation

## Overview
This document details the integration with Theta Terminal REST API for fetching real-time options data including quotes, Greeks, volume, and open interest.

## API Endpoints and Data Formats

### 1. Greeks Endpoint
**URL**: `http://localhost:25510/v2/bulk_snapshot/option/greeks?root=SPY&exp={YYYYMMDD}`

**Response Format**:
```json
{
  "header": {
    "format": ["ms_of_day", "bid", "ask", "delta", "theta", "vega", "rho", "epsilon", "lambda", "implied_vol", "iv_error", "ms_of_day2", "underlying_price", "date"]
  },
  "response": [
    {
      "contract": {
        "root": "SPY",
        "expiration": 20250731,
        "strike": 633000,  // Strike in cents (divide by 1000 for dollars)
        "right": "C"       // C for Call, P for Put
      },
      "ticks": [
        [51277881, 1.43, 1.44, 0.4915, -4.9506, 5.1173, 0.0, 0.0, 0.0, 0.288, 0.0, 51278919, 632.70, 20250731]
      ]
    }
  ]
}
```

**Field Mapping**:
- `ticks[0][0]`: ms_of_day (milliseconds since midnight)
- `ticks[0][1]`: bid price
- `ticks[0][2]`: ask price
- `ticks[0][3]`: **delta** (already in decimal format, e.g., 0.4915 for calls, -0.5083 for puts)
- `ticks[0][4]`: theta
- `ticks[0][5]`: vega
- `ticks[0][9]`: **implied_vol** (already in decimal format, e.g., 0.288 = 28.8%)

### 2. Quotes Endpoint
**URL**: `http://localhost:25510/v2/bulk_snapshot/option/quote?root=SPY&exp={YYYYMMDD}`

**Response Format**:
```json
{
  "header": {
    "format": ["ms_of_day", "bid_size", "bid_exchange", "bid", "bid_condition", "ask_size", "ask_exchange", "ask", "ask_condition", "date"]
  },
  "response": [
    {
      "contract": { /* same as above */ },
      "ticks": [
        [51018575, 10, "X", 1.43, "N", 15, "X", 1.44, "N", 20250731]
      ]
    }
  ]
}
```

**Field Mapping**:
- `ticks[0][3]`: bid price
- `ticks[0][7]`: ask price
- `ticks[0][1]`: bid size
- `ticks[0][5]`: ask size

### 3. OHLC Endpoint (Volume Data)
**URL**: `http://localhost:25510/v2/bulk_snapshot/option/ohlc?root=SPY&exp={YYYYMMDD}`

**Response Format**:
```json
{
  "header": {
    "format": ["ms_of_day", "open", "high", "low", "close", "volume", "count", "date"]
  },
  "response": [
    {
      "contract": { /* same as above */ },
      "ticks": [
        [51983012, 0.07, 0.35, 0.03, 0.12, 21785, 1982, 20250731]
      ]
    }
  ]
}
```

**Field Mapping**:
- `ticks[0][5]`: **volume** (daily volume traded)

### 4. Open Interest Endpoint
**URL**: `http://localhost:25510/v2/bulk_snapshot/option/open_interest?root=SPY&exp={YYYYMMDD}`

**Response Format**:
```json
{
  "header": {
    "format": ["ms_of_day", "open_interest", "date"]
  },
  "response": [
    {
      "contract": { /* same as above */ },
      "ticks": [
        [0, 14532, 20250731]
      ]
    }
  ]
}
```

**Field Mapping**:
- `ticks[0][1]`: **open_interest**

## Data Processing in rest_theta_connector.py

### Key Implementation Details

1. **Greeks Processing** (Lines 227-242):
```python
# Correct field mapping from Greeks API
delta = tick_data[3] if len(tick_data) > 3 else 0.0
gamma = tick_data[4] if len(tick_data) > 4 else 0.0  
theta = tick_data[5] if len(tick_data) > 5 else 0.0
iv = tick_data[9] if len(tick_data) > 9 else 0.25

# Greeks are already in correct decimal format from Theta Terminal
# No conversion needed - use values as-is
```

2. **Common Mistakes to Avoid**:
- ❌ Don't divide delta by 100 - it's already in decimal format
- ❌ Don't use aggressive min/max clamping that destroys delta variation
- ❌ Don't use field[1] for delta - that's the bid price!
- ✅ Use field[3] for delta, field[9] for IV
- ✅ Greeks values are already properly scaled from Theta Terminal

3. **Volume Data Issue** (To Be Fixed):
- OHLC endpoint returns volume correctly
- Need to ensure option_key matching between different endpoints
- Currently showing 0 due to potential mismatch in contract identification

## Data Validation

### Expected Ranges
1. **Delta**:
   - Calls: 0.0 to 1.0 (increases as strike decreases/goes ITM)
   - Puts: -1.0 to 0.0 (decreases as strike increases/goes ITM)
   - ATM: ~0.5 for calls, ~-0.5 for puts

2. **Implied Volatility**:
   - Normal range: 0.10 to 1.0 (10% to 100%)
   - 0DTE typical: 0.20 to 0.50 (20% to 50%)
   - Should always be positive

3. **Volume**:
   - 0 or positive integer
   - Can be 0 for illiquid strikes
   - Popular strikes may have thousands

4. **Open Interest**:
   - 0 or positive integer
   - Usually higher than volume
   - Accumulates over time

### Validation Script
```python
# Quick validation test
async def validate_theta_data():
    # 1. Check Greeks format
    greeks_response = await fetch_greeks()
    assert greeks_response['header']['format'][3] == 'delta'
    assert greeks_response['header']['format'][9] == 'implied_vol'
    
    # 2. Validate delta ranges
    for contract in greeks_response['response']:
        delta = contract['ticks'][0][3]
        right = contract['contract']['right']
        if right == 'C':
            assert 0 <= delta <= 1, f"Call delta {delta} out of range"
        else:
            assert -1 <= delta <= 0, f"Put delta {delta} out of range"
    
    # 3. Check volume is being fetched
    ohlc_response = await fetch_ohlc()
    assert ohlc_response['header']['format'][5] == 'volume'
```

## Active Positions Price Updates

### Current Issue
Active positions show hardcoded entry prices (0.50, 0.85, 1.10) instead of current market prices.

### Required Fix
The position manager needs to:
1. Match position strikes/types with current market data
2. Update 'CURRENT' column with live bid/ask midpoint
3. Calculate real-time P&L based on current prices

### Implementation Location
- File: `terminal_ui/mandate_panel.py`
- Need to cross-reference positions with `market_data['options_chain']`
- Update current prices in real-time from the data feed

## Testing & Verification

### Direct API Testing
```bash
# Test Greeks endpoint
curl -s "http://localhost:25510/v2/bulk_snapshot/option/greeks?root=SPY&exp=20250731" | jq '.response[0]'

# Test OHLC (volume) endpoint
curl -s "http://localhost:25510/v2/bulk_snapshot/option/ohlc?root=SPY&exp=20250731" | jq '.response[0]'

# Test Open Interest endpoint
curl -s "http://localhost:25510/v2/bulk_snapshot/option/open_interest?root=SPY&exp=20250731" | jq '.response[0]'
```

### Verification Checklist
- [ ] Greeks show proper variation (not all -0.01 for puts)
- [ ] IV values are positive percentages
- [ ] Volume data displays (not all zeros)
- [ ] Open Interest displays correctly
- [ ] Active positions show live prices
- [ ] P&L updates in real-time

## Troubleshooting

### Common Issues
1. **All puts show -0.01 delta**: Check if using wrong field index or excessive clamping
2. **Volume shows 0**: Verify OHLC endpoint is being called and option keys match
3. **Greeks look like prices**: Using field[1] (bid) instead of field[3] (delta)
4. **Positions don't update**: Position manager not fetching current market prices

### Debug Commands
```python
# Check raw API response
self.logger.debug(f"Greeks response for {option_key}: {tick_data}")

# Verify field mapping
print(f"Delta at position 3: {tick_data[3]}")
print(f"IV at position 9: {tick_data[9]}")
```

## Future Improvements
1. Implement WebSocket streaming when available (currently using REST polling)
2. Add data quality monitoring and alerts
3. Cache optimization for reduced API calls
4. Historical data comparison for anomaly detection