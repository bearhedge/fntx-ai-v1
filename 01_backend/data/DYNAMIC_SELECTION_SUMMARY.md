# Dynamic Volatility-Based Strike Selection

## Overview
Replaces static strike selection with a dynamic system that automatically adjusts based on implied volatility (IV), ensuring appropriate data collection across different market conditions.

## Key Features

### 1. **Volatility-Based Scaling**
```python
# Core formula
daily_1sd_move = spot_price * iv * sqrt(hours/8760)
strikes_per_sd = daily_1sd_move / strike_increment
target_strikes = int(strikes_per_sd * 2.5)  # 2.5 standard deviations
```

### 2. **Automatic Adjustment**
- **Calm markets (IV < 15%)**: 5 strikes per side
- **Normal markets (IV 15-25%)**: 7-12 strikes per side
- **Elevated volatility (IV 25-35%)**: 12-17 strikes per side
- **High volatility (IV 35-50%)**: 17-25 strikes per side
- **Extreme volatility (IV > 50%)**: 25-30 strikes per side (capped)

### 3. **Volume Filtering**
- Downloads all strikes in the calculated range
- Filters contracts with < 60 bars (5 hours of data)
- Ensures only liquid contracts are kept

## Implementation Details

### DynamicStrikeSelector Class
```python
class DynamicStrikeSelector:
    def __init__(self):
        self.stdev_multiplier = 2.5      # Captures 98.76% of moves
        self.min_contracts_per_side = 5   # Floor
        self.max_contracts_per_side = 30  # Ceiling
        self.min_volume_bars = 60        # Liquidity threshold
```

### Configuration (strike_config.py)
All parameters are externalized for easy tuning:
- Standard deviation multiplier
- Min/max contracts per side
- Volume bar thresholds
- Fallback parameters

### Integration Flow
```
1. Get non-adjusted SPY price (Yahoo Finance)
2. Calculate ATM strike
3. Fetch ATM implied volatility
4. Calculate strikes needed based on IV
5. Download data for selected strikes
6. Apply volume filter (60+ bars)
7. Save filtered contracts to database
```

## Benefits

### 1. **Market Adaptive**
- Automatically expands range on volatile days
- Contracts range on calm days
- No manual adjustment needed

### 2. **Data Efficiency**
- Downloads only relevant strikes
- Reduces API calls on calm days
- Captures all important data on volatile days

### 3. **Quality Control**
- Volume filtering ensures liquid contracts
- Minimum contract guarantee (5 per side)
- Maximum cap prevents excessive downloads

### 4. **Robust Design**
- Fallback to fixed range if IV unavailable
- Configuration-driven parameters
- Clear logging and monitoring

## Examples

### Calm Day (Jan 15, 2024)
- SPY: $450, IV: 12%
- Expected move: ±$1.47
- Strikes selected: 5 per side
- Range: $445-$455

### Normal Day (Jan 3, 2023)
- SPY: $384, IV: 31%
- Expected move: ±$3.22
- Strikes selected: 8 per side
- Range: $376-$392

### Volatile Day (March 2020)
- SPY: $300, IV: 65%
- Expected move: ±$5.31
- Strikes selected: 20 per side
- Range: $280-$320

## Usage

### Basic Command
```bash
# Uses dynamic selection by default
python3 download_day_strikes_dynamic.py --date 2023-01-03
```

### With Options
```bash
# Use smart selection instead
python3 download_day_strikes_dynamic.py --date 2023-01-03 --use-smart

# Custom checkpoint
python3 download_day_strikes_dynamic.py --date 2023-01-03 --checkpoint my_checkpoint.json
```

## Testing

### Test Volatility Scenarios
```bash
python3 dynamic_strike_selector.py
```

This shows how the system scales across different volatility levels.

## Monitoring

The system logs:
- ATM strike and IV
- Calculated strike range
- Number of contracts downloaded vs filtered
- Coverage statistics

## Future Enhancements

1. **Historical IV Percentile**: Use percentile ranking for more context
2. **Intraday Adjustment**: Recalculate if volatility spikes mid-day
3. **Product-Specific Tuning**: Different parameters for SPX, QQQ, etc.
4. **Machine Learning**: Learn optimal parameters from historical data

## Success Metrics

✅ **Adaptive Range**: Adjusts from 5 to 30 strikes based on volatility
✅ **Quality Data**: 60-bar filter ensures liquid contracts
✅ **Efficient Downloads**: Reduces unnecessary API calls
✅ **Robust Fallbacks**: Handles missing IV gracefully
✅ **Configurable**: All parameters externalized for tuning