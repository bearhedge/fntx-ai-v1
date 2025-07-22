-- Insert sample trades for testing the History tab
-- These represent typical SPY 0DTE options trades

-- Sample closed trades (with P&L)
INSERT INTO trading.trades (
    ibkr_order_id, ibkr_perm_id, symbol, strike_price, option_type,
    expiration, quantity, entry_time, entry_price, entry_commission,
    exit_time, exit_price, exit_commission, exit_reason, status,
    stop_loss_price, take_profit_price, market_snapshot
) VALUES 
-- Winning trade (expired worthless)
(
    1001, 2001, 'SPY', 605.00, 'PUT',
    '2025-06-25', 1, '2025-06-25 09:35:00-05:00', 0.45, 0.65,
    '2025-06-25 16:00:00-05:00', 0.01, 0.65, 'expired', 'closed',
    1.35, 0.22, '{"spy_price": 608.50, "vix_level": 12.5}'::jsonb
),
-- Stopped out trade
(
    1002, 2002, 'SPY', 610.00, 'CALL',
    '2025-06-24', 1, '2025-06-24 10:15:00-05:00', 0.55, 0.65,
    '2025-06-24 14:22:00-05:00', 1.65, 0.65, 'stopped_out', 'closed',
    1.65, 0.27, '{"spy_price": 607.80, "vix_level": 13.2}'::jsonb
),
-- Take profit trade
(
    1003, 2003, 'SPY', 602.00, 'PUT',
    '2025-06-23', 2, '2025-06-23 09:40:00-05:00', 0.68, 1.30,
    '2025-06-23 11:45:00-05:00', 0.34, 1.30, 'take_profit', 'closed',
    2.04, 0.34, '{"spy_price": 606.90, "vix_level": 11.8}'::jsonb
),
-- Manual exit trade
(
    1004, 2004, 'SPY', 608.00, 'CALL',
    '2025-06-23', 1, '2025-06-23 13:20:00-05:00', 0.42, 0.65,
    '2025-06-23 15:30:00-05:00', 0.25, 0.65, 'manual', 'closed',
    1.26, 0.21, '{"spy_price": 606.50, "vix_level": 12.1}'::jsonb
);

-- Sample open trades (currently active)
INSERT INTO trading.trades (
    ibkr_order_id, ibkr_perm_id, symbol, strike_price, option_type,
    expiration, quantity, entry_time, entry_price, entry_commission,
    status, stop_loss_price, take_profit_price, market_snapshot
) VALUES 
(
    1005, 2005, 'SPY', 604.00, 'PUT',
    '2025-06-26', 1, '2025-06-26 09:32:00-05:00', 0.52, 0.65,
    'open', 1.56, 0.26, '{"spy_price": 607.87, "vix_level": 12.3}'::jsonb
),
(
    1006, 2006, 'SPY', 611.00, 'CALL',
    '2025-06-26', 1, '2025-06-26 09:33:00-05:00', 0.48, 0.65,
    'open', 1.44, 0.24, '{"spy_price": 607.87, "vix_level": 12.3}'::jsonb
);