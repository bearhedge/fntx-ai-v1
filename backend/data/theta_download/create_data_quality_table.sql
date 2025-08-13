-- Create table to track data quality issues for later cleanup and IV recalculation
CREATE TABLE IF NOT EXISTS theta.data_quality_issues (
    id BIGSERIAL PRIMARY KEY,
    contract_id BIGINT NOT NULL,
    datetime TIMESTAMP NOT NULL,
    issue_type VARCHAR(50) NOT NULL, -- 'sentinel_iv', 'missing_iv', 'missing_greeks', 'missing_ohlc', 'no_volume'
    field_name VARCHAR(50),
    original_value NUMERIC,
    symbol VARCHAR(10),
    strike NUMERIC(10,2),
    option_type CHAR(1),
    expiration DATE,
    underlying_price NUMERIC(10,2),
    time_to_expiry NUMERIC, -- in days
    moneyness NUMERIC, -- (underlying/strike) for calls, (strike/underlying) for puts
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contract_id) REFERENCES theta.options_contracts(contract_id)
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_quality_issues_type ON theta.data_quality_issues(issue_type);
CREATE INDEX IF NOT EXISTS idx_quality_issues_contract ON theta.data_quality_issues(contract_id, datetime);
CREATE INDEX IF NOT EXISTS idx_quality_issues_symbol ON theta.data_quality_issues(symbol, issue_type);
CREATE INDEX IF NOT EXISTS idx_quality_issues_datetime ON theta.data_quality_issues(datetime);

-- Grant permissions
GRANT ALL ON theta.data_quality_issues TO postgres;
GRANT USAGE, SELECT ON SEQUENCE theta.data_quality_issues_id_seq TO postgres;

-- Add comment
COMMENT ON TABLE theta.data_quality_issues IS 'Tracks data quality issues for post-download cleanup and IV recalculation';
COMMENT ON COLUMN theta.data_quality_issues.issue_type IS 'Type of issue: sentinel_iv (negative IV sentinel values), missing_iv, missing_greeks, missing_ohlc, no_volume';
COMMENT ON COLUMN theta.data_quality_issues.moneyness IS 'For calls: underlying/strike, for puts: strike/underlying';
COMMENT ON COLUMN theta.data_quality_issues.time_to_expiry IS 'Days until expiration at the time of the data point';