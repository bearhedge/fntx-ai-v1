-- Options Data Schema for ThetaTerminal
-- Modular design to support OHLC now, Greeks/IV later

-- Create schema
CREATE SCHEMA IF NOT EXISTS theta;

-- Contract metadata table
CREATE TABLE IF NOT EXISTS theta.options_contracts (
    contract_id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    expiration DATE NOT NULL,
    strike DECIMAL(10,2) NOT NULL,
    option_type CHAR(1) NOT NULL CHECK (option_type IN ('C', 'P')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, expiration, strike, option_type)
);

-- OHLC data table (available now with Value subscription)
CREATE TABLE IF NOT EXISTS theta.options_ohlc (
    id BIGSERIAL PRIMARY KEY,
    contract_id INTEGER NOT NULL REFERENCES theta.options_contracts(contract_id),
    datetime TIMESTAMP NOT NULL,
    open DECIMAL(10,4),
    high DECIMAL(10,4),
    low DECIMAL(10,4),
    close DECIMAL(10,4),
    volume BIGINT DEFAULT 0,
    trade_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(contract_id, datetime)
);

-- Greeks table (ready for Standard subscription - July 18)
CREATE TABLE IF NOT EXISTS theta.options_greeks (
    id BIGSERIAL PRIMARY KEY,
    contract_id INTEGER NOT NULL REFERENCES theta.options_contracts(contract_id),
    datetime TIMESTAMP NOT NULL,
    delta DECIMAL(8,6),
    gamma DECIMAL(8,6),
    theta DECIMAL(10,4),
    vega DECIMAL(10,4),
    rho DECIMAL(10,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(contract_id, datetime)
);

-- Implied Volatility table (ready for Standard subscription)
CREATE TABLE IF NOT EXISTS theta.options_iv (
    id BIGSERIAL PRIMARY KEY,
    contract_id INTEGER NOT NULL REFERENCES theta.options_contracts(contract_id),
    datetime TIMESTAMP NOT NULL,
    implied_volatility DECIMAL(8,6),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(contract_id, datetime)
);

-- Open Interest tracking
CREATE TABLE IF NOT EXISTS theta.options_oi (
    id BIGSERIAL PRIMARY KEY,
    contract_id INTEGER NOT NULL REFERENCES theta.options_contracts(contract_id),
    date DATE NOT NULL,
    open_interest BIGINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(contract_id, date)
);

-- Download status tracking
CREATE TABLE IF NOT EXISTS theta.download_status (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    data_type VARCHAR(20) NOT NULL, -- 'ohlc', 'greeks', 'iv', 'oi'
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- 'pending', 'in_progress', 'completed', 'failed'
    records_downloaded BIGINT DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_ohlc_datetime ON theta.options_ohlc(datetime);
CREATE INDEX idx_ohlc_contract_datetime ON theta.options_ohlc(contract_id, datetime);
CREATE INDEX idx_contracts_symbol_exp ON theta.options_contracts(symbol, expiration);
CREATE INDEX idx_contracts_strike ON theta.options_contracts(strike);
CREATE INDEX idx_download_status ON theta.download_status(symbol, start_date, end_date, data_type);

-- Future indexes for Greeks/IV (will be used when data is available)
CREATE INDEX idx_greeks_datetime ON theta.options_greeks(datetime);
CREATE INDEX idx_greeks_contract_datetime ON theta.options_greeks(contract_id, datetime);
CREATE INDEX idx_iv_datetime ON theta.options_iv(datetime);
CREATE INDEX idx_iv_contract_datetime ON theta.options_iv(contract_id, datetime);

-- Function to get contract ID (creates if not exists)
CREATE OR REPLACE FUNCTION theta.get_or_create_contract(
    p_symbol VARCHAR(10),
    p_expiration DATE,
    p_strike DECIMAL(10,2),
    p_option_type CHAR(1)
) RETURNS INTEGER AS $$
DECLARE
    v_contract_id INTEGER;
BEGIN
    -- Try to find existing contract
    SELECT contract_id INTO v_contract_id
    FROM theta.options_contracts
    WHERE symbol = p_symbol 
      AND expiration = p_expiration 
      AND strike = p_strike 
      AND option_type = p_option_type;
    
    -- Create if not exists
    IF v_contract_id IS NULL THEN
        INSERT INTO theta.options_contracts (symbol, expiration, strike, option_type)
        VALUES (p_symbol, p_expiration, p_strike, p_option_type)
        RETURNING contract_id INTO v_contract_id;
    END IF;
    
    RETURN v_contract_id;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT ALL ON SCHEMA theta TO postgres;
GRANT ALL ON ALL TABLES IN SCHEMA theta TO postgres;
GRANT ALL ON ALL SEQUENCES IN SCHEMA theta TO postgres;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA theta TO postgres;