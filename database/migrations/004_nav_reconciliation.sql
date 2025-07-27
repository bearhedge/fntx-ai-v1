-- NAV and Cash Movement Reconciliation Schema
-- Tracks daily NAV, withdrawals/deposits, and ensures everything balances

-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS portfolio;

-- Daily NAV Snapshots
-- Records opening and closing NAV for each trading day
CREATE TABLE IF NOT EXISTS portfolio.daily_nav_snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_date DATE NOT NULL UNIQUE,
    
    -- NAV Components
    opening_nav DECIMAL(15,2) NOT NULL,
    closing_nav DECIMAL(15,2),
    
    -- Cash balances
    opening_cash DECIMAL(15,2) NOT NULL,
    closing_cash DECIMAL(15,2),
    
    -- Position values
    opening_positions_value DECIMAL(15,2) DEFAULT 0,
    closing_positions_value DECIMAL(15,2) DEFAULT 0,
    
    -- Daily changes
    trading_pnl DECIMAL(15,2) DEFAULT 0,
    commissions_paid DECIMAL(15,2) DEFAULT 0,
    interest_earned DECIMAL(15,2) DEFAULT 0,
    fees_charged DECIMAL(15,2) DEFAULT 0,
    
    -- Data source
    source VARCHAR(20) DEFAULT 'IBKR', -- 'IBKR', 'MANUAL', 'CALCULATED'
    
    -- Status
    is_reconciled BOOLEAN DEFAULT FALSE,
    reconciliation_notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_fetched_at TIMESTAMP WITH TIME ZONE
);

-- Cash Movements (Deposits/Withdrawals)
CREATE TABLE IF NOT EXISTS portfolio.cash_movements (
    movement_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    movement_date DATE NOT NULL,
    movement_time TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Movement details
    movement_type VARCHAR(20) NOT NULL CHECK (movement_type IN ('DEPOSIT', 'WITHDRAWAL', 'FEE', 'INTEREST', 'DIVIDEND')),
    amount DECIMAL(15,2) NOT NULL, -- Positive for deposits, negative for withdrawals
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Reference information
    ibkr_transaction_id VARCHAR(50),
    external_reference VARCHAR(100),
    destination_type VARCHAR(20) CHECK (destination_type IN ('BANK', 'CRYPTO', 'CHECK', 'WIRE', 'ACH')),
    destination_details TEXT,
    
    -- Status tracking
    status VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'COMPLETED', 'FAILED', 'CANCELLED')),
    settlement_date DATE,
    
    -- Reconciliation
    is_reconciled BOOLEAN DEFAULT FALSE,
    reconciled_in_nav_date DATE,
    
    -- Notes
    description TEXT,
    notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- NAV Reconciliation Records
-- Ensures daily NAV changes are fully explained
CREATE TABLE IF NOT EXISTS portfolio.nav_reconciliation (
    reconciliation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reconciliation_date DATE NOT NULL UNIQUE,
    
    -- Starting point
    opening_nav DECIMAL(15,2) NOT NULL,
    
    -- Changes during the day
    trading_pnl DECIMAL(15,2) DEFAULT 0,
    deposits DECIMAL(15,2) DEFAULT 0,
    withdrawals DECIMAL(15,2) DEFAULT 0,
    fees DECIMAL(15,2) DEFAULT 0,
    interest DECIMAL(15,2) DEFAULT 0,
    other_adjustments DECIMAL(15,2) DEFAULT 0,
    
    -- Expected vs Actual
    calculated_closing_nav DECIMAL(15,2) GENERATED ALWAYS AS (
        opening_nav + trading_pnl + deposits - withdrawals - fees + interest + other_adjustments
    ) STORED,
    actual_closing_nav DECIMAL(15,2),
    discrepancy DECIMAL(15,2) GENERATED ALWAYS AS (
        actual_closing_nav - (opening_nav + trading_pnl + deposits - withdrawals - fees + interest + other_adjustments)
    ) STORED,
    
    -- Reconciliation status
    is_balanced BOOLEAN GENERATED ALWAYS AS (
        ABS(actual_closing_nav - (opening_nav + trading_pnl + deposits - withdrawals - fees + interest + other_adjustments)) < 0.01
    ) STORED,
    manual_adjustment DECIMAL(15,2) DEFAULT 0,
    adjustment_reason TEXT,
    
    -- Audit
    reconciled_by VARCHAR(100),
    reconciled_at TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Account Statement Records (from IBKR Flex Query)
CREATE TABLE IF NOT EXISTS portfolio.account_statements (
    statement_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    statement_date DATE NOT NULL,
    account_id VARCHAR(20) NOT NULL,
    
    -- Balance information
    starting_cash DECIMAL(15,2),
    ending_cash DECIMAL(15,2),
    starting_nav DECIMAL(15,2),
    ending_nav DECIMAL(15,2),
    
    -- Daily activity
    trades_count INTEGER DEFAULT 0,
    deposits_total DECIMAL(15,2) DEFAULT 0,
    withdrawals_total DECIMAL(15,2) DEFAULT 0,
    commissions_total DECIMAL(15,2) DEFAULT 0,
    realized_pnl DECIMAL(15,2) DEFAULT 0,
    
    -- Raw data storage
    flex_query_xml TEXT,
    
    -- Processing status
    is_processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(statement_date, account_id)
);

-- Indexes for performance
CREATE INDEX idx_nav_snapshots_date ON portfolio.daily_nav_snapshots(snapshot_date DESC);
CREATE INDEX idx_cash_movements_date ON portfolio.cash_movements(movement_date DESC);
CREATE INDEX idx_cash_movements_status ON portfolio.cash_movements(status);
CREATE INDEX idx_cash_movements_type ON portfolio.cash_movements(movement_type);
CREATE INDEX idx_reconciliation_date ON portfolio.nav_reconciliation(reconciliation_date DESC);
CREATE INDEX idx_reconciliation_balanced ON portfolio.nav_reconciliation(is_balanced);
CREATE INDEX idx_statements_date ON portfolio.account_statements(statement_date DESC);
CREATE INDEX idx_statements_processed ON portfolio.account_statements(is_processed);

-- Views for easy reporting

-- Current NAV Status
CREATE OR REPLACE VIEW portfolio.current_nav_status AS
SELECT 
    snapshot_date,
    closing_nav as nav,
    closing_cash as cash,
    closing_positions_value as positions_value,
    trading_pnl,
    is_reconciled
FROM portfolio.daily_nav_snapshots
ORDER BY snapshot_date DESC
LIMIT 1;

-- Monthly NAV Summary
CREATE OR REPLACE VIEW portfolio.monthly_nav_summary AS
SELECT 
    DATE_TRUNC('month', snapshot_date) as month,
    MIN(opening_nav) as month_opening_nav,
    MAX(closing_nav) as month_closing_nav,
    MAX(closing_nav) - MIN(opening_nav) as month_change,
    SUM(trading_pnl) as total_trading_pnl,
    COUNT(*) as trading_days
FROM portfolio.daily_nav_snapshots
WHERE closing_nav IS NOT NULL
GROUP BY DATE_TRUNC('month', snapshot_date)
ORDER BY month DESC;

-- Pending Cash Movements
CREATE OR REPLACE VIEW portfolio.pending_cash_movements AS
SELECT 
    movement_id,
    movement_date,
    movement_type,
    amount,
    destination_type,
    destination_details,
    status,
    settlement_date
FROM portfolio.cash_movements
WHERE status = 'PENDING'
ORDER BY movement_date DESC;

-- Reconciliation Dashboard
CREATE OR REPLACE VIEW portfolio.reconciliation_dashboard AS
SELECT 
    r.reconciliation_date,
    r.opening_nav,
    r.actual_closing_nav,
    r.calculated_closing_nav,
    r.discrepancy,
    r.is_balanced,
    r.trading_pnl,
    r.deposits,
    r.withdrawals,
    CASE 
        WHEN r.is_balanced THEN 'Balanced'
        WHEN r.discrepancy IS NULL THEN 'Pending'
        ELSE 'Discrepancy'
    END as status
FROM portfolio.nav_reconciliation r
ORDER BY r.reconciliation_date DESC;

-- Triggers

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION portfolio.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_nav_snapshots_timestamp
    BEFORE UPDATE ON portfolio.daily_nav_snapshots
    FOR EACH ROW EXECUTE FUNCTION portfolio.update_updated_at();

CREATE TRIGGER update_cash_movements_timestamp
    BEFORE UPDATE ON portfolio.cash_movements
    FOR EACH ROW EXECUTE FUNCTION portfolio.update_updated_at();

CREATE TRIGGER update_reconciliation_timestamp
    BEFORE UPDATE ON portfolio.nav_reconciliation
    FOR EACH ROW EXECUTE FUNCTION portfolio.update_updated_at();

-- Helper functions

-- Function to create daily reconciliation record
CREATE OR REPLACE FUNCTION portfolio.create_daily_reconciliation(p_date DATE)
RETURNS UUID AS $$
DECLARE
    v_reconciliation_id UUID;
    v_opening_nav DECIMAL(15,2);
    v_closing_nav DECIMAL(15,2);
    v_trading_pnl DECIMAL(15,2);
    v_deposits DECIMAL(15,2);
    v_withdrawals DECIMAL(15,2);
BEGIN
    -- Get NAV data
    SELECT opening_nav, closing_nav, trading_pnl
    INTO v_opening_nav, v_closing_nav, v_trading_pnl
    FROM portfolio.daily_nav_snapshots
    WHERE snapshot_date = p_date;
    
    -- Get cash movements
    SELECT 
        COALESCE(SUM(CASE WHEN movement_type = 'DEPOSIT' THEN amount ELSE 0 END), 0),
        COALESCE(SUM(CASE WHEN movement_type = 'WITHDRAWAL' THEN ABS(amount) ELSE 0 END), 0)
    INTO v_deposits, v_withdrawals
    FROM portfolio.cash_movements
    WHERE movement_date = p_date AND status = 'COMPLETED';
    
    -- Create reconciliation record
    INSERT INTO portfolio.nav_reconciliation (
        reconciliation_date,
        opening_nav,
        actual_closing_nav,
        trading_pnl,
        deposits,
        withdrawals
    ) VALUES (
        p_date,
        v_opening_nav,
        v_closing_nav,
        v_trading_pnl,
        v_deposits,
        v_withdrawals
    ) RETURNING reconciliation_id INTO v_reconciliation_id;
    
    RETURN v_reconciliation_id;
END;
$$ LANGUAGE plpgsql;

-- Comments
COMMENT ON TABLE portfolio.daily_nav_snapshots IS 'Daily NAV tracking with opening/closing balances';
COMMENT ON TABLE portfolio.cash_movements IS 'All cash deposits, withdrawals, and transfers';
COMMENT ON TABLE portfolio.nav_reconciliation IS 'Daily reconciliation ensuring NAV changes are fully explained';
COMMENT ON TABLE portfolio.account_statements IS 'Raw account statements from IBKR Flex Query';