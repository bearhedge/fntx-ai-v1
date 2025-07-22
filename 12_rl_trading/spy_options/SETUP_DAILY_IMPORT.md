# Setting Up Daily IBKR FlexQuery Import

This guide explains how to set up automated daily imports from IBKR to populate your database with real account data.

## Why Use Daily Import?

Instead of calling IBKR API every time the terminal starts (slow, rate-limited), we:
1. Run a daily import job that fetches data once
2. Store it in the database
3. Terminal UI reads from database (instant!)

## Quick Setup

### 1. Test the Import Script

First, test that the import works:

```bash
cd /home/info/fntx-ai-v1/01_backend/scripts
python3 daily_flex_import.py
```

This will:
- Fetch your account data from IBKR
- Save NAV snapshots to `portfolio.daily_nav_snapshots`
- Save cash movements to `portfolio.cash_movements`
- Save trades to `portfolio.trades`

### 2. Set Up Daily Cron Job

Add to your crontab to run daily at 6 AM:

```bash
# Edit crontab
crontab -e

# Add this line (adjust path if needed):
0 6 * * * cd /home/info/fntx-ai-v1 && source venv/bin/activate && python3 01_backend/scripts/daily_flex_import.py >> /var/log/flex_import.log 2>&1
```

### 3. Verify Database Population

Check if data is being stored:

```sql
-- Connect to database
psql -U info -d fntx_trading

-- Check NAV snapshots
SELECT * FROM portfolio.daily_nav_snapshots ORDER BY snapshot_date DESC LIMIT 5;

-- Check cash movements  
SELECT * FROM portfolio.cash_movements ORDER BY transaction_date DESC LIMIT 5;
```

## How It Works

```
Daily at 6 AM:
┌─────────────────┐
│   Cron Job      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ daily_flex_     │  1. Calls IBKR FlexQuery API
│ import.py       │  2. Fetches account data
└────────┬────────┘  3. Parses XML response
         │
         ▼
┌─────────────────┐
│   PostgreSQL    │  Stores:
│    Database     │  - Daily NAV snapshots
└────────┬────────┘  - Cash movements
         │           - Trade history
         ▼
┌─────────────────┐
│  Terminal UI    │  Reads latest NAV
│  (Instant!)     │  No API calls needed
└─────────────────┘
```

## Terminal UI Usage

Once daily import is set up:

```bash
# Normal usage - reads from database (instant!)
python3 run_terminal_ui.py --use-database

# Force refresh from IBKR (if needed)
python3 run_terminal_ui.py --use-database --force-ibkr-refresh
```

## Benefits

1. **Speed**: Terminal starts instantly (no 5+ second wait)
2. **Reliability**: Works even if IBKR API is down
3. **History**: Builds historical NAV tracking over time
4. **No Rate Limits**: Only calls API once per day

## Troubleshooting

If no data appears:
1. Check IBKR credentials in `.env`
2. Run import manually: `python3 daily_flex_import.py`
3. Check logs: `/var/log/flex_import.log`
4. Verify database connection

## Database Schema

The import populates these tables:

- `portfolio.daily_nav_snapshots` - Daily account values
- `portfolio.cash_movements` - Deposits/withdrawals
- `portfolio.trades` - All executed trades
- `portfolio.nav_reconciliation` - Daily reconciliation