
-- Migration: Add description to portfolio.trades
--
-- This migration adds the `description` column to the `portfolio.trades`
-- table to match the data present in the FlexQuery XML files.

ALTER TABLE portfolio.trades
ADD COLUMN IF NOT EXISTS description VARCHAR(255);
