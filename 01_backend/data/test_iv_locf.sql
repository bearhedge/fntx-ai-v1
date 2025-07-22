-- Test the IV LOCF functionality for the $385 put
-- First, check raw IV data with NULLs
SELECT 
    '1. Raw IV data for $385 Put showing NULLs:' as test_description;

SELECT 
    o.datetime::time as time,
    o.close,
    o.volume,
    iv.implied_volatility as raw_iv,
    CASE 
        WHEN iv.implied_volatility IS NULL THEN 'NULL'
        ELSE iv.implied_volatility::varchar
    END as iv_display
FROM theta.options_contracts c
JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
LEFT JOIN theta.options_iv iv ON c.contract_id = iv.contract_id 
    AND o.datetime = iv.datetime
WHERE c.symbol = 'SPY' 
    AND c.expiration = '2023-01-03'
    AND c.strike = 385
    AND c.option_type = 'P'
    AND o.datetime::time BETWEEN '11:00:00' AND '11:30:00'
ORDER BY o.datetime;

-- Now test the LOCF view
SELECT 
    '',
    '2. LOCF view showing filled IV values:' as test_description;

SELECT 
    datetime::time as time,
    close,
    volume,
    raw_iv,
    iv_filled,
    is_iv_interpolated
FROM theta.options_data_filled
WHERE symbol = 'SPY' 
    AND expiration = '2023-01-03'
    AND strike = 385
    AND option_type = 'P'
    AND datetime::time BETWEEN '11:00:00' AND '11:30:00'
ORDER BY datetime;

-- Check IV coverage statistics
SELECT 
    '',
    '3. IV Coverage Summary:' as test_description;

SELECT 
    strike,
    option_type,
    total_bars,
    bars_with_iv,
    bars_without_iv,
    iv_coverage_pct,
    total_volume
FROM theta.iv_coverage_summary
WHERE expiration = '2023-01-03'
    AND strike BETWEEN 384 AND 386
ORDER BY strike, option_type;