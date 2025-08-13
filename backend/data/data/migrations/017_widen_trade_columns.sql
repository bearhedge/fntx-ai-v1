
-- Migration: Widen text-based columns in portfolio.trades
--
-- This migration changes the data type of several character varying columns
-- to TEXT to prevent "value too long" errors during import. The XML data
-- sometimes contains values longer than the initial estimates.

ALTER TABLE portfolio.trades
    ALTER COLUMN asset_class TYPE TEXT,
    ALTER COLUMN symbol TYPE TEXT,
    ALTER COLUMN description TYPE TEXT,
    ALTER COLUMN listing_exchange TYPE TEXT,
    ALTER COLUMN underlying_listing_exchange TYPE TEXT,
    ALTER COLUMN transaction_type TYPE TEXT,
    ALTER COLUMN exchange TYPE TEXT,
    ALTER COLUMN order_type TYPE TEXT,
    ALTER COLUMN buy_sell TYPE TEXT,
    ALTER COLUMN delivery_type TYPE TEXT,
    ALTER COLUMN code TYPE TEXT;
