
-- Migration: Drop check constraint on portfolio.trades.option_type
--
-- This migration removes the CHECK constraint from the `option_type` column
-- to allow for non-option trades (e.g., stocks) that have an empty or NULL
-- value for this field.

ALTER TABLE portfolio.trades
    DROP CONSTRAINT IF EXISTS trades_option_type_check;
