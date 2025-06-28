# IBKR Flex Query Setup for NAV Reconciliation

## Overview
The NAV reconciliation system requires IBKR Flex Query credentials to fetch:
- Daily NAV (Net Asset Value)
- Cash movements (deposits/withdrawals)
- Trade history with settlement dates

## Setup Steps

### 1. Create Flex Query in IBKR Account Management

1. Log into IBKR Account Management
2. Navigate to **Reports/Tax Docs > Flex Queries**
3. Click **Create** for a new Activity Flex Query
4. Configure the following sections:

#### Account Information
- ☑️ Account Information
- ☑️ Change in NAV
- ☑️ Mark-to-Market Performance Summary

#### Cash Report
- ☑️ Cash Report
- ☑️ Cash Transactions
  - Include: Deposits, Withdrawals, Dividends, Interest, Fees

#### Trades
- ☑️ Trades
  - Execution Type: All Executions
  - Include: All trades

#### Positions
- ☑️ Open Positions
- ☑️ Financial Instrument Information

#### Statement of Funds
- ☑️ Statement of Funds
- ☑️ Change in Position Value

5. Set **Format**: XML
6. Set **Period**: Last 7 Calendar Days
7. **Save** the query and note:
   - Query ID (shown after saving)
   - Create a Flex Web Service token

### 2. Configure Environment Variables

```bash
# Add to your .env file or export in terminal
export IBKR_FLEX_TOKEN='your_flex_token_here'
export IBKR_FLEX_QUERY_ID='your_query_id_here'
```

### 3. Run Historical Data Import

```bash
cd /home/info/fntx-ai-v1
./setup_nav_reconciliation.sh
```

This will:
- Import June 25-26 trades (with T+1 settlement)
- Fetch NAV snapshots
- Import cash movements
- Run reconciliation

## Daily Usage

The system automatically tracks:
- **Opening NAV**: Previous day's closing balance
- **Trading P&L**: Sum of closed trades
- **Cash Movements**: Deposits and withdrawals
- **Closing NAV**: End of day balance

### Reconciliation Formula
```
Closing NAV = Opening NAV + Trading P&L + Deposits - Withdrawals - Fees + Interest
```

## Viewing Data

### In the UI:
1. **PERFORMANCE Tab**: View NAV history, charts, and reconciliation status
2. **WITHDRAWALS Tab**: Create withdrawals and view history
3. **HISTORY Tab**: See trades with settlement status

### API Endpoints:
- `GET /api/portfolio/nav/current` - Current NAV and available balance
- `GET /api/portfolio/nav/history` - Historical NAV data
- `POST /api/portfolio/withdrawals` - Create withdrawal request
- `GET /api/portfolio/reconciliation/status` - Check daily reconciliation

## Troubleshooting

### "No NAV data available"
- Ensure Flex Query includes Account Information section
- Check that the query is set to XML format
- Verify credentials are correctly set

### "Reconciliation discrepancy"
- Check for pending trades not yet settled
- Verify all cash movements are captured
- Review fees and interest charges

### "Open orders showing in history"
The system now properly handles:
- T+1 settlement for options trades
- Distinction between executed and open orders
- Proper P&L calculation only for closed positions