# IBKR Flex Query Setup Guide

## Overview
The IBKR Flex Query API allows retrieval of complete trade history including both opening and closing trades, solving the limitation of the standard API that only shows closing executions.

## Setup Steps

### 1. Create Flex Query in IBKR Account Management

1. Log into IBKR Account Management portal
2. Navigate to: **Reports > Flex Queries > Activity Flex Query**
3. Click **Create New Query**
4. Configure the query:
   - Query Name: `FNTX Trade History`
   - Period: `Last 365 Days` (or your preferred period)
   - Format: `XML` (required for API)
   - Sections to include:
     - ✅ **Trade Confirmations** (REQUIRED)
     - ✅ Account Information
     - ✅ Cash Transactions (optional)
   
5. In Trade Confirmations section, select ALL fields including:
   - Trade ID
   - Order ID
   - Execution ID
   - Date/Time
   - Symbol
   - Buy/Sell
   - Quantity
   - Price
   - Commission
   - P&L

6. Save the query and note the **Query ID**

### 2. Get Flex Web Service Token

1. In Account Management, go to: **Settings > Account Settings > Flex Web Service**
2. Click **Generate New Token** if you don't have one
3. Copy and save the token securely

### 3. Configure Environment Variables

Add to your `.env` file:

```bash
# IBKR Flex Query Configuration
IBKR_FLEX_TOKEN=your_flex_token_here
IBKR_FLEX_QUERY_ID=your_query_id_here
```

### 4. Usage

#### Import Historical Trades via API
```bash
# Import last 30 days of trades
curl -X POST http://localhost:8000/api/trades/import/flex \
  -H "Content-Type: application/json" \
  -d '{"days_back": 30}'

# Check import status
curl http://localhost:8000/api/trades/import/status/{import_id}
```

#### Import via Command Line
```bash
# Import last 30 days
python backend/scripts/import_flex_trades.py --days 30

# Include open positions
python backend/scripts/import_flex_trades.py --days 30 --include-open
```

#### Import CSV File
```bash
# Manual CSV import
python backend/scripts/import_trades_csv.py /path/to/flex_query_export.csv
```

## API Endpoints

### 1. `/api/trades/import/flex` (POST)
Trigger Flex Query import
- `days_back`: Number of days to import (default: 30)
- `include_open_positions`: Import open positions (default: false)

### 2. `/api/trades/import/csv` (POST)
Upload and import CSV file
- Form data with file upload

### 3. `/api/trades/import/status/{import_id}` (GET)
Check import status

### 4. `/api/trades/import/history` (GET)
View import history

## Database Schema Updates

Run the migration to add Flex Query support:
```bash
psql -U info -d fntx_trading -f database/flex_query_update.sql
```

## Features

1. **Complete Trade History**: Retrieves both opening (SLD) and closing (BOT) trades
2. **Automatic P&L Calculation**: Matches trades and calculates net P&L including commissions
3. **Duplicate Prevention**: Checks existing trades to prevent duplicates
4. **Import Tracking**: Logs all imports with status and statistics
5. **Multiple Import Methods**: API, command line, or CSV upload

## Troubleshooting

### Common Issues

1. **"Flex Query credentials not configured"**
   - Ensure `IBKR_FLEX_TOKEN` and `IBKR_FLEX_QUERY_ID` are set in environment

2. **"Report not yet available"**
   - The service automatically retries. Large reports may take 30-60 seconds

3. **No trades found**
   - Verify the Flex Query includes Trade Confirmations
   - Check the date range in your query configuration

4. **Authentication errors**
   - Regenerate token in IBKR Account Management
   - Ensure token hasn't expired (tokens expire after 1 year)

## Security Notes

- Store Flex Query tokens securely
- Never commit tokens to version control
- Consider using a secrets management service in production
- Tokens provide read-only access to trade data