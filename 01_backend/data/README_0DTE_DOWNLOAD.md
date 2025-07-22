# 0DTE SPY Options Download System

## Overview
This system downloads 2.5 years (January 2023 - June 2025) of 0DTE SPY options data with 5-minute bars, including OHLC, Greeks, and IV data.

## Architecture

### Two-Tier Strike Strategy
- **Core Strikes**: ±10 strikes from ATM (high priority)
- **Extended Strikes**: ±11-20 strikes from ATM (lower priority)

### Components

1. **download_day_strikes.py** - Strike-aware daily downloader
   - Downloads a single day with checkpoint recovery
   - Supports core-only or full download modes
   - Handles rate limiting and retries

2. **monthly_parallel_manager.py** - Monthly parallel processor
   - Manages concurrent downloads of multiple days
   - Default: 3 parallel downloads
   - Tracks monthly progress

3. **master_0dte_orchestrator.py** - Master orchestrator
   - Manages entire 2.5-year download
   - Two-phase approach: core first, then extended
   - Checkpoint-based recovery

4. **monitor_0dte_progress.py** - Progress monitoring
   - Real-time dashboard
   - Speed metrics and ETA
   - Database statistics

## Quick Start

### 1. Test Single Day
```bash
python3 test_strike_download.py
```

### 2. Start Full Download (Background)
```bash
./start_0dte_download.sh
```

### 3. Monitor Progress
```bash
# Live dashboard
python3 monitor_0dte_progress.py --dashboard

# Quick status
python3 master_0dte_orchestrator.py --status

# Detailed report
python3 monitor_0dte_progress.py --report --output progress_report.txt
```

## Tmux Commands

View session:
```bash
tmux attach -t odte_download
```

Detach (keep running):
```
Ctrl+B then D
```

Kill session:
```bash
tmux kill-session -t odte_download
```

## Manual Controls

### Download Specific Month
```bash
python3 monthly_parallel_manager.py --year 2023 --month 1
```

### Download Single Day
```bash
python3 download_day_strikes.py --date 2023-01-03
```

### Resume from Specific Month
```bash
python3 master_0dte_orchestrator.py --run --start-from 2023-06
```

### Core Strikes Only
```bash
python3 download_day_strikes.py --date 2023-01-03 --core-only
```

## Checkpoint Files

All progress is saved in the `checkpoints/` directory:
- `master_progress.json` - Overall progress
- `monthly_YYYY_MM.json` - Monthly progress
- `checkpoint_YYYYMMDD.json` - Daily progress

## Database Tables

Data is stored in PostgreSQL with TimescaleDB:
- `theta.options_contracts` - Contract definitions
- `theta.options_ohlc` - Price data
- `theta.options_greeks` - Greeks data
- `theta.options_iv` - Implied volatility

## Time Estimates

Based on testing:
- Core strikes (±10): ~5 minutes per day
- Extended strikes (±11-20): ~3 minutes per day
- Total time: ~200-250 hours for 2.5 years

## Troubleshooting

### Check Logs
```bash
# View tmux session output
tmux attach -t odte_download
```

### Database Connection
```bash
psql -h localhost -U postgres -d theta_terminal
\dt theta.*
SELECT COUNT(*) FROM theta.options_contracts;
```

### Resume After Failure
The system automatically resumes from the last checkpoint:
```bash
python3 master_0dte_orchestrator.py --run
```

### Clean Restart
To start fresh (WARNING: deletes progress):
```bash
rm -rf checkpoints/
python3 master_0dte_orchestrator.py --run
```

## Coverage Notes

- Coverage percentage reflects actual trading activity
- Far OTM strikes may not trade every 5 minutes
- 35-40% coverage is normal for far strikes
- This represents 100% of available data, not missing data