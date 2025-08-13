
-- Migration: Add all remaining columns to portfolio.trades
--
-- This migration adds all the necessary columns to the `portfolio.trades`
-- table at once, based on the comprehensive FlexQuery definitions provided.
-- This avoids the slow, iterative process of adding one column at a time.

ALTER TABLE portfolio.trades
    ADD COLUMN IF NOT EXISTS option_type VARCHAR(4) CHECK (option_type IN ('P', 'C')),
    ADD COLUMN IF NOT EXISTS expiration_date DATE,
    ADD COLUMN IF NOT EXISTS trade_date DATE,
    ADD COLUMN IF NOT EXISTS trade_time TIME,
    ADD COLUMN IF NOT EXISTS quantity INTEGER,
    ADD COLUMN IF NOT EXISTS trade_price DECIMAL(18, 8),
    ADD COLUMN IF NOT EXISTS proceeds DECIMAL(18, 4),
    ADD COLUMN IF NOT EXISTS commission DECIMAL(18, 4),
    ADD COLUMN IF NOT EXISTS fee DECIMAL(18, 4),
    ADD COLUMN IF NOT EXISTS cost_basis DECIMAL(18, 4),
    ADD COLUMN IF NOT EXISTS realized_pnl DECIMAL(18, 4),
    ADD COLUMN IF NOT EXISTS mtm_pnl DECIMAL(18, 4),
    ADD COLUMN IF NOT EXISTS code VARCHAR(50),
    ADD COLUMN IF NOT EXISTS level_of_detail VARCHAR(50),
    ADD COLUMN IF NOT EXISTS client_account_id VARCHAR(50),
    ADD COLUMN IF NOT EXISTS account_alias VARCHAR(100),
    ADD COLUMN IF NOT EXISTS currency_primary VARCHAR(10),
    ADD COLUMN IF NOT EXISTS asset_class VARCHAR(20),
    ADD COLUMN IF NOT EXISTS security_id VARCHAR(100),
    ADD COLUMN IF NOT EXISTS listing_exchange VARCHAR(50),
    ADD COLUMN IF NOT EXISTS underlying_con_id VARCHAR(100),
    ADD COLUMN IF NOT EXISTS underlying_security_id VARCHAR(100),
    ADD COLUMN IF NOT EXISTS underlying_listing_exchange VARCHAR(50),
    ADD COLUMN IF NOT EXISTS ibkr_trade_id VARCHAR(100),
    ADD COLUMN IF NOT EXISTS multiplier INTEGER,
    ADD COLUMN IF NOT EXISTS report_date DATE,
    ADD COLUMN IF NOT EXISTS trade_datetime TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS transaction_type VARCHAR(50),
    ADD COLUMN IF NOT EXISTS exchange VARCHAR(50),
    ADD COLUMN IF NOT EXISTS trade_money DECIMAL(18, 4),
    ADD COLUMN IF NOT EXISTS net_cash DECIMAL(18, 4),
    ADD COLUMN IF NOT EXISTS close_price DECIMAL(18, 8),
    ADD COLUMN IF NOT EXISTS fifo_pnl_realized DECIMAL(18, 4),
    ADD COLUMN IF NOT EXISTS orig_trade_price DECIMAL(18, 8),
    ADD COLUMN IF NOT EXISTS orig_trade_date DATE,
    ADD COLUMN IF NOT EXISTS orig_trade_id VARCHAR(100),
    ADD COLUMN IF NOT EXISTS orig_order_id VARCHAR(100),
    ADD COLUMN IF NOT EXISTS orig_transaction_id VARCHAR(100),
    ADD COLUMN IF NOT EXISTS buy_sell VARCHAR(10),
    ADD COLUMN IF NOT EXISTS ibkr_order_id VARCHAR(100),
    ADD COLUMN IF NOT EXISTS transaction_id VARCHAR(100),
    ADD COLUMN IF NOT EXISTS change_in_price DECIMAL(18, 8),
    ADD COLUMN IF NOT EXISTS change_in_quantity INTEGER,
    ADD COLUMN IF NOT EXISTS order_type VARCHAR(50),
    ADD COLUMN IF NOT EXISTS serial_number VARCHAR(100),
    ADD COLUMN IF NOT EXISTS delivery_type VARCHAR(50);

-- Add a comment to note the comprehensive update
COMMENT ON TABLE portfolio.trades IS 'Table schema updated comprehensively on 2025-07-20 to include all columns from FlexQuery definitions for Trades.';
