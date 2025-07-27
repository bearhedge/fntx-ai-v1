-- Add Flex Query support to trades schema
-- This migration adds fields for tracking Flex Query imports

-- Add columns for Flex Query tracking
ALTER TABLE trading.trades 
ADD COLUMN IF NOT EXISTS flex_query_data BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS csv_import BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS flex_trade_id VARCHAR(50),
ADD COLUMN IF NOT EXISTS raw_trade_data JSONB;

-- Add indexes for Flex Query fields
CREATE INDEX IF NOT EXISTS idx_trades_flex_query ON trading.trades(flex_query_data) WHERE flex_query_data = TRUE;
CREATE INDEX IF NOT EXISTS idx_trades_csv_import ON trading.trades(csv_import) WHERE csv_import = TRUE;
CREATE INDEX IF NOT EXISTS idx_trades_flex_trade_id ON trading.trades(flex_trade_id) WHERE flex_trade_id IS NOT NULL;

-- Create Flex Query import log table
CREATE TABLE IF NOT EXISTS trading.flex_query_imports (
    import_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    import_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    reference_code VARCHAR(50),
    query_id VARCHAR(50),
    period_start DATE,
    period_end DATE,
    trades_imported INTEGER DEFAULT 0,
    trades_skipped INTEGER DEFAULT 0,
    total_pnl DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed')),
    error_message TEXT,
    raw_xml TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create CSV import log table
CREATE TABLE IF NOT EXISTS trading.csv_imports (
    import_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    import_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    filename VARCHAR(255) NOT NULL,
    file_hash VARCHAR(64),
    trades_imported INTEGER DEFAULT 0,
    trades_skipped INTEGER DEFAULT 0,
    total_rows INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed')),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create trade sources view
CREATE OR REPLACE VIEW trading.trade_sources AS
SELECT 
    COUNT(*) FILTER (WHERE flex_query_data = TRUE) as flex_query_trades,
    COUNT(*) FILTER (WHERE csv_import = TRUE) as csv_import_trades,
    COUNT(*) FILTER (WHERE flex_query_data = FALSE AND csv_import = FALSE) as live_trades,
    COUNT(*) as total_trades,
    MIN(entry_time) as earliest_trade,
    MAX(entry_time) as latest_trade
FROM trading.trades;

-- Create complete trades view (matched pairs)
CREATE OR REPLACE VIEW trading.complete_trades AS
SELECT 
    trade_id,
    symbol,
    strike_price,
    option_type,
    expiration,
    quantity,
    entry_time,
    entry_price,
    entry_commission,
    exit_time,
    exit_price,
    exit_commission,
    realized_pnl,
    exit_reason,
    EXTRACT(EPOCH FROM (exit_time - entry_time))/3600 as holding_hours,
    CASE 
        WHEN realized_pnl > 0 THEN 'WIN'
        WHEN realized_pnl < 0 THEN 'LOSS'
        ELSE 'BREAKEVEN'
    END as trade_result,
    flex_query_data,
    csv_import
FROM trading.trades
WHERE status = 'closed' AND exit_time IS NOT NULL
ORDER BY entry_time DESC;

-- Add comment to trades table
COMMENT ON TABLE trading.trades IS 'Automated trade logging with support for Flex Query imports and CSV uploads';