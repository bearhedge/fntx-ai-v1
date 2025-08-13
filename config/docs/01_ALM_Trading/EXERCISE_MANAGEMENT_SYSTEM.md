# Option Exercise Management System

## Overview

This system automatically detects when options are exercised/assigned and immediately places extended hours orders to dispose of the resulting stock positions. Designed for Hong Kong timezone users trading US markets.

## Key Features

1. **Early Exercise Detection** (7:00 AM HKT)
   - Uses IBKR FlexQuery API to detect exercises before they appear in TWS
   - Exercises are finalized at 5:30 AM HKT but only visible in UI at 2:00 PM HKT
   - Our system detects them at 7:00 AM HKT using FlexQuery

2. **ASAP Disposal via Extended Hours**
   - Places limit orders for pre-market trading (4:00 PM - 9:30 PM HKT)
   - Uses aggressive pricing (0.1% below last close) for quick fills
   - Orders valid until 8:00 PM ET

3. **No Mock Data Policy**
   - Terminal UI always shows real IBKR account balance
   - No hardcoded fallbacks or fake data
   - System exits if no real data available

## Components

### 1. Terminal UI Fix (`run_terminal_ui.py`)
- Fixed flawed logic that prevented IBKR API calls
- Always tries IBKR FlexQuery first for real balance
- Falls back to database only if IBKR unavailable
- Removed all hardcoded $80,000 mock values

### 2. Exercise Detection (`exercise_detector.py`)
- Runs daily at 7:00 AM HKT
- Parses FlexQuery XML for exercise indicators
- Detects exercises 7+ hours before UI shows them
- Automatically triggers disposal script

### 3. Extended Hours Disposal (`exercise_disposal_asap.py`)
- Places pre-market limit orders immediately
- Calculates aggressive limits for quick fills
- Updates database with order status
- Supports multiple exercises in one run

### 4. Database Schema (`003_exercise_tracking.sql`)
```sql
portfolio.option_exercises
- Tracks all exercises and disposal status
- Records order IDs and execution prices
- Indexed for quick pending lookups
```

### 5. Automation Options

#### Cron (Recommended)
```bash
# Run setup script
./scripts/setup_cron_jobs.sh

# Scheduled tasks:
0 23 * * * daily_flex_import.py    # 7:00 AM HKT
0 23 * * * exercise_detector.py    # 7:00 AM HKT
```

#### Python Scheduler
```bash
# Run as background process
nohup python3 scripts/scheduler.py &
```

#### Manual Execution
```bash
# Run both tasks
./scripts/run_daily_tasks.sh
```

### 6. Supporting Scripts
- `historical_backfill.py` - Backfill 30 days of NAV history
- `test_exercise_system.py` - Complete system test
- `SCHEDULING_SETUP.md` - Detailed scheduling instructions

## Usage

### Initial Setup
```bash
# 1. Ensure database table exists
psql -d fntx_trading -f 03_database/portfolio/003_exercise_tracking.sql

# 2. Test the system
python3 scripts/test_exercise_system.py

# 3. Set up automation
./scripts/setup_cron_jobs.sh
```

### Daily Operation
The system runs automatically at 7:00 AM HKT:
1. Fetches latest NAV from IBKR
2. Detects any overnight exercises
3. Places extended hours disposal orders
4. Updates database with results

### Monitoring
Check logs in `/home/info/fntx-ai-v1/logs/`:
- `exercise_detection.log` - Detection results
- `exercise_disposal.log` - Order placement
- `daily_import.log` - NAV updates

## Timeline Example

For a 622 PUT exercised on Friday:
- **5:30 AM HKT Saturday**: Exercise finalized by OCC
- **7:00 AM HKT Saturday**: Our system detects it
- **7:30 AM HKT Saturday**: Disposal order placed
- **4:00 PM HKT Monday**: Pre-market opens, order can fill
- **2:00 PM HKT Saturday**: Exercise finally visible in TWS

## Configuration

### Environment Variables (.env)
```
IBKR_FLEX_TOKEN=your_token_here
IBKR_FLEX_QUERY_ID=your_query_id_here
```

### IB Gateway
- Must be running on port 4001 for order placement
- Not required for exercise detection
- Client ID 20 reserved for disposal orders

## Troubleshooting

### No Balance Showing
1. Check IBKR credentials in .env
2. Run `python3 01_backend/scripts/daily_flex_import.py`
3. Check database: `SELECT * FROM portfolio.daily_nav_snapshots ORDER BY snapshot_date DESC LIMIT 5;`

### Exercises Not Detected
1. Verify FlexQuery is configured for T+1 reports
2. Check exercise_detection.log for errors
3. Manually run: `python3 01_backend/scripts/exercise_detector.py`

### Orders Not Placing
1. Ensure IB Gateway is running
2. Check extended hours permissions on account
3. Verify SPY trading permissions

## Key Benefits

1. **14+ Hour Head Start**: Detect exercises 14+ hours before market open
2. **Immediate Action**: No waiting for regular hours
3. **Automated Flow**: Detection → Disposal without manual intervention
4. **Real Data Only**: Never shows fake balances
5. **Hong Kong Optimized**: Handles timezone challenges