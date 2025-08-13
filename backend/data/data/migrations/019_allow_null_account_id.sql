
-- Migration: Allow NULLs in portfolio.trades.ibkr_account_id
--
-- This migration modifies the `ibkr_account_id` column in the `portfolio.trades`
-- table to allow NULL values. Some trade records in the FlexQuery XML data
-- may not contain a ClientAccountID.

ALTER TABLE portfolio.trades
    ALTER COLUMN ibkr_account_id DROP NOT NULL;
