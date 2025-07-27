-- Create portfolio.trades table for FlexQuery trade imports
-- This table stores historical trades from IBKR FlexQuery XML files

CREATE TABLE IF NOT EXISTS portfolio.trades (
    -- Primary key
    id SERIAL PRIMARY KEY,
    
    -- IBKR identifiers
    ibkr_order_id BIGINT NOT NULL,
    ibkr_exec_id VARCHAR(50),
    ibkr_trade_id VARCHAR(50),
    ibkr_account_id VARCHAR(20) NOT NULL,
    
    -- Trade details
    symbol VARCHAR(20) NOT NULL,
    asset_category VARCHAR(20) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    
    -- Quantities and prices
    quantity DECIMAL(12,4) NOT NULL,
    trade_price DECIMAL(12,6) NOT NULL,
    proceeds DECIMAL(12,2) NOT NULL,
    
    -- Fees and commissions
    ibkr_commission DECIMAL(10,4) DEFAULT 0,
    ibkr_commission_currency VARCHAR(10) DEFAULT 'USD',
    taxes DECIMAL(10,4) DEFAULT 0,
    
    -- Dates
    trade_date DATE NOT NULL,
    trade_time TIME,
    settlement_date DATE,
    
    -- Transaction type
    buy_sell VARCHAR(10) NOT NULL CHECK (buy_sell IN ('BUY', 'SELL')),
    
    -- Options specific fields
    put_call VARCHAR(4) CHECK (put_call IN ('P', 'C', NULL)),
    strike DECIMAL(12,4),
    expiry DATE,
    multiplier INTEGER DEFAULT 1,
    
    -- P&L tracking
    fifoPnlRealized DECIMAL(12,2),
    mtmPnl DECIMAL(12,2),
    
    -- Import tracking
    import_id UUID NOT NULL,
    imported_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT unique_ibkr_trade UNIQUE (ibkr_account_id, ibkr_exec_id),
    CONSTRAINT fk_import_id FOREIGN KEY (import_id) 
        REFERENCES portfolio.flexquery_imports(import_id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX idx_portfolio_trades_symbol ON portfolio.trades(symbol);
CREATE INDEX idx_portfolio_trades_trade_date ON portfolio.trades(trade_date DESC);
CREATE INDEX idx_portfolio_trades_import ON portfolio.trades(import_id);
CREATE INDEX idx_portfolio_trades_account ON portfolio.trades(ibkr_account_id);

-- Add comments
COMMENT ON TABLE portfolio.trades IS 'Historical trades imported from IBKR FlexQuery XML files';
COMMENT ON COLUMN portfolio.trades.proceeds IS 'Net cash flow (negative for buys, positive for sells)';
COMMENT ON COLUMN portfolio.trades.fifoPnlRealized IS 'Realized P&L using FIFO method from IBKR';