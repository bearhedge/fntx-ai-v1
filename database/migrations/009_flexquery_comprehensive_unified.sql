-- Unified Comprehensive FlexQuery Import Schema
-- Builds on existing portfolio.cash_transactions and portfolio.interest_accruals
-- Adds NAV, positions, and exercises/expiries for complete ALM system

-- NAV Snapshots Table
-- Captures daily net asset value from NAV FlexQuery reports
CREATE TABLE IF NOT EXISTS portfolio.nav_snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Date and period information
    report_date DATE NOT NULL,
    from_date DATE NOT NULL,
    to_date DATE NOT NULL,
    period VARCHAR(20) NOT NULL, -- 'MTD', 'LBD', 'Custom'
    
    -- NAV components (all in base currency HKD)
    opening_nav DECIMAL(15,2),
    closing_nav DECIMAL(15,2),
    change_in_nav DECIMAL(15,2),
    
    -- Position value changes
    change_in_position_value DECIMAL(15,2),
    realized_pnl DECIMAL(15,2),
    unrealized_pnl DECIMAL(15,2),
    
    -- Cash components
    cash_balance DECIMAL(15,2),
    cash_changes DECIMAL(15,2),
    
    -- Account reference
    account_id VARCHAR(20) NOT NULL,
    base_currency VARCHAR(3) DEFAULT 'HKD',
    
    -- Import tracking
    flexquery_import_id UUID REFERENCES portfolio.flexquery_imports(import_id),
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    UNIQUE(report_date, account_id, period)
);

-- Open Positions Table  
-- Captures position snapshots from Open Positions FlexQuery
CREATE TABLE IF NOT EXISTS portfolio.open_positions (
    position_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Position identification
    symbol VARCHAR(50) NOT NULL,
    underlying_symbol VARCHAR(50),
    security_type VARCHAR(20) NOT NULL, -- 'STK', 'OPT', 'CASH', etc.
    
    -- Option details (for options)
    strike DECIMAL(12,4),
    expiry DATE,
    call_put VARCHAR(1), -- 'C' or 'P'
    multiplier INTEGER DEFAULT 1,
    
    -- Position details
    position DECIMAL(15,4) NOT NULL, -- Quantity held
    mark_price DECIMAL(12,4),
    position_value DECIMAL(15,2),
    
    -- Cost basis
    avg_cost DECIMAL(12,4),
    unrealized_pnl DECIMAL(15,2),
    pct_of_nav DECIMAL(8,4),
    
    -- Date information
    report_date DATE NOT NULL,
    value_date DATE,
    
    -- Account reference
    account_id VARCHAR(20) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Import tracking
    flexquery_import_id UUID REFERENCES portfolio.flexquery_imports(import_id),
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    UNIQUE(report_date, account_id, symbol, security_type, strike, expiry, call_put)
);

-- Exercises and Expiries Table
-- Captures option exercise and expiry events from Trades FlexQuery
CREATE TABLE IF NOT EXISTS portfolio.exercises_expiries (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Event identification
    event_type VARCHAR(20) NOT NULL, -- 'Exercise', 'Expiry', 'Assignment'
    symbol VARCHAR(50) NOT NULL,
    underlying_symbol VARCHAR(50),
    
    -- Option details
    strike DECIMAL(12,4) NOT NULL,
    expiry DATE NOT NULL,
    call_put VARCHAR(1) NOT NULL, -- 'C' or 'P'
    multiplier INTEGER DEFAULT 100,
    
    -- Event details
    quantity DECIMAL(15,4) NOT NULL,
    event_date DATE NOT NULL,
    event_time TIMESTAMP WITH TIME ZONE,
    
    -- Financial impact
    proceeds DECIMAL(15,2),
    commission DECIMAL(8,2),
    net_amount DECIMAL(15,2),
    
    -- References
    trade_id VARCHAR(50), -- Reference to original trade
    order_id VARCHAR(50),
    execution_id VARCHAR(50),
    
    -- Account reference
    account_id VARCHAR(20) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Import tracking
    flexquery_import_id UUID REFERENCES portfolio.flexquery_imports(import_id),
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    UNIQUE(event_date, account_id, symbol, strike, expiry, call_put, event_type, execution_id)
);

-- FlexQuery Import Tracking Table (must be created first due to foreign key references)
CREATE TABLE IF NOT EXISTS portfolio.flexquery_imports (
    import_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Import metadata
    import_type VARCHAR(50) NOT NULL, -- 'NAV_MTD', 'NAV_LBD', 'TRADES_MTD', etc.
    file_path TEXT NOT NULL,
    file_size BIGINT,
    file_hash VARCHAR(64), -- SHA-256 of file content
    
    -- FlexQuery metadata
    account_id VARCHAR(20) NOT NULL,
    query_name VARCHAR(100),
    from_date DATE,
    to_date DATE,
    period VARCHAR(20),
    when_generated TIMESTAMP WITH TIME ZONE,
    
    -- Import results
    records_processed INTEGER NOT NULL DEFAULT 0,
    records_inserted INTEGER NOT NULL DEFAULT 0,
    records_updated INTEGER NOT NULL DEFAULT 0,
    records_skipped INTEGER NOT NULL DEFAULT 0,
    
    -- Status tracking
    import_status VARCHAR(20) NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'
    error_message TEXT,
    processing_duration_ms INTEGER,
    
    -- Audit
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(50) DEFAULT 'system',
    
    -- Constraints
    UNIQUE(file_hash, import_type) -- Prevent duplicate imports of same file
);

-- Add foreign key constraint to existing cash_transactions (if not already present)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_cash_transactions_import'
    ) THEN
        ALTER TABLE portfolio.cash_transactions 
        ADD COLUMN flexquery_import_id UUID REFERENCES portfolio.flexquery_imports(import_id);
    END IF;
END $$;

-- Add foreign key constraint to existing interest_accruals (if not already present)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_interest_accruals_import'
    ) THEN
        ALTER TABLE portfolio.interest_accruals 
        ADD COLUMN flexquery_import_id UUID REFERENCES portfolio.flexquery_imports(import_id);
    END IF;
END $$;

-- Indexes for performance

-- NAV Snapshots indexes
CREATE INDEX idx_nav_snapshots_date ON portfolio.nav_snapshots(report_date DESC);
CREATE INDEX idx_nav_snapshots_account ON portfolio.nav_snapshots(account_id);
CREATE INDEX idx_nav_snapshots_period ON portfolio.nav_snapshots(period);
CREATE INDEX idx_nav_snapshots_import ON portfolio.nav_snapshots(flexquery_import_id);

-- Open Positions indexes
CREATE INDEX idx_open_positions_date ON portfolio.open_positions(report_date DESC);
CREATE INDEX idx_open_positions_symbol ON portfolio.open_positions(symbol);
CREATE INDEX idx_open_positions_account ON portfolio.open_positions(account_id);
CREATE INDEX idx_open_positions_type ON portfolio.open_positions(security_type);
CREATE INDEX idx_open_positions_expiry ON portfolio.open_positions(expiry);

-- Exercises/Expiries indexes
CREATE INDEX idx_exercises_expiries_date ON portfolio.exercises_expiries(event_date DESC);
CREATE INDEX idx_exercises_expiries_symbol ON portfolio.exercises_expiries(symbol);
CREATE INDEX idx_exercises_expiries_expiry ON portfolio.exercises_expiries(expiry);
CREATE INDEX idx_exercises_expiries_type ON portfolio.exercises_expiries(event_type);
CREATE INDEX idx_exercises_expiries_account ON portfolio.exercises_expiries(account_id);

-- Import tracking indexes
CREATE INDEX idx_flexquery_imports_type ON portfolio.flexquery_imports(import_type);
CREATE INDEX idx_flexquery_imports_date ON portfolio.flexquery_imports(started_at DESC);
CREATE INDEX idx_flexquery_imports_status ON portfolio.flexquery_imports(import_status);
CREATE INDEX idx_flexquery_imports_account ON portfolio.flexquery_imports(account_id);

-- Views for ALM reconciliation and reporting

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

-- Triggers for updated_at timestamps
CREATE TRIGGER update_nav_snapshots_timestamp
    BEFORE UPDATE ON portfolio.nav_snapshots
    FOR EACH ROW EXECUTE FUNCTION portfolio.update_updated_at();

-- Comments for documentation
COMMENT ON TABLE portfolio.nav_snapshots IS 'Daily NAV snapshots from IBKR NAV FlexQuery reports';
COMMENT ON TABLE portfolio.open_positions IS 'Position snapshots from IBKR Open Positions FlexQuery';
COMMENT ON TABLE portfolio.exercises_expiries IS 'Option exercise and expiry events from IBKR Trades FlexQuery';
COMMENT ON TABLE portfolio.flexquery_imports IS 'Import tracking and audit log for all FlexQuery imports';

COMMENT ON VIEW portfolio.daily_nav_movement IS 'Daily NAV changes with breakdown of contributing factors';
COMMENT ON VIEW portfolio.current_positions_summary IS 'Latest position snapshot with key metrics';
COMMENT ON VIEW portfolio.options_activity_summary IS 'Monthly summary of option exercises, expiries and assignments';
COMMENT ON VIEW portfolio.alm_reconciliation IS 'ALM reconciliation using core formula: Opening NAV + Deposits - Withdrawals + Trading P&L - Fees + Interest = Closing NAV';