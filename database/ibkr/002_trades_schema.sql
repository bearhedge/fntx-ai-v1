-- Automated Trade Logging Schema
-- Captures all trades executed through IBKR automatically

-- Create trades schema if not exists
CREATE SCHEMA IF NOT EXISTS trading;

-- Main trades table for automated trade capture
CREATE TABLE IF NOT EXISTS trading.trades (
    -- Primary identifiers
    trade_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ibkr_order_id INTEGER NOT NULL,
    ibkr_exec_id VARCHAR(50),
    ibkr_perm_id INTEGER,
    
    -- Contract details (auto-captured from IBKR)
    symbol VARCHAR(10) NOT NULL DEFAULT 'SPY',
    strike_price DECIMAL(10,2) NOT NULL,
    option_type VARCHAR(4) NOT NULL CHECK (option_type IN ('PUT', 'CALL')),
    expiration DATE NOT NULL,
    
    -- Trade execution details
    quantity INTEGER NOT NULL,
    entry_time TIMESTAMP WITH TIME ZONE NOT NULL,
    entry_price DECIMAL(10,4) NOT NULL,
    entry_commission DECIMAL(10,2) DEFAULT 0,
    
    -- Exit details (populated when trade closes)
    exit_time TIMESTAMP WITH TIME ZONE,
    exit_price DECIMAL(10,4),
    exit_commission DECIMAL(10,2) DEFAULT 0,
    exit_reason VARCHAR(20) CHECK (exit_reason IN ('expired', 'stopped_out', 'take_profit', 'manual', 'assigned')),
    
    -- Linked orders
    stop_loss_order_id INTEGER,
    stop_loss_price DECIMAL(10,4),
    take_profit_order_id INTEGER,
    take_profit_price DECIMAL(10,4),
    
    -- P&L Calculation
    realized_pnl DECIMAL(10,2) GENERATED ALWAYS AS (
        CASE 
            WHEN exit_price IS NOT NULL THEN
                ((entry_price - exit_price) * quantity * 100) - COALESCE(entry_commission, 0) - COALESCE(exit_commission, 0)
            ELSE NULL
        END
    ) STORED,
    
    -- Status tracking
    status VARCHAR(10) NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed')),
    
    -- Market snapshot at entry (for AI training)
    market_snapshot JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_trades_status ON trading.trades(status);
CREATE INDEX idx_trades_entry_time ON trading.trades(entry_time DESC);
CREATE INDEX idx_trades_symbol_expiry ON trading.trades(symbol, expiration);
CREATE INDEX idx_trades_ibkr_order_id ON trading.trades(ibkr_order_id);

-- Trade executions table (for tracking partial fills)
CREATE TABLE IF NOT EXISTS trading.executions (
    execution_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trade_id UUID REFERENCES trading.trades(trade_id),
    ibkr_exec_id VARCHAR(50) NOT NULL UNIQUE,
    ibkr_order_id INTEGER NOT NULL,
    
    execution_time TIMESTAMP WITH TIME ZONE NOT NULL,
    quantity INTEGER NOT NULL,
    price DECIMAL(10,4) NOT NULL,
    commission DECIMAL(10,2) DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Order tracking table (for linking stops/TPs)
CREATE TABLE IF NOT EXISTS trading.order_links (
    link_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_order_id INTEGER NOT NULL,
    child_order_id INTEGER NOT NULL,
    order_type VARCHAR(20) NOT NULL CHECK (order_type IN ('stop_loss', 'take_profit')),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(parent_order_id, child_order_id)
);

-- Performance metrics view
CREATE OR REPLACE VIEW trading.performance_metrics AS
WITH daily_stats AS (
    SELECT 
        DATE(entry_time) as trade_date,
        COUNT(*) as total_trades,
        COUNT(CASE WHEN status = 'closed' AND realized_pnl > 0 THEN 1 END) as winning_trades,
        COUNT(CASE WHEN status = 'closed' AND realized_pnl <= 0 THEN 1 END) as losing_trades,
        SUM(CASE WHEN status = 'closed' THEN realized_pnl ELSE 0 END) as daily_pnl
    FROM trading.trades
    GROUP BY DATE(entry_time)
)
SELECT 
    COUNT(DISTINCT trade_date) as total_trading_days,
    SUM(total_trades) as total_trades,
    SUM(winning_trades) as total_wins,
    SUM(losing_trades) as total_losses,
    CASE 
        WHEN SUM(winning_trades) + SUM(losing_trades) > 0 
        THEN ROUND(SUM(winning_trades)::NUMERIC / (SUM(winning_trades) + SUM(losing_trades)) * 100, 2)
        ELSE 0 
    END as win_rate,
    SUM(daily_pnl) as total_pnl,
    AVG(daily_pnl) as avg_daily_pnl,
    MAX(daily_pnl) as best_day,
    MIN(daily_pnl) as worst_day
FROM daily_stats;

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_trades_updated_at BEFORE UPDATE ON trading.trades
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();