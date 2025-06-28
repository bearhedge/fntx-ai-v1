# Monitoring Scripts

This directory contains scripts for monitoring trading positions and market data.

## Scripts

### check_spy_positions.py
Monitors open SPY option positions and manages risk:
- Checks current positions against market prices
- Monitors stop-loss levels (3x premium)
- Tracks take-profit targets (50% of premium)
- Alerts when action is needed
- Can be run manually or scheduled

**Usage:**
```bash
python3 check_spy_positions.py
```

### spy_option_chain.py
Displays real-time SPY option chains:
- Shows bid/ask spreads
- Displays implied volatility
- Highlights ATM options
- Filters by expiration date
- Useful for manual trading decisions

**Usage:**
```bash
python3 spy_option_chain.py [--expiry YYYY-MM-DD]
```

## Features

- Real-time market data from IBKR
- Position risk analysis
- P&L tracking
- Greeks calculation
- Volatility monitoring

## Requirements

- Active IBKR connection
- Python virtual environment activated
- Market hours for real-time data

## Scheduling

To run position checks automatically:
```bash
# Add to crontab for hourly checks during market hours
0 9-16 * * 1-5 cd /home/info/fntx-ai-v1 && source venv/bin/activate && python scripts/monitoring/check_spy_positions.py
```