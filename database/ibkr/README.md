# IBKR Trading Data

This directory contains SQL schemas for Interactive Brokers trading data.

## Tables
- `trading.trades` - Executed trades
- `trading.matched_trades` - Opening/closing trade pairs
- `trading.import_log` - Trade import history
- `trading.trades_audit` - Audit trail for data integrity

## Data Source
- Provider: Interactive Brokers (IBKR)
- Import method: Flex Queries API
- Coverage: Live trading data from June 20, 2025 onwards
- Purpose: First-level AI training data for trade execution patterns