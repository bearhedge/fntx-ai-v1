# ALM Reporting Guide

## Overview
The ALM (Asset Liability Management) reporting system tracks daily trading performance for SPY options trading. It handles 0DTE (zero days to expiration) options trades, assignments, and cash flows with proper NAV adjustments.

## Core Components

### 1. Data Pipeline
- **IBKR FlexQuery Reports**: Downloaded daily via XML files
  - NAV (Net Asset Value)
  - Cash Transactions
  - Trades
  - Exercises and Expiries
  - Interest Accruals
- **Database**: PostgreSQL with `alm_reporting` schema
- **Automation**: `alm_automation.py` for daily updates

### 2. Key Calculation Logic

#### Daily Return Formula
```
Daily Return = Net P&L / Opening NAV Base

Where:
- Net P&L = Gross P&L - Commissions
- Opening NAV Base = Adjusted Opening NAV (if deposits before 9:30 AM ET) 
                   OR Original Opening NAV (otherwise)
- Adjusted Opening NAV = Original Opening NAV + Deposits before market open
```

#### Cash Transaction Timing
- **Deposits**: Timestamped at 8:00 AM ET (before market open)
- **Withdrawals**: Timestamped at 4:00 PM ET (at market close)
- Rationale: IBKR doesn't provide actual timestamps, so we use logical assumptions

#### Option Expiration Logic
For 0DTE options without exercise data from IBKR:
- **OTM (Out of The Money)**: Create expiration event with zero P&L
- **ITM (In The Money)**: Create assumed assignment event
- Detection runs at 6 PM and 12 AM HKT to confirm via FlexQuery

#### Synthetic Event Tracking
- **Synthetic Events**: Created when IBKR data not yet available
  - Marked with `[SYNTHETIC]` in calculation engine output
  - Database flag: `is_synthetic = TRUE`
  - Created for options expiring after 4 PM ET when IBKR hasn't reported yet
- **Validation Process**: Runs after IBKR downloads (6:05 PM, 12:05 AM HKT)
  - `synthetic_validated = TRUE`: IBKR confirmed our assumption
  - `synthetic_validated = FALSE`: IBKR data contradicts assumption
  - `ibkr_exercise_time`: Actual exercise time when available
- **Purpose**: Ensures accurate daily P&L while waiting for IBKR settlement data

### 3. Daily Narrative Structure

The calculation engine produces daily narratives following this pattern:

```
**Opening Position**
   Original NAV: **X HKD**
   [If deposit before open: Deposit before market open: **+Y HKD**]
   [If deposit before open: Adjusted NAV at market open: **X+Y HKD**]

**Assignment Workflow from Previous Trading Day** [if applicable]
   • Assignment details with timestamps
   • Share disposal trades
   • Overnight P&L calculations

**Trading Activity**
   • New positions opened (with premium and commissions)
   • Expired positions
   • Assigned positions
   • Closed positions (stop-loss)

**Day Summary**
   Closing NAV: **Z HKD**
   Daily Return: **±X.XX%** (using net P&L / adjusted opening NAV)
   Gross P&L: X HKD
   Total Commissions: Y HKD
   Net P&L: X-Y HKD
   [Deposit/Withdrawal amounts if applicable]
   [Assignment count if applicable]
```

### 4. Key Files

- `/home/info/fntx-ai-v1/backend/alm/calculation_engine_v1.py`: Main report generator
- `/home/info/fntx-ai-v1/backend/alm/build_alm_data_append.py`: XML parser and DB loader
- `/home/info/fntx-ai-v1/backend/alm/alm_automation.py`: Daily automation script
- `/home/info/fntx-ai-v1/data/[MonthYear]/`: XML files organized by month

### 5. Database Schema

```sql
-- Main events table
alm_reporting.chronological_events (
    event_timestamp TIMESTAMPTZ,
    event_type VARCHAR,
    description TEXT,
    cash_impact_hkd DECIMAL,
    realized_pnl_hkd DECIMAL,
    ib_commission_hkd DECIMAL,
    source_transaction_id VARCHAR UNIQUE
)

-- Daily summary table
alm_reporting.daily_summary (
    summary_date DATE PRIMARY KEY,
    opening_nav_hkd DECIMAL,
    closing_nav_hkd DECIMAL,
    total_pnl_hkd DECIMAL,
    net_cash_flow_hkd DECIMAL
)
```

## Running the Calculation Engine

### Manual Run for Specific Date
```bash
python3 calculation_engine_v1.py 2025-07-28
```

### Run for All Dates (Full Report)
```bash
python3 calculation_engine_v1.py
```

### Daily Automation
The system runs automatically via `alm_automation.py` which:
1. Downloads latest FlexQuery reports
2. Parses and loads data to database
3. Runs calculation engine
4. Manages file rotation (keeps 3 most recent)

## Important Notes

1. **July 16, 2025 Pattern**: This day shows the complete workflow including:
   - Assignment from previous day
   - Share disposal with overnight P&L
   - New trades
   - Stop-loss closures
   - NAV reconciliation with withdrawal

2. **NAV Adjustments**: Always check for deposits before market open (9:30 AM ET) to calculate adjusted NAV

3. **Assignment Timing**: Assignments occur at 4:30 PM ET (4:30 AM HKT next day)

4. **Expired Options**: All sold options that reach expiration are shown as either:
   - Expired (if OTM)
   - Assigned (if ITM)

5. **Commission Impact**: Daily returns use NET P&L (gross P&L minus commissions)

## Troubleshooting

### Wrong Daily Return
- Check if deposits are timestamped at 8 AM ET
- Verify calculation uses net P&L / adjusted opening NAV
- Run SQL fix if needed:
```sql
UPDATE alm_reporting.chronological_events
SET event_timestamp = event_timestamp - INTERVAL '8 hours'
WHERE event_type = 'Deposits/Withdrawals'
  AND cash_impact_hkd > 0
  AND EXTRACT(HOUR FROM event_timestamp AT TIME ZONE 'US/Eastern') = 16;
```

### Missing Expiration Events
- Check if IBKR XML was downloaded after 6 PM HKT
- Verify `check_itm_options_for_assignment()` is creating events for OTM options

### Database Connection
```
Host: localhost
Database: options_data
User: postgres
Password: theta_data_2024
```