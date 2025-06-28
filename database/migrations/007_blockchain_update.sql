-- Add blockchain preparation fields to trades table
ALTER TABLE trading.trades ADD COLUMN IF NOT EXISTS blockchain_hash VARCHAR(66);
ALTER TABLE trading.trades ADD COLUMN IF NOT EXISTS blockchain_tx_id VARCHAR(66);
ALTER TABLE trading.trades ADD COLUMN IF NOT EXISTS blockchain_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE trading.trades ADD COLUMN IF NOT EXISTS blockchain_timestamp TIMESTAMP WITH TIME ZONE;

-- Add index for blockchain status
CREATE INDEX IF NOT EXISTS idx_trades_blockchain_status ON trading.trades(blockchain_status);

-- Create analytics views for trade optimization

-- Daily performance summary
CREATE OR REPLACE VIEW trading.daily_performance AS
SELECT 
    DATE(entry_time) as trade_date,
    COUNT(*) as total_trades,
    COUNT(CASE WHEN status = 'closed' THEN 1 END) as closed_trades,
    COUNT(CASE WHEN status = 'open' THEN 1 END) as open_trades,
    COUNT(CASE WHEN exit_reason = 'expired' THEN 1 END) as expired_trades,
    COUNT(CASE WHEN exit_reason = 'stopped_out' THEN 1 END) as stopped_out_trades,
    COUNT(CASE WHEN exit_reason = 'take_profit' THEN 1 END) as take_profit_trades,
    SUM(CASE WHEN status = 'closed' THEN realized_pnl ELSE 0 END) as total_pnl,
    AVG(CASE WHEN status = 'closed' THEN realized_pnl END) as avg_pnl,
    MAX(CASE WHEN status = 'closed' THEN realized_pnl END) as best_trade,
    MIN(CASE WHEN status = 'closed' THEN realized_pnl END) as worst_trade,
    COUNT(CASE WHEN status = 'closed' AND realized_pnl > 0 THEN 1 END) as winning_trades,
    COUNT(CASE WHEN status = 'closed' AND realized_pnl <= 0 THEN 1 END) as losing_trades,
    CASE 
        WHEN COUNT(CASE WHEN status = 'closed' THEN 1 END) > 0 
        THEN ROUND(COUNT(CASE WHEN status = 'closed' AND realized_pnl > 0 THEN 1 END)::NUMERIC / 
                   COUNT(CASE WHEN status = 'closed' THEN 1 END) * 100, 2)
        ELSE 0 
    END as win_rate
FROM trading.trades
GROUP BY DATE(entry_time)
ORDER BY trade_date DESC;

-- Strike analysis for optimization
CREATE OR REPLACE VIEW trading.strike_analysis AS
SELECT 
    strike_price,
    option_type,
    COUNT(*) as trade_count,
    COUNT(CASE WHEN status = 'closed' THEN 1 END) as closed_count,
    AVG(CASE WHEN status = 'closed' THEN realized_pnl END) as avg_pnl,
    SUM(CASE WHEN status = 'closed' THEN realized_pnl ELSE 0 END) as total_pnl,
    COUNT(CASE WHEN exit_reason = 'stopped_out' THEN 1 END) as stop_outs,
    COUNT(CASE WHEN exit_reason = 'expired' THEN 1 END) as expirations,
    ROUND(AVG(CASE WHEN status = 'closed' THEN 
        EXTRACT(EPOCH FROM (exit_time - entry_time)) / 3600.0 
    END), 2) as avg_hold_hours
FROM trading.trades
GROUP BY strike_price, option_type
ORDER BY trade_count DESC;

-- Time of day analysis
CREATE OR REPLACE VIEW trading.time_analysis AS
SELECT 
    EXTRACT(HOUR FROM entry_time) as entry_hour,
    COUNT(*) as trade_count,
    AVG(CASE WHEN status = 'closed' THEN realized_pnl END) as avg_pnl,
    COUNT(CASE WHEN status = 'closed' AND realized_pnl > 0 THEN 1 END) as wins,
    COUNT(CASE WHEN status = 'closed' AND realized_pnl <= 0 THEN 1 END) as losses
FROM trading.trades
GROUP BY EXTRACT(HOUR FROM entry_time)
ORDER BY entry_hour;

-- Risk analysis view
CREATE OR REPLACE VIEW trading.risk_analysis AS
SELECT 
    option_type,
    AVG(stop_loss_price - entry_price) as avg_risk_per_contract,
    AVG(CASE WHEN exit_reason = 'stopped_out' THEN 
        (exit_price - entry_price) * quantity * 100 
    END) as avg_stop_loss_amount,
    COUNT(CASE WHEN exit_reason = 'stopped_out' THEN 1 END) as stop_count,
    COUNT(CASE WHEN exit_reason = 'take_profit' THEN 1 END) as tp_count,
    ROUND(COUNT(CASE WHEN exit_reason = 'stopped_out' THEN 1 END)::NUMERIC / 
          NULLIF(COUNT(CASE WHEN status = 'closed' THEN 1 END), 0) * 100, 2) as stop_rate
FROM trading.trades
GROUP BY option_type;