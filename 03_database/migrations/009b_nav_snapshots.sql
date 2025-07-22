-- NAV Snapshots Table (Part 2/4)
-- Creates the NAV snapshots table for daily net asset value tracking

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

-- NAV Snapshots indexes
CREATE INDEX IF NOT EXISTS idx_nav_snapshots_date ON portfolio.nav_snapshots(report_date DESC);
CREATE INDEX IF NOT EXISTS idx_nav_snapshots_account ON portfolio.nav_snapshots(account_id);
CREATE INDEX IF NOT EXISTS idx_nav_snapshots_period ON portfolio.nav_snapshots(period);
CREATE INDEX IF NOT EXISTS idx_nav_snapshots_import ON portfolio.nav_snapshots(flexquery_import_id);

-- Triggers for updated_at timestamps
CREATE TRIGGER update_nav_snapshots_timestamp
    BEFORE UPDATE ON portfolio.nav_snapshots
    FOR EACH ROW EXECUTE FUNCTION portfolio.update_updated_at();

COMMENT ON TABLE portfolio.nav_snapshots IS 'Daily NAV snapshots from IBKR NAV FlexQuery reports';