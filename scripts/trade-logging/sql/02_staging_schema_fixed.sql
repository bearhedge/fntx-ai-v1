-- Master Trading Database - Phase 2: Staging Schema & Validation (Fixed)
-- This creates the staging infrastructure for safe data imports
-- Run with: psql -U info -d fntx_trading -f 02_staging_schema_fixed.sql

BEGIN;

-- Create staging schema
CREATE SCHEMA IF NOT EXISTS staging;

-- 1. Staging table for Flex Query imports
CREATE TABLE IF NOT EXISTS staging.flex_trades (
    staging_id BIGSERIAL PRIMARY KEY,
    import_id UUID NOT NULL,
    -- Raw IBKR fields
    ibkr_trade_id VARCHAR(50),
    ibkr_order_id VARCHAR(50),
    ibkr_exec_id VARCHAR(50),
    ibkr_perm_id VARCHAR(50),
    account_id VARCHAR(20),
    symbol VARCHAR(20),
    underlying VARCHAR(20),
    asset_category VARCHAR(20),
    sub_category VARCHAR(20),
    trade_date DATE,
    trade_time TIME,
    settle_date DATE,
    quantity INTEGER,
    price NUMERIC(12,6),
    proceeds NUMERIC(15,2),
    commission NUMERIC(10,2),
    fees NUMERIC(10,2),
    realized_pnl NUMERIC(15,2),
    fx_rate NUMERIC(10,6),
    -- Options specific
    strike NUMERIC(10,2),
    expiry DATE,
    put_call VARCHAR(4),
    -- Processing fields
    raw_data JSONB NOT NULL,
    validation_status VARCHAR(20) DEFAULT 'PENDING',
    validation_errors JSONB,
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMPTZ,
    matched_trade_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for staging
CREATE INDEX idx_staging_flex_import_id ON staging.flex_trades(import_id);
CREATE INDEX idx_staging_flex_processed ON staging.flex_trades(processed);
CREATE INDEX idx_staging_flex_symbol_date ON staging.flex_trades(symbol, trade_date);

-- 2. Validation rules table
CREATE TABLE IF NOT EXISTS staging.validation_rules (
    rule_id SERIAL PRIMARY KEY,
    rule_name VARCHAR(100) NOT NULL UNIQUE,
    rule_category VARCHAR(50) NOT NULL,
    rule_sql TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('ERROR', 'WARNING', 'INFO')),
    error_message TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Validation results table
CREATE TABLE IF NOT EXISTS staging.validation_results (
    result_id BIGSERIAL PRIMARY KEY,
    import_id UUID NOT NULL,
    staging_id BIGINT REFERENCES staging.flex_trades(staging_id),
    rule_id INTEGER REFERENCES staging.validation_rules(rule_id),
    severity VARCHAR(20) NOT NULL,
    error_message TEXT,
    error_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_validation_results_import ON staging.validation_results(import_id);
CREATE INDEX idx_validation_results_staging ON staging.validation_results(staging_id);

-- 4. Import mapping table for tracking staging->production mappings
CREATE TABLE IF NOT EXISTS staging.import_mappings (
    mapping_id BIGSERIAL PRIMARY KEY,
    import_id UUID NOT NULL,
    staging_id BIGINT NOT NULL REFERENCES staging.flex_trades(staging_id),
    trade_id UUID REFERENCES trading.trades(trade_id),
    action_taken VARCHAR(20) NOT NULL CHECK (action_taken IN ('INSERTED', 'UPDATED', 'SKIPPED', 'ERROR')),
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_import_mappings_import ON staging.import_mappings(import_id);
CREATE INDEX idx_import_mappings_trade ON staging.import_mappings(trade_id);

-- 5. Insert default validation rules
INSERT INTO staging.validation_rules (rule_name, rule_category, rule_sql, severity, error_message) VALUES
-- Required fields validation
('required_ibkr_ids', 'completeness', 
 'SELECT staging_id FROM staging.flex_trades WHERE import_id = $1 AND (ibkr_order_id IS NULL OR ibkr_trade_id IS NULL) AND NOT processed',
 'ERROR', 'Missing required IBKR identifiers'),

('required_trade_details', 'completeness',
 'SELECT staging_id FROM staging.flex_trades WHERE import_id = $1 AND (symbol IS NULL OR quantity IS NULL OR price IS NULL) AND NOT processed',
 'ERROR', 'Missing required trade details'),

-- Data quality validation
('invalid_quantity', 'data_quality',
 'SELECT staging_id FROM staging.flex_trades WHERE import_id = $1 AND quantity = 0 AND NOT processed',
 'ERROR', 'Trade quantity cannot be zero'),

('future_trade_date', 'data_quality',
 'SELECT staging_id FROM staging.flex_trades WHERE import_id = $1 AND trade_date > CURRENT_DATE AND NOT processed',
 'ERROR', 'Trade date cannot be in the future'),

('invalid_option_type', 'data_quality',
 'SELECT staging_id FROM staging.flex_trades WHERE import_id = $1 AND asset_category = ''OPT'' AND put_call NOT IN (''P'', ''PUT'', ''C'', ''CALL'') AND NOT processed',
 'ERROR', 'Invalid option type'),

-- Duplicate detection
('duplicate_in_staging', 'duplicates',
 'SELECT s1.staging_id FROM staging.flex_trades s1 WHERE s1.import_id = $1 AND EXISTS (SELECT 1 FROM staging.flex_trades s2 WHERE s2.import_id != s1.import_id AND s2.ibkr_trade_id = s1.ibkr_trade_id AND s2.processed = true) AND NOT s1.processed',
 'WARNING', 'Trade already exists in previous import'),

('duplicate_in_production', 'duplicates',
 'SELECT s.staging_id FROM staging.flex_trades s WHERE s.import_id = $1 AND EXISTS (SELECT 1 FROM trading.trades t WHERE t.ibkr_order_id::TEXT = s.ibkr_order_id) AND NOT s.processed',
 'WARNING', 'Trade already exists in production'),

-- Business rules
('spy_only', 'business_rules',
 'SELECT staging_id FROM staging.flex_trades WHERE import_id = $1 AND underlying != ''SPY'' AND NOT processed',
 'WARNING', 'Non-SPY trade detected'),

('options_only', 'business_rules',
 'SELECT staging_id FROM staging.flex_trades WHERE import_id = $1 AND asset_category NOT IN (''OPT'', ''FOP'') AND NOT processed',
 'INFO', 'Non-option trade detected')

ON CONFLICT (rule_name) DO UPDATE SET
    rule_sql = EXCLUDED.rule_sql,
    error_message = EXCLUDED.error_message,
    updated_at = NOW();

-- 6. Create staging summary view
CREATE OR REPLACE VIEW staging.import_summary AS
SELECT 
    i.import_id,
    i.source_type,
    i.period_start,
    i.period_end,
    i.status as import_status,
    i.created_at as import_date,
    COUNT(DISTINCT s.staging_id) as total_records,
    COUNT(DISTINCT s.staging_id) FILTER (WHERE s.processed) as processed_records,
    COUNT(DISTINCT s.staging_id) FILTER (WHERE s.validation_status = 'PASSED') as valid_records,
    COUNT(DISTINCT s.staging_id) FILTER (WHERE s.validation_status = 'FAILED') as failed_records,
    COUNT(DISTINCT v.result_id) FILTER (WHERE v.severity = 'ERROR') as error_count,
    COUNT(DISTINCT v.result_id) FILTER (WHERE v.severity = 'WARNING') as warning_count
FROM trading.import_log i
LEFT JOIN staging.flex_trades s ON i.import_id = s.import_id
LEFT JOIN staging.validation_results v ON i.import_id = v.import_id
GROUP BY i.import_id, i.source_type, i.period_start, i.period_end, i.status, i.created_at
ORDER BY i.created_at DESC;

-- 7. Create validation functions
CREATE OR REPLACE FUNCTION staging.validate_import(p_import_id UUID)
RETURNS TABLE(rule_name VARCHAR, severity VARCHAR, error_count BIGINT) AS $$
DECLARE
    v_rule RECORD;
    v_staging_record RECORD;
    v_count BIGINT;
BEGIN
    -- Clear previous validation results for this import
    DELETE FROM staging.validation_results WHERE import_id = p_import_id;
    
    -- Run each active validation rule
    FOR v_rule IN 
        SELECT rule_id, rule_name, rule_sql, severity, error_message 
        FROM staging.validation_rules 
        WHERE is_active = TRUE
        ORDER BY 
            CASE severity 
                WHEN 'ERROR' THEN 1 
                WHEN 'WARNING' THEN 2 
                ELSE 3 
            END
    LOOP
        -- Execute the validation query
        FOR v_staging_record IN 
            EXECUTE v_rule.rule_sql USING p_import_id
        LOOP
            INSERT INTO staging.validation_results (
                import_id, staging_id, rule_id, severity, error_message
            ) VALUES (
                p_import_id, v_staging_record.staging_id, v_rule.rule_id, v_rule.severity, v_rule.error_message
            );
        END LOOP;
    END LOOP;
    
    -- Update validation status in staging records
    UPDATE staging.flex_trades
    SET validation_status = CASE
        WHEN EXISTS (
            SELECT 1 FROM staging.validation_results vr 
            WHERE vr.staging_id = flex_trades.staging_id 
            AND vr.severity = 'ERROR'
        ) THEN 'FAILED'
        WHEN EXISTS (
            SELECT 1 FROM staging.validation_results vr 
            WHERE vr.staging_id = flex_trades.staging_id 
            AND vr.severity = 'WARNING'
        ) THEN 'WARNING'
        ELSE 'PASSED'
    END
    WHERE import_id = p_import_id;
    
    -- Return summary
    RETURN QUERY
    SELECT 
        r.rule_name,
        r.severity,
        COUNT(DISTINCT vr.staging_id)::BIGINT as error_count
    FROM staging.validation_results vr
    JOIN staging.validation_rules r ON vr.rule_id = r.rule_id
    WHERE vr.import_id = p_import_id
    GROUP BY r.rule_name, r.severity
    ORDER BY 
        CASE r.severity 
            WHEN 'ERROR' THEN 1 
            WHEN 'WARNING' THEN 2 
            ELSE 3 
        END,
        error_count DESC;
END;
$$ LANGUAGE plpgsql;

-- 8. Create function to clean old staging data
CREATE OR REPLACE FUNCTION staging.cleanup_old_imports(p_days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    v_deleted INTEGER;
BEGIN
    DELETE FROM staging.flex_trades
    WHERE created_at < CURRENT_DATE - INTERVAL '1 day' * p_days_to_keep
    AND processed = TRUE;
    
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    RETURN v_deleted;
END;
$$ LANGUAGE plpgsql;

COMMIT;

-- Verification
SELECT 'Staging schema' as component,
       CASE WHEN COUNT(*) > 0 THEN 'Created' ELSE 'Failed' END as status
FROM information_schema.schemata WHERE schema_name = 'staging'
UNION ALL
SELECT 'Staging tables' as component,
       COUNT(*)::TEXT || ' tables' as status
FROM information_schema.tables 
WHERE table_schema = 'staging'
UNION ALL
SELECT 'Validation rules' as component,
       COUNT(*)::TEXT || ' rules' as status
FROM staging.validation_rules
UNION ALL
SELECT 'Staging functions' as component,
       COUNT(*)::TEXT || ' functions' as status
FROM information_schema.routines
WHERE routine_schema = 'staging';