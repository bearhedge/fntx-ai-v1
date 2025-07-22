
-- Migration: Allow NULLs in portfolio.trades.import_id
--
ALTER TABLE portfolio.trades
    ALTER COLUMN import_id DROP NOT NULL;
