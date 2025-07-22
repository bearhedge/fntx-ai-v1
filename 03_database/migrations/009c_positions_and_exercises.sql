-- Open Positions and Exercises/Expiries Tables (Part 3/4)
-- Creates tables for position snapshots and option events

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

-- Open Positions indexes
CREATE INDEX IF NOT EXISTS idx_open_positions_date ON portfolio.open_positions(report_date DESC);
CREATE INDEX IF NOT EXISTS idx_open_positions_symbol ON portfolio.open_positions(symbol);
CREATE INDEX IF NOT EXISTS idx_open_positions_account ON portfolio.open_positions(account_id);
CREATE INDEX IF NOT EXISTS idx_open_positions_type ON portfolio.open_positions(security_type);
CREATE INDEX IF NOT EXISTS idx_open_positions_expiry ON portfolio.open_positions(expiry);

-- Exercises/Expiries indexes
CREATE INDEX IF NOT EXISTS idx_exercises_expiries_date ON portfolio.exercises_expiries(event_date DESC);
CREATE INDEX IF NOT EXISTS idx_exercises_expiries_symbol ON portfolio.exercises_expiries(symbol);
CREATE INDEX IF NOT EXISTS idx_exercises_expiries_expiry ON portfolio.exercises_expiries(expiry);
CREATE INDEX IF NOT EXISTS idx_exercises_expiries_type ON portfolio.exercises_expiries(event_type);
CREATE INDEX IF NOT EXISTS idx_exercises_expiries_account ON portfolio.exercises_expiries(account_id);

COMMENT ON TABLE portfolio.open_positions IS 'Position snapshots from IBKR Open Positions FlexQuery';
COMMENT ON TABLE portfolio.exercises_expiries IS 'Option exercise and expiry events from IBKR Trades FlexQuery';