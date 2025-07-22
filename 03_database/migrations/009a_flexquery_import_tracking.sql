-- FlexQuery Import Tracking Table (Part 1/4)
-- Creates the core import tracking table that other tables reference

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

-- Import tracking indexes
CREATE INDEX IF NOT EXISTS idx_flexquery_imports_type ON portfolio.flexquery_imports(import_type);
CREATE INDEX IF NOT EXISTS idx_flexquery_imports_date ON portfolio.flexquery_imports(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_flexquery_imports_status ON portfolio.flexquery_imports(import_status);
CREATE INDEX IF NOT EXISTS idx_flexquery_imports_account ON portfolio.flexquery_imports(account_id);

-- Add flexquery_import_id columns to existing tables
-- These tables were created in migration 008_cash_transactions_interest.sql
ALTER TABLE portfolio.cash_transactions 
ADD COLUMN IF NOT EXISTS flexquery_import_id UUID REFERENCES portfolio.flexquery_imports(import_id);

ALTER TABLE portfolio.interest_accruals 
ADD COLUMN IF NOT EXISTS flexquery_import_id UUID REFERENCES portfolio.flexquery_imports(import_id);

COMMENT ON TABLE portfolio.flexquery_imports IS 'Import tracking and audit log for all FlexQuery imports';