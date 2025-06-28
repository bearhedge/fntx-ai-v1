-- Enriched Views combining Trade Lifecycles with Historical Data
-- These views provide comprehensive trade analysis by joining real trades with market data

-- Drop existing views if they exist
DROP VIEW IF EXISTS trading.enriched_trades CASCADE;
DROP VIEW IF EXISTS trading.trade_context CASCADE;
DROP VIEW IF EXISTS ml.trade_features CASCADE;

-- Create ML schema if not exists
CREATE SCHEMA IF NOT EXISTS ml;

-- Enriched trades view with historical options data
CREATE OR REPLACE VIEW trading.enriched_trades AS
WITH trade_data AS (
    SELECT 
        tl.*,
        -- Calculate additional metrics
        CASE 
            WHEN tl.close_time IS NOT NULL THEN
                EXTRACT(EPOCH FROM (tl.close_time - tl.open_time)) / 3600.0
            ELSE 
                EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - tl.open_time)) / 3600.0
        END as actual_hours_held,
        -- Moneyness at entry
        CASE 
            WHEN tl.open_option_type = 'PUT' AND tl.spy_price_at_open > 0 THEN
                (tl.spy_price_at_open - tl.open_strike) / tl.spy_price_at_open
            WHEN tl.open_option_type = 'CALL' AND tl.spy_price_at_open > 0 THEN
                (tl.open_strike - tl.spy_price_at_open) / tl.spy_price_at_open
            ELSE 0
        END as moneyness_at_open
    FROM trading.trade_lifecycles tl
),
-- Get historical OHLC data for the contracts
historical_data AS (
    SELECT 
        oc.symbol,
        oc.strike,
        oc.option_type,
        oc.expiration,
        DATE(oh.datetime) as trade_date,
        MAX(oh.high) as day_high,
        MIN(oh.low) as day_low,
        AVG(oh.close - oh.open) as avg_price_change,
        SUM(oh.volume) as daily_volume,
        COUNT(*) as price_updates
    FROM theta.options_contracts oc
    JOIN theta.options_ohlc oh ON oc.contract_id = oh.contract_id
    GROUP BY oc.symbol, oc.strike, oc.option_type, oc.expiration, DATE(oh.datetime)
)
SELECT 
    td.*,
    -- Historical price data
    h_open.day_high as open_day_high,
    h_open.day_low as open_day_low,
    h_open.daily_volume as open_day_volume,
    h_close.day_high as close_day_high,
    h_close.day_low as close_day_low,
    h_close.daily_volume as close_day_volume,
    -- Price movement metrics
    CASE 
        WHEN h_open.day_high > 0 AND h_open.day_low > 0 THEN
            (h_open.day_high - h_open.day_low) / td.open_price
        ELSE NULL
    END as open_day_price_range_pct,
    -- Volume analysis
    CASE 
        WHEN h_open.daily_volume > 1000 THEN 'high_volume'
        WHEN h_open.daily_volume > 100 THEN 'normal_volume'
        ELSE 'low_volume'
    END as volume_regime
FROM trade_data td
LEFT JOIN historical_data h_open ON 
    h_open.symbol = td.symbol AND
    h_open.strike = td.open_strike AND
    h_open.option_type = LEFT(td.open_option_type, 1) AND
    h_open.expiration = td.open_expiration AND
    h_open.trade_date = td.open_date
LEFT JOIN historical_data h_close ON 
    h_close.symbol = td.symbol AND
    h_close.strike = td.open_strike AND
    h_close.option_type = LEFT(td.open_option_type, 1) AND
    h_close.expiration = td.open_expiration AND
    h_close.trade_date = td.close_date;

-- Trade context view - adds market regime and technical indicators
CREATE OR REPLACE VIEW trading.trade_context AS
SELECT 
    tl.*,
    -- Time-based features
    EXTRACT(hour FROM tl.open_time) as entry_hour,
    EXTRACT(dow FROM tl.open_date) as day_of_week,
    CASE 
        WHEN EXTRACT(hour FROM tl.open_time) < 10 THEN 'opening'
        WHEN EXTRACT(hour FROM tl.open_time) >= 15 THEN 'closing'
        ELSE 'midday'
    END as session_period,
    -- Market regime classification
    CASE 
        WHEN tl.vix_at_open < 15 THEN 'low_vol'
        WHEN tl.vix_at_open < 20 THEN 'normal_vol'
        WHEN tl.vix_at_open < 30 THEN 'high_vol'
        ELSE 'extreme_vol'
    END as vix_regime,
    -- P&L analysis
    CASE 
        WHEN tl.net_pnl > 0 THEN 'winner'
        WHEN tl.net_pnl < 0 THEN 'loser'
        WHEN tl.net_pnl = 0 THEN 'breakeven'
        ELSE 'open'
    END as trade_outcome,
    -- Risk metrics
    CASE 
        WHEN tl.open_quantity > 1 THEN 'multi_contract'
        ELSE 'single_contract'
    END as position_size_type,
    -- Days to expiration buckets
    CASE 
        WHEN tl.dte_at_open = 0 THEN '0dte'
        WHEN tl.dte_at_open <= 7 THEN 'weekly'
        WHEN tl.dte_at_open <= 30 THEN 'monthly'
        ELSE 'long_dated'
    END as dte_bucket
FROM trading.trade_lifecycles tl;

-- ML-ready feature engineering view
CREATE OR REPLACE VIEW ml.trade_features AS
SELECT 
    -- Target variable
    CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END as is_profitable,
    net_pnl as profit_loss,
    
    -- Trade characteristics
    open_option_type,
    open_quantity,
    
    -- Time features
    EXTRACT(hour FROM open_time) as entry_hour,
    EXTRACT(dow FROM open_date) as day_of_week,
    EXTRACT(month FROM open_date) as month,
    dte_at_open,
    
    -- Price features
    open_price,
    open_strike,
    CASE 
        WHEN spy_price_at_open > 0 THEN open_strike / spy_price_at_open 
        ELSE NULL 
    END as strike_to_spot_ratio,
    
    -- Moneyness
    CASE 
        WHEN open_option_type = 'PUT' AND spy_price_at_open > 0 THEN
            (spy_price_at_open - open_strike) / spy_price_at_open
        WHEN open_option_type = 'CALL' AND spy_price_at_open > 0 THEN
            (open_strike - spy_price_at_open) / spy_price_at_open
        ELSE NULL
    END as moneyness,
    
    -- Greeks (when available)
    open_delta,
    open_gamma,
    open_theta,
    open_vega,
    open_iv,
    
    -- Market context
    spy_price_at_open,
    vix_at_open,
    CASE 
        WHEN vix_at_open > 0 AND open_iv > 0 THEN open_iv / vix_at_open
        ELSE NULL
    END as iv_to_vix_ratio,
    
    -- Risk features
    CASE 
        WHEN max_risk > 0 THEN (open_price * open_quantity * 100) / max_risk
        ELSE NULL
    END as premium_to_risk_ratio,
    
    -- Outcome features (for closed trades)
    days_in_trade,
    hours_held,
    close_reason,
    pnl_percentage
FROM trading.trade_lifecycles
WHERE status = 'closed'  -- Only use completed trades for training
ORDER BY open_date;

-- Performance by market condition
CREATE OR REPLACE VIEW trading.performance_by_regime AS
SELECT 
    market_regime,
    COUNT(*) as trade_count,
    AVG(net_pnl) as avg_pnl,
    SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) as winners,
    SUM(CASE WHEN net_pnl <= 0 THEN 1 ELSE 0 END) as losers,
    ROUND(SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END)::NUMERIC / 
          COUNT(*)::NUMERIC * 100, 2) as win_rate
FROM trading.trade_lifecycles
WHERE status = 'closed' AND market_regime IS NOT NULL
GROUP BY market_regime;

-- Grant permissions
GRANT SELECT ON ALL TABLES IN SCHEMA trading TO info;
GRANT SELECT ON ALL TABLES IN SCHEMA ml TO info;