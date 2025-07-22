-- Master Trading Database - Phase 1: Data Integrity & Constraints
-- This migration adds missing constraints and creates the matched_trades infrastructure
-- Run with: psql -U info -d fntx_trading -f 01_data_integrity_phase1.sql

BEGIN;

-- 1. Add versioning columns to trades table for audit trail
ALTER TABLE trading.trades 
ADD COLUMN IF NOT EXISTS version_id BIGSERIAL,
ADD COLUMN IF NOT EXISTS valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS valid_to TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS modified_by VARCHAR(100) DEFAULT CURRENT_USER;

-- 2. Create trades history table for versioning
CREATE TABLE IF NOT EXISTS trading.trades_history (
    LIKE trading.trades INCLUDING ALL,
    history_id BIGSERIAL PRIMARY KEY,
    history_action VARCHAR(10) NOT NULL,
    history_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Add composite unique constraint to prevent duplicate trades
-- First, let's check for existing duplicates
DO $$
DECLARE
    duplicate_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO duplicate_count
    FROM (
        SELECT ibkr_order_id, entry_time, COUNT(*) as cnt
        FROM trading.trades
        WHERE ibkr_order_id IS NOT NULL
        GROUP BY ibkr_order_id, entry_time
        HAVING COUNT(*) > 1
    ) dupes;
    
    IF duplicate_count > 0 THEN
        RAISE NOTICE 'Found % duplicate order groups. Please resolve before adding constraint.', duplicate_count;
    ELSE
        -- Add constraint only if no duplicates
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint 
            WHERE conname = 'trades_ibkr_composite_unique'
        ) THEN
            ALTER TABLE trading.trades 
            ADD CONSTRAINT trades_ibkr_composite_unique 
            UNIQUE (ibkr_order_id, entry_time);
        END IF;
    END IF;
END $$;

-- 4. Create matched trades table for tracking opening/closing pairs
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

-- 5. Create import log table for deduplication
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

-- 6. Add missing indexes on trades table
CREATE INDEX IF NOT EXISTS idx_trades_expiration ON trading.trades(expiration);
CREATE INDEX IF NOT EXISTS idx_trades_strike ON trading.trades(strike_price);
CREATE INDEX IF NOT EXISTS idx_trades_updated ON trading.trades(updated_at DESC);

-- 7. Create trigger function for trade history
CREATE OR REPLACE FUNCTION trading.trades_history_trigger()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        -- Insert old version into history
        INSERT INTO trading.trades_history
        SELECT OLD.*, nextval('trading.trades_history_history_id_seq'), 
               TG_OP, NOW();
        
        -- Update versioning columns
        NEW.valid_from = NOW();
        NEW.modified_by = CURRENT_USER;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        -- Insert deleted record into history
        INSERT INTO trading.trades_history
        SELECT OLD.*, nextval('trading.trades_history_history_id_seq'), 
               TG_OP, NOW();
        RETURN OLD;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- 8. Attach history trigger to trades table
DROP TRIGGER IF EXISTS trades_history_trigger ON trading.trades;
CREATE TRIGGER trades_history_trigger
BEFORE UPDATE OR DELETE ON trading.trades
FOR EACH ROW EXECUTE FUNCTION trading.trades_history_trigger();

-- 9. Create view for trade matching candidates
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

-- 10. Add constraints to ensure data quality
ALTER TABLE trading.trades
ADD CONSTRAINT trades_entry_exit_check 
CHECK (exit_time IS NULL OR exit_time > entry_time);

-- 11. Create summary statistics view
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

COMMIT;

-- Verification queries
SELECT 'Trades table columns' as check_type, COUNT(*) as count 
FROM information_schema.columns 
WHERE table_schema = 'trading' AND table_name = 'trades'
UNION ALL
SELECT 'Matched trades table exists' as check_type, COUNT(*) as count
FROM information_schema.tables 
WHERE table_schema = 'trading' AND table_name = 'matched_trades'
UNION ALL
SELECT 'Import log table exists' as check_type, COUNT(*) as count
FROM information_schema.tables 
WHERE table_schema = 'trading' AND table_name = 'import_log';