-- Efficient cleanup using TRUNCATE (much faster than DELETE)
-- First drop foreign key constraints temporarily

BEGIN;

-- Store SPY contract IDs to verify
CREATE TEMP TABLE spy_contracts AS
SELECT contract_id FROM theta.options_contracts WHERE symbol = 'SPY';

-- Count records before deletion
SELECT 'SPY contracts:', COUNT(*) FROM spy_contracts;

-- Since we want to delete ALL SPY data and SPY is likely the only data,
-- we can TRUNCATE if SPY is the only symbol
SELECT DISTINCT symbol FROM theta.options_contracts;

COMMIT;