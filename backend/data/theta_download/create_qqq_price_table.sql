-- Create QQQ price data table with NON-ADJUSTED prices
CREATE TABLE IF NOT EXISTS qqq_price_data (
    date DATE PRIMARY KEY,
    open NUMERIC(10,2) NOT NULL,
    high NUMERIC(10,2) NOT NULL,
    low NUMERIC(10,2) NOT NULL,
    close NUMERIC(10,2) NOT NULL,
    volume BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE qqq_price_data IS 'NON-ADJUSTED QQQ price data for options strike selection';

-- Create index for efficient date lookups
CREATE INDEX IF NOT EXISTS idx_qqq_price_date ON qqq_price_data(date);

-- Grant permissions
GRANT ALL ON qqq_price_data TO postgres;