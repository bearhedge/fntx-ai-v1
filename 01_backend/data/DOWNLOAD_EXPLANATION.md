# 0DTE Download System Explanation

## 1. What's in the Checkpoint File?

The checkpoint file (`checkpoint_20230103.json`) contains:
- **Date**: The trading day being downloaded
- **Status**: "complete" means all data was successfully downloaded
- **Core strikes**: Progress for ±10 strikes from ATM (42 contracts completed)
- **Extended strikes**: Progress for ±11-20 strikes from ATM (38 contracts completed)
- **Stats**:
  - Total contracts: 80 (41 calls + 39 puts)
  - Total OHLC bars: 3,144 (price data points)
  - Total Greeks bars: 6,320 (delta, gamma, theta, vega, rho)
  - Total IV bars: 4,675 (implied volatility)
  - SPY open: $371.60 (used to determine ATM)
  - ATM strike: $372
  - Coverage: 50.4% (normal for 0DTE - many strikes don't trade every 5 minutes)

## 2. Where is the Checkpoint File Located?

Individual day checkpoints are in the current directory:
- `checkpoint_20230103.json` (for Jan 3, 2023)

When running the full system, all checkpoints go to:
- `checkpoints/` directory
- `checkpoints/master_progress.json` (overall progress)
- `checkpoints/monthly_2023_01.json` (monthly progress)
- `checkpoints/checkpoint_20230103.json` (daily progress)

## 3. What is the Monthly Manager?

The monthly manager (`monthly_parallel_manager.py`) coordinates downloading an entire month:
- Downloads multiple days in parallel (3 concurrent by default)
- Tracks progress for all trading days in the month
- Handles rate limiting between downloads
- Creates monthly checkpoint files
- Can resume if interrupted

For January 2023, it would download all 20 trading days.

## 4. What Does the Full Download Encompass?

The full download covers **2.5 years of 0DTE SPY options data**:

### Date Range
- **Start**: January 2023
- **End**: June 2025
- **Total**: ~30 months, ~630 trading days

### Data per Day
- **Strikes**: 
  - Core: ±10 strikes from ATM (21 strikes × 2 option types = 42 contracts)
  - Extended: ±11-20 strikes from ATM (20 strikes × 2 option types = 40 contracts)
  - Total: ~80-120 contracts per day
  
### Data Types (per contract)
- **OHLC**: Open, High, Low, Close prices every 5 minutes
- **Greeks**: Delta, Gamma, Theta, Vega, Rho every 5 minutes
- **IV**: Implied Volatility every 5 minutes
- **Volume**: Number of contracts traded

### Two-Phase Strategy
1. **Phase 1**: Download all core strikes (±10) for every day
   - Higher priority as these are most liquid
   - ~5 minutes per day
   
2. **Phase 2**: Download extended strikes (±11-20)
   - Lower priority, less liquid
   - ~3 minutes per day

### Total Data Volume Estimate
- **Contracts**: ~25,000-50,000 total
- **OHLC bars**: ~15-20 million data points
- **Time**: ~200-250 hours total download time
- **Database size**: ~5-10 GB

### Why This Data is Valuable
- Complete intraday options pricing for backtesting
- Greeks evolution throughout the day
- IV term structure analysis
- 0DTE trading strategy development
- Options market microstructure research

## 5. Quick Command Reference

```bash
# Check what we just downloaded
python3 query_downloaded_data.py --date 2023-01-03

# See monthly status
python3 monthly_parallel_manager.py --year 2023 --month 1 --status

# Start full download (in background)
./start_0dte_download.sh

# Monitor progress
python3 monitor_0dte_progress.py --dashboard

# Check master status
python3 master_0dte_orchestrator.py --status
```

The system is designed to be resilient - it can be interrupted at any time and will resume exactly where it left off using the checkpoint system.