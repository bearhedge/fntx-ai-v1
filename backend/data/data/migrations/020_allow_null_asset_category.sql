
-- Migration: Allow NULLs in portfolio.trades.asset_category
--
-- This migration modifies the `asset_category` column in the `portfolio.trades`
-- table to allow NULL values.

ALTER TABLE portfolio.trades
    ALTER COLUMN asset_category DROP NOT NULL;
