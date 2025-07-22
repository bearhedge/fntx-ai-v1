-- Views and ALM Reconciliation (Part 4/4)
-- Creates views for reporting and ALM reconciliation

-- Daily NAV Movement View
-- Shows daily NAV changes with breakdown of contributing factors
CREATE OR REPLACE VIEW portfolio.daily_nav_movement AS
SELECT 
    report_date,
    account_id,
    opening_nav,
    closing_nav,
    change_in_nav,
    change_in_position_value,
    realized_pnl,
    unrealized_pnl,
    cash_changes,
    -- Calculate trading P&L (realized + unrealized)
    (COALESCE(realized_pnl, 0) + COALESCE(unrealized_pnl, 0)) as trading_pnl,
    -- Calculate implied deposits/withdrawals
    (change_in_nav - COALESCE(change_in_position_value, 0) - COALESCE(cash_changes, 0)) as implied_cash_flow,
    period
FROM portfolio.nav_snapshots
ORDER BY report_date DESC, account_id;

-- Current Positions Summary
-- Latest position snapshot with key metrics
CREATE OR REPLACE VIEW portfolio.current_positions_summary AS
WITH latest_date AS (
    SELECT MAX(report_date) as max_date 
    FROM portfolio.open_positions
)
SELECT 
    p.symbol,
    p.underlying_symbol,
    p.security_type,
    p.strike,
    p.expiry,
    p.call_put,
    p.position,
    p.mark_price,
    p.position_value,
    p.unrealized_pnl,
    p.pct_of_nav,
    -- Days to expiry for options
    CASE 
        WHEN p.expiry IS NOT NULL THEN 
            p.expiry - p.report_date
        ELSE NULL 
    END as days_to_expiry,
    p.report_date,
    p.account_id
FROM portfolio.open_positions p
CROSS JOIN latest_date ld
WHERE p.report_date = ld.max_date
ORDER BY ABS(p.position_value) DESC;

-- Options Activity Summary
-- Summary of option exercises, expiries and assignments
CREATE OR REPLACE VIEW portfolio.options_activity_summary AS
SELECT 
    DATE_TRUNC('month', event_date) as month,
    event_type,
    underlying_symbol,
    call_put,
    COUNT(*) as event_count,
    SUM(quantity) as total_quantity,
    SUM(net_amount) as total_net_amount,
    AVG(strike) as avg_strike,
    MIN(event_date) as first_event,
    MAX(event_date) as last_event
FROM portfolio.exercises_expiries
GROUP BY DATE_TRUNC('month', event_date), event_type, underlying_symbol, call_put
ORDER BY month DESC, event_type, underlying_symbol;

-- ALM Reconciliation View
-- Core ALM formula: Opening NAV + Deposits - Withdrawals + Trading P&L - Commissions - Fees + Interest = Closing NAV
CREATE OR REPLACE VIEW portfolio.alm_reconciliation AS
SELECT 
    n.report_date,
    n.account_id,
    n.opening_nav,
    n.closing_nav,
    n.change_in_nav,
    
    -- From NAV data
    n.change_in_position_value as nav_position_change,
    n.cash_changes as nav_cash_change,
    
    -- From cash transactions (same day) - leverages your existing table
    COALESCE(ct.deposits, 0) as deposits,
    COALESCE(ct.withdrawals, 0) as withdrawals, 
    COALESCE(ct.interest, 0) as interest,
    COALESCE(ct.fees, 0) as fees,
    COALESCE(ct.commissions, 0) as commissions,
    
    -- From exercises/expiries (same day)
    COALESCE(ee.total_proceeds, 0) as exercise_proceeds,
    COALESCE(ee.total_commission, 0) as exercise_commissions,
    
    -- ALM calculation
    (n.opening_nav + 
     COALESCE(ct.deposits, 0) - 
     COALESCE(ct.withdrawals, 0) + 
     COALESCE(n.realized_pnl, 0) - 
     COALESCE(ct.commissions, 0) - 
     COALESCE(ct.fees, 0) + 
     COALESCE(ct.interest, 0) +
     COALESCE(ee.total_proceeds, 0) -
     COALESCE(ee.total_commission, 0)) as calculated_closing_nav,
     
    -- Reconciliation difference
    (n.closing_nav - 
     (n.opening_nav + 
      COALESCE(ct.deposits, 0) - 
      COALESCE(ct.withdrawals, 0) + 
      COALESCE(n.realized_pnl, 0) - 
      COALESCE(ct.commissions, 0) - 
      COALESCE(ct.fees, 0) + 
      COALESCE(ct.interest, 0) +
      COALESCE(ee.total_proceeds, 0) -
      COALESCE(ee.total_commission, 0))) as reconciliation_difference
      
FROM portfolio.nav_snapshots n
LEFT JOIN (
    -- Aggregate cash transactions by date using your existing table
    SELECT 
        transaction_date,
        SUM(CASE WHEN category = 'DEPOSIT' THEN amount ELSE 0 END) as deposits,
        SUM(CASE WHEN category = 'WITHDRAWAL' THEN ABS(amount) ELSE 0 END) as withdrawals,
        SUM(CASE WHEN category IN ('INTEREST_PAID', 'INTEREST_RECEIVED') THEN amount ELSE 0 END) as interest,
        SUM(CASE WHEN category = 'FEE' THEN ABS(amount) ELSE 0 END) as fees,
        SUM(CASE WHEN category = 'COMMISSION_ADJ' THEN ABS(amount) ELSE 0 END) as commissions
    FROM portfolio.cash_transactions
    GROUP BY transaction_date
) ct ON n.report_date = ct.transaction_date
LEFT JOIN (
    -- Aggregate exercises/expiries by date
    SELECT 
        event_date,
        SUM(proceeds) as total_proceeds,
        SUM(commission) as total_commission
    FROM portfolio.exercises_expiries
    GROUP BY event_date
) ee ON n.report_date = ee.event_date
ORDER BY n.report_date DESC;

COMMENT ON VIEW portfolio.daily_nav_movement IS 'Daily NAV changes with breakdown of contributing factors';
COMMENT ON VIEW portfolio.current_positions_summary IS 'Latest position snapshot with key metrics';
COMMENT ON VIEW portfolio.options_activity_summary IS 'Monthly summary of option exercises, expiries and assignments';