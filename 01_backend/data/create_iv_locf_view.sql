-- Create view with Last Observation Carried Forward (LOCF) for IV gaps
CREATE OR REPLACE VIEW theta.options_data_filled AS
WITH iv_with_gaps AS (
    SELECT 
        c.contract_id,
        c.symbol,
        c.expiration,
        c.strike,
        c.option_type,
        o.datetime,
        o.open,
        o.high,
        o.low,
        o.close,
        o.volume,
        o.trade_count,
        g.delta,
        g.gamma,
        g.theta AS greeks_theta,
        g.vega,
        g.rho,
        iv.implied_volatility as raw_iv,
        -- Create groups for LOCF by marking when a non-null IV appears
        SUM(CASE WHEN iv.implied_volatility IS NOT NULL THEN 1 ELSE 0 END) 
            OVER (PARTITION BY c.contract_id ORDER BY o.datetime) as iv_group
    FROM theta.options_contracts c
    JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
    LEFT JOIN theta.options_greeks g ON c.contract_id = g.contract_id 
        AND o.datetime = g.datetime
    LEFT JOIN theta.options_iv iv ON c.contract_id = iv.contract_id 
        AND o.datetime = iv.datetime
)
SELECT 
    contract_id,
    symbol,
    expiration,
    strike,
    option_type,
    datetime,
    open,
    high,
    low,
    close,
    volume,
    trade_count,
    delta,
    gamma,
    greeks_theta,
    vega,
    rho,
    raw_iv,
    -- LOCF: Use the first non-null IV within each group
    FIRST_VALUE(raw_iv) OVER (
        PARTITION BY contract_id, iv_group 
        ORDER BY datetime
    ) as iv_filled,
    -- Track if this IV was interpolated
    CASE 
        WHEN raw_iv IS NULL AND iv_group > 0 THEN TRUE
        ELSE FALSE
    END as is_iv_interpolated
FROM iv_with_gaps
ORDER BY contract_id, datetime;

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_options_data_filled_lookup 
ON theta.options_ohlc(contract_id, datetime);

-- Add helpful comments
COMMENT ON VIEW theta.options_data_filled IS 
'Complete options data with IV gaps filled using Last Observation Carried Forward (LOCF)';

COMMENT ON COLUMN theta.options_data_filled.raw_iv IS 
'Original IV from API (may be NULL)';

COMMENT ON COLUMN theta.options_data_filled.iv_filled IS 
'IV with gaps filled using LOCF';

COMMENT ON COLUMN theta.options_data_filled.is_iv_interpolated IS 
'TRUE if iv_filled is interpolated, FALSE if original';

-- Create summary view for IV coverage statistics
CREATE OR REPLACE VIEW theta.iv_coverage_summary AS
SELECT 
    c.expiration,
    c.strike,
    c.option_type,
    COUNT(*) as total_bars,
    COUNT(iv.implied_volatility) as bars_with_iv,
    COUNT(*) - COUNT(iv.implied_volatility) as bars_without_iv,
    ROUND(COUNT(iv.implied_volatility)::numeric / COUNT(*) * 100, 1) as iv_coverage_pct,
    MIN(o.datetime) as first_bar,
    MAX(o.datetime) as last_bar,
    SUM(o.volume) as total_volume
FROM theta.options_contracts c
JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
LEFT JOIN theta.options_iv iv ON c.contract_id = iv.contract_id 
    AND o.datetime = iv.datetime
WHERE c.symbol = 'SPY'
GROUP BY c.contract_id, c.expiration, c.strike, c.option_type
ORDER BY c.expiration, c.strike, c.option_type;

COMMENT ON VIEW theta.iv_coverage_summary IS 
'Summary of IV data coverage by contract';