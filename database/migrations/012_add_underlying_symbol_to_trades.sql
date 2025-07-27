
-- Migration: Add underlying_symbol to portfolio.trades
--
-- This migration adds the `underlying_symbol` column to the `portfolio.trades`
-- table to match the data present in the FlexQuery XML files.

ALTER TABLE portfolio.trades
ADD COLUMN IF NOT EXISTS underlying_symbol VARCHAR(50);
