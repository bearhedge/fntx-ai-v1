-- Master Trading Database - Phase 1: Data Integrity & Constraints (v2)
-- This version creates new tables that can be owned by current user
-- Run with: psql -U info -d fntx_trading -f 01_data_integrity_phase1_v2.sql

BEGIN;

-- 1. Create matched trades table for tracking opening/closing pairs
CREATE TABLE IF NOT EXISTS trading.matched_trades (
    match_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    opening_trade_id UUID NOT NULL REFERENCES trading.trades(trade_id),
    closing_trade_id UUID NOT NULL REFERENCES trading.trades(trade_id),
    match_method VARCHAR(20) NOT NULL CHECK (match_method IN ('FIFO', 'LIFO', 'SPECIFIC', 'AUTO')),
    quantity_matched INTEGER NOT NULL CHECK (quantity_matched > 0),
    opening_price NUMERIC(10,4) NOT NULL,
    closing_price NUMERIC(10,4) NOT NULL,
    realized_pnl NUMERIC(12,2) NOT NULL,
    commissions_total NUMERIC(10,2) DEFAULT 0,
    match_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT CURRENT_USER,
    notes TEXT,
    CONSTRAINT matched_trades_unique UNIQUE(opening_trade_id, closing_trade_id),
    CONSTRAINT matched_trades_different CHECK (opening_trade_id != closing_trade_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_matched_trades_opening ON trading.matched_trades(opening_trade_id);
CREATE INDEX IF NOT EXISTS idx_matched_trades_closing ON trading.matched_trades(closing_trade_id);
CREATE INDEX IF NOT EXISTS idx_matched_trades_timestamp ON trading.matched_trades(match_timestamp DESC);

-- 2. Create import log table for deduplication
CREATE TABLE IF NOT EXISTS trading.import_log (
    import_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type VARCHAR(20) NOT NULL CHECK (source_type IN ('FLEX_QUERY', 'API', 'MANUAL', 'CSV')),
    source_id VARCHAR(100) NOT NULL,
    source_filename VARCHAR(255),
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    import_hash VARCHAR(64) NOT NULL, -- SHA256 hash of import data
    record_count INTEGER DEFAULT 0,
    trades_imported INTEGER DEFAULT 0,
    trades_updated INTEGER DEFAULT 0,
    trades_skipped INTEGER DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'PARTIAL')),
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT CURRENT_USER,
    metadata JSONB DEFAULT '{}',
    CONSTRAINT import_log_unique UNIQUE(source_type, source_id, period_start, period_end)
);

-- Create indexes for import log
CREATE INDEX IF NOT EXISTS idx_import_log_status ON trading.import_log(status);
CREATE INDEX IF NOT EXISTS idx_import_log_dates ON trading.import_log(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_import_log_created ON trading.import_log(created_at DESC);

-- 3. Create trades_audit table for tracking changes (since we can't modify trades table)
CREATE TABLE IF NOT EXISTS trading.trades_audit (
    audit_id BIGSERIAL PRIMARY KEY,
    trade_id UUID NOT NULL,
    action VARCHAR(10) NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    changed_fields JSONB,
    old_values JSONB,
    new_values JSONB,
    change_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    changed_by VARCHAR(100) DEFAULT CURRENT_USER,
    change_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_trades_audit_trade_id ON trading.trades_audit(trade_id);
CREATE INDEX IF NOT EXISTS idx_trades_audit_timestamp ON trading.trades_audit(change_timestamp DESC);

-- 4. Create view for trade matching candidates
CREATE OR REPLACE VIEW trading.unmatched_trades AS
SELECT 
    t.trade_id,
    t.symbol,
    t.strike_price,
    t.option_type,
    t.expiration,
    t.quantity,
    t.entry_time,
    t.exit_time,
    t.status,
    CASE 
        WHEN t.quantity < 0 THEN 'SELL'
        ELSE 'BUY'
    END as trade_direction,
    NOT EXISTS (
        SELECT 1 FROM trading.matched_trades mt
        WHERE mt.opening_trade_id = t.trade_id 
           OR mt.closing_trade_id = t.trade_id
    ) as is_unmatched
FROM trading.trades t
WHERE t.status = 'closed';

-- 5. Create summary statistics view
CREATE OR REPLACE VIEW trading.trade_statistics AS
SELECT 
    DATE(entry_time) as trade_date,
    COUNT(*) as total_trades,
    COUNT(CASE WHEN status = 'open' THEN 1 END) as open_trades,
    COUNT(CASE WHEN status = 'closed' THEN 1 END) as closed_trades,
    COUNT(CASE WHEN realized_pnl > 0 THEN 1 END) as winning_trades,
    COUNT(CASE WHEN realized_pnl < 0 THEN 1 END) as losing_trades,
    SUM(CASE WHEN status = 'closed' THEN realized_pnl ELSE 0 END) as total_pnl,
    AVG(CASE WHEN status = 'closed' THEN realized_pnl END) as avg_pnl
FROM trading.trades
GROUP BY DATE(entry_time)
ORDER BY trade_date DESC;

-- 6. Create duplicate detection view
CREATE OR REPLACE VIEW trading.duplicate_trade_check AS
SELECT 
    ibkr_order_id,
    entry_time,
    COUNT(*) as duplicate_count,
    STRING_AGG(trade_id::TEXT, ', ') as trade_ids,
    MIN(created_at) as first_created,
    MAX(created_at) as last_created
FROM trading.trades
WHERE ibkr_order_id IS NOT NULL
GROUP BY ibkr_order_id, entry_time
HAVING COUNT(*) > 1
ORDER BY COUNT(*) DESC, entry_time DESC;

-- 7. Create trade audit function that can be called manually
CREATE OR REPLACE FUNCTION trading.audit_trade_change(
    p_trade_id UUID,
    p_action VARCHAR(10),
    p_old_values JSONB DEFAULT NULL,
    p_new_values JSONB DEFAULT NULL,
    p_changed_fields JSONB DEFAULT NULL,
    p_reason TEXT DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    INSERT INTO trading.trades_audit (
        trade_id, action, old_values, new_values, 
        changed_fields, change_reason
    ) VALUES (
        p_trade_id, p_action, p_old_values, p_new_values,
        p_changed_fields, p_reason
    );
END;
$$ LANGUAGE plpgsql;

-- 8. Create matched trades summary view
CREATE OR REPLACE VIEW trading.matched_trades_summary AS
SELECT 
    mt.match_id,
    mt.match_timestamp,
    -- Opening trade details
    ot.symbol,
    ot.strike_price,
    ot.option_type,
    ot.expiration,
    ot.entry_time as opening_time,
    mt.opening_price,
    -- Closing trade details
    ct.exit_time as closing_time,
    mt.closing_price,
    -- Match details
    mt.quantity_matched,
    mt.realized_pnl,
    mt.commissions_total,
    mt.match_method,
    -- Duration
    EXTRACT(EPOCH FROM (ct.exit_time - ot.entry_time))/3600 as holding_hours
FROM trading.matched_trades mt
JOIN trading.trades ot ON mt.opening_trade_id = ot.trade_id
JOIN trading.trades ct ON mt.closing_trade_id = ct.trade_id
ORDER BY mt.match_timestamp DESC;

COMMIT;

-- Verification queries
SELECT 'Matched trades table' as check_type, 
       CASE WHEN COUNT(*) > 0 THEN 'Created' ELSE 'Failed' END as status
FROM information_schema.tables 
WHERE table_schema = 'trading' AND table_name = 'matched_trades'
UNION ALL
SELECT 'Import log table' as check_type,
       CASE WHEN COUNT(*) > 0 THEN 'Created' ELSE 'Failed' END as status
FROM information_schema.tables 
WHERE table_schema = 'trading' AND table_name = 'import_log'
UNION ALL
SELECT 'Trades audit table' as check_type,
       CASE WHEN COUNT(*) > 0 THEN 'Created' ELSE 'Failed' END as status
FROM information_schema.tables 
WHERE table_schema = 'trading' AND table_name = 'trades_audit'
UNION ALL
SELECT 'Views created' as check_type,
       COUNT(*)::TEXT || ' views' as status
FROM information_schema.views
WHERE table_schema = 'trading' 
  AND table_name IN ('unmatched_trades', 'trade_statistics', 'duplicate_trade_check', 'matched_trades_summary');