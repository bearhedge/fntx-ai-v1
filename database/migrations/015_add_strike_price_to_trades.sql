
-- Migration: Add strike_price to portfolio.trades
--
-- This migration adds the `strike_price` column to the `portfolio.trades`
-- table to match the data present in the FlexQuery XML files.

ALTER TABLE portfolio.trades
ADD COLUMN IF NOT EXISTS strike_price DECIMAL(12, 4);
