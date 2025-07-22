# IBKR FlexQuery IDs Reference

## Complete FlexQuery Configuration (11 Queries)

### NAV Tracking
1. **NAV (1244257) - MTD**
   - Query ID: 1244257
   - Type: NAV tracking (Month to Date)
   - Contains: Daily equity summaries, cash, options, interest accruals

2. **NAV (1257542) - LBD**
   - Query ID: 1257542
   - Type: NAV tracking (Last Business Day)
   - Contains: Daily NAV snapshot

### Trading Activity
3. **Trades (1257686) - MTD**
   - Query ID: 1257686
   - Type: Trade history (Month to Date)
   - Contains: All trades with proceeds, commissions, P&L

4. **Trades (1257690) - LBD**
   - Query ID: 1257690
   - Type: Trade history (Last Business Day)
   - Contains: Daily trades with commission details

### Options Activity
5. **Exercises and Expiries (1257675) - MTD**
   - Query ID: 1257675
   - Type: Options exercises/assignments (Month to Date)
   - Contains: Option expirations and exercises

6. **Exercises and Expiries (1257679) - LBD**
   - Query ID: 1257679
   - Type: Options exercises/assignments (Last Business Day)
   - Contains: Daily option activity

### Position Tracking
7. **Open Positions (1257695) - LBD**
   - Query ID: 1257695
   - Type: Current positions (Last Business Day)
   - Contains: All open positions snapshot

### Cash Movements
8. **Cash Transactions (1257703) - MTD**
   - Query ID: 1257703
   - Type: Cash movements (Month to Date)
   - Contains: Deposits, withdrawals, fees, adjustments

9. **Cash Transactions (1257704) - LBD**
   - Query ID: 1257704
   - Type: Cash movements (Last Business Day)
   - Contains: Daily cash transaction details

### Interest Tracking
10. **Interest Accruals (1257707) - MTD**
    - Query ID: 1257707
    - Type: Interest details (Month to Date)
    - Contains: Interest accrued, tier details, balances

11. **Interest Accruals (1257708) - LBD**
    - Query ID: 1257708
    - Type: Interest details (Last Business Day)
    - Contains: Daily interest accrual details

## ALM Reconciliation Formula
These queries provide complete data for:
```
Opening NAV + Deposits - Withdrawals + Trading P&L - Commissions - Fees + Interest = Closing NAV
```

## File Size Management
Each query produces files between 5-50KB, well under the 256KB processing limit.