-- Enhanced Trade Lifecycle Schema
-- Each record represents a complete round-trip options trade
-- Designed for clarity, AI training, and performance analysis

-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS trading;

-- Drop existing tables if we're recreating (comment out in production)
-- DROP TABLE IF EXISTS trading.trade_lifecycles CASCADE;
-- DROP TABLE IF EXISTS trading.daily_summaries CASCADE;
-- DROP TABLE IF EXISTS trading.risk_metrics CASCADE;

-- Main trade lifecycle table
CREATE TABLE IF NOT EXISTS trading.trade_lifecycles (
    -- Identity
    lifecycle_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trade_number SERIAL UNIQUE, -- Sequential trade number for easy reference
    
    -- Trade Classification
    symbol VARCHAR(10) NOT NULL DEFAULT 'SPY',
    strategy_type VARCHAR(20) DEFAULT 'naked_option', -- 'naked_put', 'naked_call', 'spread', etc.
    trade_direction VARCHAR(10) DEFAULT 'credit', -- 'credit', 'debit'
    
    -- Opening Transaction
    open_date DATE NOT NULL,
    open_time TIMESTAMP WITH TIME ZONE NOT NULL,
    open_strike DECIMAL(10,2) NOT NULL,
    open_option_type VARCHAR(4) NOT NULL CHECK (open_option_type IN ('PUT', 'CALL')),
    open_expiration DATE NOT NULL,
    open_quantity INTEGER NOT NULL,
    open_price DECIMAL(10,4) NOT NULL,
    open_commission DECIMAL(10,2) DEFAULT 0,
    open_exec_id VARCHAR(50),
    open_order_id VARCHAR(20),
    
    -- Closing Transaction
    close_date DATE,
    close_time TIMESTAMP WITH TIME ZONE,
    close_price DECIMAL(10,4),
    close_commission DECIMAL(10,2) DEFAULT 0,
    close_reason VARCHAR(20) CHECK (close_reason IN ('expired', 'stopped', 'profit_target', 'manual', 'assigned')),
    close_exec_id VARCHAR(50),
    close_order_id VARCHAR(20),
    
    -- Risk Management
    max_risk DECIMAL(10,2) GENERATED ALWAYS AS (
        open_quantity * 100 * CASE 
            WHEN open_option_type = 'PUT' THEN open_strike
            ELSE 999999 -- Undefined for naked calls
        END
    ) STORED,
    stop_loss_price DECIMAL(10,4),
    profit_target_price DECIMAL(10,4),
    
    -- P&L Metrics
    gross_pnl DECIMAL(10,2) GENERATED ALWAYS AS (
        CASE 
            WHEN close_price IS NOT NULL THEN
                (open_price - close_price) * open_quantity * 100
            ELSE NULL
        END
    ) STORED,
    net_pnl DECIMAL(10,2) GENERATED ALWAYS AS (
        CASE 
            WHEN close_price IS NOT NULL THEN
                ((open_price - close_price) * open_quantity * 100) - COALESCE(open_commission, 0) - COALESCE(close_commission, 0)
            ELSE NULL
        END
    ) STORED,
    pnl_percentage DECIMAL(8,2) GENERATED ALWAYS AS (
        CASE 
            WHEN close_price IS NOT NULL AND open_price > 0 THEN
                ((open_price - close_price) / open_price) * 100
            ELSE NULL
        END
    ) STORED,
    
    -- Duration Metrics
    days_in_trade INTEGER GENERATED ALWAYS AS (
        CASE 
            WHEN close_date IS NOT NULL THEN
                close_date - open_date
            ELSE 
                NULL  -- Will calculate dynamically in views
        END
    ) STORED,
    hours_held DECIMAL(8,2) GENERATED ALWAYS AS (
        CASE 
            WHEN close_time IS NOT NULL THEN
                EXTRACT(EPOCH FROM (close_time - open_time)) / 3600.0
            ELSE 
                NULL  -- Will calculate dynamically in views
        END
    ) STORED,
    dte_at_open INTEGER GENERATED ALWAYS AS (
        open_expiration - open_date
    ) STORED,
    
    -- Market Context (populated via triggers or batch updates)
    spy_price_at_open DECIMAL(10,2),
    spy_price_at_close DECIMAL(10,2),
    vix_at_open DECIMAL(8,2),
    vix_at_close DECIMAL(8,2),
    market_regime VARCHAR(20), -- 'trending_up', 'trending_down', 'ranging', 'volatile'
    
    -- Greeks at Entry (when available from ThetaData after July 18)
    open_delta DECIMAL(8,6),
    open_gamma DECIMAL(8,6),
    open_theta DECIMAL(10,4),
    open_vega DECIMAL(10,4),
    open_iv DECIMAL(8,6),
    
    -- Status
    status VARCHAR(10) GENERATED ALWAYS AS (
        CASE 
            WHEN close_time IS NOT NULL THEN 'closed'
            ELSE 'open'
        END
    ) STORED,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Daily trade summary for quick dashboards
CREATE TABLE IF NOT EXISTS trading.daily_summaries (
    trade_date DATE PRIMARY KEY,
    trades_opened INTEGER DEFAULT 0,
    trades_closed INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    expired_trades INTEGER DEFAULT 0,
    gross_pnl DECIMAL(10,2) DEFAULT 0,
    net_pnl DECIMAL(10,2) DEFAULT 0,
    commissions_paid DECIMAL(10,2) DEFAULT 0,
    win_rate DECIMAL(5,2),
    avg_winner DECIMAL(10,2),
    avg_loser DECIMAL(10,2),
    largest_win DECIMAL(10,2),
    largest_loss DECIMAL(10,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Risk metrics tracking
CREATE TABLE IF NOT EXISTS trading.risk_metrics (
    metric_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trade_date DATE NOT NULL,
    lifecycle_id UUID REFERENCES trading.trade_lifecycles(lifecycle_id),
    max_portfolio_risk DECIMAL(10,2),
    actual_drawdown DECIMAL(10,2),
    risk_reward_ratio DECIMAL(8,2),
    kelly_percentage DECIMAL(5,2), -- Optimal position sizing
    sharpe_ratio DECIMAL(8,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Performance indexes
CREATE INDEX idx_lifecycle_status ON trading.trade_lifecycles(status);
CREATE INDEX idx_lifecycle_open_date ON trading.trade_lifecycles(open_date DESC);
CREATE INDEX idx_lifecycle_symbol_date ON trading.trade_lifecycles(symbol, open_date DESC);
CREATE INDEX idx_lifecycle_strategy ON trading.trade_lifecycles(strategy_type);
CREATE INDEX idx_lifecycle_pnl ON trading.trade_lifecycles(net_pnl) WHERE status = 'closed';

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_trade_lifecycles_updated_at 
    BEFORE UPDATE ON trading.trade_lifecycles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_daily_summaries_updated_at 
    BEFORE UPDATE ON trading.daily_summaries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- View for current open positions
CREATE OR REPLACE VIEW trading.open_positions AS
SELECT 
    trade_number,
    symbol,
    open_strike,
    open_option_type,
    open_expiration,
    open_quantity,
    open_price,
    open_time,
    CURRENT_DATE - open_date as days_in_trade,
    open_expiration - CURRENT_DATE as dte_remaining,
    spy_price_at_open,
    CASE 
        WHEN open_option_type = 'PUT' AND spy_price_at_open > 0 THEN 
            ROUND((spy_price_at_open - open_strike) / spy_price_at_open * 100, 2)
        WHEN open_option_type = 'CALL' AND spy_price_at_open > 0 THEN 
            ROUND((open_strike - spy_price_at_open) / spy_price_at_open * 100, 2)
        ELSE NULL
    END as otm_percentage
FROM trading.trade_lifecycles
WHERE status = 'open'
ORDER BY open_expiration, open_strike;

-- View for trade performance analytics
CREATE OR REPLACE VIEW trading.performance_analytics AS
SELECT 
    DATE_TRUNC('month', open_date) as month,
    COUNT(*) as total_trades,
    COUNT(CASE WHEN status = 'closed' THEN 1 END) as closed_trades,
    COUNT(CASE WHEN net_pnl > 0 THEN 1 END) as winners,
    COUNT(CASE WHEN net_pnl <= 0 AND status = 'closed' THEN 1 END) as losers,
    ROUND(COUNT(CASE WHEN net_pnl > 0 THEN 1 END)::NUMERIC / 
          NULLIF(COUNT(CASE WHEN status = 'closed' THEN 1 END), 0) * 100, 2) as win_rate,
    SUM(net_pnl) as total_pnl,
    AVG(net_pnl) as avg_pnl,
    AVG(CASE WHEN net_pnl > 0 THEN net_pnl END) as avg_win,
    AVG(CASE WHEN net_pnl <= 0 AND status = 'closed' THEN net_pnl END) as avg_loss,
    MAX(net_pnl) as best_trade,
    MIN(net_pnl) as worst_trade
FROM trading.trade_lifecycles
GROUP BY DATE_TRUNC('month', open_date)
ORDER BY month DESC;