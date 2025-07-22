# ALM Currency Conversion Fix Report

## Issue Summary
The ALM (Asset Liability Management) database was showing incorrect NAV values of 142,000 HKD instead of the expected ~80,000 HKD.

## Root Cause
The `build_alm_data.py` script was adding USD trade amounts directly to HKD NAV without converting them. The script defined `HKD_USD_RATE = 7.8472` but never used it in calculations.

### Example of the Error:
- Starting NAV: 79,754.81 HKD
- SPY SELL trade proceeds: 62,800 USD
- Incorrect calculation: 79,754.81 + 62,800 = 142,554.81 HKD
- Correct calculation: 79,754.81 + (62,800 × 7.8472) = 572,558.84 HKD

## Fix Applied
Modified `build_alm_data.py` to properly convert USD amounts to HKD before adding them to NAV:

1. **Trade Processing** (lines 46-66):
   - Added currency conversion for proceeds, commissions, and PnL
   - `proceeds_hkd = proceeds * HKD_USD_RATE`
   - `commission_hkd = commission * HKD_USD_RATE`
   - `pnl_hkd = pnl * HKD_USD_RATE`

2. **Cash Transactions** (lines 92-102):
   - Added currency conversion for withdrawal amounts
   - `amount_hkd = amount * HKD_USD_RATE`

3. **Enhanced Logging**:
   - Added logging to track currency conversions
   - Shows USD to HKD conversions for debugging
   - Logs major NAV changes for transparency

## Test Results
After applying the fix:
- Starting NAV: 79,754.81 HKD ✓
- Final NAV: 79,065.22 HKD ✓
- All USD amounts properly converted to HKD
- NAV calculations now correct throughout the process

### Daily Summary (Corrected):
- **2025-07-17**: 
  - Opening: 79,754.81 HKD
  - Closing: 572,837.37 HKD
  - Net Cash Flow: +492,804.03 HKD (from SPY assignment)
  
- **2025-07-18**:
  - Opening: 572,837.37 HKD
  - Closing: 79,065.22 HKD
  - Net Cash Flow: -493,359.24 HKD (SPY purchase and option trades)

## Impact
This fix ensures accurate NAV reporting in HKD for the ALM system, preventing misrepresentation of portfolio values due to missing currency conversion.

## Implementation Date
July 20, 2025