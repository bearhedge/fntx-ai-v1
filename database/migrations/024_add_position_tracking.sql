-- Add position tracking for options assignments
-- This enables accurate NAV calculation through position lifecycle

-- Create position tracking table
CREATE TABLE IF NOT EXISTS alm_reporting.stock_positions (
    position_id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    quantity INTEGER NOT NULL, -- Negative for short positions
    entry_price DECIMAL(15,4) NOT NULL,
    entry_date TIMESTAMP NOT NULL,
    entry_transaction_id VARCHAR(50) UNIQUE NOT NULL,
    exit_price DECIMAL(15,4),
    exit_date TIMESTAMP,
    exit_transaction_id VARCHAR(50),
    realized_pnl_hkd DECIMAL(15,2),
    status VARCHAR(20) DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'CLOSED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add indexes for performance
CREATE INDEX idx_positions_symbol ON alm_reporting.stock_positions(symbol);
CREATE INDEX idx_positions_status ON alm_reporting.stock_positions(status);
CREATE INDEX idx_positions_entry_date ON alm_reporting.stock_positions(entry_date);

-- Add position tracking columns to daily summary
ALTER TABLE alm_reporting.daily_summary 
ADD COLUMN IF NOT EXISTS open_positions_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS open_positions_value_hkd DECIMAL(15,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS unrealized_pnl_hkd DECIMAL(15,2) DEFAULT 0;

-- Add assignment tracking to chronological events
ALTER TABLE alm_reporting.chronological_events
ADD COLUMN IF NOT EXISTS position_id INTEGER REFERENCES alm_reporting.stock_positions(position_id),
ADD COLUMN IF NOT EXISTS is_assignment BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS is_position_close BOOLEAN DEFAULT FALSE;

-- Create view for current positions
CREATE OR REPLACE VIEW alm_reporting.current_positions AS
SELECT 
    sp.position_id,
    sp.symbol,
    sp.quantity,
    sp.entry_price,
    sp.entry_date,
    sp.entry_transaction_id,
    -- Calculate current value in HKD (would need market price)
    sp.quantity * sp.entry_price * 7.8472 as position_value_hkd,
    sp.created_at
FROM alm_reporting.stock_positions sp
WHERE sp.status = 'OPEN'
ORDER BY sp.entry_date DESC;

-- Create view for position history
CREATE OR REPLACE VIEW alm_reporting.position_history AS
SELECT 
    sp.position_id,
    sp.symbol,
    sp.quantity,
    sp.entry_price,
    sp.entry_date,
    sp.exit_price,
    sp.exit_date,
    sp.realized_pnl_hkd,
    sp.status,
    -- Calculate holding period
    CASE 
        WHEN sp.exit_date IS NOT NULL THEN 
            sp.exit_date - sp.entry_date
        ELSE 
            CURRENT_TIMESTAMP - sp.entry_date
    END as holding_period
FROM alm_reporting.stock_positions sp
ORDER BY sp.entry_date DESC;

-- Add comments for documentation
COMMENT ON TABLE alm_reporting.stock_positions IS 'Tracks stock positions created by options assignments and their lifecycle';
COMMENT ON COLUMN alm_reporting.stock_positions.quantity IS 'Position size - negative for short positions';
COMMENT ON COLUMN alm_reporting.stock_positions.entry_price IS 'Price at which position was created (assignment price)';
COMMENT ON COLUMN alm_reporting.stock_positions.realized_pnl_hkd IS 'P&L realized when position is closed, in HKD';

-- Function to calculate NAV including positions
CREATE OR REPLACE FUNCTION alm_reporting.calculate_nav_with_positions(
    p_date DATE,
    p_market_price DECIMAL DEFAULT NULL
) RETURNS DECIMAL AS $$
DECLARE
    v_cash_nav DECIMAL;
    v_position_value DECIMAL;
    v_total_nav DECIMAL;
BEGIN
    -- Get cash NAV from daily summary
    SELECT closing_nav_hkd INTO v_cash_nav
    FROM alm_reporting.daily_summary
    WHERE summary_date = p_date;
    
    -- Calculate open position values
    -- In production, this would use real market prices
    SELECT COALESCE(SUM(
        CASE 
            WHEN quantity < 0 THEN -- Short position is a liability
                quantity * COALESCE(p_market_price, entry_price) * 7.8472
            ELSE -- Long position is an asset
                quantity * COALESCE(p_market_price, entry_price) * 7.8472
        END
    ), 0) INTO v_position_value
    FROM alm_reporting.stock_positions
    WHERE status = 'OPEN'
    AND entry_date::date <= p_date;
    
    -- Total NAV = Cash + Positions
    v_total_nav := v_cash_nav + v_position_value;
    
    RETURN v_total_nav;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION alm_reporting.calculate_nav_with_positions IS 'Calculates total NAV including open stock positions';