# FNTX AI Trade Logging System

## Overview

This directory contains the comprehensive trade logging and reconciliation system for FNTX AI. The system provides:

- **Immutable Trade History**: All trades are logged with full audit trail
- **Automated IBKR Import**: Daily imports from Interactive Brokers Flex Queries
- **Trade Matching**: Automatic pairing of opening and closing trades
- **Reconciliation**: Daily NAV and P&L reconciliation
- **Data Integrity**: Deduplication and validation of all imports

## Architecture

```
Master Trading Database
├── Trading Schema
│   ├── trades (with versioning)
│   ├── trades_history (audit log)
│   ├── matched_trades (paired trades)
│   └── import_log (deduplication)
├── Staging Schema
│   ├── flex_trades (import staging)
│   └── validation_rules
└── Ledger Schema
    ├── daily_snapshots
    └── reconciliations
```

## Directory Structure

```
trade-logging/
├── sql/                    # Database migrations
│   ├── 01_data_integrity_phase1.sql
│   ├── 02_staging_schema.sql
│   └── 03_ledger_schema.sql
├── scripts/                # Python scripts
│   ├── historical_import.py
│   ├── daily_trade_import.py
│   ├── trade_reconciliation.py
│   └── trade_matcher.py
├── config/                 # Configuration files
│   └── flex_queries.json
└── logs/                   # Import logs
```

## Setup Instructions

### 1. Database Setup

Run the SQL migrations in order:

```bash
cd /home/info/fntx-ai-v1/scripts/trade-logging
psql -U info -d fntx_trading -f sql/01_data_integrity_phase1.sql
psql -U info -d fntx_trading -f sql/02_staging_schema.sql
psql -U info -d fntx_trading -f sql/03_ledger_schema.sql
```

### 2. Configure IBKR Flex Queries

1. Log into IBKR Account Management
2. Create a new Flex Query with:
   - Query Name: "FNTX_Trade_History"
   - Include: Trades, Executions, Cash Transactions
   - Date Period: Custom Range
   - Format: XML v3

3. Update config/flex_queries.json with your Query ID and Token

### 3. Historical Import (One-time)

Import all trades since June 20, 2025 (when trading began):

```bash
python3 scripts/historical_import.py
# or specify dates explicitly:
python3 scripts/historical_import.py --start-date 2025-06-20
```

Note: Initial deposit was made on June 12, 2025

### 4. Daily Automation

Add to crontab for daily imports:

```bash
# Daily trade import at 11 PM EST
0 23 * * * cd /home/info/fntx-ai-v1/scripts/trade-logging && python3 scripts/daily_trade_import.py

# Reconciliation at 11:30 PM EST
30 23 * * * cd /home/info/fntx-ai-v1/scripts/trade-logging && python3 scripts/trade_reconciliation.py
```

## Key Features

### 1. Data Integrity
- **Unique Constraints**: Prevent duplicate trades
- **Version History**: Full audit trail of all changes
- **Import Deduplication**: Never import same data twice
- **Hash Verification**: Cryptographic integrity checks

### 2. Trade Matching
- **Automatic Pairing**: FIFO matching of opening/closing trades
- **P&L Calculation**: Accurate realized P&L with commissions
- **Partial Matching**: Handle partial fills correctly
- **Manual Override**: Ability to manually match trades

### 3. Reconciliation
- **Daily NAV Check**: Compare trade P&L with NAV changes
- **Cash Movement Tracking**: All deposits/withdrawals logged
- **Discrepancy Alerts**: Automatic notification of mismatches
- **Monthly Reports**: Comprehensive reconciliation reports

### 4. Analysis Ready
- **Time Series Data**: Daily snapshots for analysis
- **Performance Metrics**: Win rate, average return, etc.
- **Strategy Analysis**: Group by strategy type
- **Export Formats**: CSV, JSON, Excel

## Database Schema Details

### trades Table Enhancements
- Added versioning columns (version_id, valid_from, valid_to)
- Composite unique constraint on (ibkr_order_id, entry_time)
- Full history tracking in trades_history table

### matched_trades Table
```sql
- match_id: UUID primary key
- opening_trade_id: References opening trade
- closing_trade_id: References closing trade
- match_method: FIFO, LIFO, SPECIFIC, AUTO
- quantity_matched: Number of contracts matched
- realized_pnl: Calculated P&L for this match
```

### import_log Table
```sql
- import_id: UUID primary key
- source_type: FLEX_QUERY, API, MANUAL, CSV
- period_start/end: Date range of import
- import_hash: SHA256 for deduplication
- status: PENDING, PROCESSING, COMPLETED, FAILED
```

## Monitoring

Check import status:
```sql
SELECT * FROM trading.import_log 
WHERE created_at > CURRENT_DATE - INTERVAL '7 days'
ORDER BY created_at DESC;
```

View unmatched trades:
```sql
SELECT * FROM trading.unmatched_trades 
WHERE is_unmatched = true;
```

Daily statistics:
```sql
SELECT * FROM trading.trade_statistics 
WHERE trade_date >= CURRENT_DATE - INTERVAL '30 days';
```

## Troubleshooting

### Common Issues

1. **Duplicate Import Attempt**
   - Check import_log for existing import
   - Use --force flag to reimport if needed

2. **Trade Matching Failures**
   - Review unmatched_trades view
   - Check for data quality issues
   - Use manual matching if needed

3. **Reconciliation Discrepancies**
   - Compare with IBKR statements
   - Check for missing cash movements
   - Verify commission calculations

## Best Practices

1. **Never modify historical data directly**
   - All changes create audit trail
   - Use correction entries if needed

2. **Run reconciliation daily**
   - Catch discrepancies early
   - Maintain data integrity

3. **Monitor import logs**
   - Check for failed imports
   - Verify record counts

4. **Regular backups**
   - Daily database backups
   - Archive Flex Query XMLs