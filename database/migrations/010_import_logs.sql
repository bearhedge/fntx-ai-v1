-- Import Logs Table for ALM Daily Import Service
-- Tracks all automated imports with detailed status and reconciliation info

BEGIN;

-- Create import logs table
CREATE TABLE IF NOT EXISTS portfolio.import_logs (
    log_id SERIAL PRIMARY KEY,
    import_date DATE NOT NULL,
    import_type VARCHAR(50) NOT NULL, -- DAILY_LBD, MONTHLY_MTD, etc.
    import_started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    import_completed_at TIMESTAMP,
    status VARCHAR(20) NOT NULL, -- RUNNING, SUCCESS, FAILED, PARTIAL
    
    -- Import metrics
    queries_attempted INTEGER DEFAULT 0,
    queries_successful INTEGER DEFAULT 0,
    queries_failed INTEGER DEFAULT 0,
    records_imported INTEGER DEFAULT 0,
    
    -- Reconciliation status
    reconciliation_status BOOLEAN,
    reconciliation_difference DECIMAL(15,2),
    reconciliation_percentage DECIMAL(5,2),
    
    -- Error tracking
    errors JSONB,
    
    -- Full summary
    summary_json JSONB,
    
    -- Indexes
    CONSTRAINT unique_import_date_type UNIQUE (import_date, import_type)
);

-- Indexes for performance
CREATE INDEX idx_import_logs_date ON portfolio.import_logs(import_date DESC);
CREATE INDEX idx_import_logs_status ON portfolio.import_logs(status);
CREATE INDEX idx_import_logs_type ON portfolio.import_logs(import_type);

-- View for recent imports
CREATE OR REPLACE VIEW portfolio.recent_imports AS
SELECT 
    log_id,
    import_date,
    import_type,
    import_started_at,
    import_completed_at,
    EXTRACT(EPOCH FROM (import_completed_at - import_started_at)) AS duration_seconds,
    status,
    queries_attempted,
    queries_successful,
    records_imported,
    reconciliation_status,
    reconciliation_difference,
    reconciliation_percentage,
    CASE 
        WHEN reconciliation_status IS NULL THEN 'NOT_CHECKED'
        WHEN reconciliation_status = true THEN 'RECONCILED'
        ELSE 'DISCREPANCY'
    END AS reconciliation_label,
    errors
FROM portfolio.import_logs
WHERE import_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY import_date DESC, import_started_at DESC;

-- View for import health monitoring
CREATE OR REPLACE VIEW portfolio.import_health AS
WITH daily_stats AS (
    SELECT 
        DATE_TRUNC('day', import_date) AS day,
        COUNT(*) AS total_imports,
        SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) AS successful_imports,
        SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) AS failed_imports,
        AVG(EXTRACT(EPOCH FROM (import_completed_at - import_started_at))) AS avg_duration_seconds,
        SUM(records_imported) AS total_records_imported
    FROM portfolio.import_logs
    WHERE import_date >= CURRENT_DATE - INTERVAL '7 days'
    GROUP BY DATE_TRUNC('day', import_date)
)
SELECT 
    day,
    total_imports,
    successful_imports,
    failed_imports,
    ROUND(100.0 * successful_imports / NULLIF(total_imports, 0), 2) AS success_rate,
    avg_duration_seconds,
    total_records_imported
FROM daily_stats
ORDER BY day DESC;

-- Function to get latest import status
CREATE OR REPLACE FUNCTION portfolio.get_latest_import_status(
    p_import_type VARCHAR DEFAULT 'DAILY_LBD'
) RETURNS TABLE (
    import_date DATE,
    status VARCHAR,
    queries_successful INTEGER,
    records_imported INTEGER,
    reconciliation_status BOOLEAN,
    last_error TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        il.import_date,
        il.status,
        il.queries_successful,
        il.records_imported,
        il.reconciliation_status,
        CASE 
            WHEN il.errors IS NOT NULL THEN 
                il.errors::TEXT
            ELSE NULL
        END AS last_error
    FROM portfolio.import_logs il
    WHERE il.import_type = p_import_type
    ORDER BY il.import_date DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Add comments
COMMENT ON TABLE portfolio.import_logs IS 'Tracks all automated FlexQuery imports with detailed metrics';
COMMENT ON COLUMN portfolio.import_logs.import_type IS 'Type of import: DAILY_LBD (Last Business Day), MONTHLY_MTD (Month to Date)';
COMMENT ON COLUMN portfolio.import_logs.reconciliation_status IS 'True if ALM reconciliation passed, False if discrepancy found, NULL if not checked';

COMMIT;