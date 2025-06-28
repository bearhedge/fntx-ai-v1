# Archived Scripts

This directory contains scripts that were used for one-time operations or migrations and are no longer needed for production use.

## Migration Scripts

### auto_backfill_monitor.py
- **Purpose**: Monitored the main SPY options download process and automatically triggered Greeks/IV backfill
- **Usage**: Ran continuously checking every 5 minutes for download completion
- **Status**: One-time data migration helper, no longer needed

### backfill_greeks_iv.py
- **Purpose**: Backfilled missing Greeks and implied volatility data for existing OHLC contracts
- **Usage**: Run manually or triggered by auto_backfill_monitor.py
- **Status**: One-time data enhancement script

### start_greeks_iv_download.py
- **Purpose**: Downloaded Greeks and IV data for historical periods (2021-2024)
- **Usage**: Processed quarterly periods to enhance existing OHLC data
- **Status**: One-time historical data enhancement

### fetch_historical_nav_data.py
- **Purpose**: Fetched historical NAV data from IBKR for initial system setup
- **Usage**: Called by setup_nav_reconciliation.sh during system configuration
- **Status**: Setup/migration script, kept for potential recovery use

## One-Time Scripts

### execute_single_spy_trades.py
- **Purpose**: Executed specific SPY options trades (1x 605 PUT, 1x 610 CALL)
- **Usage**: Manual trade execution with hard-coded strikes
- **Status**: One-time trading script with fixed parameters

### clear_chats.py
- **Purpose**: Cleared all chat sessions from the database
- **Usage**: Run manually to reset chat history
- **Status**: Database cleanup utility

### daily_nav_calculator.py
- **Purpose**: Recalculates historical NAV values from transaction history
- **Usage**: Manual runs for NAV reconciliation and validation
- **Status**: Utility script for correcting/validating NAV data

### run_cleanup.py
- **Purpose**: Quick database cleanup to remove far OTM option contracts
- **Usage**: One-time cleanup to optimize database size
- **Status**: Database optimization utility

### background_cleanup.py
- **Purpose**: Background database cleanup with batch processing
- **Usage**: Run while downloader continues, processes in batches
- **Status**: Database optimization utility with better performance

## Note
These scripts are preserved for reference but should not be used in production. For current functionality, use the consolidated tools in the main directories.