# FlexQuery Configuration Update Guide

## Issue
The current FlexQuery configuration for Cash Transactions is missing critical fields:
- `amount` - The monetary value of the transaction
- `dateTime` - The date and time when the transaction occurred

This prevents the ALM system from properly capturing withdrawals and deposits.

## Solution

### Step 1: Log into IBKR Account Management
1. Go to https://www.interactivebrokers.com
2. Click "Login" → "Account Management"
3. Enter your credentials

### Step 2: Navigate to FlexQuery Configuration
1. In Account Management, go to "Reports" → "Flex Queries"
2. Find the Cash Transactions query (ID: 1257703 for MTD, 1257704 for LBD)
3. Click "Edit" next to the query

### Step 3: Update Cash Transaction Fields
Add the following fields to the Cash Transaction section:
- ✅ `amount` - Transaction amount
- ✅ `dateTime` - Transaction date and time
- ✅ `transactionID` - Unique identifier (should already be included)
- ✅ `description` - Transaction description (should already be included)
- ✅ `currency` - Transaction currency (should already be included)

### Step 4: Save and Test
1. Save the updated FlexQuery configuration
2. Run a test query to download XML
3. Verify the Cash Transaction elements now include amount and dateTime attributes

### Step 5: Update All Related Queries
Repeat for all Cash Transaction queries:
- Cash Transactions (1257703) MTD
- Cash Transactions (1257704) LBD

## Expected XML Format After Update

### Before (Current - Missing Fields):
```xml
<CashTransaction accountId="U19860056" currency="HKD" 
                description="DISBURSEMENT INITIATED BY Tsun Ming Hou" 
                transactionID="3916940009" />
```

### After (With Required Fields):
```xml
<CashTransaction accountId="U19860056" currency="HKD" 
                description="DISBURSEMENT INITIATED BY Tsun Ming Hou" 
                transactionID="3916940009"
                amount="-1230.00"
                dateTime="20250717;093000" />
```

## Verification
After updating, download a new XML file and check that:
1. All CashTransaction elements have `amount` attributes
2. All CashTransaction elements have `dateTime` attributes
3. The values are populated correctly (not empty)

## Note
This is a manual configuration change that must be done through the IBKR web interface. There is no API or programmatic way to update FlexQuery configurations.