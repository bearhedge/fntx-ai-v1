-- Fast cleanup using TRUNCATE since SPY is the only data
BEGIN;

-- Truncate all tables (CASCADE handles foreign keys)
TRUNCATE TABLE theta.options_ohlc CASCADE;
TRUNCATE TABLE theta.options_greeks CASCADE;
TRUNCATE TABLE theta.options_iv CASCADE;
TRUNCATE TABLE theta.options_oi CASCADE;
TRUNCATE TABLE theta.options_contracts CASCADE;
TRUNCATE TABLE theta.download_status CASCADE;

-- Reset sequences
ALTER SEQUENCE theta.options_contracts_contract_id_seq RESTART WITH 1;

COMMIT;

-- Add constraints
ALTER TABLE theta.options_contracts 
DROP CONSTRAINT IF EXISTS reasonable_strike_range;

ALTER TABLE theta.options_contracts 
ADD CONSTRAINT reasonable_strike_range 
CHECK (strike >= 50 AND strike <= 1000);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_ohlc_datetime_date 
ON theta.options_ohlc (DATE(datetime));

CREATE INDEX IF NOT EXISTS idx_contracts_symbol_exp_strike 
ON theta.options_contracts (symbol, expiration, strike, option_type);

-- Verify cleanup
SELECT 'Contracts remaining:', COUNT(*) FROM theta.options_contracts;
SELECT 'OHLC remaining:', COUNT(*) FROM theta.options_ohlc;