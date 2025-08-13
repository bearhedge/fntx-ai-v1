
-- Migration: Allow NULLs in portfolio.trades.ibkr_order_id
--
-- This migration modifies the `ibkr_order_id` column in the `portfolio.trades`
-- table to allow NULL values. Some trade records, particularly for non-stock
-- items or certain transaction types, may not have an associated order ID.

ALTER TABLE portfolio.trades
    ALTER COLUMN ibkr_order_id DROP NOT NULL;
