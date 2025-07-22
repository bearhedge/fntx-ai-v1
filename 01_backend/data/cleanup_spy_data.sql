-- Complete SPY options data cleanup
BEGIN;

-- Delete OHLC data
DELETE FROM theta.options_ohlc 
WHERE contract_id IN (
    SELECT contract_id FROM theta.options_contracts WHERE symbol = 'SPY'
);

-- Delete Greeks data
DELETE FROM theta.options_greeks 
WHERE contract_id IN (
    SELECT contract_id FROM theta.options_contracts WHERE symbol = 'SPY'
);

-- Delete IV data
DELETE FROM theta.options_iv 
WHERE contract_id IN (
    SELECT contract_id FROM theta.options_contracts WHERE symbol = 'SPY'
);

-- Delete OI data
DELETE FROM theta.options_oi 
WHERE contract_id IN (
    SELECT contract_id FROM theta.options_contracts WHERE symbol = 'SPY'
);

-- Delete contracts
DELETE FROM theta.options_contracts WHERE symbol = 'SPY';

-- Delete download status
DELETE FROM theta.download_status WHERE symbol = 'SPY';

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

-- Vacuum
VACUUM ANALYZE;