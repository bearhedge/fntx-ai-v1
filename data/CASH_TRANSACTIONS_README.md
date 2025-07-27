# Cash Transactions Data Limitation

## Issue
The IBKR FlexQuery Cash Transactions reports do not include transaction amounts in the XML data. The reports only contain:
- Transaction ID
- Description
- Currency
- Account ID

## Example
```xml
<CashTransaction accountId="U19860056" currency="HKD" description="DISBURSEMENT INITIATED BY Tsun Ming Hou" transactionID="3916940009" />
```

## Solutions

### Option 1: Reconfigure FlexQuery (Recommended)
1. Log into IBKR Portal
2. Navigate to Performance & Reports > Flex Queries
3. Edit your Cash Transactions query
4. Add the "Amount" field to the query configuration
5. Re-download the reports

### Option 2: Use Activity Statements
1. Download full Activity Statements from IBKR
2. These contain complete transaction details including amounts
3. Parse the Activity Statement format instead of FlexQuery

### Option 3: Manual Reconciliation
1. Use the NAV report's `depositsWithdrawals` field for period totals
2. Cross-reference with bank statements
3. Manually update the database with correct amounts

## Current State
- Cash transactions are imported with amount = 0
- Transaction metadata (ID, description, date) is preserved
- No fabricated data exists in the database

## Important Note
Never fabricate or estimate transaction amounts. Only use actual data from IBKR or other verified sources.